# Installation

`dino` is distro-agnostic: it relies on three pieces of software that ship in the official repos of every major Linux distribution.

## 1. System dependencies

### Arch / Manjaro / EndeavourOS

```bash
sudo pacman -S python pipewire wtype libnotify
```

### Debian / Ubuntu / Pop!_OS

```bash
sudo apt install python3 python3-pip pipewire-bin wtype libnotify-bin
```

### Fedora / Nobara

```bash
sudo dnf install python3 pipewire-utils wtype libnotify
```

### openSUSE

```bash
sudo zypper install python3 pipewire-tools wtype libnotify-tools
```

### Verify

```bash
pw-record --help     # should print PipeWire's capture help
wtype --help         # should print wtype's help
notify-send hello    # should pop a notification
```

If any of those fail, fix it before continuing — `dino` won't.

## 2. Install dino

The recommended path is [`pipx`](https://pipx.pypa.io/) so the install does not pollute your system Python.

```bash
sudo pacman -S python-pipx   # or: apt install pipx / dnf install pipx
pipx ensurepath

git clone https://github.com/thsergitox/dino.git
cd dino
pipx install .
```

Alternative without pipx:

```bash
python -m pip install --user .
```

Verify:

```bash
dino --version
```

## 3. Configure your OpenAI API key

Create one at <https://platform.openai.com/api-keys>. Pick **any** of these three options:

### Option A — Environment variable (simple)

Add to `~/.bashrc`, `~/.zshrc`, or `~/.config/fish/config.fish`:

```bash
export OPENAI_API_KEY="sk-..."
```

Reload your shell. If you launch Hyprland from a TTY, also export it in `~/.config/hypr/hyprland.conf`:

```ini
env = OPENAI_API_KEY,sk-...
```

### Option B — Config file (cleaner)

```bash
mkdir -p ~/.config/dino
cat > ~/.config/dino/config.toml <<'EOF'
[whisper]
api_key  = "sk-..."
model    = "whisper-1"
language = "en"
EOF
chmod 600 ~/.config/dino/config.toml
```

### Option C — Secret manager (most secure)

Pull the key from `pass`, `gnome-keyring`, `1password-cli`, etc. and export it before Hyprland starts. Example with `pass`:

```bash
export OPENAI_API_KEY="$(pass show openai/api-key)"
```

## 4. Bind a hotkey

See [HYPRLAND_SETUP.md](HYPRLAND_SETUP.md) for the push-to-talk binding and troubleshooting.

## Environment variables reference

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | API authentication | *(required)* |
| `DINO_MODEL` | Whisper model | `whisper-1` |
| `DINO_LANGUAGE` | ISO-639-1 hint (`en`, `es`, …) | auto-detect |
| `DINO_PROMPT` | Vocabulary bias prompt | *(empty)* |
| `XDG_CONFIG_HOME` | Config file root | `~/.config` |
| `XDG_RUNTIME_DIR` | PID / WAV root | `/tmp/dino-$UID` |

## Uninstall

```bash
pipx uninstall dino-voice
rm -rf ~/.config/dino
```
