"""Wayland text injection via `wtype`."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from dino.output.base import TextOutputError


@dataclass(frozen=True)
class WtypeOutput:
    def type(self, text: str) -> None:
        if not text:
            return
        if shutil.which("wtype") is None:
            raise TextOutputError(
                "wtype not found. Install it (`pacman -S wtype` on Arch, "
                "`apt install wtype` on Debian/Ubuntu)."
            )
        # `--` ends option parsing so text starting with `-` is not misread as a flag.
        result = subprocess.run(
            ["wtype", "--", text],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise TextOutputError(
                f"wtype failed (exit {result.returncode}): {result.stderr.strip()}"
            )
