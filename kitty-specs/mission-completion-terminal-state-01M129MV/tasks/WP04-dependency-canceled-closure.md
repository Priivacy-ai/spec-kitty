---
work_package_id: WP04
title: Dependency-on-canceled closure (claim gate)
dependencies:
- WP02
requirement_refs:
- FR-009
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 3 - Dependency gate
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-D after post-spec squad (F5 strand trap)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — own workflow_executor claim gate, provenance param, replace _SATISFYING_DEPENDENCY_LANES (pedro HIGH, paula BLOCKER)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/specify_cli/core/test_dependency_graph_canceled.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/dependency_graph.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/specify_cli/core/test_dependency_graph_canceled.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3590
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. State which you applied, then begin.

## Objective

Stop a canceled dependency from stranding its dependent at **claim time** — the mission's own trap
re-created (post-spec squad **F5**). `core/dependency_graph.py:59` lists `canceled` as non-satisfying
and `_SATISFYING_DEPENDENCY_LANES` (`:34`) is a **fourth** parallel authority (the F2 smell). Canceling
a depended-upon WP is reachable from `in_progress` **without** `--force`, so a survivor becomes
permanently unclaimable. Align the claim gate to the shared authority and wire provenance into it.

> **Post-tasks squad corrections:**
> - **The fix cannot reach the strand site inside `dependency_graph.py` alone (pedro HIGH / paula
>   BLOCKER):** `dependency_readiness_for_wp(wp_id, dependencies, wp_lanes)` takes a **lane-only** map;
>   it has no provenance. The runtime **claim gate** caller `workflow_executor.py:634-649` already
>   reduces `dependency_snapshot` (provenance available) but collapses it to lane-only before calling.
>   WP04 therefore also owns `workflow_executor.py`.
> - **Replace, do not special-case (paula HIGH):** `_SATISFYING_DEPENDENCY_LANES`'s truth table becomes
>   identical to `is_acceptable_ending` — replace it with the predicate rather than adding a canceled
>   branch beside it (directive 044).
> - **Scoped callers:** add an **optional** `provenance` param (backward-compatible default) so the five
>   read-only callers keep compiling; only the claim gate (`workflow_executor.py`) and
>   `implement.py`-driven claim path are updated to pass provenance in this WP. The runtime `next`
>   path (`runtime/next/decision.py`, `discovery.py` — governed Shared Package Boundary), the display
>   `tasks_status_view.py:223`, and `orchestrator_api/commands.py` are **deferred with rationale** (see
>   research.md R5) — track as a follow-up so the fix is not inert at the CLI claim path it targets.

## Context

- Evidence: F5 (planner); post-tasks pedro HIGH / paula BLOCKER. Decisions: [../research.md](../research.md)
  R5. Spec FR-009 / SC-005. Boundary: #3432/PR#3713 fixed the *finalize* path only; do not touch
  `mission_finalize.py` (C-005). The **merge-side** face of FR-009 is WP03 (`policy/merge_gates.py`).

## Subtasks

### T015 — Provenance-aware claim gate via the shared authority
Give `dependency_readiness_for_wp` an **optional** per-dependency provenance input (default preserves
current behavior for the 5 read-only callers). Replace `_SATISFYING_DEPENDENCY_LANES` with
`is_acceptable_ending` + `has_operator_provenance` (WP02): a dependency `canceled` **with** operator
provenance counts as resolved; `canceled` **without** provenance stays non-satisfying (consistent with
FR-003 — an undocumented cancellation is not a valid removal); approved/done unchanged. In
`workflow_executor.py:634-649`, stop collapsing `dependency_snapshot` to lane-only — pass provenance
through so the claim gate actually consumes it.

### T016 — Tests
`tests/specify_cli/core/test_dependency_graph_canceled.py` (new; declare `pytestmark`): a dependent of
a canceled(operator provenance) WP is claimable and can reach an acceptable ending (SC-005); a
dependent of a canceled(synthetic) WP stays gated; approved/done dependencies behave unchanged; and
the optional-param default keeps the legacy lane-only call signature working (so the deferred callers
still compile and behave as before).

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- `_SATISFYING_DEPENDENCY_LANES` is gone (replaced by the predicate); the claim gate consumes
  provenance via `workflow_executor.py`; canceled+provenance dependency no longer strands its
  dependent; synthetic still gates; approved/done unchanged; deferred callers still compile.
- T016 passes; `ruff` + `mypy` clean on owned files; `mission_finalize.py` untouched; the deferred
  caller list is recorded in research.md R5 as a tracked follow-up.

## Risks / Reviewer guidance

- Verify the gate consults the shared authority (WP02), not a new lane set (F2 anti-pattern), and that
  `workflow_executor.py` actually passes provenance (else the fix is inert — pedro HIGH).
- Verify "synthetic still gates" — otherwise this reopens the FR-003 silent-skip hole via the
  dependency path.
- The merge-side dependency gate is WP03's, not this WP's — do not touch `policy/merge_gates.py` here.
