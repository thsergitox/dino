#!/usr/bin/env bash
# dino installer — Linux, Wayland-first.
#
# Usage (from a cloned repo):
#   ./scripts/install.sh
#
# Usage (one-shot via curl):
#   curl -LsSf https://raw.githubusercontent.com/thsergitox/dino/main/scripts/install.sh | bash
#
# Flags (env vars):
#   DINO_INSTALLER=uv|pipx     Force a specific install backend (default: prefer uv).
#   DINO_NO_SYSTEM_DEPS=1      Skip the system-dependency step (CI / unusual distros).
#   DINO_SKIP_SETUP=1          Don't run `dino setup` at the end (CI / unattended).
#   DINO_GIT_REF=branch|tag    When piped, install from this ref (default: main).

set -euo pipefail

# ── Pretty output ────────────────────────────────────────────────────────────
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$'\033[1m'; CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
    RED=$'\033[31m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
    BOLD=""; CYAN=""; GREEN=""; YELLOW=""; RED=""; DIM=""; RESET=""
fi

log()  { printf '%s==>%s %s\n' "$CYAN" "$RESET" "$1" >&2; }
ok()   { printf '%s✓%s   %s\n' "$GREEN" "$RESET" "$1" >&2; }
warn() { printf '%s!%s   %s\n' "$YELLOW" "$RESET" "$1" >&2; }
die()  { printf '%s✗%s   %s\n' "$RED" "$RESET" "$1" >&2; exit 1; }
ask()  { # prompt → echoes y/n
    local q="$1" default="${2:-y}"
    local hint="[Y/n]"; [ "$default" = "n" ] && hint="[y/N]"
    local reply
    read -rp "$(printf '%s?%s %s %s ' "$CYAN" "$RESET" "$q" "$hint")" reply </dev/tty || true
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy] ]]
}

banner() {
    cat >&2 <<EOF
${CYAN}${BOLD}
   ┌─────────────────────────────────────────────┐
   │   dino — push-to-talk voice dictation       │
   │   Wayland · Hyprland · OpenAI Whisper       │
   └─────────────────────────────────────────────┘
${RESET}
EOF
}

# ── Distro detection ─────────────────────────────────────────────────────────
detect_distro() {
    if [ -r /etc/os-release ]; then
        . /etc/os-release
        echo "${ID_LIKE:-$ID}"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    [ "${DINO_NO_SYSTEM_DEPS:-0}" = "1" ] && { log "Skipping system deps (DINO_NO_SYSTEM_DEPS=1)."; return; }

    local distro
    distro=$(detect_distro)
    log "Detected distro family: ${BOLD}${distro}${RESET}"

    local missing=()
    command -v pw-record   >/dev/null 2>&1 || missing+=("pw-record (PipeWire)")
    command -v wtype       >/dev/null 2>&1 || missing+=("wtype")
    command -v notify-send >/dev/null 2>&1 || missing+=("notify-send (libnotify)")
    command -v python3     >/dev/null 2>&1 || missing+=("python3")

    if [ ${#missing[@]} -eq 0 ]; then
        ok "System dependencies already installed."
        return
    fi

    warn "Missing: ${missing[*]}"

    case "$distro" in
        *arch*|*manjaro*|*endeavouros*|*cachyos*)
            ask "Install via pacman? (sudo required)" "y" \
                && sudo pacman -S --needed --noconfirm python pipewire wtype libnotify
            ;;
        *debian*|*ubuntu*|*pop*|*mint*)
            ask "Install via apt? (sudo required)" "y" \
                && { sudo apt update && sudo apt install -y python3 python3-pip pipewire-bin wtype libnotify-bin; }
            ;;
        *fedora*|*nobara*|*rhel*)
            ask "Install via dnf? (sudo required)" "y" \
                && sudo dnf install -y python3 pipewire-utils wtype libnotify
            ;;
        *suse*|*opensuse*)
            ask "Install via zypper? (sudo required)" "y" \
                && sudo zypper install -y python3 pipewire-tools wtype libnotify-tools
            ;;
        *)
            die "Unknown distro. Install manually: python3, pipewire (pw-record), wtype, libnotify, then re-run with DINO_NO_SYSTEM_DEPS=1."
            ;;
    esac
    ok "System dependencies installed."
}

# ── Python install backend (uv preferred) ────────────────────────────────────
ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        ok "uv already installed ($(uv --version))."
        return 0
    fi
    warn "uv not found."
    if ask "Install uv now? (recommended — 10–100× faster than pip, manages Python automatically)" "y"; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Pick up the freshly installed binary without requiring a new shell.
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        command -v uv >/dev/null 2>&1 || die "uv install ran but the binary isn't on PATH. Open a new shell and re-run."
        ok "uv installed."
    else
        return 1
    fi
}

ensure_pipx() {
    if command -v pipx >/dev/null 2>&1; then
        ok "pipx already installed."
        return 0
    fi
    warn "pipx not found."
    case "$(detect_distro)" in
        *arch*|*manjaro*|*endeavouros*|*cachyos*) sudo pacman -S --needed --noconfirm python-pipx ;;
        *debian*|*ubuntu*|*pop*|*mint*)           sudo apt install -y pipx ;;
        *fedora*|*nobara*|*rhel*)                 sudo dnf install -y pipx ;;
        *suse*|*opensuse*)                        sudo zypper install -y python3-pipx ;;
        *) die "Install pipx manually for your distro." ;;
    esac
    pipx ensurepath >/dev/null
    export PATH="$HOME/.local/bin:$PATH"
}

install_dino() {
    local backend="${DINO_INSTALLER:-}"
    local source

    # Source resolution: cloned repo if pyproject.toml is here, else from git.
    if [ -f "$(dirname "$0")/../pyproject.toml" ]; then
        source="$(cd "$(dirname "$0")/.." && pwd)"
        log "Installing from local checkout: ${source}"
    else
        local ref="${DINO_GIT_REF:-main}"
        source="git+https://github.com/thsergitox/dino.git@${ref}"
        log "Installing from ${source}"
    fi

    # Backend selection.
    if [ -z "$backend" ]; then
        if ensure_uv 2>/dev/null; then backend="uv"; else backend="pipx"; fi
    fi

    case "$backend" in
        uv)
            ensure_uv || die "uv requested but unavailable."
            uv tool install --force "$source"
            ok "Installed via uv tool."
            ;;
        pipx)
            ensure_pipx
            pipx install --force "$source"
            ok "Installed via pipx."
            ;;
        *)
            die "Unknown DINO_INSTALLER=$backend (expected: uv | pipx)."
            ;;
    esac

    if ! command -v dino >/dev/null 2>&1; then
        warn "'dino' is not on PATH yet. Add ~/.local/bin to PATH or open a new shell."
        export PATH="$HOME/.local/bin:$PATH"
    fi
    ok "dino $(dino --version 2>/dev/null | awk '{print $2}') ready."
}

# ── Run the interactive setup ────────────────────────────────────────────────
run_setup() {
    [ "${DINO_SKIP_SETUP:-0}" = "1" ] && { log "Skipping setup (DINO_SKIP_SETUP=1)."; return; }
    echo
    log "Launching interactive setup…"
    dino setup
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    banner
    install_system_deps
    install_dino
    run_setup
    echo
    ok "All done. Bind your hotkey in Hyprland and start dictating."
}

main "$@"
