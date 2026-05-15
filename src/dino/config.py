"""Configuration loading.

Order of precedence (lowest → highest):
  1. Built-in defaults
  2. ~/.config/dino/config.toml (or $XDG_CONFIG_HOME/dino/config.toml)
  3. Environment variables (OPENAI_API_KEY, DINO_MODEL, DINO_LANGUAGE, DINO_PROMPT)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str = "whisper-1"
    language: str | None = None
    prompt: str | None = None
    sample_rate: int = 16000
    channels: int = 1
    runtime_dir: Path = field(default_factory=lambda: Path(_runtime_dir()))


def _runtime_dir() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/dino-{os.getuid()}"
    path = Path(base) / "dino"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "dino" / "config.toml"


def _load_toml() -> dict:
    path = _config_path()
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load() -> Config:
    """Resolve configuration from file + environment.

    Raises:
        SystemExit: if no API key is found.
    """
    file_cfg = _load_toml()
    whisper_cfg = file_cfg.get("whisper", {})

    api_key = os.environ.get("OPENAI_API_KEY") or whisper_cfg.get("api_key")
    if not api_key:
        sys.stderr.write(
            "dino: OPENAI_API_KEY is not set.\n"
            "  Export it in your shell or set [whisper].api_key in ~/.config/dino/config.toml.\n"
        )
        raise SystemExit(2)

    return Config(
        api_key=api_key,
        model=os.environ.get("DINO_MODEL") or whisper_cfg.get("model", "whisper-1"),
        language=os.environ.get("DINO_LANGUAGE") or whisper_cfg.get("language") or None,
        prompt=os.environ.get("DINO_PROMPT") or whisper_cfg.get("prompt") or None,
        sample_rate=int(whisper_cfg.get("sample_rate", 16000)),
        channels=int(whisper_cfg.get("channels", 1)),
    )
