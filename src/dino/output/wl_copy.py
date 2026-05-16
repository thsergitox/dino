"""Wayland clipboard adapter via `wl-copy` (wl-clipboard).

`wl-copy` forks by default — once it has the text, dino can exit and the
clipboard contents survive until something else replaces them (or the Wayland
session ends). For full survival across sessions, recommend `wl-clip-persist`.
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
        result = subprocess.run(
            ["wl-copy", "--"],
            input=text,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise TextOutputError(
                f"wl-copy failed (exit {result.returncode}): {result.stderr.strip()}"
            )
