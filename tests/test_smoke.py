"""Smoke tests — verify packaging wires up correctly."""

import dino


def test_version_exposed():
    assert isinstance(dino.__version__, str) and dino.__version__


def test_cli_parser_has_all_subcommands():
    from dino.cli import _build_parser

    parser = _build_parser()
    help_text = parser.format_help()
    for cmd in ("tui", "start", "stop", "toggle", "setup"):
        assert cmd in help_text


def test_i18n_default_and_fallback():
    from dino.i18n import set_lang, t

    set_lang("es")
    assert t("status.idle") == "Espacio para grabar"

    set_lang("en")
    assert t("status.idle") == "Space to record"

    # Unknown lang falls back to es default.
    set_lang("xx")
    assert t("status.idle") == "Espacio para grabar"

    set_lang("es")  # leave the module in a clean state


def test_i18n_format_substitution():
    from dino.i18n import set_lang, t

    set_lang("es")
    assert t("status.error", msg="boom") == "Error: boom"
