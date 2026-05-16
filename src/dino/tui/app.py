"""dino TUI — Textual app.

State machine:
    IDLE → RECORDING → TRANSCRIBING → CLIPBOARDING → IDLE
                              │
                              └── error → ERROR → IDLE

Concurrency:
    `StreamingRecorder` runs `pw-record --raw -` in an asyncio subprocess;
    its stdout reader fans chunks into (a) `SpectrumWidget`'s queue at ~30 FPS
    and (b) an in-memory WAV buffer.

    Transcription runs in a worker via `asyncio.to_thread` so the sync
    `requests.post` call does not block the UI event loop.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Label

from dino import __version__
from dino.audio import StreamingRecorder, StreamingRecorderError
from dino.config import Config
from dino.i18n import set_lang, t
from dino.output import TextOutputError
from dino.output import build as build_output
from dino.stt import OpenAIWhisper, TranscriberError
from dino.tui.state import AppState, can_transition
from dino.tui.widgets import FooterHints, HistoryLog, SpectrumWidget, StatusLabel

if TYPE_CHECKING:
    from dino.output.base import TextOutput


class DinoApp(App):
    """Persistent voice-dictation TUI."""

    CSS_PATH = "styles.tcss"
    TITLE = "dino"

    BINDINGS = [
        Binding("space", "toggle_recording", "Grabar / Detener", priority=True),
        Binding("escape", "cancel", "Cancelar"),
        Binding("q", "quit", "Salir"),
        Binding("c", "clear_history", "Limpiar"),
        Binding("r", "retry", "Reintentar"),
    ]

    state: reactive[AppState] = reactive(AppState.IDLE)

    def __init__(self, config: Config, *, lang: str | None = None):
        super().__init__()
        set_lang(lang or config.tui_language)
        self._config = config
        self._recorder = StreamingRecorder(
            runtime_dir=config.runtime_dir,
            sample_rate=config.sample_rate,
            channels=config.channels,
        )
        self._transcriber = OpenAIWhisper(
            api_key=config.api_key,
            model=config.model,
            language=config.language,
            prompt=config.prompt,
        )
        self._output: "TextOutput" = build_output(config.output_adapter)
        self._last_wav: Path | None = None
        self._last_error_msg: str | None = None

    # ── Layout ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="container"):
            yield Label(f"  dino v{__version__}", id="title")
            yield Label(t("banner.no_hyprland"), id="hyprland-notice")
            yield StatusLabel(id="status")
            yield SpectrumWidget(self._recorder, id="spectrum")
            yield HistoryLog(id="history")
            yield FooterHints(id="footer")

    def on_mount(self) -> None:
        if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            notice = self.query_one("#hyprland-notice")
            notice.add_class("-visible")
        self._render_state()

    # ── State changes ───────────────────────────────────────────────────────

    def watch_state(self, _old: AppState, _new: AppState) -> None:
        self._render_state()

    def _set_state(self, new: AppState) -> None:
        if not can_transition(self.state, new):
            return
        self.state = new

    def _render_state(self) -> None:
        status: StatusLabel = self.query_one("#status", StatusLabel)
        footer: FooterHints = self.query_one("#footer", FooterHints)
        spectrum: SpectrumWidget = self.query_one("#spectrum", SpectrumWidget)

        if self.state == AppState.IDLE:
            status.set_status("status.idle", tone="cyan")
            footer.set_key("footer.idle")
            spectrum.stop()
        elif self.state == AppState.RECORDING:
            status.set_status("status.listening", tone="bright_red")
            footer.set_key("footer.recording")
            spectrum.start()
        elif self.state == AppState.TRANSCRIBING:
            status.set_status("status.transcribing", tone="yellow")
            footer.set_key("footer.transcribing")
            spectrum.stop()
        elif self.state == AppState.CLIPBOARDING:
            status.set_status("status.copied", tone="green")
            footer.set_key("footer.idle")
        elif self.state == AppState.ERROR:
            status.set_status("status.error", tone="bright_red", msg=self._last_error_msg or "")
            footer.set_key("footer.error")
            spectrum.stop()

    # ── Actions (key bindings) ──────────────────────────────────────────────

    async def action_toggle_recording(self) -> None:
        if self.state == AppState.IDLE:
            await self._start_recording()
        elif self.state == AppState.RECORDING:
            await self._stop_and_transcribe()

    async def action_cancel(self) -> None:
        if self.state == AppState.RECORDING:
            await self._recorder.cancel()
            self._set_state(AppState.IDLE)
        elif self.state == AppState.TRANSCRIBING:
            # The to_thread task can't really be interrupted; we just flip state
            # and ignore the late result.
            self._set_state(AppState.IDLE)
        elif self.state == AppState.ERROR:
            self._set_state(AppState.IDLE)

    async def action_retry(self) -> None:
        if self.state == AppState.ERROR and self._last_wav is not None:
            await self._transcribe_path(self._last_wav)

    def action_clear_history(self) -> None:
        if self.state in (AppState.IDLE, AppState.ERROR):
            history: HistoryLog = self.query_one("#history", HistoryLog)
            history.clear_all()

    # ── Internal flow ───────────────────────────────────────────────────────

    async def _start_recording(self) -> None:
        try:
            await self._recorder.start()
        except StreamingRecorderError as exc:
            self._fail(str(exc))
            return
        self._set_state(AppState.RECORDING)

    async def _stop_and_transcribe(self) -> None:
        try:
            wav_path = await self._recorder.stop()
        except StreamingRecorderError as exc:
            self._fail(str(exc))
            return
        self._last_wav = wav_path
        self._set_state(AppState.TRANSCRIBING)
        await self._transcribe_path(wav_path)

    async def _transcribe_path(self, wav_path: Path) -> None:
        try:
            text = await asyncio.to_thread(self._transcriber.transcribe, wav_path)
        except TranscriberError as exc:
            self._fail(t("error.api", msg=str(exc)))
            return

        text = text.strip()
        if not text:
            history: HistoryLog = self.query_one("#history", HistoryLog)
            self._set_state(AppState.IDLE)
            self.notify(t("status.no_speech"), timeout=2)
            return

        await self._copy_and_record(text)

    async def _copy_and_record(self, text: str) -> None:
        self._set_state(AppState.CLIPBOARDING)
        try:
            self._output.type(text)
        except TextOutputError as exc:
            self._fail(str(exc))
            return

        history: HistoryLog = self.query_one("#history", HistoryLog)
        history.append_transcript(text)

        await asyncio.sleep(1.2)
        self._set_state(AppState.IDLE)

    def _fail(self, msg: str) -> None:
        self._last_error_msg = msg
        self._set_state(AppState.ERROR)

    # ── Shutdown ────────────────────────────────────────────────────────────

    async def on_unmount(self) -> None:
        # Make sure pw-record dies with us.
        try:
            await self._recorder.cancel()
        except Exception:
            pass
