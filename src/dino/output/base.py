"""Port for text-output methods.

Concrete adapters (wtype for Wayland, xdotool for X11, wl-copy fallback, etc.)
implement this interface so the rest of the system stays compositor-agnostic.
"""

from __future__ import annotations

from typing import Protocol


class TextOutputError(RuntimeError):
    """Raised when text cannot be delivered to the focused window."""


class TextOutput(Protocol):
    def type(self, text: str) -> None: ...
