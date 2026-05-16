"""TUI state machine.

Single source of truth for what the app is doing right now. Transitions are
validated; invalid attempts raise so bugs surface during testing instead of
silently corrupting state.
"""

from __future__ import annotations

from enum import StrEnum


class AppState(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    CLIPBOARDING = "clipboarding"
    ERROR = "error"


# Allowed transitions (origin → destinations). Keep this table compact and
# authoritative — every other module should defer to `can_transition`.
_TRANSITIONS: dict[AppState, frozenset[AppState]] = {
    AppState.IDLE:         frozenset({AppState.RECORDING, AppState.ERROR}),
    AppState.RECORDING:    frozenset({AppState.TRANSCRIBING, AppState.IDLE, AppState.ERROR}),
    AppState.TRANSCRIBING: frozenset({AppState.CLIPBOARDING, AppState.IDLE, AppState.ERROR}),
    AppState.CLIPBOARDING: frozenset({AppState.IDLE, AppState.ERROR}),
    AppState.ERROR:        frozenset({AppState.IDLE}),
}


def can_transition(src: AppState, dst: AppState) -> bool:
    return dst in _TRANSITIONS.get(src, frozenset())


def assert_transition(src: AppState, dst: AppState) -> None:
    if not can_transition(src, dst):
        raise ValueError(f"Invalid state transition: {src} → {dst}")
