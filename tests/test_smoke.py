"""Smoke tests — verify packaging wires up correctly."""

import dino


def test_version_exposed():
    assert isinstance(dino.__version__, str) and dino.__version__


def test_cli_parser_has_three_commands():
    from dino.cli import _build_parser

    parser = _build_parser()
    # Argparse subparsers live on a private attribute, so we just verify --help works.
    help_text = parser.format_help()
    for cmd in ("start", "stop", "toggle"):
        assert cmd in help_text
