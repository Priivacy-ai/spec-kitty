# Implementation Plan: Acceptance Pipeline Regression Fixes

**Branch**: `052-acceptance-pipeline-regression-fixes` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)

## Summary

Fix 4 regressions in the acceptance/verification pipeline introduced during the status model refactor. The core issue is that `collect_feature_summary()` calls `materialize()` — which always rewrites `status.json` with a fresh timestamp — before checking git cleanliness, making acceptance self-defeating. Secondary fixes: persist the acceptance commit SHA into `meta.json`, bootstrap `sys.path` for standalone script invocation, and catch `StoreError` as a structured acceptance failure.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: None new — uses existing pathlib, json, subprocess, dataclasses
**Storage**: Filesystem (meta.json, status.json, status.events.jsonl)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: macOS/Linux CLI
**Project Type**: Single Python package
**Constraints**: No new external dependencies (NFR-001). Both `src/` and `scripts/` copies must stay in sync (C-001).

## Constitution Check

*No constitution file present — skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/052-acceptance-pipeline-regression-fixes/
├── spec.md
├── plan.md              # This file
├── meta.json
├── checklists/
│   └── requirements.md
└── tasks/
    └── README.md
```

### Source Code (affected files)

```
src/specify_cli/
├── acceptance.py                          # WP01, WP02: collect_feature_summary(), perform_acceptance()
├── feature_metadata.py                    # WP02: record_acceptance() — already correct, caller is wrong
├── status/
│   ├── reducer.py                         # WP01: materialize() — needs read-only variant or deferred call
│   └── store.py                           # WP01: StoreError — needs to be caught in acceptance
├── cli/commands/
│   └── accept.py                          # WP01: error handler needs StoreError coverage
└── scripts/tasks/
    ├── tasks_cli.py                       # WP03: sys.path bootstrap
    └── acceptance_support.py              # WP01, WP02, WP03: standalone copy (mirrors acceptance.py)

scripts/tasks/
├── acceptance_support.py                  # Legacy copy — synced from src/ copy
└── tasks_cli.py                           # Legacy copy
.kittify/scripts/tasks/
└── acceptance_support.py                  # Generated copy — synced from scripts/
```

## Bug Analysis

### P0: materialize() dirties repo before cleanliness check

**Root cause**: `collect_feature_summary()` calls `materialize(feature_dir)` at line 361 (`acceptance.py`) / line 463 (`acceptance_support.py`). `materialize()` always writes `status.json` with a fresh `materialized_at` timestamp (`reducer.py:167`), even when the underlying events haven't changed. This happens *before* `git_status_lines()` at line 455 / 556, so the cleanliness check sees `status.json` as modified.

**Fix strategy**: Move the `git_status_lines()` call *before* the `materialize()` call. The git cleanliness check is a read-only observation of the working tree — it has no dependency on the materialized snapshot. The snapshot is needed only for lane bucketing, which happens after both calls. Additionally, wrap the `materialize()` call in a `StoreError` handler (P2 fix shares this call site).

**Affected files**: `src/specify_cli/acceptance.py`, `src/specify_cli/scripts/tasks/acceptance_support.py`

### P1 (standalone): tasks_cli.py can't import specify_cli.*

**Root cause**: `tasks_cli.py` (line 18-20) adds only its own `SCRIPT_DIR` to `sys.path`. When `acceptance_support.py` was refactored to import `specify_cli.status.*` and `specify_cli.feature_metadata`, it gained a dependency on the package being importable. But the standalone script entrypoint never adds the repo `src/` root to `sys.path`.

**Fix strategy**: In the `sys.path` bootstrap block of `tasks_cli.py` (and `acceptance_support.py`), also add the repo's `src/` directory. The script already knows its location via `SCRIPT_DIR = Path(__file__).resolve().parent`. Walk up to find `src/` relative to the script's known position in `src/specify_cli/scripts/tasks/`. For the scripts/ copy, walk up similarly from `scripts/tasks/`.

**Affected files**: `src/specify_cli/scripts/tasks/tasks_cli.py`, `src/specify_cli/scripts/tasks/acceptance_support.py`, `scripts/tasks/tasks_cli.py`, `scripts/tasks/acceptance_support.py`

### P1 (commit SHA): perform_acceptance() doesn't persist SHA

**Root cause**: `perform_acceptance()` calls `record_acceptance(..., accept_commit=None)` at line 545/628 *before* creating the git commit. After the commit, the SHA is captured into the local `accept_commit` variable (line 568/651) and returned in the `AcceptanceResult`, but never written back to `meta.json`.

**Fix strategy**: After the commit is created and the SHA is captured, call `record_acceptance()` again (or a lighter helper) to update `meta.json` with the real SHA. The `feature_metadata.record_acceptance()` function already supports the `accept_commit` parameter — the bug is that the caller passes `None` and never updates. The simplest fix: after getting the SHA, reload meta.json, set `accept_commit` and `acceptance_history[-1]["accept_commit"]`, and write it back. Use `feature_metadata.load_meta()` + `feature_metadata.write_meta()` for the update to keep it minimal (avoid appending a duplicate history entry).

**Affected files**: `src/specify_cli/acceptance.py`, `src/specify_cli/scripts/tasks/acceptance_support.py`

### P2: StoreError crashes CLI

**Root cause**: `collect_feature_summary()` calls `materialize()` which calls `read_events()`, which raises `StoreError` on malformed JSONL. Neither `collect_feature_summary()` nor `accept.py`'s error handler catches `StoreError`. The CLI's `try/except` at `accept.py:176` only catches `AcceptanceError`.

**Fix strategy**: Catch `StoreError` inside `collect_feature_summary()` (at the `materialize()` call site) and convert it to an `AcceptanceError` with a user-friendly message. This keeps the fix contained — `accept.py` already handles `AcceptanceError` correctly.

**Affected files**: `src/specify_cli/acceptance.py`, `src/specify_cli/scripts/tasks/acceptance_support.py`

## Work Package Design

### WP01: Verification Path Hardening (FR-001, FR-004, FR-005)

**Surface**: The read-only verification path in `collect_feature_summary()`.

**Changes in `src/specify_cli/acceptance.py`**:
1. Move `git_dirty = git_status_lines(repo_root)` from line ~454 to *before* the `materialize()` call (before line 351). This means the git status is captured before any file writes.
2. Wrap the `materialize()` call (line 361) in a `try/except StoreError` block. Import `StoreError` from `specify_cli.status.store`. On catch, convert to `AcceptanceError` with message like: `f"Status event log is corrupted for feature '{feature}': {exc}"`.
3. The existing flow already handles `events_path.exists()` check — the `StoreError` catch covers the case where the file exists but contains invalid JSON.

**Changes in `src/specify_cli/scripts/tasks/acceptance_support.py`**:
Mirror the same reorder and `StoreError` catch. Import `StoreError` alongside existing `materialize` and `EVENTS_FILENAME` imports.

**Changes in `accept.py`**: None needed — `AcceptanceError` is already caught.

**Dependency**: None — this is the first WP.

### WP02: Acceptance Metadata Persistence (FR-002, FR-005)

**Surface**: The write path in `perform_acceptance()`.

**Changes in `src/specify_cli/acceptance.py`**:
After the commit is created and `accept_commit` is captured (after line 573), add:
```python
# Persist commit SHA to meta.json
if accept_commit:
    from specify_cli.feature_metadata import load_meta, write_meta
    meta = load_meta(summary.feature_dir)
    if meta is not None:
        meta["accept_commit"] = accept_commit
        history = meta.get("acceptance_history", [])
        if history:
            history[-1]["accept_commit"] = accept_commit
        write_meta(summary.feature_dir, meta)
```
This is a targeted update — not a second `record_acceptance()` call — to avoid appending a duplicate history entry.

The `meta.json` is already staged and committed at this point, so this update happens *after* the acceptance commit. That's acceptable: the SHA is recorded for reference. If needed, a follow-up `git add + git commit --amend` could be considered, but that changes the SHA and creates a chicken-and-egg problem. Recording the SHA in a subsequent write (without a new commit) is the pragmatic approach.

**Changes in `src/specify_cli/scripts/tasks/acceptance_support.py`**: Mirror the same post-commit SHA persistence.

**Dependency**: WP01 (shares the same two files).

### WP03: Standalone Script Contract (FR-003)

**Surface**: The `sys.path` bootstrap in standalone scripts.

**Changes in `src/specify_cli/scripts/tasks/tasks_cli.py`**:
After the existing `sys.path.insert(0, str(SCRIPT_DIR))` block (line 18-20), add:
```python
# Bootstrap repo src/ root for specify_cli.* imports
_SRC_ROOT = SCRIPT_DIR.parent.parent.parent.parent  # scripts/tasks/ → specify_cli → src
if _SRC_ROOT.name == "src" and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))
```

**Changes in `src/specify_cli/scripts/tasks/acceptance_support.py`**:
Add a similar bootstrap at the top of the file, before the `from specify_cli.status.reducer import materialize` line. Since this file currently has no `sys.path` manipulation, add it after the stdlib imports:
```python
SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_ROOT = SCRIPT_DIR.parent.parent.parent.parent  # scripts/tasks/ → specify_cli → src
if _SRC_ROOT.name == "src" and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))
```

**Changes in `scripts/tasks/tasks_cli.py`** and **`scripts/tasks/acceptance_support.py`**:
The legacy copies under `scripts/tasks/` have a different directory structure (they're at repo root, not under `src/`). These currently do NOT import `specify_cli.*`, so they don't need the bootstrap. However, per C-001, if the src/ copies are synced to scripts/, the bootstrap must detect its location dynamically. Use a parent-walk approach:
```python
# Walk up from SCRIPT_DIR looking for src/ containing specify_cli/
_candidate = SCRIPT_DIR
for _ in range(6):  # bounded walk
    _candidate = _candidate.parent
    _src = _candidate / "src"
    if (_src / "specify_cli").is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
        break
```

**Dependency**: WP01 (the files modified in WP01 must have the sys.path fix to work standalone).

### WP04: Regression Coverage and Copy-Parity Sweep (NFR-002, NFR-003)

**Surface**: Test files only.

**New tests** (in `tests/specify_cli/`):

1. **test_acceptance_materialize_ordering**: Create a temp git repo with a clean feature (all WPs done, event log present). Call `collect_feature_summary()`. Assert that `git_dirty` is empty — proving that `materialize()` doesn't dirty the repo before the check.

2. **test_acceptance_commit_sha_persisted**: Mock or create a real acceptance scenario. Call `perform_acceptance()`. Assert that `meta.json` contains a non-None `accept_commit` field and that `acceptance_history[-1]["accept_commit"]` matches.

3. **test_standalone_script_importable**: Use `subprocess.run()` to invoke `python3 src/specify_cli/scripts/tasks/tasks_cli.py --help` and assert exit code 0 and no `ModuleNotFoundError` in stderr. This tests the actual standalone entrypoint without mocking.

4. **test_malformed_event_log_acceptance_error**: Create a feature dir with a malformed `status.events.jsonl`. Call `collect_feature_summary()`. Assert it raises `AcceptanceError` (not `StoreError`).

5. **test_copy_parity**: Compare function signatures and key behavior between `acceptance.py` and `acceptance_support.py` to verify they stay aligned. This could be a structural comparison of the `__all__` exports or a hash of key function bodies.

**Sync verification**: After all fixes, run a diff between `acceptance.py` and `src/specify_cli/scripts/tasks/acceptance_support.py` to document expected differences (the standalone copy has extras like `ArtifactEncodingError`, `normalize_feature_encoding`).

**Dependency**: WP01, WP02, WP03 (tests must verify the fixes).

## Execution Order

```
WP01 (verification hardening)
  ↓
WP02 (metadata persistence)
  ↓
WP03 (standalone script contract)
  ↓
WP04 (regression tests + parity sweep)
```

All sequential. WP01–WP03 each touch overlapping files (`acceptance.py`, `acceptance_support.py`), so parallel execution would cause merge conflicts.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Moving `git_status_lines()` earlier changes the order of side effects | `git_status_lines()` is read-only — no dependency on materialize output |
| Post-commit SHA write creates an uncommitted change to `meta.json` | Acceptable: the SHA is reference data, not part of the acceptance commit itself |
| `sys.path` walk may not find `src/` in unusual repo layouts | Bounded walk (6 levels) + `_SRC_ROOT.name == "src"` guard |
| Standalone test may be flaky if spec-kitty is pip-installed | Test can use `--isolated` or a subprocess with clean `PYTHONPATH` |
