---
work_package_id: WP13
title: Legacy migration event-rebuild single-port (#1754)
dependencies: []
requirement_refs:
- FR-032
- FR-033
- FR-034
tracker_refs:
- '1754'
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
phase: Phase 6 - Fold-in follow-ups
assignee: ''
agent: ''
history:
- at: '2026-06-07T09:30:00Z'
  actor: system
  action: Prompt generated as #1754 fold-in (post-#1756 rebase)
agent_profile: python-pedro
authoritative_surface: 'src/specify_cli/migration/'
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/migration/mission_state.py
- src/specify_cli/migration/runner.py
- src/specify_cli/migration/normalize_mission_lifecycle.py
- src/specify_cli/migration/rebuild_state.py
- src/specify_cli/migration/__init__.py
- tests/specify_cli/migration/**
role: implementer
tags:
- migration
- single-ownership
- fold-in
task_type: implement
---

# Work Package Prompt: WP13 – Legacy migration event-rebuild single-port (#1754)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below).

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Route the two live legacy-migration callers off the deprecated `rebuild_event_log` and onto a single canonical per-mission event-rebuild entry on `mission_state` that returns event counts. Prove behavior preservation with migration fixtures.

- FR-032/033/034. SC-010. NFR-002 (leanness — one rebuild path), NFR-004 (legacy missions migrate unchanged).

## Context & Constraints

- **Provenance**: #1754 — a #1756 follow-up. The import-time `DeprecationWarning` pollution was already removed (lazy `__getattr__` in `migration/__init__`, point-of-use import in `normalize_mission_lifecycle`); the symbol now warns only on access. The behavioral migration is what remains.
- **Why `repair_repo` is not a drop-in**: `rebuild_event_log(feature_dir, slug, wp_id_map) -> RebuildResult` is **per-feature** and returns `events_generated`/`events_corrected`/`errors`/`warnings`. `repair_repo(repo_root, *, scan_root, mission, manifest_path, allow_dirty) -> RepairReport` is **repo-level**, takes a git lock, writes a manifest, and its per-mission `MissionRepairResult` has **no `events_generated`** (`file_changes`/`row_transformations`/`quarantined_rows` instead). Overlapping but not equivalent.
- **Live callers to migrate**:
  - `migration/normalize_mission_lifecycle.py` — `rebuild_event_log(feature_dir, slug, wp_id_map={})`
  - `migration/runner.py` (Step 4: State rebuild) — per-feature loop
- **Two sanctioned resolutions (pick + record in the WP summary)**: (1) expose a per-mission canonical event-rebuild entry on `mission_state` returning event counts and migrate the two callers; or (2) retire the legacy `migration/runner.py` flow onto `repair_repo` end-to-end. Both are behavioral changes to legacy-project migration and need fixtures — not a deprecation-cleanup. Resolution (1) is the lower-risk default (preserves the per-feature reporting contract).
- **`__all__` nuisance (#1757.4 / FR-033)**: after the PEP 562 lazy re-export, `RebuildResult`/`rebuild_event_log` sit in `migration/__init__.__all__` but are not eagerly bound, so some linters flag "declared in `__all__` but not defined". When the symbol is removed/shimmed, clean up the `__all__` entry accordingly.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T047 – Canonical per-mission rebuild entry
- **Decision (pinned, FR-032)**: add the per-mission entry on `mission_state`. Do **not** retire onto `repair_repo` — it is repo-level and drops the per-feature event counts the runner reports. Full `repair_repo` retirement is a separate, fixture-backed change.
- **Steps**: Add a per-mission event-rebuild entry on `migration/mission_state.py` returning event counts (`events_generated`/`events_corrected`/`errors`/`warnings`).
- **Files**: `src/specify_cli/migration/mission_state.py`.

### Subtask T048 – Migrate runner Step 4
- **Steps**: Repoint the `migration/runner.py` Step 4 per-feature loop onto the canonical entry; preserve its reporting (counts/errors/warnings).
- **Files**: `src/specify_cli/migration/runner.py`.

### Subtask T049 – Migrate normalize_mission_lifecycle
- **Steps**: Repoint `normalize_mission_lifecycle.py` onto the canonical entry.
- **Files**: `src/specify_cli/migration/normalize_mission_lifecycle.py`.

### Subtask T050 – Retire the deprecated symbol
- **Steps**: Remove `rebuild_event_log` (or reduce to a thin shim with no live callers); clean the `migration/__init__.__all__` lazy-symbol nuisance (#1757.4).
- **Files**: `src/specify_cli/migration/rebuild_state.py`, `src/specify_cli/migration/__init__.py`.

### Subtask T051 – Migration fixtures + behavior preservation
- **Steps**: Add fixtures covering the per-mission rebuild path; assert behavior preservation (events generated/corrected equivalent to the deprecated path) and that legacy missions migrate unchanged.
- **Files**: `tests/specify_cli/migration/**`.

## Test Strategy

- **ATDD-first (C-011, binding):** author + commit subtask **T051 RED first** (the migration fixtures + behavior-preservation assertions), before the T047–T050 implementation. Reviewer verifies red→green (RED on `planning_base_branch`, GREEN on the final commit).
- New fixtures + tests green; existing migration tests green; legacy-mission load/migration unchanged (NFR-004); `ruff` + `mypy` clean (NFR-007). No deprecation warnings on unrelated import paths.

## Risks & Mitigations

- Behavioral change to legacy-project migration — fixture-backed; diff event counts against the deprecated path before deleting it.
- Do not leave a second rebuild path alive — one canonical entry only (Randy-Reducer leanness IC).

## Review Guidance — **Persona IC: reviewer-renata (+ Randy-Reducer leanness)**

- Reviewer profile: `reviewer-renata`. Verify: both callers use the canonical entry; the deprecated symbol has no live callers; fixtures prove behavior preservation; `__all__` no longer flags a declared-but-undefined name. Confirm exactly one rebuild path remains.

## Activity Log

- 2026-06-07T09:30:00Z – system – Prompt created as #1754 fold-in.
