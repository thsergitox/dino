# Installation

Three paths, from least friction to most control. **Pick one — they install the same software.**

| Path | When to use it |
|---|---|
| [Automated installer](#1-automated-installer-recommended) | You want a single command and an interactive wizard. |
| [Manual with `uv`](#2-manual--uv-recommended-for-tinkerers) | You already manage Python with `uv` (Astral). |
| [Manual with `pipx`](#3-manual--pipx) | You prefer the older, stable `pipx` workflow. |

> **v0.2 supports the OpenAI Whisper API only.** The setup wizard lists Groq, Deepgram, AssemblyAI, and local `whisper.cpp` in the provider menu so you can see what is coming, but selecting them returns a "coming soon" message. Multi-provider support lands in v0.3.

---

## 1. Automated installer (recommended)

```bash
curl -LsSf https://raw.githubusercontent.com/thsergitox/dino/main/scripts/install.sh | bash
```

The script:

1. Detects your distribution (Arch, Debian/Ubuntu, Fedora, openSUSE).
2. Installs missing system dependencies via your package manager (`python`, `pipewire`/`pw-record`, `wl-clipboard`, `libnotify`) — shows the exact sudo command in a big warning and asks before running it.
3. Installs `uv` if not present (you can decline), falling back to `pipx`.
4. Runs `uv tool install dino-voice` (or `pipx install dino-voice`).
5. Launches `dino setup` — a TUI that asks for your provider, API key, model, language hint, vocabulary prompt, and offers to append the Hyprland binding to your `hyprland.conf`.

**Environment overrides**:

| Variable | Effect |
|---|---|
| `DINO_INSTALLER=uv` or `pipx` | Force a specific backend. |
| `DINO_NO_SYSTEM_DEPS=1` | Skip the system-deps step (CI / unusual distros). |
| `DINO_SKIP_SETUP=1` | Don't launch `dino setup` at the end. |
| `DINO_GIT_REF=branch_or_tag` | When piped, install from a non-`main` ref. |

If you already cloned the repo, the same script works locally — it just installs from the checkout instead of GitHub:

```bash
git clone https://github.com/thsergitox/dino.git
cd dino
./scripts/install.sh
```

---

## 2. Manual — `uv` (recommended for tinkerers)

[`uv`](https://docs.astral.sh/uv/) is Astral's Python tool — 10–100× faster than `pipx`, manages Python versions automatically, configures PATH for you.

### 2a. Install system dependencies

```bash
# Arch / Manjaro / EndeavourOS / CachyOS
sudo pacman -S python pipewire wl-clipboard libnotify

# Debian / Ubuntu / Pop!_OS / Mint
sudo apt install python3 pipewire-bin wl-clipboard libnotify-bin

# Fedora / Nobara
sudo dnf install python3 pipewire-utils wl-clipboard libnotify

# openSUSE
sudo zypper install python3 pipewire-tools wl-clipboard libnotify-tools
```

`wtype` is **optional** (only needed if you set `[output].adapter = "wtype"` in `config.toml`). The default `wl-copy` flow doesn't need it.

### 2b. Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new shell or `source ~/.cargo/env` to pick up `uv` on PATH.

### 2c. Install `dino`

```bash
# From GitHub
uv tool install git+https://github.com/thsergitox/dino.git

# Or from a local checkout
git clone https://github.com/thsergitox/dino.git
cd dino
uv tool install .
```

### 2d. Configure

```bash
dino setup
```

---

## 3. Manual — `pipx`

If you don't want `uv` and don't have `pipx`:

```bash
# Arch
sudo pacman -S python-pipx
# Debian/Ubuntu
sudo apt install pipx
# Fedora
sudo dnf install pipx
# openSUSE
sudo zypper install python3-pipx

pipx ensurepath   # adds ~/.local/bin to PATH if needed
```

Then install `dino` (system deps from § 2a still required):

```bash
pipx install git+https://github.com/thsergitox/dino.git
# or, from a local checkout:
pipx install .
```

Configure:

```bash
dino setup
```

---

## 4. After installation

Verify:

```bash
dino --version
pw-record --help && wtype --help && notify-send hello
```

Bind the hotkey in Hyprland — `dino setup` offers to do this for you, or do it manually as shown in [HYPRLAND_SETUP.md](HYPRLAND_SETUP.md).

## Configuration reference

`dino` reads, in order:

1. Built-in defaults.
2. `~/.config/dino/config.toml` (`dino setup` writes this).
3. Environment variables (override anything in the file):

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | API authentication | *(required if not in config)* |
| `DINO_MODEL` | Whisper model | `whisper-1` |
| `DINO_LANGUAGE` | ISO-639-1 language hint for transcription (`en`, `es`, …) | auto-detect |
| `DINO_LANG` | TUI UI language (`es` / `en`) — override `[tui].language` | `es` |
| `DINO_PROMPT` | Vocabulary bias prompt | *(empty)* |
| `TERMINAL` | Override auto-detect for terminal-launch command | auto |
| `XDG_CONFIG_HOME` | Config file root | `~/.config` |
| `XDG_RUNTIME_DIR` | PID / WAV root | `/tmp/dino-$UID` |

## Uninstall

```bash
# uv install
uv tool uninstall dino-voice

# pipx install
pipx uninstall dino-voice

# Remove your configuration
rm -rf ~/.config/dino
```
