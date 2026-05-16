# Architecture

`dino` follows a **hexagonal (ports & adapters)** layout. The orchestration layers — the CLI in `cli.py` and the Textual app in `tui/app.py` — depend on `Protocol`s (`Transcriber`, `TextOutput`), never on concrete implementations. Swapping the STT engine or the text-output method is "implement the protocol, register in the factory."

## High-level diagram

```
                       ┌──────────────────────────────────────────────┐
                       │   tui/app.py  (Textual App + state machine)  │
                       │   IDLE → RECORDING → TRANSCRIBING →          │
                       │   CLIPBOARDING → IDLE   (ERROR side path)    │
                       └─────┬─────────────┬──────────────┬───────────┘
                             │             │              │
              ┌──────────────▼──────┐  ┌───▼────────┐  ┌──▼─────────────┐
              │ audio/streaming.py  │  │ stt/       │  │ output/        │
              │ asyncio pw-record   │  │ Transcriber│  │ TextOutput     │
              │ stdout → Queue      │  │  (Port)    │  │  (Port)        │
              │ + WAV buffer        │  │ OpenAI ad. │  │ wl-copy / wtype│
              └──────────────┬──────┘  └────────────┘  └────────────────┘
                             │
              ┌──────────────▼──────┐
              │ widgets/spectrum.py │  numpy FFT @ 30 FPS, drop-oldest
              │ (FFT visualizer)    │
              └─────────────────────┘

                       ─────────────  Legacy CLI ─────────────
                       cli.py: dino start/stop/toggle
                              ↓                ↓
                       audio/recorder.py  → Transcriber → TextOutput
```

## Module map

| Path | Responsibility |
|---|---|
| `src/dino/cli.py` | Argparse; default → TUI, plus `tui`, `start`, `stop`, `toggle`, `setup` subcommands. |
| `src/dino/config.py` | Resolves config from TOML + env. Sections: `[whisper]`, `[tui]`, `[output]`. |
| `src/dino/i18n.py` | Dict-based `t(key, **kw)` for Spanish/English. |
| `src/dino/notify.py` | Best-effort `notify-send` wrapper (legacy CLI paths). |
| `src/dino/setup_wizard.py` | rich + questionary first-run wizard. Writes config, appends Hyprland block. |
| `src/dino/audio/recorder.py` | Legacy `pw-record` subprocess with PID-file lifecycle (used by `dino start`/`stop`). |
| `src/dino/audio/streaming.py` | Async PCM stream over `pw-record --raw -` to stdout. Fan-out to FFT queue + WAV buffer. |
| `src/dino/stt/base.py` | `Transcriber` Protocol. |
| `src/dino/stt/openai_whisper.py` | OpenAI API adapter. |
| `src/dino/output/base.py` | `TextOutput` Protocol. |
| `src/dino/output/wl_copy.py` | Wayland clipboard adapter (default). |
| `src/dino/output/wtype_inject.py` | wtype adapter (opt-in via `[output].adapter = "wtype"`). |
| `src/dino/terminal/detect.py` | Detect kitty/alacritty/foot/ghostty/wezterm + build launch command. |
| `src/dino/tui/app.py` | Textual `App` subclass — bindings, state-machine watchers, wiring. |
| `src/dino/tui/state.py` | `AppState` enum + transition validation. |
| `src/dino/tui/single_instance.py` | `fcntl.flock` PID lock; on collision, dispatches `togglespecialworkspace`. |
| `src/dino/tui/styles.tcss` | Textual CSS — blue accent, layout, spacing. |
| `src/dino/tui/widgets/spectrum.py` | FFT visualizer (reactive `bars`). |
| `src/dino/tui/widgets/status.py` | Big status label driven by i18n. |
| `src/dino/tui/widgets/history.py` | Session transcript history (RichLog). |
| `src/dino/tui/widgets/footer_hints.py` | Bottom hint bar (state-dependent). |

## State machine

```
        ┌───────────────┐
        │     IDLE      │◄─────────────────────────────────┐
        └──┬────────────┘                                  │
           │ Space                                          │
           ▼                                                │
    ┌──────────────┐    Space / Esc    ┌──────────────┐    │
    │  RECORDING   │ ─────────────────►│ TRANSCRIBING │    │
    └──────┬───────┘                   └──────┬───────┘    │
           │ Esc                              │ ok          │
           └──────────► IDLE                  ▼             │
                                       ┌──────────────┐    │
                                       │ CLIPBOARDING │ ───┤
                                       └──────────────┘    │
                                              │ error       │
                                              ▼             │
                                       ┌──────────────┐    │
                                       │    ERROR     │ ─R/Esc/3s
                                       └──────────────┘
```

`AppState` is a Textual `reactive` on the App. `watch_state` is the single side-effect site — it pushes the new status text, footer hint, and spectrum visibility. Invalid transitions raise via `assert_transition` (caught only in tests; the App guards via `can_transition` before assigning).

## Concurrency model

The TUI uses Textual's built-in asyncio event loop. Key tasks:

| Task | Owner | What it does |
|---|---|---|
| `StreamingRecorder._reader_loop` | `audio/streaming.py` | Reads `pw-record` stdout in 2048-byte chunks (1024 frames × s16). For each chunk: fan out to (a) `chunk_queue`, (b) `_wav_buffer`. |
| `SpectrumWidget._consume_loop` | `tui/widgets/spectrum.py` | Pulls from `chunk_queue`, runs numpy FFT, computes log-spaced bar heights, assigns to reactive `bars`. ~30 FPS. |
| Transcription | `tui/app.py` | `asyncio.to_thread(transcriber.transcribe, wav_path)` — sync `requests.post` runs in a thread so the loop stays responsive. |

`chunk_queue` is bounded (`maxsize=8`) with drop-oldest behaviour — the visualizer is allowed to drop frames if it falls behind, but the WAV is always lossless because it's fed from the same per-chunk path *before* enqueueing.

## Failure modes

| Failure | Surface | Handling |
|---|---|---|
| `pw-record` missing | TUI mount | Status → `ERROR` with install hint. |
| `pw-record` exits in <200 ms | `StreamingRecorder.start` | `StreamingRecorderError("no microphone")` → `ERROR`. |
| Whisper API failure | `_transcribe_path` | `ERROR` + retry hint. WAV kept for retry. |
| Empty transcript | `_transcribe_path` | Soft toast "Sin habla detectada", → `IDLE`. |
| `wl-copy` missing | `WlCopyOutput.type` | `TextOutputError` → `ERROR`. |
| User closes TUI mid-recording | `on_unmount` | `recorder.cancel()` kills pw-record, partial WAV discarded. |
| Second dino instance | `SingleInstanceLock.acquire` | `flock` fails → dispatch `togglespecialworkspace dino`, exit 0. |
| Not under Hyprland | App `on_mount` | Yellow banner; TUI still works. |

## Adding a new STT adapter

1. Create `src/dino/stt/<engine>.py`.
2. Implement `transcribe(audio_path: Path) -> str` matching the `Transcriber` protocol.
3. Wire it into `cli.py` / `tui/app.py` behind a `config.toml` switch (`[stt].provider`).

That's the entire footprint of the change.

## Adding a new output adapter

Same drill under `src/dino/output/`. Implement `TextOutput.type(text: str) -> None`. Add a branch in `dino/output/__init__.py::build()`.

## Out of scope for 0.2

- Streaming / partial transcripts (planned v0.3).
- Wake-word activation (planned v1.0).
- Voice commands inside the TUI ("new line", "punto").
- AppImage / Flatpak packaging.
