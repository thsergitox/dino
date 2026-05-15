# Contributing to dino

Thanks for considering a contribution. This document is short on purpose — read it once and you have everything you need.

## Ground rules

1. **Read [ARCHITECTURE.md](ARCHITECTURE.md) first.** New features almost always slot in as a new adapter behind an existing port. If your change requires touching `cli.py` *and* an adapter *and* a port, stop and open an issue first — we should discuss the design before code.
2. **Distribution-agnostic.** No assumption that the user runs Arch. If you need a system binary, document the install command for Arch / Debian / Fedora / openSUSE.
3. **Wayland-first for 0.x.** X11 support is welcome but lives in a separate adapter (`src/dino/output/xdotool_inject.py`), never as branching inside the Wayland one.
4. **No silent failures.** Either `notify-send` the user, log to stderr, or both. Never swallow exceptions.

## Development setup

```bash
git clone https://github.com/thsergitox/dino.git
cd dino
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

You need an `OPENAI_API_KEY` to test end-to-end transcription. For unit work without the API, mock `OpenAIWhisper.transcribe`.

## Running checks locally

```bash
ruff check .
ruff format --check .
pytest -q
```

CI runs the same three commands — if they pass locally, they pass in CI.

## Commit conventions

We use **Conventional Commits**. The subject line must match `<type>(<scope>): <summary>`:

| Type | When |
|---|---|
| `feat` | New capability for the user. |
| `fix` | Bug fix the user can perceive. |
| `docs` | Docs only. |
| `refactor` | Code reshuffle, no behavior change. |
| `test` | Test changes only. |
| `chore` | Build, deps, tooling. |
| `perf` | Performance change. |

Examples:

```
feat(stt): add Groq Whisper-v3 adapter
fix(audio): handle pw-record SIGTERM race on stop
docs: clarify Hyprland env var caveat
```

Keep the subject under 72 characters. Use the body for the *why*, not the *what* — the diff already shows the what.

**Do not** add `Co-Authored-By` lines, AI attribution, or `Signed-off-by` (unless you actually use DCO).

## Pull-request checklist

Before opening a PR, confirm:

- [ ] `ruff check .` and `ruff format --check .` pass.
- [ ] `pytest -q` passes.
- [ ] You manually exercised the change (recorded, transcribed, typed) at least once.
- [ ] You updated the relevant doc(s) under `docs/` if behavior changed.
- [ ] You did **not** check in any audio file, API key, or `.env`.

Open the PR against `main`. Keep it small — one logical change per PR. If you have two changes, open two PRs.

## Reporting bugs

Use the bug-report issue template. The most useful bug reports include:

- Output of `dino --version`.
- Compositor + version (`hyprctl version` for Hyprland).
- Output of `pw-record --version` and `wtype -v`.
- The exact `dino` command and the full stderr.

## Roadmap and good-first-issues

The high-level roadmap lives in the [README](../README.md#roadmap). Issues tagged [`good first issue`](https://github.com/thsergitox/dino/labels/good%20first%20issue) are scoped small on purpose — start there.

## Code of conduct

Be kind. Disagree on technical grounds with evidence. Personal attacks get a one-strike ban.
