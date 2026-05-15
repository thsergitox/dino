# Hyprland setup

`dino` is built around push-to-talk, and push-to-talk needs two events from your compositor: **press** (start recording) and **release** (stop, transcribe, type). Hyprland provides exactly that with `bind` and `bindr`.

## Minimal binding

Add to `~/.config/hypr/hyprland.conf`:

```ini
# Push-to-talk dictation
bind  = SUPER, V, exec, dino start
bindr = SUPER, V, exec, dino stop
```

Reload Hyprland:

```bash
hyprctl reload
```

That's it — focus any text field, hold `SUPER+V`, talk, release.

## Choosing a good hotkey

Some tips from daily use:

- **Use a modifier + a non-letter** to avoid colliding with apps that may grab the key. `SUPER+V` collides with paste in some apps; consider `SUPER+SPACE` (if your launcher is on a chord), `SUPER+grave`, or a function key.
- **Avoid `SUPER` alone** — Hyprland treats lone-modifier binds differently across versions and they tend to misfire.
- **Mouse buttons work too**. Side mouse buttons (`mouse:276`, `mouse:275`) are excellent for push-to-talk because you can clutch them while typing.

```ini
# Push-to-talk on side mouse button
bind  = , mouse:276, exec, dino start
bindr = , mouse:276, exec, dino stop
```

## Toggle mode (alternative)

If you prefer one-shot toggling instead of holding the key:

```ini
bind = SUPER, V, exec, dino toggle
```

`dino toggle` starts a recording if idle, otherwise stops and transcribes.

## Environment variables under Hyprland

If you launch Hyprland from a display manager (SDDM, gdm, …) your shell's `~/.bashrc` or `~/.zshrc` is **not** sourced, so `OPENAI_API_KEY` won't be visible to `dino`.

Two clean fixes:

**Use a config file** (recommended): see [INSTALL.md § Option B](INSTALL.md#option-b--config-file-cleaner).

**Export inside Hyprland's config**:

```ini
env = OPENAI_API_KEY,sk-...
```

Reload after editing.

## Notifications

`dino` uses `notify-send`. On Hyprland you'll typically want `mako` or `dunst` running. If you don't, dictation still works — you just won't see "Listening…" / "Transcribing…" toasts.

## Troubleshooting

### Nothing happens when I press the hotkey

Run `dino start` and `dino stop` manually from a terminal first. Hyprland's `exec` doesn't print errors; the terminal does. The most common causes:

- `OPENAI_API_KEY` is unset under the Hyprland session (see above).
- `pw-record` or `wtype` is not installed.
- Hyprland version too old for `bindr`. Upgrade or switch to `dino toggle`.

### `wtype` types nothing into Electron / Chromium apps

This is a known Wayland limitation when the app forces XWayland. Either run the app natively (`--ozone-platform=wayland`), or use `dino`'s clipboard fallback (planned in 0.2).

### Audio file is empty / "no speech detected"

- Confirm the default PipeWire source picks up your mic: `pw-record /tmp/test.wav` for 3 seconds, then `aplay /tmp/test.wav`.
- If the wrong source is captured, set the right one as default in `wpctl` or `pavucontrol`.

### "Already recording — ignoring duplicate start"

A previous run did not stop cleanly. Recover with:

```bash
dino stop || true
rm -f "${XDG_RUNTIME_DIR:-/tmp/dino-$(id -u)}/dino/recorder.pid"
```
