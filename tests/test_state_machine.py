"""State-machine transitions — pure Python, no Textual required."""

from __future__ import annotations

import pytest

from dino.tui.state import AppState, assert_transition, can_transition


@pytest.mark.parametrize(
    "src,dst,allowed",
    [
        (AppState.IDLE, AppState.RECORDING, True),
        (AppState.IDLE, AppState.ERROR, True),
        (AppState.IDLE, AppState.CLIPBOARDING, False),  # must go through TRANSCRIBING
        (AppState.RECORDING, AppState.TRANSCRIBING, True),
        (AppState.RECORDING, AppState.IDLE, True),       # cancel via Esc
        (AppState.RECORDING, AppState.ERROR, True),
        (AppState.TRANSCRIBING, AppState.CLIPBOARDING, True),
        (AppState.TRANSCRIBING, AppState.IDLE, True),    # cancel via Esc
        (AppState.TRANSCRIBING, AppState.ERROR, True),
        (AppState.TRANSCRIBING, AppState.RECORDING, False),
        (AppState.CLIPBOARDING, AppState.IDLE, True),
        (AppState.CLIPBOARDING, AppState.RECORDING, False),
        (AppState.ERROR, AppState.IDLE, True),
        (AppState.ERROR, AppState.RECORDING, False),     # must clear error first
    ],
)
def test_transition_truth_table(src, dst, allowed):
    assert can_transition(src, dst) is allowed


def test_assert_transition_raises_on_invalid():
    with pytest.raises(ValueError):
        assert_transition(AppState.IDLE, AppState.CLIPBOARDING)


def test_assert_transition_silent_on_valid():
    assert_transition(AppState.IDLE, AppState.RECORDING)
