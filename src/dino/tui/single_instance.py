"""Single-instance enforcement via `fcntl.flock`.

The lock file lives at `$XDG_RUNTIME_DIR/dino/tui.pid`. Lock is held for the
lifetime of the process and released automatically when the file descriptor
closes (i.e. when dino exits, even on crash).

If acquisition fails because another instance owns the lock, we try to bring
the existing scratchpad forward via `hyprctl dispatch togglespecialworkspace
dino` so the user's hotkey-equivalent action still happens.
"""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class AlreadyRunningError(RuntimeError):
    """Another dino instance owns the lock."""


@dataclass
class SingleInstanceLock:
    runtime_dir: Path
    _fd: int | None = None

    @property
    def pid_file(self) -> Path:
        return self.runtime_dir / "tui.pid"

    def acquire(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.pid_file, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            self._try_bring_forward()
            raise AlreadyRunningError("Another dino instance is running.") from exc

        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            self.pid_file.unlink(missing_ok=True)

    @staticmethod
    def _try_bring_forward() -> None:
        if shutil.which("hyprctl") is None:
            return
        try:
            subprocess.run(
                ["hyprctl", "dispatch", "togglespecialworkspace", "dino"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
