"""OpenAI Whisper API adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from dino.stt.base import TranscriberError

_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
_DEFAULT_TIMEOUT = 30.0

# Module-level lazy Session. requests.Session pools HTTPS connections, so the
# second call onward skips the ~200-400ms TLS handshake to api.openai.com.
# Important for LATAM users: round-trip to OpenAI's US datacenters dominates
# perceived latency on short transcripts.
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


@dataclass(frozen=True)
class OpenAIWhisper:
    api_key: str
    model: str = "whisper-1"
    language: str | None = None
    prompt: str | None = None
    timeout: float = _DEFAULT_TIMEOUT

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
                response = _get_session().post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=data,
                    files={"file": (audio_path.name, fh, "audio/wav")},
                    timeout=self.timeout,
                )
        except requests.Timeout as exc:
            # Surface timeout as its own error so the TUI can show a precise message
            # ("la transcripción se demoró más de Xs") instead of a generic network error.
            raise TranscriberError(
                f"Transcription timed out after {self.timeout:g}s. "
                "Check your connection or raise [whisper].timeout_seconds in config.toml."
            ) from exc
        except requests.RequestException as exc:
            raise TranscriberError(f"Network error contacting OpenAI: {exc}") from exc

        if response.status_code != 200:
            raise TranscriberError(
                f"OpenAI API returned {response.status_code}: {response.text.strip()}"
            )

        return response.text.strip()
