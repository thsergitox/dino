"""Command-line entry point.

Subcommands map to two operating modes:

  Default (no args) / `dino tui`
        Persistent Textual TUI for Hyprland scratchpad. Space toggles
        recording; transcripts auto-copy to the clipboard via wl-copy.

  `dino start` / `dino stop` / `dino toggle`
        Legacy fire-and-forget push-to-talk for compositors without a
        scratchpad model. Output now goes through the configured adapter
        (wl-copy by default, wtype if set in [output].adapter).

  `dino setup`
        Interactive first-run wizard.
"""

from __future__ import annotations

import argparse
import sys

from dino import __version__, notify
from dino.audio import Recorder, RecorderError
from dino.config import load as load_config
from dino.output import TextOutputError
from dino.output import build as build_output
from dino.stt import OpenAIWhisper, TranscriberError


def _cmd_tui(args: argparse.Namespace) -> int:
    # Lazy imports keep the legacy hot-path (`dino start`/`stop`) fast on
    # every Hyprland keypress — Textual + numpy import time is ~500ms.
    from dino.tui.app import DinoApp
    from dino.tui.single_instance import AlreadyRunningError, SingleInstanceLock

    config = load_config()
    lock = SingleInstanceLock(config.runtime_dir)
    try:
        lock.acquire()
    except AlreadyRunningError:
        sys.stderr.write("dino: ya hay otra instancia corriendo. (Llamado a togglespecialworkspace.)\n")
        return 0

    try:
        app = DinoApp(config, lang=args.lang)
        app.run()
        return 0
    finally:
        lock.release()


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
    notify.send("dino", "Escuchando…", urgency="low", timeout_ms=1500)
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

    notify.send("dino", "Transcribiendo…", urgency="low", timeout_ms=1500)

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
        notify.send("dino", "Sin habla detectada.", urgency="low")
        return 0

    output = build_output(config.output_adapter)
    try:
        output.type(text)
    except TextOutputError as exc:
        notify.send("dino: salida falló", str(exc), urgency="critical")
        sys.stderr.write(f"dino: {exc}\nTranscript was: {text}\n")
        return 1

    notify.send("dino", "Copiado al portapapeles", urgency="low", timeout_ms=1500)
    return 0


def _cmd_toggle(args: argparse.Namespace) -> int:
    config = load_config()
    recorder = Recorder(
        runtime_dir=config.runtime_dir,
        sample_rate=config.sample_rate,
        channels=config.channels,
    )
    return _cmd_stop(args) if recorder.is_recording() else _cmd_start(args)


def _cmd_setup(args: argparse.Namespace) -> int:
    from dino import setup_wizard

    return setup_wizard.run()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dino",
        description="Voice dictation TUI for Hyprland + Wayland.",
    )
    parser.add_argument("--version", action="version", version=f"dino {__version__}")
    sub = parser.add_subparsers(dest="command", required=False)

    tui_parser = sub.add_parser("tui", help="Run the persistent dictation TUI (default).")
    tui_parser.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="UI language override (default: from config.toml, fallback es).",
    )
    tui_parser.set_defaults(func=_cmd_tui)

    sub.add_parser("start", help="Legacy: begin recording (push-to-talk press).").set_defaults(
        func=_cmd_start
    )
    sub.add_parser("stop", help="Legacy: stop, transcribe, copy result.").set_defaults(
        func=_cmd_stop
    )
    sub.add_parser("toggle", help="Legacy: start if idle, otherwise stop.").set_defaults(
        func=_cmd_toggle
    )
    sub.add_parser(
        "setup",
        help="Interactive first-run configuration (provider, API key, Hyprland binding).",
    ).set_defaults(func=_cmd_setup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # No subcommand → default to the TUI.
    if not getattr(args, "command", None):
        args.lang = None
        return _cmd_tui(args)

    return args.func(args)
