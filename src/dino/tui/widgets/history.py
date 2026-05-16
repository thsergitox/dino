"""Scrollable transcript history (current session only)."""

from __future__ import annotations

from datetime import datetime

from textual.widgets import RichLog

from dino.i18n import t


class HistoryLog(RichLog):
    """A `RichLog` that prepends a heading and timestamps entries."""

    DEFAULT_CSS = """
    HistoryLog {
        border: round $accent 30%;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        self.border_title = t("history.heading")
        self.write(f"[dim]{t('history.empty')}[/dim]")

    def append_transcript(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/dim]  {text}")

    def clear_all(self) -> None:
        self.clear()
        self.write(f"[dim]{t('history.empty')}[/dim]")
