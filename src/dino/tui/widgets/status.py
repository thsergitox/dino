"""Big-text status label driven by an i18n key."""

from __future__ import annotations

from rich.align import Align
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from dino.i18n import t


class StatusLabel(Widget):
    """Shows the current status. Color-coded by AppState category."""

    DEFAULT_CSS = """
    StatusLabel {
        height: 3;
        content-align: center middle;
    }
    """

    key: reactive[str] = reactive("status.idle")
    tone: reactive[str] = reactive("cyan")
    args: reactive[dict] = reactive({})

    def watch_key(self, _old: str, _new: str) -> None:
        self.refresh()

    def watch_tone(self, _old: str, _new: str) -> None:
        self.refresh()

    def watch_args(self, _old: dict, _new: dict) -> None:
        self.refresh()

    def set_status(self, key: str, tone: str = "cyan", **kwargs: object) -> None:
        self.tone = tone
        self.args = dict(kwargs)
        self.key = key

    def render(self) -> Align:
        text = Text(t(self.key, **self.args), style=f"bold {self.tone}")
        return Align.center(text, vertical="middle")
