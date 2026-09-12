---
work_package_id: WP17
title: Retire the R-014 additions — ACCEPT_OWNED_PATHS, dirty_classifier bundle, dead field (IC-07g)
dependencies:
- WP12
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T083
- T084
- T085
- T086
- T087
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/__init__.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/review/dirty_classifier.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP17 – Retire the R-014 additions (IC-07g)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Close the gap the original eight-symbol slice missed: retire `ACCEPT_OWNED_PATHS` (the most on-thesis instance — the accept gate ignoring the accept pipeline's own writes), the `dirty_classifier` bundle (with the review-handoff path), and delete the dead `ignores_primary_coord_residue` field.

**Done** = `ACCEPT_OWNED_PATHS` and `ignores_primary_coord_residue` absent from `src/`; the dirty_classifier bundle retired against the owner; behaviour preserved (C6/C-010); no registry row orphaned.

## Context & Constraints

- Owner contract C5 (the four R-014 additions). Plan IC-07(g).
- **Consumers (grep-confirmed)**: `ACCEPT_OWNED_PATHS` → `acceptance/__init__.py`; dirty_classifier bundle → `review/dirty_classifier.py`; `ignores_primary_coord_residue` (dead field, zero external consumers) → `mission_runtime/artifacts.py`.
- **`_exclude_coord_owned` is NOT retired here** — it is retired by WP14 (d), which deduplicates it into `_drop_if`. The plan double-listed it; do not double-retire.
- **Nothing is a permanent survivor** — the registry reaches zero rows (TAO-4/SC-004). If implementation finds a genuine must-keep, it becomes an explicit, justified registry row, never a silent survivor.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T083 – Retire ACCEPT_OWNED_PATHS

- **Steps**: Remove `ACCEPT_OWNED_PATHS` from `acceptance/__init__.py`; route the accept gate through the owner so it no longer ignores the accept pipeline's own writes.

### Subtask T084 – Retire the dirty_classifier bundle

- **Steps**: Retire the `dirty_classifier` bundle in `review/dirty_classifier.py` with the review-handoff path, against the owner/canonical classifier.

### Subtask T085 – Delete the dead field

- **Steps**: Delete `ignores_primary_coord_residue` in `mission_runtime/artifacts.py` (leeway; owned WP02) — confirm zero external consumers first, then simply delete.

### Subtask T086 – Delete group (g) registry rows

- **Steps**: Delete the group (g) rows in the WP10 registry; note `_exclude_coord_owned` is deleted by WP14.

### Subtask T087 – Migrate tests; preserve behaviour

- **Steps**: Migrate mechanism-asserting tests; no previously-succeeding operation now fails.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/specify_cli/acceptance/ tests/specify_cli/review/ -q`.

## Risks & Mitigations

- Owns `acceptance/__init__.py`, `review/dirty_classifier.py`. Leeway: `artifacts.py` (dead field; WP02). Serial after WP12 (shares `acceptance/__init__.py`, `dirty_classifier.py`). Parallel to WP13/WP14 (file-disjoint from them).

## Review Guidance

- Confirm `ACCEPT_OWNED_PATHS` and the dead field are gone; `_exclude_coord_owned` was left to WP14 (no double-retirement).
- Confirm the registry now reaches zero rows across WP11–WP17.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
