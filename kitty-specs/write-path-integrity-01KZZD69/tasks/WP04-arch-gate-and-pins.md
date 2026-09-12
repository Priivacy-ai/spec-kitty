---
work_package_id: WP04
title: Architectural gate + regression pins
dependencies:
- WP02
- WP03
requirement_refs:
- FR-011
- NFR-001
- NFR-003
planning_base_branch: mission/write-path-integrity
merge_target_branch: mission/write-path-integrity
branch_strategy: Planning artifacts for this mission were generated on mission/write-path-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/write-path-integrity unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 4 - Hardening
history:
- at: '2026-08-14T08:00:00+00:00'
  actor: system
  action: Prompt generated during tasks phase
agent_profile: implementer-ivan
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_wp_integrity_partition_call_shape.py
- tests/integration/test_wp_integrity_crash_recovery.py
- kitty-specs/write-path-integrity-01KZZD69/baseline-red.md
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_wp_integrity_partition_call_shape.py
- tests/integration/test_wp_integrity_crash_recovery.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Architectural gate + regression pins

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria

Make the P0 class hard to reintroduce and pin the invariants the earlier WPs establish.

**Done when**:
- A **static** arch gate fails CI on an un-partitioned coord-topology commit batch (SC-006, FR-011).
- The **runtime** "no `lanes.json` on a coord ref" property is owned by the SC-002 scan (WP02), not this
  static gate.
- The honest-red baseline manifest is pinned so regressions are attributable (NFR-003).
- A crash-between-commits regression pin proves idempotent recovery (R5).

## Context & Constraints

- Spec FR-011, SC-006, NFR-003; Plan IC-05. Operator decision OD-3: **route the flat arm through the
  split** (no whitelist).
- A `tests/architectural/` gate is source/AST-based — it **cannot** observe a runtime file-set. Do NOT
  put "no `lanes.json` on coord" in the static gate.
- The call-shape gate must NOT condemn the legitimate flat/legacy arm (`implement.py:909`, verbatim by
  design) — WP02/OD-3 routes it through `_partition_files_for_commit`, so the gate can require the split
  uniformly.

## Subtasks & Detailed Guidance

### Subtask T019 – Static call-shape arch gate
- **Steps**: AST gate asserting every **coord-topology** `_run_planning_artifact_commit` batch traces
  through `_partition_files_for_commit`. Because WP02 routes the flat arm (`:909`) through the split too
  (OD-3), the gate needs no special-case whitelist. Assert the negative call-shape (a raw
  `files=files_to_commit` verbatim to a coord ref is forbidden).
- **Files**: `tests/architectural/test_wp_integrity_partition_call_shape.py`.

### Subtask T020 [P] – Pin the honest-red baseline manifest
- **Steps**: Before/alongside red-first work, record the honest-red set for `tests/architectural/`,
  `tests/integration/test_coord_*`, `tests/{,specify_cli/}lanes/*` in the mission dir. Confirm these
  gates are GREEN on merge-base (so a regression is ours): `test_write_surface_placement_guard`,
  `test_read_surface_placement_guard`, `test_no_write_side_rederivation`.
- **Files**: `kitty-specs/write-path-integrity-01KZZD69/baseline-red.md`.

### Subtask T021 [P] – Crash-between-commits regression pin
- **Steps**: Simulate a kill between the PRIMARY and COORD partition commits; assert re-invoking
  `implement` re-drives idempotently with no stranded coord residue on primary (the #2702 shape must not
  reappear).
- **Files**: `tests/integration/test_wp_integrity_crash_recovery.py`.

### Subtask T022 [P] – Requirements coverage + quickstart
- **Steps**: Verify every FR maps to a passing test; validate the quickstart scenario (coord + PR-bound
  mission reaches `implement WP01` clean).

## Definition of Done

- Static gate green and biting (a deliberately un-partitioned batch fails it); baseline-red manifest
  matches CI; crash-recovery pin green; coverage complete; `ruff`/`mypy` clean; **no new** arch-gate
  regressions vs merge-base (NFR-003).

## Risks & Reviewer Guidance

- **Reviewer**: confirm the static gate does NOT assert a runtime property; confirm it does not condemn
  the flat arm; confirm the baseline-red manifest is honest (each listed red is red on merge-base too).
