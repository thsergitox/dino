"""Async PCM streaming recorder over `pw-record`.

Pipeline:
    pw-record --raw -  →  stdout (s16le @ 16 kHz mono)
                              │
                              ▼
                  StreamingRecorder.run()
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
        chunk_queue (asyncio.Queue)   wav_buffer (bytearray)
        for the FFT visualizer        finalized to WAV on stop()

The recorder is **shared single-source**: it reads pw-record's stdout once and
fans the chunks out. The visualizer is allowed to drop frames if it falls
behind; the WAV is always lossless because it is fed from the same chunks.
"""

from __future__ import annotations

import asyncio
import shutil
import struct
import uuid
from dataclasses import dataclass, field
from pathlib import Path


class StreamingRecorderError(RuntimeError):
    """Raised when streaming capture cannot start or stop cleanly."""


CHUNK_FRAMES = 1024       # samples per chunk
SAMPLE_BYTES = 2          # s16le
DEFAULT_RATE = 16000
DEFAULT_CHANNELS = 1
_CHUNK_BYTES = CHUNK_FRAMES * SAMPLE_BYTES  # mono only here

# Drop-oldest behavior: cap the visualizer queue so a slow UI never blocks audio.
_VIS_QUEUE_MAX = 8

# How long we wait after SIGTERM before SIGKILL.
_STOP_GRACE_S = 2.0

# If pw-record exits within this window, treat it as "couldn't open the mic".
_STARTUP_FAIL_WINDOW_S = 0.2


@dataclass
class StreamingRecorder:
    runtime_dir: Path
    sample_rate: int = DEFAULT_RATE
    channels: int = DEFAULT_CHANNELS

    chunk_queue: asyncio.Queue[bytes] = field(default_factory=lambda: asyncio.Queue(_VIS_QUEUE_MAX))
    _wav_buffer: bytearray = field(default_factory=bytearray)
    _proc: asyncio.subprocess.Process | None = None
    _reader_task: asyncio.Task | None = None
    _wav_path: Path | None = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> None:
        if shutil.which("pw-record") is None:
            raise StreamingRecorderError(
                "pw-record not found. Install PipeWire utilities."
            )
        if self.is_running:
            raise StreamingRecorderError("Already recording.")

        self._wav_buffer.clear()
        # Drain any leftover frames from a previous run.
        while not self.chunk_queue.empty():
            self.chunk_queue.get_nowait()

        self._wav_path = self.runtime_dir / f"recording-{uuid.uuid4().hex[:8]}.wav"

        self._proc = await asyncio.create_subprocess_exec(
            "pw-record",
            "--raw",
            "--rate", str(self.sample_rate),
            "--channels", str(self.channels),
            "--format", "s16",
            "-",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Detect "couldn't open mic" by watching for an early exit.
        await asyncio.sleep(_STARTUP_FAIL_WINDOW_S)
        if self._proc.returncode is not None:
            self._proc = None
            raise StreamingRecorderError(
                "pw-record exited immediately — likely no microphone available."
            )

        self._reader_task = asyncio.create_task(self._reader_loop())

    async def stop(self) -> Path:
        if self._proc is None:
            raise StreamingRecorderError("Not recording.")

        proc = self._proc
        try:
            proc.terminate()
        except ProcessLookupError:
            pass

        try:
            await asyncio.wait_for(proc.wait(), timeout=_STOP_GRACE_S)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

        if self._reader_task is not None:
            try:
                await asyncio.wait_for(self._reader_task, timeout=0.5)
            except asyncio.TimeoutError:
                self._reader_task.cancel()
            self._reader_task = None

        self._proc = None

        if not self._wav_buffer:
            raise StreamingRecorderError("Recording came out empty.")

        assert self._wav_path is not None
        path = self._wav_path
        path.write_bytes(self._build_wav(bytes(self._wav_buffer)))
        return path

    async def cancel(self) -> None:
        """Abort and discard whatever was captured."""
        if self._proc is None:
            return
        try:
            self._proc.kill()
            await self._proc.wait()
        except ProcessLookupError:
            pass
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None
        self._proc = None
        self._wav_buffer.clear()
        if self._wav_path is not None and self._wav_path.is_file():
            self._wav_path.unlink(missing_ok=True)
        self._wav_path = None

    async def _reader_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        stdout = self._proc.stdout
        try:
            while True:
                chunk = await stdout.readexactly(_CHUNK_BYTES)
                self._wav_buffer.extend(chunk)
                self._enqueue_drop_oldest(chunk)
        except asyncio.IncompleteReadError as exc:
            # Stream ended (pw-record exited). Persist whatever partial bytes we got.
            if exc.partial:
                self._wav_buffer.extend(exc.partial)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Surface nothing here — stop() will report empty WAV if it matters.
            pass

    def _enqueue_drop_oldest(self, chunk: bytes) -> None:
        try:
            self.chunk_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            try:
                self.chunk_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self.chunk_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                pass

    def _build_wav(self, pcm: bytes) -> bytes:
        """Prepend a 44-byte RIFF header for mono s16le @ sample_rate."""
        byte_rate = self.sample_rate * self.channels * SAMPLE_BYTES
        block_align = self.channels * SAMPLE_BYTES
        data_size = len(pcm)
        riff_size = 36 + data_size
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", riff_size, b"WAVE",
            b"fmt ", 16, 1, self.channels,
            self.sample_rate, byte_rate, block_align, 16,
            b"data", data_size,
        )
        return header + pcm
