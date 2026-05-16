from dino.output.base import TextOutput, TextOutputError
from dino.output.wl_copy import WlCopyOutput
from dino.output.wtype_inject import WtypeOutput

__all__ = ["TextOutput", "TextOutputError", "WlCopyOutput", "WtypeOutput"]


def build(adapter: str) -> TextOutput:
    """Factory: pick an output adapter by config name."""
    if adapter == "wtype":
        return WtypeOutput()
    # default and "wl-copy"
    return WlCopyOutput()
