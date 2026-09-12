---
work_package_id: WP02
title: Acceptable-ending predicate + accept consumes it
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-006
- NFR-003
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - Acceptance authority
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-B after post-spec squad (F2 supersedes planner)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — bucketing-seam resolution + shared has_operator_provenance accessor (pedro MEDIUM)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/test_acceptable_ending.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status_lanes.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/gates_core.py
- src/specify_cli/acceptance/summary_core.py
- tests/status/test_transitions.py
- tests/specify_cli/test_acceptable_ending.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/2945
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. State which you applied, then begin.

## Objective

Create the **single acceptable-ending authority** and make `accept` consume it. Terminality
(`{done,canceled}`), acceptability (`{approved,done}`), and provenance are **three separable
decisions** (post-spec squad **F2** — do NOT reuse `is_terminal()`: it would reject every `approved`
WP and accept `canceled` unconditionally). This WP adds the predicate **and a shared provenance
accessor**, routes accept through them, collapses the three duplicated accept-ready sets, and reports
`canceled_wps`.

## Context

- Contracts: [../contracts/acceptable-ending-predicate.md](../contracts/acceptable-ending-predicate.md),
  [../contracts/accept-canceled-wps.schema.json](../contracts/accept-canceled-wps.schema.json).
- Evidence: F2 (architect); post-tasks pedro MEDIUM (consumer shapes), paula (shared accessor).
  Decisions: [../research.md](../research.md) R3. Depends on WP01's `reason_source` snapshot slot.

## Subtasks

### T006 — Add the predicate AND the shared provenance accessor
`src/specify_cli/status_lanes.py` (pure-constants module, clean insertion point): add
`is_acceptable_ending(lane: str, *, has_provenance: bool) -> bool` (truth table in the contract:
`approved`/`done` → True; `canceled` → True iff `has_provenance`; else False; reference `TERMINAL_LANES`
only to classify `canceled`). Also add a single shared reader `has_operator_provenance(wp_snapshot) -> bool`
so WP03/WP04 do not each inline `reason_source == "operator"` (paula: avoid a 3-site whack-a-field).
Both pure, no I/O.

### T007 — Collapse the three ready-sets AND resolve canceled at the bucketing seam
Delete `_ACCEPTED_READY_LANES` at `acceptance/__init__.py:145`, `gates_core.py:52`, and the inlined
sets at `summary_core.py:173,202`; route through `is_acceptable_ending`. **Because the current
consumers iterate a provenance-free `dict[lane -> list[wp_id]]`** (pedro MEDIUM), carry provenance
onto `WorkPackageState`/`build_work_package_state` (`summary_core.py`, owned) at the bucketing seam
(`__init__.py:997-1027`) and decide the `canceled` case per-WP there — not lane-level.

### T008 — accept honors canceled-with-provenance + reports canceled_wps
A canceled WP whose snapshot provenance is operator → acceptable ending, reported under a dedicated
`canceled_wps` array with the pinned shape `{wp_id, reason, actor, at}` (NFR-003, schema in contracts).
A canceled WP with synthetic provenance → structured blocker naming the WP and "operator-authored
cancellation provenance required" (FR-003). Provenance is read from the coord status surface
(`resolve_status_surface`), matching the existing `status_feature_dir` discipline (F9).

### T009 — Preserve every other gate (FR-006, gate integrity) — incl. all_done re-point
Non-terminal, non-canceled lanes remain blockers. The acceptance-matrix and issue-matrix verdict
gates still run and can still fail — canceled-terminal must **not** short-circuit them. **`all_done`
(`__init__.py:366`) currently reads `self.lanes`** (lane bucket), which cannot see per-WP provenance —
re-point it at the per-WP data / pre-bucketed acceptable set for the canceled case (pedro MEDIUM).
Keep the vacuous-`all_done` guard intact.

### T010 — Unit test: predicate truth table
`tests/status/test_transitions.py` (ensure `pytestmark`): all nine lanes × provenance → expected
boolean; plus `has_operator_provenance` over operator/synthetic/None/legacy snapshots.

### T011 — Command test: accept behavior + schema
`tests/specify_cli/test_acceptable_ending.py` (new, declare `pytestmark`): drive the canonical flow —
approved + canceled(operator provenance) → accept eligible, `canceled_wps` validates against the
schema; canceled(synthetic) → structured blocker, absent from `canceled_wps`; a non-terminal WP still
blocks. Use the canonical command surface, not hand-edited events.

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- One predicate + one `has_operator_provenance` accessor; the three `_ACCEPTED_READY_LANES` copies gone;
  canceled resolved at the bucketing seam; `all_done` no longer misreads the lane bucket for canceled.
- `accept --json` emits `canceled_wps` per schema; synthetic cancellation blocks; non-terminal blocks;
  matrices still gate. T010/T011 pass; `ruff` + `mypy` clean on owned files.

## Risks / Reviewer guidance

- Verify accept reads provenance from the **coord** surface (F9), and that `all_done` no longer
  decides the canceled case off the raw lane bucket.
- WP03/WP04 import `is_acceptable_ending` + `has_operator_provenance` — keep them the single source.
