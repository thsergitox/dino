"""Audio recording over PipeWire (`pw-record`).

Push-to-talk model:
  * `start()` spawns `pw-record` detached, writes its PID to a lock file, and returns.
  * `stop()` reads the lock file, signals the process, waits for the WAV to flush,
    and returns the path to the recorded audio.

Two separate CLI invocations (one for press, one for release) share state through
the lock file in the runtime directory.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


class RecorderError(RuntimeError):
    """Raised when recording cannot start or stop cleanly."""


@dataclass(frozen=True)
class Recorder:
    runtime_dir: Path
    sample_rate: int = 16000
    channels: int = 1

    @property
    def pid_file(self) -> Path:
        return self.runtime_dir / "recorder.pid"

    @property
    def wav_pointer_file(self) -> Path:
        """Sidecar that remembers which UUID-named WAV the latest run wrote to."""
        return self.runtime_dir / "recorder.wav-path"

    def is_recording(self) -> bool:
        pid = self._read_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # Stale PID file — clean it up.
            self.pid_file.unlink(missing_ok=True)
            return False
        except PermissionError:
            return True

    def start(self) -> None:
        if shutil.which("pw-record") is None:
            raise RecorderError(
                "pw-record not found. Install PipeWire utilities (package `pipewire` "
                "on Arch, `pipewire-bin` on Debian/Ubuntu)."
            )

        if self.is_recording():
            raise RecorderError("Already recording — ignoring duplicate start.")

        wav_path = self.runtime_dir / f"recording-{uuid.uuid4().hex[:8]}.wav"

        cmd = [
            "pw-record",
            "--rate", str(self.sample_rate),
            "--channels", str(self.channels),
            "--format", "s16",
            str(wav_path),
        ]
        # start_new_session=True detaches from this process group so the recorder
        # survives the calling CLI exiting (Hyprland fires-and-forgets the bind).
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.pid_file.write_text(str(proc.pid))
        self.wav_pointer_file.write_text(str(wav_path))

    def stop(self, *, timeout: float = 2.0) -> Path:
        pid = self._read_pid()
        if pid is None:
            raise RecorderError("No recording in progress.")

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self.pid_file.unlink(missing_ok=True)
            raise RecorderError("Recorder process vanished before stop.") from None

        # Wait for pw-record to flush the WAV header on disk.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            # Last-resort kill if it refused to exit.
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        self.pid_file.unlink(missing_ok=True)

        wav_path = self._read_wav_pointer()
        if wav_path is None or not wav_path.is_file() or wav_path.stat().st_size < 44:
            raise RecorderError("Recording produced no audio (empty WAV).")
        return wav_path

    def _read_pid(self) -> int | None:
        if not self.pid_file.is_file():
            return None
        try:
            return int(self.pid_file.read_text().strip())
        except ValueError:
            self.pid_file.unlink(missing_ok=True)
            return None

    def _read_wav_pointer(self) -> Path | None:
        if not self.wav_pointer_file.is_file():
            return None
        path = Path(self.wav_pointer_file.read_text().strip())
        self.wav_pointer_file.unlink(missing_ok=True)
        return path
