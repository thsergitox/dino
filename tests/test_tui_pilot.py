"""Headless Textual integration — drive state transitions via Pilot.

We mock the recorder, transcriber, and output so the test doesn't touch the
microphone, network, or clipboard. Only the state machine + UI plumbing run.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from dino.config import Config
from dino.tui.app import DinoApp
from dino.tui.state import AppState


class _StubRecorder:
    def __init__(self, *, runtime_dir: Path, sample_rate: int = 16000, channels: int = 1):
        self.runtime_dir = runtime_dir
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_queue: asyncio.Queue[bytes] = asyncio.Queue(8)
        self._wav_path = runtime_dir / "recording-stub.wav"
        self._wav_path.write_bytes(b"RIFF" + b"\0" * 40)

    async def start(self) -> None:
        return None

    async def stop(self) -> Path:
        return self._wav_path

    async def cancel(self) -> None:
        return None


class _StubTranscriber:
    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, _wav_path) -> str:
        return "hola mundo"


class _StubOutput:
    def __init__(self):
        self.received: list[str] = []

    def type(self, text: str) -> None:
        self.received.append(text)


@pytest.fixture
def stub_config(tmp_path: Path) -> Config:
    return Config(
        api_key="sk-test",
        model="whisper-1",
        language="es",
        prompt=None,
        sample_rate=16000,
        channels=1,
        runtime_dir=tmp_path,
        tui_language="es",
        tui_lifecycle="exec-once",
        tui_terminal=None,
        output_adapter="wl-copy",
    )


@pytest.mark.asyncio
async def test_idle_to_recording_to_idle(monkeypatch, stub_config: Config):
    monkeypatch.setattr("dino.tui.app.StreamingRecorder", _StubRecorder)
    monkeypatch.setattr("dino.tui.app.OpenAIWhisper", _StubTranscriber)

    stub_output = _StubOutput()
    monkeypatch.setattr("dino.tui.app.build_output", lambda _adapter: stub_output)

    app = DinoApp(stub_config)
    async with app.run_test() as pilot:
        assert app.state == AppState.IDLE

        await pilot.press("space")
        await pilot.pause()
        assert app.state == AppState.RECORDING

        await pilot.press("space")
        # Give the to_thread transcription a moment to resolve.
        await pilot.pause()
        await asyncio.sleep(0.05)
        await pilot.pause()

        assert stub_output.received == ["hola mundo"]
        # CLIPBOARDING auto-advances back to IDLE after ~1.2s; we don't wait
        # that long in the unit test — checking we passed *through* it is fine.
        assert app.state in (AppState.IDLE, AppState.CLIPBOARDING)
