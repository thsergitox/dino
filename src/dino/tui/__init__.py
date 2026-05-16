# Intentionally empty.
#
# Importing `dino.tui.app` pulls in Textual + numpy (~500ms cold start), so we
# avoid re-exporting `DinoApp` at the package level. Callers that need the App
# should `from dino.tui.app import DinoApp` directly — this keeps `state.py`
# importable in tests and the legacy CLI without dragging in heavy deps.
