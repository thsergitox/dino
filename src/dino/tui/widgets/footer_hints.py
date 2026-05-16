"""Bottom hint bar — different copy per state."""

from __future__ import annotations

from rich.align import Align
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from dino.i18n import t


class FooterHints(Widget):
    DEFAULT_CSS = """
    FooterHints {
        height: 1;
        background: $boost;
        color: $text-muted;
    }
    """

    key: reactive[str] = reactive("footer.idle")

    def watch_key(self, _old: str, _new: str) -> None:
        self.refresh()

    def set_key(self, key: str) -> None:
        self.key = key

    def render(self) -> Align:
        return Align.center(Text(t(self.key)))
