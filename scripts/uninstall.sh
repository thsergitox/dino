#!/usr/bin/env bash
# dino uninstaller — Linux, Wayland-first.
#
# Removes:
#   - The dino-voice Python package (via uv tool or pipx).
#   - The dino block in ~/.config/hypr/hyprland.conf (with confirmation).
#   - ~/.config/dino/                                  (with confirmation).
#   - Any leftover runtime files under $XDG_RUNTIME_DIR/dino/.
#
# Does NOT touch:
#   - System packages (pw-record, wl-clipboard, libnotify, wl-clip-persist, ...)
#     They are shared system tools and may be used by other apps.
#   - uv / pipx themselves.
#
# Flags (env vars):
#   DINO_UNINSTALL_YES=1   Answer "yes" to every confirmation (CI / unattended).

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
ask()  {
    local q="$1" default="${2:-y}"
    [ "${DINO_UNINSTALL_YES:-0}" = "1" ] && return 0
    local hint="[Y/n]"; [ "$default" = "n" ] && hint="[y/N]"
    local reply
    read -rp "$(printf '%s?%s %s %s ' "$CYAN" "$RESET" "$q" "$hint")" reply </dev/tty || true
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy] ]]
}

banner() {
    cat >&2 <<EOF
${YELLOW}${BOLD}
   ┌─────────────────────────────────────────────┐
   │   dino — uninstaller                        │
   └─────────────────────────────────────────────┘
${RESET}
EOF
}

# ── Steps ────────────────────────────────────────────────────────────────────

stop_running_tui() {
    if pgrep -f 'dino tui' >/dev/null 2>&1; then
        log "Stopping any running dino TUI…"
        pkill -f 'dino tui' 2>/dev/null || true
        sleep 0.3
        ok "Stopped."
    fi
}

uninstall_package() {
    local removed=0
    if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q '^dino-voice'; then
        log "Removing dino-voice via uv tool…"
        uv tool uninstall dino-voice && ok "uv tool: removed dino-voice." && removed=1
    fi
    if command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q 'dino-voice'; then
        log "Removing dino-voice via pipx…"
        pipx uninstall dino-voice && ok "pipx: removed dino-voice." && removed=1
    fi
    if [ "$removed" -eq 0 ]; then
        warn "No dino-voice installation detected (uv/pipx). Skipped."
    fi
}

remove_config_dir() {
    local d="$HOME/.config/dino"
    if [ ! -e "$d" ]; then
        return 0
    fi
    log "Found config directory: $d"
    ls -la "$d" 2>/dev/null | sed 's/^/   /' >&2
    echo >&2
    if ask "Delete $d (config.toml, dino-toggle.sh)?" "y"; then
        rm -rf "$d"
        ok "Removed $d"
    else
        warn "Kept $d"
    fi
}

remove_runtime_dir() {
    local rt="${XDG_RUNTIME_DIR:-/tmp/dino-$(id -u)}/dino"
    if [ -d "$rt" ]; then
        rm -rf "$rt" && ok "Removed runtime dir $rt"
    fi
}

remove_hypr_block() {
    local f="$HOME/.config/hypr/hyprland.conf"
    if [ ! -f "$f" ]; then
        return 0
    fi
    if ! grep -qE 'dino|class:.*dino' "$f" 2>/dev/null; then
        log "No dino directives in $f."
        return 0
    fi

    log "Found dino-related lines in $f:"
    echo >&2
    grep -nE 'dino|class:.*dino|wl-clip-persist' "$f" | sed "s/^/   ${DIM}/; s/\$/${RESET}/" >&2 || true
    echo >&2

    if ! ask "Remove the dino block (and the wl-clip-persist line if added by dino)?" "y"; then
        warn "Kept $f as-is."
        return 0
    fi

    # Safer transform: use Python. Match any line containing dino-related tokens,
    # plus the wl-clip-persist exec-once that dino's wizard added. Collapse
    # adjacent blank lines so we don't leave gaping holes.
    python3 - "$f" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()

# Patterns that identify dino-owned lines.
DINO_PATTERNS = [
    r"dino\b",                    # 'class dino', 'togglespecialworkspace, dino', '-- dino tui', etc.
    r"class:\s*\^?\(?dino\)?\$?", # windowrule regex
]
WL_CLIP_PATTERNS = [
    r"# wl-clip-persist .*added by `dino setup`",
    r"^exec-once\s*=\s*wl-clip-persist\s*$",
]
ALL = [re.compile(p) for p in DINO_PATTERNS + WL_CLIP_PATTERNS]

filtered: list[str] = []
for line in lines:
    if any(p.search(line) for p in ALL):
        continue
    filtered.append(line)

# Collapse 2+ consecutive blank lines into one.
deduped: list[str] = []
prev_blank = False
for line in filtered:
    blank = line.strip() == ""
    if blank and prev_blank:
        continue
    deduped.append(line)
    prev_blank = blank

# Strip leading/trailing all-blank lines.
while deduped and deduped[0].strip() == "":
    deduped.pop(0)
while deduped and deduped[-1].strip() == "":
    deduped.pop()
deduped.append("")  # final newline

with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(deduped)
PY
    ok "Cleaned $f"

    if command -v hyprctl >/dev/null 2>&1 && [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
        if hyprctl reload >/dev/null 2>&1; then
            ok "hyprctl reload OK."
        else
            warn "hyprctl reload reported issues — check the output manually."
        fi
    fi
}

summary() {
    cat >&2 <<EOF

${GREEN}${BOLD}Done.${RESET}

The following were NOT removed because they are system-wide or shared:
   ${DIM}• pw-record (pipewire)
   • wl-copy   (wl-clipboard)
   • wtype     (optional adapter)
   • notify-send (libnotify)
   • wl-clip-persist binary (the hyprland.conf line was removed if present)
   • uv / pipx themselves
   • Your OpenAI API key — only the local config.toml was deleted.${RESET}

To reinstall from this checkout:  ${CYAN}./scripts/install.sh${RESET}
EOF
}

main() {
    banner
    stop_running_tui
    uninstall_package
    remove_config_dir
    remove_runtime_dir
    remove_hypr_block
    summary
}

main "$@"
