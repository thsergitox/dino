# Architecture

`dino` follows a small **hexagonal (ports & adapters)** layout. The core orchestration in `cli.py` depends on *interfaces* (`Transcriber`, `TextOutput`), never on concrete implementations. That is what lets us promise: "swap the engine, the rest doesn't move."

```
                          ┌────────────────────────────────────┐
                          │              cli.py                │
                          │  start / stop / toggle commands    │
                          │  pure orchestration, no I/O logic  │
                          └─────────┬────────┬─────────┬───────┘
                                    │        │         │
                  ┌─────────────────┘        │         └────────────────────┐
                  │                          │                              │
                  ▼                          ▼                              ▼
        ┌────────────────────┐    ┌────────────────────┐         ┌────────────────────┐
        │     Recorder       │    │   Transcriber      │ Port    │    TextOutput      │ Port
        │ (audio capture)    │    │   (Protocol)       │         │    (Protocol)      │
        │                    │    │                    │         │                    │
        │ Adapter: pw-record │    │ Adapter: OpenAI    │         │ Adapter: wtype     │
        │ (PipeWire / WAV)   │    │ Whisper API        │         │ (Wayland)          │
        └────────────────────┘    └────────────────────┘         └────────────────────┘
                                              ▲                              ▲
                                              │                              │
                                       future adapters:               future adapters:
                                       • whisper.cpp local            • xdotool (X11)
                                       • Groq Whisper-v3              • wl-copy + paste
                                       • Deepgram streaming           • virtual keyboard
```

## Module map

| Path | Responsibility |
|---|---|
| `src/dino/cli.py` | Argparse, wires Recorder → Transcriber → TextOutput. |
| `src/dino/config.py` | Resolves config from TOML + env. Single source of truth. |
| `src/dino/audio/recorder.py` | `pw-record` subprocess + PID-file lifecycle. |
| `src/dino/stt/base.py` | `Transcriber` Protocol. |
| `src/dino/stt/openai_whisper.py` | OpenAI API adapter. |
| `src/dino/output/base.py` | `TextOutput` Protocol. |
| `src/dino/output/wtype_inject.py` | Wayland `wtype` adapter. |
| `src/dino/notify.py` | Best-effort `notify-send` wrapper. |

## Why two CLI invocations instead of a daemon?

Hyprland's `bind` / `bindr` model is **fire-and-forget**: each event spawns a fresh process. Keeping `dino` daemon-less means:

- No socket protocol to maintain.
- No "is the daemon running?" check on every keypress.
- State that survives both invocations lives in a tiny PID file under `$XDG_RUNTIME_DIR`.

The cost: ~50 ms of Python interpreter startup per event. Worth it for the simplicity.

## Failure modes and where they are handled

| Failure | Where it surfaces | How it is handled |
|---|---|---|
| `pw-record` not installed | `Recorder.start()` | `RecorderError` with install hint; notify + exit 1. |
| Already recording on `start` | `Recorder.start()` | `RecorderError`; notify; exit 1. |
| `stop` with nothing recording | `Recorder.stop()` | `RecorderError`; logged to stderr, exit **0** (idempotent — a stray key release isn't an error). |
| Network failure to OpenAI | `OpenAIWhisper.transcribe()` | `TranscriberError`; notify; exit 1. |
| Empty transcript | `cli.py` | Soft notification; exit 0. |
| `wtype` missing or fails | `WtypeOutput.type()` | `TextOutputError`; transcript dumped to stderr so the work is not lost. |

## Adding a new STT adapter

1. Create `src/dino/stt/<engine>.py`.
2. Implement the `Transcriber` Protocol — a class with a `transcribe(audio_path: Path) -> str` method.
3. Wire it in `cli.py` (eventually behind a `[stt].engine` config switch).

No other file needs to change.

## Adding a new output adapter

Same drill under `src/dino/output/`. Implement `TextOutput.type(text: str) -> None`.

## Out of scope (for 0.1)

- Streaming / partial transcripts.
- Voice commands ("new line", "stop dictating").
- Wake-word activation.
- Multi-language switching mid-session.

These belong on the [roadmap](../README.md#roadmap), not in 0.1's surface area.
