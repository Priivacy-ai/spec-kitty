# Quickstart — Validating Coord Write-Placement Closure & Birth-Cutover

How a reviewer confirms the mission's outcomes (maps to SC-001…006). Run from repo root.

## 1. Corpus green + stays green (SC-001)
```bash
PWHEADLESS=1 uv run pytest tests/specify_cli/migration/test_dogfood_corpus_backfilled.py -q
```
- After IC-01 front-load: passes. After IC-09 re-key: still passes, and would red if a mission merged un-reconciled.

## 2. Whole-tree write enforcement (SC-002)
```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_no_write_side_rederivation.py tests/architectural/test_safe_commit_import_boundary.py -q
```
- Inject a synthetic non-seam-derived `safe_commit`/`CommitTarget`/`write_meta` into a module **outside** the former 17-module allowlist → the gate reds and names the site.

## 3. Read-side partition safety (SC-003)
```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_read_surface_placement_guard.py -q
```
- A coord-homed read against a primary substitute raises a typed partition-mismatch error (no silent fallback).

## 4. Repair a pre-existing split-brain (SC-004)
```bash
uv run spec-kitty agent mission repair --mission <handle>          # forward-only under strict-ancestor + clean worktree
```
- On genuine divergence: refuses with a unified diff, zero mutation.

## 5. Born-reconciled mission (SC-005)
- Create a mission, `implement` a WP (claim + tick a subtask), `merge` it, then assert it lands `status_phase>=1` + `verify_backfill().ok` + non-empty snapshot with **no** `migrate backfill-runtime-state` invocation.

## 6. Classification + fork closure (SC-006)
```bash
uv run pytest tests/architectural/ -q -k "write_side or placement or safe_commit"
```
- `decisions.events.jsonl` / `traces/` route to COORD via the port; the `emit` HEAD-derived fallback is gone.

## Gate discipline
- Every FR ships a red-first test through the real entry point (DIRECTIVE_041).
- `ruff` + `mypy` zero-warning; the three existing write-side gates stay green (NFR-004).
