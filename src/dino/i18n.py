"""Minimal i18n — dict-based, two languages.

Usage:
    from dino.i18n import t, set_lang
    set_lang("es")
    t("status.listening")      # → "Escuchando…"
    t("status.error", msg="x") # → "Error: x"
"""

from __future__ import annotations

DEFAULT_LANG = "es"
FALLBACK_LANG = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        "status.idle":         "Espacio para grabar",
        "status.listening":    "Escuchando…",
        "status.transcribing": "Transcribiendo…",
        "status.copied":       "Copiado al portapapeles",
        "status.error":        "Error: {msg}",
        "status.no_speech":    "Sin habla detectada",
        "footer.idle":         "Espacio: grabar  ·  q: salir  ·  c: limpiar",
        "footer.recording":    "Espacio: detener  ·  Esc: cancelar",
        "footer.transcribing": "Esc: cancelar transcripción",
        "footer.error":        "R: reintentar  ·  Esc: descartar",
        "history.empty":       "Sin transcripciones todavía.",
        "history.heading":     "Transcripciones de esta sesión",
        "banner.no_hyprland":  "Aviso: Hyprland no detectado. El atajo SUPER+Z no funcionará, pero la TUI sí.",
        "banner.title":        "dino — dictado por voz",
        "error.no_mic":        "No se encontró micrófono. Verifica con `pw-record` desde otra terminal.",
        "error.api":           "Falló la API de OpenAI: {msg}",
        "error.no_audio":      "La grabación quedó vacía.",
        "error.lock":          "Otra instancia de dino ya está corriendo.",
        "hint.wl_clip_persist": "Tip: instala wl-clip-persist si quieres que el portapapeles sobreviva al cerrar sesión.",
    },
    "en": {
        "status.idle":         "Space to record",
        "status.listening":    "Listening…",
        "status.transcribing": "Transcribing…",
        "status.copied":       "Copied to clipboard",
        "status.error":        "Error: {msg}",
        "status.no_speech":    "No speech detected",
        "footer.idle":         "Space: record  ·  q: quit  ·  c: clear",
        "footer.recording":    "Space: stop  ·  Esc: cancel",
        "footer.transcribing": "Esc: cancel transcription",
        "footer.error":        "R: retry  ·  Esc: discard",
        "history.empty":       "No transcripts yet.",
        "history.heading":     "Transcripts this session",
        "banner.no_hyprland":  "Notice: Hyprland not detected. The SUPER+Z shortcut won't work, but the TUI will.",
        "banner.title":        "dino — voice dictation",
        "error.no_mic":        "No microphone found. Test with `pw-record` from another terminal.",
        "error.api":           "OpenAI API failed: {msg}",
        "error.no_audio":      "Recording came out empty.",
        "error.lock":          "Another dino instance is already running.",
        "hint.wl_clip_persist": "Tip: install wl-clip-persist to keep the clipboard after session end.",
    },
}

_lang: str = DEFAULT_LANG


def set_lang(lang: str) -> None:
    """Set the active language. Unknown codes fall back silently to the default."""
    global _lang
    _lang = lang if lang in _STRINGS else DEFAULT_LANG


def get_lang() -> str:
    return _lang


def t(key: str, **kwargs: object) -> str:
    """Look up `key` in the active language, with `{name}` substitutions."""
    bundle = _STRINGS.get(_lang) or _STRINGS[DEFAULT_LANG]
    template = bundle.get(key) or _STRINGS[FALLBACK_LANG].get(key) or key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
