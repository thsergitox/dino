"""Terminal detection — PATH-mocked preference walk."""

from __future__ import annotations

import pytest

from dino.terminal.detect import (
    TERMINAL_PREFERENCE,
    build_launch_cmd,
    detect,
)


def _path_with(monkeypatch, available: set[str], env_term: str = ""):
    monkeypatch.setenv("TERMINAL", env_term)
    monkeypatch.setattr(
        "dino.terminal.detect.shutil.which",
        lambda binary: f"/usr/bin/{binary}" if binary in available else None,
    )


def test_prefers_first_available_when_terminal_unset(monkeypatch):
    _path_with(monkeypatch, available={"alacritty", "foot"})
    spec = detect()
    assert spec is not None
    assert spec.binary == "alacritty"  # alacritty is earlier than foot in preference


def test_env_terminal_wins_over_preference(monkeypatch):
    _path_with(monkeypatch, available={"kitty", "foot"}, env_term="foot")
    spec = detect()
    assert spec is not None
    assert spec.binary == "foot"


def test_env_terminal_unknown_falls_through_with_generic_spec(monkeypatch):
    _path_with(monkeypatch, available={"st"}, env_term="st")
    spec = detect()
    assert spec is not None
    assert spec.binary == "st"
    assert spec.class_flags == ()


def test_none_available(monkeypatch):
    _path_with(monkeypatch, available=set())
    assert detect() is None


def test_build_launch_cmd_kitty_has_class_and_decorations():
    spec = next(s for s in TERMINAL_PREFERENCE if s.binary == "kitty")
    cmd = build_launch_cmd(spec, ["dino", "tui"])
    assert cmd[0] == "kitty"
    assert "--class" in cmd
    assert "dino" in cmd
    assert "--override" in cmd
    assert cmd[-2:] == ["dino", "tui"]


def test_build_launch_cmd_foot_uses_app_id_no_separator():
    spec = next(s for s in TERMINAL_PREFERENCE if s.binary == "foot")
    cmd = build_launch_cmd(spec, ["dino", "tui"])
    assert cmd[0] == "foot"
    assert "--app-id=dino" in cmd
    assert "--" not in cmd
