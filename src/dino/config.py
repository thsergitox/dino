"""Configuration loading.

Order of precedence (lowest → highest):
  1. Built-in defaults
  2. ~/.config/dino/config.toml (or $XDG_CONFIG_HOME/dino/config.toml)
  3. Environment variables (OPENAI_API_KEY, DINO_MODEL, DINO_LANGUAGE, DINO_PROMPT, DINO_LANG)

Config schema (all sections optional):

    [whisper]
    api_key         = "sk-..."        # optional if OPENAI_API_KEY env var set
    model           = "whisper-1"
    language        = "es"
    prompt          = "..."
    timeout_seconds = 30              # abort if Whisper takes longer than this

    [tui]
    language  = "es"            # es | en
    lifecycle = "exec-once"     # exec-once | lazy
    terminal  = ""              # override $TERMINAL auto-detect (empty = auto)

    [output]
    adapter = "wl-copy"         # wl-copy | wtype
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
    timeout_seconds: float = 30.0
    runtime_dir: Path = field(default_factory=lambda: Path(_runtime_dir()))
    tui_language: str = "es"
    tui_lifecycle: str = "exec-once"
    tui_terminal: str | None = None
    output_adapter: str = "wl-copy"


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
    tui_cfg = file_cfg.get("tui", {})
    output_cfg = file_cfg.get("output", {})

    api_key = os.environ.get("OPENAI_API_KEY") or whisper_cfg.get("api_key")
    if not api_key:
        sys.stderr.write(
            "dino: OPENAI_API_KEY is not set.\n"
            "  Run `dino setup`, export the env var, or set [whisper].api_key in ~/.config/dino/config.toml.\n"
        )
        raise SystemExit(2)

    tui_language = (
        os.environ.get("DINO_LANG")
        or tui_cfg.get("language")
        or "es"
    )
    # If user picked Spanish but never set whisper.language, default it to "es"
    # — improves WER for Spanish-only users without an extra config step.
    language = (
        os.environ.get("DINO_LANGUAGE")
        or whisper_cfg.get("language")
        or (tui_language if tui_language == "es" else None)
    )

    timeout = float(
        os.environ.get("DINO_TIMEOUT") or whisper_cfg.get("timeout_seconds", 30)
    )

    return Config(
        api_key=api_key,
        model=os.environ.get("DINO_MODEL") or whisper_cfg.get("model", "whisper-1"),
        language=language,
        prompt=os.environ.get("DINO_PROMPT") or whisper_cfg.get("prompt") or None,
        sample_rate=int(whisper_cfg.get("sample_rate", 16000)),
        channels=int(whisper_cfg.get("channels", 1)),
        timeout_seconds=timeout,
        tui_language=tui_language,
        tui_lifecycle=tui_cfg.get("lifecycle", "exec-once"),
        tui_terminal=tui_cfg.get("terminal") or None,
        output_adapter=output_cfg.get("adapter", "wl-copy"),
    )
