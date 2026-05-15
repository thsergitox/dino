"""Port for speech-to-text engines.

Concrete adapters (OpenAI Whisper, local whisper.cpp, Groq, etc.) implement this
interface so the rest of the system stays engine-agnostic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TranscriberError(RuntimeError):
    """Raised when transcription fails."""


class Transcriber(Protocol):
    """Anything that turns an audio file into text."""

    def transcribe(self, audio_path: Path) -> str: ...
