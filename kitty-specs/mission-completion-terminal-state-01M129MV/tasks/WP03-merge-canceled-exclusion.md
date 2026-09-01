---
work_package_id: WP03
title: Merge WP-granular exclusion of canceled work packages
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-009
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
phase: Phase 3 - Merge integration
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-C after post-spec squad (F4 lane vs WP cardinality)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — second filter site done_bookkeeping:666, own merge_gates.py, snapshot+coord read (pedro HIGH, paula HIGH)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/merge/test_merge_canceled_wp.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/executor.py
- src/specify_cli/merge/done_bookkeeping.py
- src/specify_cli/policy/merge_gates.py
- tests/merge/test_merge_canceled_wp.py
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

Make `merge` tolerate a canceled work package at **work-package granularity** (post-spec squad **F4**:
a lane holds many WPs). Merge integrates per-lane branch (`executor.py:416-459`) but asserts per-WP
done/review over `all_wp_ids` (`executor.py:1660`). A canceled WP has no review artifact and is never
`done`, so it breaks merge. This WP excludes canceled WPs from those per-WP assertions, skips a lane
branch only when all its WPs are canceled, and closes the **merge-side** face of FR-009.

> **Post-tasks squad corrections:**
> - **`:1660` is NOT the single filter point (pedro HIGH):** `done_bookkeeping.py:666`
>   (`_record_merged_wps_done_for_merge`) independently re-derives WPs from `lanes_manifest.lanes` and
>   would drive a canceled WP through an invalid `canceled -> done`, corrupting the honest-ending
>   record. It is a **second** filter site.
> - **The merge-side dependency gate (paula HIGH):** `policy/merge_gates.py` (`:155-164`, `:253`) has
>   its own `{approved,done}` dependency check — a survivor depending on a canceled+provenance WP
>   passes WP04's *claim* gate but would strand here at *merge*. WP03 owns `merge_gates.py` and routes
>   its dependency/evidence checks through `is_acceptable_ending` (this is the merge face of FR-009;
>   the claim face is WP04).
> - `all_wp_ids` derives from `lanes.json`, not the snapshot — load `reduce(read_events(...))` from the
>   **coord** status surface (`resolve_status_surface`, already imported in `done_bookkeeping.py:24`) to
>   know which WPs are canceled-with-provenance (F9).

## Context

- Contract: [../contracts/acceptable-ending-predicate.md](../contracts/acceptable-ending-predicate.md)
  (merge consumer obligations). Decisions: [../research.md](../research.md) R4. C-005: compose with —
  do not preempt — a future `merge --skip-lanes` (#2745); do not touch `mission_finalize.py`.

## Subtasks

### T012 — Exclude canceled WPs from BOTH per-WP derivations (coord snapshot)
Load the reduced snapshot from the coord surface once; using `is_acceptable_ending` /
`has_operator_provenance` (WP02), filter canceled WPs out of `all_wp_ids` at `executor.py:1660` (feeds
`_enforce_review_artifact_consistency` `:1671`, `wp_order` `:1681`, evidence gate `:392`,
canonical-history `:407`) **and** out of the independent derivation in
`done_bookkeeping._record_merged_wps_done_for_merge:666` (so no canceled WP is driven `canceled->done`).
Retain the cancellation record in the audit trail.

### T013 — All-canceled lane-skip guard + merge dependency gate
In `_phase_merge_lanes` (`executor.py:416-459`), skip a lane's branch integration only when **every**
WP in that lane is canceled (its branch may not exist). A mixed lane still integrates its survivors.
In `policy/merge_gates.py`, route the dependency gate (`:253`) and the `{approved,done}` logic
(`:155-164`) through `is_acceptable_ending` so a canceled-with-provenance dependency does not strand a
survivor at merge (FR-009 merge face).

### T014 — In-diff real-git integration test
`tests/merge/test_merge_canceled_wp.py` (new; declare `pytestmark = [pytest.mark.integration]` —
use the real-git fixture pattern from `tests/merge/test_issue_2711_merge_rollback_resume_coherence.py`,
**not** a seam-only `_enforce_review_artifact_consistency` call). Construct a coord-topology mission
where a WP is canceled **mid-mission after finalize** (its lane branch exists — the #2945 shape) via
WP01's provenance mechanism, with surviving approved WPs. Assert: a survivor's commit lands on the
mission branch; the canceled WP is excluded from done/review assertions, order, and the
`_record_merged_wps_done_for_merge` path (no `canceled->done`); its audit record is retained; a
fully-canceled lane is skipped; and a survivor depending on the canceled+provenance WP is not stranded
by the merge dependency gate. This is the SC-001 proof and MUST be observable in this diff.

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- Both per-WP derivations (`executor.py:1660` and `done_bookkeeping.py:666`) exclude canceled WPs;
  merge dependency gate honors canceled+provenance; all-canceled lane skipped; audit retained.
- T014 is a real-git `integration`-marked fixture proving survivor integration in-diff; `ruff` + `mypy`
  clean on owned files; `mission_finalize.py` untouched.

## Risks / Reviewer guidance

- Reject a seam-only T014 that never runs a real merge (renata MEDIUM).
- Verify the canceled WP is NOT driven `canceled->done` at `done_bookkeeping.py:666` — that would
  corrupt the very honest-ending record the mission protects.
- Confirm the snapshot read uses the **coord** surface, and the lane-skip composes with future #2745.
