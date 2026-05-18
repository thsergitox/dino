"""Scrollable transcript history (current session only)."""

from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.widgets import RichLog

from dino.i18n import t


class HistoryLog(RichLog):
    """A `RichLog` that prepends a heading and timestamps entries.

    Note: `RichLog.write(str)` renders the string verbatim — it does NOT
    interpret Rich BBCode-style markup like `[dim]…[/dim]`. We always wrap
    in `Text.from_markup` (or `Text.assemble`) so styling actually applies
    instead of leaking as literal `[dim]` tags in the UI.
    """

    DEFAULT_CSS = """
    HistoryLog {
        border: round $accent 30%;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        self.border_title = t("history.heading")
        self._write_empty_placeholder()

    def append_transcript(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = Text.assemble((f"{timestamp}  ", "dim"), text)
        self.write(line)

    def clear_all(self) -> None:
        self.clear()
        self._write_empty_placeholder()

    def _write_empty_placeholder(self) -> None:
        self.write(Text(t("history.empty"), style="dim"))
