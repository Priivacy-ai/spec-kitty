# Implementation Plan: Canonical State Authority & Single Metadata Writer

**Branch**: `051-canonical-state-authority-single-metadata-writer` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/051-canonical-state-authority-single-metadata-writer/spec.md`

## Summary

Make workflow correctness depend on canonical state (`status.events.jsonl`, `status.json`, `meta.json`) instead of markdown-body compatibility views. Collapse all 18 meta.json write sites into a single API module (`feature_metadata.py`) with atomic writes, TypedDict schema validation, and explicit mutation helpers. Acceptance validation reads `materialize()` instead of parsing Activity Log text.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (all existing)
**Storage**: Filesystem only (JSON, JSONL, Markdown)
**Testing**: pytest with 90%+ coverage for new code; mypy --strict
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform)
**Project Type**: Single Python package (CLI tool)
**Performance Goals**: meta.json write < 50ms p95
**Constraints**: No new third-party dependencies; no removal of compatibility views
**Scale/Scope**: 18 write sites migrated, 2 acceptance paths refactored

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | Existing codebase requirement |
| pytest + 90%+ coverage | PASS | New module gets unit + integration tests |
| mypy --strict | PASS | TypedDict provides static types |
| CLI < 2 seconds | PASS | meta.json writes are sub-millisecond |
| Cross-platform | PASS | `os.replace()` works on POSIX and Windows |
| No new dependencies | PASS | TypedDict is stdlib |
| 2.x branch | PASS | Target branch is 2.x |
| Terminology: Mission vs Feature | OBSERVED | Existing code uses `feature_*` extensively; renaming is out of scope for this sprint. The new module is named `feature_metadata.py` to match existing conventions. Terminology cleanup is a separate initiative. |

**Post-design re-check**: No new violations introduced. All gates still pass.

## Project Structure

### Documentation (this feature)

```
kitty-specs/051-canonical-state-authority-single-metadata-writer/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: write site inventory, acceptance analysis
├── data-model.md        # Phase 1: entity definitions, API surface
├── quickstart.md        # Phase 1: usage examples
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── feature_metadata.py          # NEW: Single metadata writer API
├── acceptance.py                # MODIFIED: Read canonical state instead of Activity Log
├── doc_state.py                 # MODIFIED: Route writes through feature_metadata.py
├── scripts/tasks/
│   ├── acceptance_support.py    # MODIFIED: Same as acceptance.py
│   └── tasks_cli.py             # MODIFIED: Route merge writes through feature_metadata.py
├── orchestrator_api/
│   └── commands.py              # MODIFIED: Route acceptance through feature_metadata.py
├── cli/commands/
│   ├── implement.py             # MODIFIED: Route VCS lock through feature_metadata.py
│   └── agent/
│       └── feature.py           # MODIFIED: Route creation writes through feature_metadata.py
├── upgrade/
│   └── feature_meta.py          # MODIFIED: Thin wrapper delegating to feature_metadata.py
└── status/                      # UNCHANGED (already canonical)
    ├── emit.py
    ├── reducer.py
    ├── legacy_bridge.py
    └── ...

tests/
├── specify_cli/
│   ├── test_feature_metadata.py         # NEW: Unit tests for metadata API
│   ├── test_canonical_acceptance.py     # NEW: Integration tests for canonical-state acceptance
│   └── ...
```

**Structure Decision**: No new directories needed. One new module (`feature_metadata.py`) at the package root. One new test file per concern. All other changes are modifications to existing files.

## Implementation Strategy

### Phase 3: Canonical Workflow State (acceptance refactor)

**Goal**: Acceptance reads `materialize()` instead of Activity Log body text.

**Approach**:
1. In `acceptance.py` and `acceptance_support.py`, replace the Activity Log parsing block (3 validation rules) with a single `materialize()` call that checks all WPs are in `done` lane.
2. Keep Activity Log generation in `legacy_bridge.py` unchanged — it remains a compatibility view.
3. Add integration tests proving:
   - Acceptance succeeds when canonical state says done, even with deleted Activity Log
   - Acceptance fails when canonical state says not-done, even with falsified Activity Log

**Key change** (both `acceptance.py:355-392` and `acceptance_support.py:457-492`):

```python
# BEFORE: Parse Activity Log from markdown body
entries = activity_entries(wp.body)
lanes_logged = {entry["lane"] for entry in entries}
# ... 3 validation rules against Activity Log

# AFTER: Read canonical status snapshot
from specify_cli.status.reducer import materialize
snapshot = materialize(feature_dir)
for wp_id in expected_wp_ids:
    wp_state = snapshot.get(wp_id)
    if wp_state is None:
        issues.append(f"{wp_id}: no canonical state found")
    elif wp_state.lane != "done":
        issues.append(f"{wp_id}: lane is {wp_state.lane}, expected done")
```

### Phase 4: Single Metadata Writer (feature_metadata.py)

**Goal**: All meta.json mutations go through one module.

**Approach**:
1. Create `src/specify_cli/feature_metadata.py`:
   - Move `load_feature_meta()` and `write_feature_meta()` from `upgrade/feature_meta.py`
   - Add `_atomic_write()` (temp file + `os.replace()`)
   - Add `validate_meta()` (TypedDict-based, checks required fields)
   - Add mutation helpers: `record_acceptance()`, `record_merge()`, `finalize_merge()`, `set_vcs_lock()`, `set_documentation_state()`, `set_target_branch()`
   - Standardize formatting: `json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"`
   - Bounded history: cap `acceptance_history` and `merge_history` at 20 entries

2. Migrate each write site (smallest defensible diff per site):
   - Replace direct `json.dumps` + `write_text` with the appropriate mutation helper
   - Each migration is a mechanical replacement, not a logic change

3. Leave thin compatibility wrapper in `upgrade/feature_meta.py`:
   - `load_feature_meta()` → re-export from `feature_metadata.py`
   - `write_feature_meta()` → re-export from `feature_metadata.py`
   - Other inference functions (`infer_target_branch`, `infer_mission`, etc.) stay in `upgrade/feature_meta.py` since they're upgrade-specific logic

4. Update `doc_state.py` write functions to delegate to `feature_metadata.py` for the actual file I/O while keeping their validation logic.

### Dependency Order

```
WP01: feature_metadata.py module (no dependencies — foundational)
  ↓
WP02: Migrate write sites to feature_metadata.py (depends on WP01)
  ↓
WP03: Canonical acceptance refactor (depends on WP01 for metadata writes in acceptance)
  ↓
WP04: Integration tests (depends on WP02 + WP03)
  ↓
WP05: doc_state.py migration (depends on WP01, can parallel with WP03)
```

### Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Formatting change causes noisy diffs in existing meta.json files | Migration writes only on actual mutations, not bulk reformatting |
| Acceptance refactor breaks edge cases | Integration tests with deleted/corrupted Activity Log |
| doc_state.py validation logic entangled with I/O | Keep validation in doc_state.py, delegate only file I/O |
| Concurrent writes in parallel WP implementation | Atomic writes prevent corruption; history cap prevents unbounded growth |
| Legacy features without event log | Explicit error, not silent fallback |

## Complexity Tracking

No constitution violations to justify. All gates pass.
