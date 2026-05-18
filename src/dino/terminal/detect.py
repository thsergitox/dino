"""Detect the user's terminal emulator and build a launch command.

This module decides which terminal to use to host the dino TUI in a Hyprland
scratchpad. The detection order is:

  1. `$TERMINAL` (most explicit user preference)
  2. preference list, picking the first whose binary is on PATH

Each terminal spec also carries its per-emulator flag for setting the Wayland
`app_id` (or X11 WM class) to ``dino`` — required so Hyprland's
``windowrule ... class:^(dino)$`` rules match — and the flag(s) for hiding
window decorations so the TUI looks like an app, not a terminal.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TerminalSpec:
    binary: str
    class_flags: tuple[str, ...]
    decoration_flags: tuple[str, ...] = ()
    # Some terminals need a separator before the inner command. e.g. kitty wants
    # ``--`` to mark "everything after this is the program to run".
    exec_separator: tuple[str, ...] = ("--",)
    # wezterm requires a subcommand.
    pre_flags: tuple[str, ...] = ()


# Order matters — first hit wins when $TERMINAL is unset.
TERMINAL_PREFERENCE: tuple[TerminalSpec, ...] = (
    TerminalSpec(
        binary="kitty",
        class_flags=("--class", "dino"),
        decoration_flags=("--override", "hide_window_decorations=yes"),
    ),
    TerminalSpec(
        binary="alacritty",
        class_flags=("--class", "dino,dino"),
        # alacritty's decoration toggle lives in its TOML config; document instead.
        decoration_flags=(),
    ),
    TerminalSpec(
        binary="foot",
        class_flags=("--app-id=dino",),
        # foot's CSD toggle is `-T none` / `--title=none` — foot is mostly
        # decoration-free under Hyprland by default, so empty.
        decoration_flags=(),
        exec_separator=(),
    ),
    TerminalSpec(
        binary="ghostty",
        class_flags=("--class=dino",),
        decoration_flags=("--window-decoration=false",),
        exec_separator=("-e",),
    ),
    TerminalSpec(
        binary="wezterm",
        pre_flags=("start",),
        class_flags=("--class", "dino"),
        decoration_flags=(),
    ),
)


def detect() -> TerminalSpec | None:
    """Return the best terminal for hosting the TUI, or None if none found.

    Honors ``$TERMINAL`` first, then walks the preference list.
    """
    env_term = (os.environ.get("TERMINAL") or "").strip()
    if env_term:
        # Match $TERMINAL against the basename of each known spec.
        for spec in TERMINAL_PREFERENCE:
            if env_term == spec.binary and shutil.which(spec.binary):
                return spec
        # $TERMINAL is set but we don't have a spec for it — return a generic
        # spec that just passes through the binary without flags. Better than
        # silently ignoring the user's preference.
        if shutil.which(env_term):
            return TerminalSpec(binary=env_term, class_flags=())

    for spec in TERMINAL_PREFERENCE:
        if shutil.which(spec.binary):
            return spec
    return None


def build_launch_cmd(spec: TerminalSpec, inner: list[str]) -> list[str]:
    """Construct the full ``[terminal, ...flags, --, inner...]`` argv."""
    return [
        spec.binary,
        *spec.pre_flags,
        *spec.class_flags,
        *spec.decoration_flags,
        *spec.exec_separator,
        *inner,
    ]


def hyprland_exec_string(inner: list[str]) -> str | None:
    """Return a single-line shell command suitable for ``exec-once = ...``.

    Returns None when no terminal is detected — caller should warn the user.
    """
    spec = detect()
    if spec is None:
        return None
    return " ".join(build_launch_cmd(spec, inner))
