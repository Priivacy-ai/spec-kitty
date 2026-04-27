---
work_package_id: WP05
title: Lifecycle Gate + Thin next Caller
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- NFR-007
- NFR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
agent: "claude:opus:reviewer:reviewer"
shell_pid: "2584"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/retrospective/gate.py
- src/specify_cli/retrospective/lifecycle.py
- src/specify_cli/next/_internal_runtime/retrospective_hook.py
- tests/retrospective/test_gate_decision.py
priority: P1
status: planned
tags: []
---

# WP05 — Lifecycle Gate + Thin `next` Caller

## Objective

Implement the single source of truth for the retrospective gate (AD-001 / Q1-C). The gate decides whether a mission is allowed to transition to `done` based on the resolved `Mode` and the latest retrospective event for the mission. Both `specify_cli.next` and any status-transition surface that ever needs mission-level mode policy MUST consult this module.

Mission-level policy is **not** added to `specify_cli.status.transitions`. Per-WP transitions remain governed by the existing per-WP transition matrix.

## Spec coverage

- **FR-011** autonomous blocks until `retrospective.completed`.
- **FR-012** silent skip in autonomous is impossible.
- **FR-013** HiC offers retrospective and permits explicit skip.
- **FR-014** silent auto-run in HiC is impossible.
- **FR-015** HiC completion allowed after either `completed` or `skipped`.
- **NFR-007** gate adds < 500 ms overhead when `completed` is present.
- **NFR-008** deterministic gate decision.

## Context

Source-of-truth API contract is in [`../contracts/gate_api.md`](../contracts/gate_api.md). The full decision matrix (autonomous + HiC × 5 event-state branches) is enumerated there.

## Subtasks

### T020 — `gate.is_completion_allowed()` API + `GateDecision`/`GateReason` shapes

In `src/specify_cli/retrospective/gate.py`:

```python
def is_completion_allowed(
    mission_id: MissionId,
    *,
    feature_dir: Path,
    repo_root: Path,
    mode_override: Mode | None = None,
) -> GateDecision: ...
```

`GateDecision` and `GateReason` per `data-model.md`. The function reads:

- `meta.json` (for charter/mode source if `mode_override is None`).
- `feature_dir/status.events.jsonl` filtered to retrospective events for this mission.
- `repo_root/.kittify/missions/<mission_id>/retrospective.yaml` only when needed for hash verification.

### T021 — Decision matrix (8 rows)

Implement the eight rows from the contract as a typed dispatch:

| Mode | Latest retrospective event | Decision | `reason.code` |
|---|---|---|---|
| autonomous | none | block | `missing_completion_autonomous` |
| autonomous | `retrospective.completed` | allow | `completed_present` |
| autonomous | `retrospective.skipped` | block (or allow if charter authorizes) | `silent_skip_attempted` (or `skipped_permitted`) |
| autonomous | `retrospective.failed` | block | `facilitator_failure` |
| HiC | none | block | `silent_auto_run_attempted` (when next-driven) or generic block |
| HiC | `retrospective.completed` (operator-driven) | allow | `completed_present_hic` |
| HiC | `retrospective.completed` (runtime-driven) | block | `silent_auto_run_attempted` |
| HiC | `retrospective.skipped` | allow | `skipped_permitted` |
| HiC | `retrospective.failed` | block | `facilitator_failure` |

Implement as a dispatch keyed on `(mode.value, latest_retro_event_kind, requested_actor_kind)`.

### T022 — Charter-clause resolution for autonomous-skip override

In autonomous mode + `retrospective.skipped`, check whether the project charter has a clause authorizing operator-skip. If yes, return `allow=True` with `reason.code="skipped_permitted"` and `reason.charter_clause_ref` set. Implementation: read the same charter context API used by WP04; the clause is identified by an id pattern (e.g., `mode-policy:autonomous-allow-skip`). Document the expected clause shape in code-comment near the charter check.

### T023 — Operational predicates for "silent auto-run" and "silent skip"

- **Silent auto-run** (HiC): a `retrospective.completed` event whose upstream `retrospective.requested` event has `actor.kind == "runtime"` (not human) is silent. The gate examines the request event for the same retrospective sequence and blocks with `silent_auto_run_attempted` if the request was runtime-driven.
- **Silent skip** (autonomous): any `retrospective.skipped` in autonomous mode is silent unless the charter authorizes (T022). The gate blocks with `silent_skip_attempted`.

### T024 — Thin caller in `next/_internal_runtime/retrospective_hook.py`

```python
# src/specify_cli/next/_internal_runtime/retrospective_hook.py

from specify_cli.retrospective import gate as _gate

def before_mark_done(mission_id, *, feature_dir, repo_root) -> None:
    """Refuse to mark mission done if the gate says no."""
    decision = _gate.is_completion_allowed(
        mission_id=mission_id, feature_dir=feature_dir, repo_root=repo_root,
    )
    if not decision.allow_completion:
        raise MissionCompletionBlocked(decision)
```

`MissionCompletionBlocked` is a typed exception defined here (not in `gate.py`) so callers in `next` can catch it without importing from retrospective directly.

This file is the only `next/`-located module owned by this WP. WP06 wires the actual call from existing `next/` flow.

### T025 — Tests: every decision-matrix row + determinism replay

In `tests/retrospective/test_gate_decision.py`:

- One test per decision-matrix row.
- A determinism replay test: build an event log fixture, run the gate twice in the same process, assert identical `GateDecision` (including ordering of `blocking_event_ids`).
- A performance smoke test: gate decision for a mission with `retrospective.completed` present completes in < 500 ms (allow generous slack to avoid CI flakiness).

Use a fake event-log builder (a small helper in the test file or `tests/retrospective/_fakes.py`) so tests don't depend on real disk IO when not needed.

## Definition of Done

- [ ] All 8+ matrix rows covered by tests.
- [ ] Determinism replay test passes.
- [ ] Performance smoke test passes.
- [ ] Gate raises typed errors only (no bare `Exception`).
- [ ] No silent `allow=True` on any error path.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90% on `gate.py`, `lifecycle.py`, and the thin caller.
- [ ] No changes outside `owned_files`.

## Risks

- **Silent auto-run predicate**: too tight blocks legitimate operator-driven completion in HiC; too loose lets a runtime-driven `retrospective.completed` slip through. Tests must cover both legitimate and silent paths.
- **Charter clause shape**: agreed pattern needs to land in code-comment so future charter authors can find it. WP12 ADR also documents.

## Reviewer guidance

- Walk the matrix table in the test file alongside the matrix dispatch in `gate.py`. They must match row-for-row.
- Confirm `MissionCompletionBlocked` is raised, not returned, by the thin caller.
- Confirm the gate does not write to disk (read-only).

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Activity Log

- 2026-04-27T09:33:57Z – claude:sonnet:implementer:implementer – shell_pid=108 – Started implementation via action command
- 2026-04-27T09:46:28Z – claude:sonnet:implementer:implementer – shell_pid=108 – Ready for review: gate + decision matrix + thin caller; lifecycle.py stub for WP06. 38 tests, gate.py 95% coverage, retrospective_hook.py 100%, mypy strict clean.
- 2026-04-27T09:46:52Z – claude:opus:reviewer:reviewer – shell_pid=2584 – Started review via action command
