---
work_package_id: WP19
title: Mission archiving as a first-class lifecycle operation (IC-13)
dependencies:
- WP04
requirement_refs:
- FR-015
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T093
- T094
- T095
- T096
- T097
- T098
phase: Phase 9 - Enforcement, Docs & Archiving
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_archive.py
create_intent:
- src/specify_cli/missions/_archive.py
- src/specify_cli/cli/commands/archive.py
- tests/integration/test_mission_archiving.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/missions/_archive.py
- src/specify_cli/cli/commands/archive.py
- tests/integration/test_mission_archiving.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP19 – Mission archiving (IC-13)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

A first-class archive operation producing an immutable, explicitly-legacy `ArchivedMission` snapshot excluded from live validation but kept enumerable — with the four `AM` guards so it can never be an escape hatch from an acceptance failure.

**Done** = SC-008 / the four US6 scenarios pass.

## Context & Constraints

- Spec US6, FR-015; data-model `ArchivedMission` (AM-1..AM-5); contract `negative-invariant-provenance.md` C10.
- **Orthogonal to both seams** — shares no surface with IC-01..IC-12. It is the **first concern to cut** if scope must shrink (P3).
- **AM-4 / AM-5 interplay**: the FR-014 migration (WP05) must never reach archiving; cancellation clears outstanding deferrals to a `canceled` disposition so an abandoned mission with a dangling deferral is archivable (no deadlock).
- The final module paths are indicative — confirm the existing missions/CLI command surface and `doctor` enumeration path at implement time.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T093 – Archive command + record

- **Steps**: New archive command/verb producing an `ArchivedMission` record (`mission_id`, `archived_by`, `archived_at`, `reason`, `terminal_state_at_archive`).

### Subtask T094 – AM-1 / AM-2 refusals

- **Steps**: Refuse unless the mission is terminal (`merged`/`canceled`) with a stated reason (AM-1); refuse while any invariant is recorded `still_present` (AM-2).

### Subtask T095 – AM-3 enumerable-not-live + AM-5 cancellation

- **Steps**: An archived mission is excluded from live validation but remains enumerable (e.g. via `doctor`) (AM-3). Cancellation resolves outstanding `deferred_to_consolidation` invariants to a `canceled` disposition (AM-5) — abandonment is not a deadlock.

### Subtask T096 – AM-4 never automatic

- **Steps**: No lifecycle step, including the FR-014 migration, may auto-archive; archiving is operator-invoked only and unreachable from the migration's failure path.

### Subtask T097 – US6 scenario tests (SC-008)

- **Steps**: The four US6 scenarios: non-terminal refused; `still_present` refused; clean terminal archived + enumerable + excluded from live validation; migration never auto-archives.

### Subtask T098 – C-006 registration

- **Steps**: Register any new filesystem sink / command surface with the project gates (path-audit inventory, help text).

## Test Strategy

- New: `tests/integration/test_mission_archiving.py` (four US6 scenarios).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/integration/test_mission_archiving.py -q`.

## Risks & Mitigations

- An ungoverned archive is a one-command escape from acceptance failure — the four `AM` invariants are the point of this WP; do not weaken them.

## Review Guidance

- Confirm all four AM guards; confirm the migration path (WP05) can never trigger an archive.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
