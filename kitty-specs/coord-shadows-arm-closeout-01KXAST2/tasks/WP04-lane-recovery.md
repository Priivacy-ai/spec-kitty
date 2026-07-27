---
work_package_id: WP04
title: "IC-LANE — sparse-checkout on lane recovery"
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "20646"
history:
- created at planning (tasks) — parallel lane; fixes the #2514 recovery regression (FR-006 only — FR-008 withdrawn, the allocator has no stale-claim decision)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/worktree_allocator.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- tests/specify_cli/lanes/test_worktree_allocator_recovery.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-006 +
Scenario 2 + the edge case "non-coord topologies → sparse-checkout re-registration is a no-op;
byte-identical to today", [plan.md](../plan.md) §IC-LANE (the "Close-by-construction (not 'mirror
the guards')" design note — hoist the computation, don't duplicate the guard). **FR-008 (an
allocator-side stale-claim decision consulting a liveness helper) has been withdrawn from this
mission** — the allocator has no stale-claim decision to wire liveness into. This WP is scoped
solely to FR-006: the sparse-checkout recovery fix. Do not import `core/process_liveness` or any
liveness helper into `worktree_allocator.py`.

## Objective
`allocate_lane_worktree` (`lanes/worktree_allocator.py`) has two branches: fresh-create
(~:195-212), which registers the coord-topology sparse-checkout exclusion (so
`status.events.jsonl` / `status.json` never land in the lane worktree), and recovery
(~:172-184, triggered by `_branch_exists(...)` — the branch survives but the worktree directory
was lost, e.g. an agent process killed by OS idle-sleep), which currently **skips**
sparse-checkout entirely — re-leaking status files into a recovered coord-topology lane and
reintroducing the exact husk defect this mission closes (#2514/Scenario 2). This WP hoists the
`coordination_branch`/`short_id` computation above the recovery branch and extracts one
`_register_sparse_checkout_if_coord` helper both paths call — "close by construction", not two
independently-maintained copies of the same guard. This is the WP's entire scope (FR-006 only).

## Subtasks

### T018 — Hoist `coordination_branch` / `short_id` above the recovery branch
Today `coordination_branch = _read_coordination_branch(repo_root, mission_slug)` is called at
~:195, *after* the recovery branch (`if _branch_exists(repo_root, branch): ... return worktree_path,
branch` at ~:172-184) has already returned. Move this computation (and the `short_id =
resolve_mid8(mission_slug, mission_id=lanes_manifest.mission_id) or None` computation, currently
at ~:210-211, which uses the already-imported `resolve_mid8` from ~:28) **above** the recovery
branch, so both the recovery path (~:172) and the fresh-create path (~:195+) have access to the
same two values without recomputing them twice. Both are derivable purely from parameters already
in scope at ~:172 (`repo_root`, `mission_slug`, `lanes_manifest`) — no new parameters need
threading into the function signature. Preserve the exact semantics of each: `_read_coordination_branch`
returns `None` for legacy (no-coord) missions; `resolve_mid8(...) or None` preserves the existing
`None`-on-decline contract (the function's own comment documents this: "resolve_mid8's
decline-to-`""`-contract; `or None` preserves the prior `None` behaviour").

### T019 — Extract `_register_sparse_checkout_if_coord` and call it from BOTH paths
Add a helper (module-level private function, alongside the other `_`-prefixed helpers in this
file):

```python
def _register_sparse_checkout_if_coord(
    worktree_path: Path,
    mission_slug: str,
    coordination_branch: str | None,
    short_id: str | None,
) -> None:
    if coordination_branch is not None and short_id is not None:
        register_lane_sparse_checkout(worktree_path, mission_slug, short_id)
```

(adjust the parameter list/order to whatever reads cleanest against the existing
`register_lane_sparse_checkout` signature — the point is ONE call site for the guard, not the
exact shape above). Both guards (`coordination_branch is not None` — currently checked at ~:197
via the enclosing `if coordination_branch is not None:` block — AND `short_id is not None` —
currently checked at ~:211) must be preserved exactly; do not weaken either to an implicit
truthiness check if the current code uses explicit `is not None`.

Call this helper from:
- The **fresh-create** path, replacing its current inline `if short_id is not None:
  register_lane_sparse_checkout(...)` block (~:210-212) — same call, now routed through the
  shared helper.
- The **recovery** branch (~:172-184), immediately after `_recover_lane_worktree(...)` and
  `_validate_worktree_clean(...)` succeed, using the T018-hoisted `coordination_branch`/`short_id`
  values — this is the actual #2514 fix.

The **non-coord path** (`coordination_branch is None`, the `else:` branch at ~:214 handling
`mission_branch` legacy missions) must remain a byte-identical no-op: `_register_sparse_checkout_if_coord`
called with `coordination_branch=None` does nothing, by construction of the guard inside the
helper — do not add a second, separate no-op branch for this case.

### T020 — Tests: sparse-checkout on recovery, and non-coord no-op
In `tests/specify_cli/lanes/test_worktree_allocator_recovery.py`:
- **(a)** Recover a coord-topology lane: set up a mission with a `coordination_branch` in
  `meta.json`, create+register a lane, delete the worktree directory (simulating the OS-kill
  scenario) while leaving the branch intact, then call `allocate_lane_worktree` again and assert
  it takes the recovery branch (not fresh-create) AND that the resulting worktree has
  sparse-checkout registered — assert directly that the recovered worktree does **not** contain
  `status.events.jsonl` / `status.json` (the Scenario 2 acceptance bar), not just that
  `register_lane_sparse_checkout` was called.
- **(b)** Recover a **non-coord** (legacy `mission_branch`) lane the same way and assert the
  recovery path is a byte-identical no-op compared to today — no sparse-checkout call, no
  behavior change from the pre-WP04 code path.

### T021 — Closeout: lint/type/architectural verification
Run `uv run pytest tests/specify_cli/lanes/ -q`, `uv run ruff check
src/specify_cli/lanes/worktree_allocator.py tests/specify_cli/lanes/test_worktree_allocator_recovery.py`,
`uv run mypy src/specify_cli/lanes/worktree_allocator.py` — zero new issues, zero new
suppressions. Confirm full `tests/architectural/` 0-failed. Confirm via `git diff` that the
non-coord (flat/single-branch) allocation path is unchanged — this WP's edits are scoped entirely
to the coord-topology recovery branch and the shared helper extraction.

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP04` allocates an execution worktree per the lane computed from
`lanes.json`. No WP dependency — fully parallel with the WP01→WP02→WP03 spine and with WP05/WP06.
This WP has no import or build-order relationship with WP05 (FR-008, the sole reason for that
coupling, has been withdrawn).

## Definition of Done
- `coordination_branch`/`short_id` are computed once, above both the recovery and fresh-create
  branches; `_register_sparse_checkout_if_coord` is the single call site both paths use.
- A recovered coord-topology lane materializes no `status.events.jsonl`/`status.json`; a recovered
  non-coord lane is byte-identical to pre-WP04 behavior.
- `uv run pytest tests/specify_cli/lanes/ -q` green; `uv run ruff check` + `uv run mypy` clean,
  zero new suppressions; full `tests/architectural/` 0-failed.

## Risks
- **Recomputing instead of hoisting** — a tempting shortcut is to just duplicate the
  `_read_coordination_branch`/`resolve_mid8` calls inside the recovery branch rather than hoisting
  them once; this reintroduces the "two drifting guard copies" problem the plan explicitly warns
  against. Hoist, don't duplicate.
- **Weakening a guard during extraction** — `_register_sparse_checkout_if_coord` must preserve
  both `is not None` checks exactly; an accidental `if coordination_branch:` (truthy) instead of
  `is not None` could change behavior for an edge-case falsy-but-not-None value.
  Diff carefully against the original guards.

## Reviewer Guidance
Confirm: `_register_sparse_checkout_if_coord` is genuinely called from both the recovery and
fresh-create branches (grep for `register_lane_sparse_checkout` — it should appear exactly once,
inside the new helper); both `is not None` guards are preserved; the non-coord path diff is empty
(byte-identical); the recovery test asserts absence of the actual status files, not just a mock
call; no `core/process_liveness` import anywhere in this WP's diff (FR-008 withdrawn); ruff/mypy
clean; full arch suite 0-failed.

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T11:03:50Z – claude:sonnet:python-pedro:implementer – shell_pid=4168956 – Assigned agent via action command
- 2026-07-12T11:14:58Z – claude:sonnet:python-pedro:implementer – shell_pid=4168956 – WP04 IC-LANE: one _register_sparse_checkout_if_coord helper both paths; 6 recovery tests green, ruff clean, mypy no-new (line-73 pre-existing); commit 4a0c3c7ad
- 2026-07-12T11:15:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=20646 – Started review via action command
- 2026-07-12T11:20:16Z – user – shell_pid=20646 – APPROVE (opus renata): one sparse-checkout helper both paths; recovery status-file-absence tested; no liveness creep
