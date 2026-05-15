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
    def wav_file(self) -> Path:
        return self.runtime_dir / "recording.wav"

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

        # Fresh WAV every run.
        self.wav_file.unlink(missing_ok=True)

        cmd = [
            "pw-record",
            "--rate", str(self.sample_rate),
            "--channels", str(self.channels),
            "--format", "s16",
            str(self.wav_file),
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

        if not self.wav_file.is_file() or self.wav_file.stat().st_size < 44:
            raise RecorderError("Recording produced no audio (empty WAV).")
        return self.wav_file

    def _read_pid(self) -> int | None:
        if not self.pid_file.is_file():
            return None
        try:
            return int(self.pid_file.read_text().strip())
        except ValueError:
            self.pid_file.unlink(missing_ok=True)
            return None
