"""Command-line entry point.

Three subcommands map to the push-to-talk lifecycle:

  dino start    Begin recording (bound to the key-down event in your compositor).
  dino stop     End recording, transcribe, and type the result into the focused window
                (bound to the key-up event).
  dino toggle   Convenience: behaves like start if idle, otherwise like stop.
"""

from __future__ import annotations

import argparse
import sys

from dino import __version__, notify
from dino.audio import Recorder, RecorderError
from dino.config import load as load_config
from dino.output import TextOutputError, WtypeOutput
from dino.stt import OpenAIWhisper, TranscriberError


def _cmd_start(args: argparse.Namespace) -> int:
    config = load_config()
    recorder = Recorder(
        runtime_dir=config.runtime_dir,
        sample_rate=config.sample_rate,
        channels=config.channels,
    )
    try:
        recorder.start()
    except RecorderError as exc:
        notify.send("dino: failed to start", str(exc), urgency="critical")
        sys.stderr.write(f"dino: {exc}\n")
        return 1
    notify.send("dino", "Listening…", urgency="low", timeout_ms=1500)
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    config = load_config()
    recorder = Recorder(
        runtime_dir=config.runtime_dir,
        sample_rate=config.sample_rate,
        channels=config.channels,
    )

    try:
        wav_path = recorder.stop()
    except RecorderError as exc:
        # No-op when nothing is recording — a stray key release shouldn't bother the user.
        sys.stderr.write(f"dino: {exc}\n")
        return 0

    notify.send("dino", "Transcribing…", urgency="low", timeout_ms=1500)

    transcriber = OpenAIWhisper(
        api_key=config.api_key,
        model=config.model,
        language=config.language,
        prompt=config.prompt,
    )
    try:
        text = transcriber.transcribe(wav_path)
    except TranscriberError as exc:
        notify.send("dino: transcription failed", str(exc), urgency="critical")
        sys.stderr.write(f"dino: {exc}\n")
        return 1

    if not text:
        notify.send("dino", "No speech detected.", urgency="low")
        return 0

    try:
        WtypeOutput().type(text)
    except TextOutputError as exc:
        notify.send("dino: cannot type result", str(exc), urgency="critical")
        sys.stderr.write(f"dino: {exc}\nTranscript was: {text}\n")
        return 1

    return 0


def _cmd_toggle(args: argparse.Namespace) -> int:
    config = load_config()
    recorder = Recorder(
        runtime_dir=config.runtime_dir,
        sample_rate=config.sample_rate,
        channels=config.channels,
    )
    return _cmd_stop(args) if recorder.is_recording() else _cmd_start(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dino",
        description="Push-to-talk voice dictation for Wayland.",
    )
    parser.add_argument("--version", action="version", version=f"dino {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start", help="Begin recording.").set_defaults(func=_cmd_start)
    sub.add_parser("stop", help="Stop recording, transcribe, type result.").set_defaults(
        func=_cmd_stop
    )
    sub.add_parser("toggle", help="Start if idle, otherwise stop.").set_defaults(
        func=_cmd_toggle
    )
    sub.add_parser(
        "setup",
        help="Interactive first-run configuration (API key, model, Hyprland binding).",
    ).set_defaults(func=_cmd_setup)
    return parser


def _cmd_setup(args: argparse.Namespace) -> int:
    # Lazy import so the hot-path commands (start/stop/toggle) don't pay
    # rich/questionary startup cost on every Hyprland keypress.
    from dino import setup_wizard

    return setup_wizard.run()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)
