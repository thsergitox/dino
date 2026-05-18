"""FFT spectrum visualizer.

Reads PCM chunks from an `asyncio.Queue` (fed by `StreamingRecorder`), runs a
windowed FFT, log-spaces the magnitudes into ``bar_count`` bins, and renders
them as a vertical bar chart using Unicode block characters.

Rendering is driven by Textual's `Static` widget + a worker task. The widget
re-renders at ~30 FPS while recording and goes idle otherwise.
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

import numpy as np
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from dino.audio.streaming import StreamingRecorder

_BLOCKS = " ▁▂▃▄▅▆▇█"  # 0–8 fill levels
_TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / _TARGET_FPS
_MIN_BARS = 8
_MAX_BARS_PER_WIDTH = 2  # one bar every two columns


class SpectrumWidget(Static):
    """Multi-bar FFT visualizer. Active only while `recording` is True."""

    bars: reactive[tuple[int, ...]] = reactive(())
    recording: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    SpectrumWidget {
        height: 100%;
        width: 100%;
        content-align: center middle;
        color: $accent;
    }
    """

    def __init__(
        self,
        recorder: "StreamingRecorder | None" = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._recorder: "StreamingRecorder | None" = recorder
        self._worker: asyncio.Task | None = None

    # ── Public API ──────────────────────────────────────────────────────────

    def attach_recorder(self, recorder: "StreamingRecorder") -> None:
        self._recorder = recorder

    def start(self) -> None:
        if self._worker is not None and not self._worker.done():
            return
        self.recording = True
        self._worker = asyncio.create_task(self._consume_loop())

    def stop(self) -> None:
        self.recording = False
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        self.bars = ()

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def on_unmount(self) -> None:
        self.stop()

    # ── Reactive watchers ──────────────────────────────────────────────────

    def watch_bars(self, _old: tuple[int, ...], _new: tuple[int, ...]) -> None:
        self.refresh()

    def watch_recording(self, _old: bool, _new: bool) -> None:
        self.refresh()

    # ── Rendering ──────────────────────────────────────────────────────────

    def render(self) -> Text:
        if not self.recording or not self.bars:
            return Text("· · · · · · ·", style="dim")
        height = max(1, self.size.height - 1)
        rows: list[str] = []
        for row in range(height, 0, -1):
            threshold = row / height
            line_chars: list[str] = []
            for bar in self.bars:
                norm = bar / 100.0
                if norm >= threshold:
                    line_chars.append("█")
                else:
                    # partial fill on the topmost row only
                    delta = norm - (threshold - 1.0 / height)
                    if 0 < delta < 1.0 / height:
                        idx = int(delta * height * (len(_BLOCKS) - 1))
                        line_chars.append(_BLOCKS[max(0, min(len(_BLOCKS) - 1, idx))])
                    else:
                        line_chars.append(" ")
            rows.append(" ".join(line_chars))
        return Text("\n".join(rows), style="bold cyan")

    # ── Consumer task ──────────────────────────────────────────────────────

    async def _consume_loop(self) -> None:
        recorder = self._recorder
        if recorder is None:
            return
        loop = asyncio.get_running_loop()
        next_tick = loop.time()
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        recorder.chunk_queue.get(),
                        timeout=_FRAME_INTERVAL * 2,
                    )
                except asyncio.TimeoutError:
                    # No data — keep last bars, just throttle.
                    await asyncio.sleep(_FRAME_INTERVAL)
                    continue

                bars = self._chunk_to_bars(chunk)
                self.bars = bars

                next_tick += _FRAME_INTERVAL
                sleep = next_tick - loop.time()
                if sleep > 0:
                    await asyncio.sleep(sleep)
                else:
                    next_tick = loop.time()  # we fell behind; resync
        except asyncio.CancelledError:
            raise

    # ── Pure math ───────────────────────────────────────────────────────────

    def _bar_count(self) -> int:
        width = max(1, self.size.width)
        return max(_MIN_BARS, width // _MAX_BARS_PER_WIDTH)

    def _chunk_to_bars(self, chunk: bytes) -> tuple[int, ...]:
        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size == 0:
            return ()
        windowed = samples * np.hanning(samples.size)
        spectrum = np.abs(np.fft.rfft(windowed))
        if spectrum.size == 0 or not np.any(spectrum):
            return tuple(0 for _ in range(self._bar_count()))

        # Log-space bin edges across the FFT bins.
        n_bars = self._bar_count()
        bins = spectrum.size
        # +1 so we avoid log(0); start at bin 1 so we skip DC.
        edges = np.logspace(0, math.log10(bins), num=n_bars + 1).astype(int)
        edges = np.clip(edges, 1, bins)

        bars: list[int] = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=False):
            if hi <= lo:
                hi = lo + 1
            band = spectrum[lo:hi]
            magnitude = float(band.mean()) if band.size else 0.0
            # Normalize empirically — speech in normal range peaks around 20-40.
            scaled = int(min(100, magnitude * 4))
            bars.append(scaled)
        return tuple(bars)
