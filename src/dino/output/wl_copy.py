"""Wayland clipboard adapter via `wl-copy` (wl-clipboard).

`wl-copy` forks by default — once it has the text, dino can exit and the
clipboard contents survive until something else replaces them (or the Wayland
session ends). For full survival across sessions, recommend `wl-clip-persist`.

Implementation gotcha: `wl-copy` daemonizes a background child that holds the
clipboard. If you let it inherit stdout/stderr pipes from the parent (e.g. via
`capture_output=True`), `subprocess.run` waits for those pipes to close — and
the daemon keeps them open until the clipboard contents are replaced. That
blocks the event loop indefinitely. We redirect stdout/stderr to DEVNULL so
the run() call returns as soon as the parent process exits, ~milliseconds.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from dino.output.base import TextOutputError


@dataclass(frozen=True)
class WlCopyOutput:
    def type(self, text: str) -> None:
        if not text:
            return
        if shutil.which("wl-copy") is None:
            raise TextOutputError(
                "wl-copy not found. Install wl-clipboard "
                "(`pacman -S wl-clipboard` on Arch, `apt install wl-clipboard` on Debian/Ubuntu)."
            )
        # `--` ends option parsing so text starting with `-` is not misread as a flag.
        # DEVNULL on stdout/stderr is REQUIRED — see module docstring.
        result = subprocess.run(
            ["wl-copy", "--"],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise TextOutputError(f"wl-copy failed (exit {result.returncode})")
