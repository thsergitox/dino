"""OpenAI Whisper API adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from dino.stt.base import TranscriberError

_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class OpenAIWhisper:
    api_key: str
    model: str = "whisper-1"
    language: str | None = None
    prompt: str | None = None

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.is_file():
            raise TranscriberError(f"Audio file not found: {audio_path}")

        data: dict[str, str] = {"model": self.model, "response_format": "text"}
        if self.language:
            data["language"] = self.language
        if self.prompt:
            data["prompt"] = self.prompt

        try:
            with audio_path.open("rb") as fh:
                response = requests.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=data,
                    files={"file": (audio_path.name, fh, "audio/wav")},
                    timeout=_TIMEOUT_SECONDS,
                )
        except requests.RequestException as exc:
            raise TranscriberError(f"Network error contacting OpenAI: {exc}") from exc

        if response.status_code != 200:
            raise TranscriberError(
                f"OpenAI API returned {response.status_code}: {response.text.strip()}"
            )

        return response.text.strip()
