"""StreamingRecorder unit tests — synthetic PCM via a fake subprocess.

We don't spawn `pw-record`; we monkey-patch `asyncio.create_subprocess_exec`
to return a fake process whose stdout yields known PCM bytes, and verify the
WAV header + chunk-queue fan-out behaviour.
"""

from __future__ import annotations

import asyncio
import struct
from pathlib import Path

import pytest

from dino.audio.streaming import (
    CHUNK_FRAMES,
    SAMPLE_BYTES,
    StreamingRecorder,
    StreamingRecorderError,
)


class _FakeStdout:
    def __init__(self, pcm: bytes):
        self._buf = pcm
        self._pos = 0

    async def readexactly(self, n: int) -> bytes:
        if self._pos + n > len(self._buf):
            partial = self._buf[self._pos:]
            self._pos = len(self._buf)
            raise asyncio.IncompleteReadError(partial=partial, expected=n)
        chunk = self._buf[self._pos:self._pos + n]
        self._pos += n
        return chunk


class _FakeProc:
    def __init__(self, pcm: bytes):
        self.stdout = _FakeStdout(pcm)
        self.returncode: int | None = None
        self._terminated = asyncio.Event()

    def terminate(self):
        self.returncode = 0
        self._terminated.set()

    def kill(self):
        self.returncode = -9
        self._terminated.set()

    async def wait(self):
        await self._terminated.wait()
        return self.returncode


@pytest.fixture
def runtime_dir(tmp_path: Path) -> Path:
    return tmp_path


def _synthetic_pcm(num_chunks: int) -> bytes:
    """Pure-tone-ish PCM, just non-zero bytes; we don't verify audio content."""
    return b"".join(
        struct.pack("<h", (i * 37) & 0x7FFF) * CHUNK_FRAMES
        for i in range(num_chunks)
    )


@pytest.mark.asyncio
async def test_stop_writes_valid_wav(monkeypatch, runtime_dir: Path):
    pcm = _synthetic_pcm(num_chunks=3)
    proc = _FakeProc(pcm)

    async def fake_exec(*args, **kwargs):
        return proc

    monkeypatch.setattr("dino.audio.streaming.shutil.which", lambda _: "/usr/bin/pw-record")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    rec = StreamingRecorder(runtime_dir=runtime_dir)
    await rec.start()
    # Let the reader drain the fake stdout.
    await asyncio.sleep(0.05)

    wav_path = await rec.stop()
    assert wav_path.is_file()
    data = wav_path.read_bytes()
    # RIFF header sanity.
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    # Body is exactly the PCM we fed.
    assert data[44:] == pcm[: 3 * CHUNK_FRAMES * SAMPLE_BYTES]


@pytest.mark.asyncio
async def test_cancel_discards_and_removes_wav(monkeypatch, runtime_dir: Path):
    proc = _FakeProc(_synthetic_pcm(1))

    async def fake_exec(*args, **kwargs):
        return proc

    monkeypatch.setattr("dino.audio.streaming.shutil.which", lambda _: "/usr/bin/pw-record")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    rec = StreamingRecorder(runtime_dir=runtime_dir)
    await rec.start()
    await rec.cancel()

    # No partial WAVs from this run should be left behind.
    assert not list(runtime_dir.glob("recording-*.wav"))


@pytest.mark.asyncio
async def test_stop_without_start_raises(runtime_dir: Path):
    rec = StreamingRecorder(runtime_dir=runtime_dir)
    with pytest.raises(StreamingRecorderError):
        await rec.stop()
