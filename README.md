# dino

> Persistent voice-dictation TUI for Hyprland. Pop the scratchpad, tap Space, speak, tap Space — the transcript lands on your clipboard.

`dino` is a small, hackable, distribution-agnostic voice-to-text tool for Wayland desktops. Since **v0.2** it ships as a Textual TUI that lives in a Hyprland special workspace: toggle it with `SUPER+Z`, record by tapping Space, watch a live FFT spectrum of your voice, and your transcribed text auto-copies to the clipboard for manual paste with `Ctrl+V`.

The internals are deliberately small (~700 LOC + numpy) and behind hexagonal ports: the STT engine (`Transcriber`) and the text-output method (`TextOutput`) are protocols, so adding `whisper.cpp` local, Groq, Deepgram, or X11 support later is a matter of writing one adapter — no rewrites.

**Status:** `0.2.0` — alpha. Targets **Hyprland** on **Wayland** with the **OpenAI Whisper API**.

---

## Why another dictation tool?

| Tool | Hotkey | Wayland | Hackable | Cloud-or-local |
|---|---|---|---|---|
| `nerd-dictation` | ❌ DIY | ⚠️ wrappers | ✅ | local only |
| OpenWhispr | ✅ | ✅ | Electron | both |
| whisrs | ✅ | ✅ | Rust | both |
| **dino** | ✅ scratchpad | ✅ | ✅ Python, ports & adapters | cloud (local planned v0.3) |

`dino` exists to be the small, readable codebase you can grow into a full voice assistant — not a finished product to consume.

## Requirements

| Component | Why | Install (Arch / Debian) |
|---|---|---|
| Python ≥ 3.10 | runtime | `pacman -S python` / `apt install python3` |
| PipeWire (`pw-record`) | audio capture | `pacman -S pipewire` / `apt install pipewire-bin` |
| `wl-clipboard` | text output (`wl-copy`) | `pacman -S wl-clipboard` / `apt install wl-clipboard` |
| `wl-clip-persist` *(recommended)* | keep clipboard across sessions | `pacman -S wl-clip-persist` (Arch extra) / `cargo install wl-clip-persist` |
| `notify-send` *(optional)* | desktop notifications | `pacman -S libnotify` / `apt install libnotify-bin` |
| OpenAI API key | transcription | <https://platform.openai.com/api-keys> |

A full per-distro install guide is in [docs/INSTALL.md](docs/INSTALL.md).

## Quick start

**One-liner install** (system deps + Python package + interactive setup):

```bash
curl -LsSf https://raw.githubusercontent.com/thsergitox/dino/main/scripts/install.sh | bash
```

The installer:

1. Detects your distribution (Arch, Debian/Ubuntu, Fedora, openSUSE) and shows the exact sudo command for the missing deps **in a big warning** before asking permission to run it.
2. Picks `uv tool install` (recommended) or `pipx install` based on what you have.
3. Runs `dino setup` — a TUI that asks for your provider, API key, model, language, lifecycle (always-on vs lazy-spawn), and offers to append the Hyprland scratchpad block to your `hyprland.conf`.

> **v0.2 supports OpenAI Whisper only.** The setup menu shows Groq, Deepgram, AssemblyAI, and local `whisper.cpp` as **coming in v0.3**.

**Already cloned?**

```bash
./scripts/install.sh
```

**Want to drive it manually?** See [docs/INSTALL.md](docs/INSTALL.md) for the `uv`, `pipx`, and step-by-step paths.

Reload Hyprland (`hyprctl reload`), press `SUPER+Z`, the scratchpad appears. Inside: Space starts, Space stops, the transcript is on your clipboard.

## CLI

```text
dino           # launch the TUI (no args)
dino tui       # launch the TUI explicitly (accepts --lang es|en)
dino setup     # interactive first-run wizard
dino start     # legacy push-to-talk press (used in Hyprland bind)
dino stop      # legacy push-to-talk release (used in Hyprland bindr)
dino toggle    # legacy: start if idle, otherwise stop
dino --version
```

The legacy commands are kept for users who prefer a hotkey-driven flow without a persistent window. They now copy via `wl-copy` instead of typing.

State lives under `$XDG_RUNTIME_DIR/dino/` — a stray crash never leaves junk in your home directory.

## Configuration

`dino` reads, in order:

1. Built-in defaults.
2. `~/.config/dino/config.toml` (or `$XDG_CONFIG_HOME/dino/config.toml`).
3. Environment variables (`OPENAI_API_KEY`, `DINO_MODEL`, `DINO_LANGUAGE`, `DINO_LANG`, `DINO_PROMPT`, `TERMINAL`).

Example `config.toml`:

```toml
[whisper]
api_key  = "sk-..."
model    = "whisper-1"      # or gpt-4o-transcribe / gpt-4o-mini-transcribe
language = "es"             # ISO-639-1; omit to auto-detect
prompt   = "Términos: kubernetes, postgres, kafka, hyprland."

[tui]
language  = "es"            # es | en
lifecycle = "exec-once"     # exec-once | lazy

[output]
adapter = "wl-copy"         # wl-copy | wtype
```

## Architecture (TL;DR)

```
┌────────────┐   ┌──────────────────┐   ┌─────────────┐   ┌──────────────┐
│ tui/app.py │ → │ audio/streaming  │ → │ Transcriber │ → │ TextOutput   │
│ (TUI +     │   │ pw-record - raw  │   │ OpenAI API  │   │ wl-copy      │
│  state)    │   │ stdout → Queue   │   │             │   │ (wtype opt-in)│
└────────────┘   └──────────────────┘   └─────────────┘   └──────────────┘
       │              numpy FFT             port              port
       │              30 FPS              (swappable)       (swappable)
       ▼
SpectrumWidget
```

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap

- [x] **0.1** — Push-to-talk CLI, Hyprland bind/bindr, OpenAI Whisper API, wtype output.
- [x] **0.2** — Persistent TUI in Hyprland scratchpad, FFT spectrum, wl-copy default, Spanish/English UI.
- [ ] **0.3** — Multi-provider STT (Groq, Deepgram, AssemblyAI, local `whisper.cpp`), streaming transcripts.
- [ ] **0.4** — Voice commands inside TUI ("punto", "nueva línea"), text post-processing.
- [ ] **1.0** — Assistant mode: wake word → command router → tool calls.

## Contributing

PRs welcome. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) before opening one — it covers dev setup, conventional commits, and the architecture ground rules.

## License

[MIT](LICENSE) © 2026 thsergitox
