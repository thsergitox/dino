# dino

> Push-to-talk voice dictation for Wayland. Hold a key, speak, release — your words appear at the cursor.

`dino` is a tiny, hackable, distribution-agnostic dictation tool for Wayland desktops. It records while you hold a hotkey, sends the audio to OpenAI Whisper, and types the result into whichever window is focused.

It is intentionally small (≈ 300 LOC) and designed to grow: the STT engine and the text-output method are behind hexagonal ports, so adding `whisper.cpp`, Groq, Deepgram, or X11 support later is a swap-in adapter, not a rewrite.

**Status:** `0.1.0` — alpha. The current release targets **Hyprland** on **Wayland** with the **OpenAI Whisper API** as the STT engine.

---

## Why another dictation tool?

| Tool | Hotkey | Wayland | Hackable | Cloud-or-local |
|---|---|---|---|---|
| `nerd-dictation` | ❌ DIY | ⚠️ wrappers | ✅ | local only |
| OpenWhispr | ✅ | ✅ | Electron | both |
| whisrs | ✅ | ✅ | Rust | both |
| **dino** | ✅ (via compositor) | ✅ | ✅ Python, ports & adapters | cloud (local backend planned) |

`dino` exists because we wanted a small, readable codebase that we could grow into a full voice assistant — not a finished product to consume.

## Requirements

| Component | Why | Install (Arch / Debian) |
|---|---|---|
| Python ≥ 3.10 | runtime | `pacman -S python` / `apt install python3` |
| PipeWire | audio capture (`pw-record`) | `pacman -S pipewire` / `apt install pipewire-bin` |
| `wtype` | inject text on Wayland | `pacman -S wtype` / `apt install wtype` |
| `notify-send` *(optional)* | desktop notifications | `pacman -S libnotify` / `apt install libnotify-bin` |
| OpenAI API key | transcription | <https://platform.openai.com/api-keys> |

A full per-distro install guide lives in [docs/INSTALL.md](docs/INSTALL.md).

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/thsergitox/dino.git
cd dino
pipx install .   # or:  python -m pip install --user .

# 2. Tell dino your OpenAI key (any of these works)
export OPENAI_API_KEY="sk-..."
# or write ~/.config/dino/config.toml — see docs/INSTALL.md

# 3. Wire it to a hotkey in Hyprland (~/.config/hypr/hyprland.conf)
bind  = SUPER, V, exec, dino start
bindr = SUPER, V, exec, dino stop
```

Reload Hyprland (`hyprctl reload`), focus any text field, hold `SUPER+V`, talk, release. The transcript appears where you were typing.

A copy-pasteable Hyprland snippet lives in [examples/hyprland.conf](examples/hyprland.conf), and a deeper Hyprland walkthrough lives in [docs/HYPRLAND_SETUP.md](docs/HYPRLAND_SETUP.md).

## CLI

```text
dino start    # begin recording (bound to key-down)
dino stop     # stop, transcribe, type the result (bound to key-up)
dino toggle   # start if idle, otherwise stop — handy outside push-to-talk
dino --version
```

State lives under `$XDG_RUNTIME_DIR/dino/`, so a stray crash never leaves junk in your home directory.

## Configuration

`dino` reads, in order:

1. Built-in defaults.
2. `~/.config/dino/config.toml` (or `$XDG_CONFIG_HOME/dino/config.toml`).
3. Environment variables (`OPENAI_API_KEY`, `DINO_MODEL`, `DINO_LANGUAGE`, `DINO_PROMPT`).

Example `config.toml`:

```toml
[whisper]
api_key   = "sk-..."        # optional — env var preferred
model     = "whisper-1"     # or gpt-4o-transcribe / gpt-4o-mini-transcribe
language  = "en"            # ISO-639-1, omit to auto-detect
prompt    = "Coding terms: kubernetes, postgres, kafka."
```

## Architecture (TL;DR)

```
┌───────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│  cli.py   │ → │ Recorder     │ → │ Transcriber │ → │ TextOutput   │
│ (orchest.)│   │ pw-record    │   │ OpenAI API  │   │ wtype        │
└───────────┘   └──────────────┘   └─────────────┘   └──────────────┘
                    adapter             port              port
                  (PipeWire)         (swappable)       (swappable)
```

`Transcriber` and `TextOutput` are `Protocol`s — adding a local `whisper.cpp` engine or X11 support is "implement the protocol, register in the CLI." Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap

- [x] **0.1** — Push-to-talk, Hyprland, OpenAI Whisper API
- [ ] **0.2** — Local backend (`whisper.cpp`), X11 adapter, Sway/GNOME smoke tests
- [ ] **0.3** — Streaming transcription, partial results
- [ ] **0.4** — Voice commands ("new line", "fix that"), text post-processing
- [ ] **1.0** — Assistant mode: wake word → command router → tool calls

## Contributing

PRs welcome. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) before opening one — it covers dev setup, conventional commits, and the architecture ground rules.

## License

[MIT](LICENSE) © 2026 thsergitox
