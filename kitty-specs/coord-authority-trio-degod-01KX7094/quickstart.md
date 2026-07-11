# Quickstart / Validation: Coord-Authority Trio Degod

1. **Characterization green pre-refactor**: `uv run pytest tests/characterization/ -q` passes on the untouched trio (FR-008).
2. **Decompose a module**: extract cores → thin Typer-shell + executor; re-run characterization + the module's existing tests (green via shims/repin).
3. **Seam routing**: `rg` the trio for leaf-resolver imports → zero outside the allowed wrappers; `uv run pytest tests/architectural/test_single_mission_surface_resolver.py -q` (trio seam-only pin) green.
4. **Complexity**: SonarCloud branch review → S3776 ≤15 on the touched functions; `rg "noqa: C901" <trio>` → zero.
5. **#2508**: the red-first repro fails on `main`, passes on the branch; `safe_commit` fallback no longer misfires.
6. **Closeout**: full `tests/` + characterization + `tests/architectural/` + ruff + mypy green; no un-normalized output/transition diff.
