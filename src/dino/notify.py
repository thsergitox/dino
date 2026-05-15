"""Thin wrapper over `notify-send`. Silently no-ops if the binary is missing."""

from __future__ import annotations

import shutil
import subprocess

_APP_NAME = "dino"
_AVAILABLE: bool | None = None


def _has_notify_send() -> bool:
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = shutil.which("notify-send") is not None
    return _AVAILABLE


def send(summary: str, body: str = "", *, urgency: str = "low", timeout_ms: int = 2000) -> None:
    if not _has_notify_send():
        return
    cmd = [
        "notify-send",
        "--app-name", _APP_NAME,
        "--urgency", urgency,
        "--expire-time", str(timeout_ms),
        summary,
    ]
    if body:
        cmd.append(body)
    subprocess.run(cmd, check=False)
