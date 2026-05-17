---
work_package_id: WP01
title: Backward Detector + Emit-Path Fix
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-backward-transition-cli-emit-01KRV8GC
base_commit: deb78f02a559839dac05e5332da3149edee1929d
created_at: '2026-05-17T15:36:17.631963+00:00'
subtasks:
- T001
- T002
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4206"
history:
- timestamp: '2026-05-17T15:30:00Z'
  actor: planner
  action: created
  note: Initial WP01 prompt drafted by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
mission_slug: backward-transition-cli-emit-01KRV8GC
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
priority: P1
role: implementer
tags: []
---

# WP01 — Backward Detector + Emit-Path Fix

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are a Python implementer working on the CLI emit path of the spec-kitty repo.

## Objective

Make the CLI emit honest `WPStatusChanged` events when a user requests a backward `move-task`. Today the emit sets `force=False` even though the operator's intent is clearly a rewind (e.g. `in_review → planned` for a review rejection). After this WP, the emit auto-promotes `force=True` with a canonical reason on backward moves, while preserving every other code path (forward, explicit-`--force`, terminal-lane).

## Context

- Cross-repo planning issue: `Priivacy-ai/spec-kitty-planning#16`.
- Contract anchors (Mission 1, merged in `spec-kitty-events` mission_number=15):
  - Module docstring of `src/spec_kitty_events/status.py` ("Review-Rejection Transition Family")
  - `docs/consumer-contract-dossier-v2.4.0.md` §7
- Mission spec: `kitty-specs/backward-transition-cli-emit-01KRV8GC/spec.md`
- Plan: `kitty-specs/backward-transition-cli-emit-01KRV8GC/plan.md`
- Research (R-001..R-006): `kitty-specs/backward-transition-cli-emit-01KRV8GC/research.md`
- Local code contract (THE source of truth for your changes): `kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md`
- Data model: `kitty-specs/backward-transition-cli-emit-01KRV8GC/data-model.md`

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- Lane: assigned by `finalize-tasks`. Single-lane mission (WP01 + WP02 same lane).

## Worktree Setup (per the worktree guide)

After the workflow puts you in the lane worktree:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/spec-kitty/.worktrees/<lane-path>
python3.11 -m pip install -e ".[dev]"
```

Editable installs do not propagate to fresh worktrees. WP02 will need the install to run pytest; you don't need it for the source edit but installing now avoids surprise.

## Subtasks

### T001 — Add `_is_backward_transition` Helper

**Purpose**: A pure predicate that returns True iff both lanes are in the canonical forward order AND the target precedes the current.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/tasks.py`.
2. Locate the existing closure `_lane_targets_for_emit` at line ~1714.
3. Inside it, note the local list:
   ```python
   forward = [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, Lane.DONE]
   ```
4. Extract this list to a module-level private constant `_FORWARD_ORDER` placed near the top of the file (after imports, before the first function definition). Update `_lane_targets_for_emit` to reference `_FORWARD_ORDER` instead of the local literal.
5. Add a new private function (module-level, adjacent to the constant or near `_lane_targets_for_emit` if it's also module-level — keep them co-located):

   ```python
   def _is_backward_transition(current_lane: str, target_lane: str) -> bool:
       """Return True iff target precedes current in the canonical forward order.

       Returns False for non-forward lanes (BLOCKED, CANCELED), equal lanes,
       and forward moves. See:
       kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md
       """
       c = resolve_lane_alias(current_lane)
       t = resolve_lane_alias(target_lane)
       if c not in _FORWARD_ORDER or t not in _FORWARD_ORDER:
           return False
       return _FORWARD_ORDER.index(t) < _FORWARD_ORDER.index(c)
   ```

6. If extracting `_FORWARD_ORDER` to module level proves harder than expected (e.g. import-cycle), fall back to duplicating the literal inside `_is_backward_transition`. Both options are acceptable; module-level is preferred for DRY.

**Files**:

- `src/specify_cli/cli/commands/agent/tasks.py` (modify — additive helper + minor refactor of `_lane_targets_for_emit` to use the constant)

**Validation**:

- [ ] `python -c "from specify_cli.cli.commands.agent.tasks import _is_backward_transition; assert _is_backward_transition('in_review', 'planned') is True; assert _is_backward_transition('planned', 'claimed') is False; assert _is_backward_transition('done', 'planned') is False; assert _is_backward_transition('claimed', 'claimed') is False"` — exit 0 (smoke test; can be done as a `python -c` from inside the worktree).
- [ ] `uv run ruff check src/specify_cli/cli/commands/agent/tasks.py` exits 0.
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` exits 0 (or matches the project's standing typing convention for this file).
- [ ] Existing `_lane_targets_for_emit` behavior unchanged (the FR-008e skip-ahead forward expansion test in WP02 will codify this).

### T002 — Insert Auto-Promote Block at Hotspot

**Purpose**: After the existing `emit_force = force` and `emit_reason` fallback at lines ~1710-1712, insert the auto-promote logic per the contract Decision Procedure.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/tasks.py` at line ~1710.
2. The current code looks like:

   ```python
   # Keep force semantics strict: only user-requested --force should bypass guards.
   emit_force = force
   if not emit_reason:
       emit_reason = f"Force move to {target_lane}" if force else f"move-task: {old_lane} -> {target_lane}"
   ```

3. AFTER that block (and BEFORE the existing `def _lane_targets_for_emit` at line 1714), insert:

   ```python
   # Auto-promote backward transitions to force=True with canonical reason shape.
   # The review-rejection family (in_review/approved/for_review/in_progress -> planned)
   # is contract-required to be a forced backward emit per:
   # spec-kitty-events docs/consumer-contract-dossier-v2.4.0.md § "Backward Transitions:
   # The Review-Rejection Family" and the status.py module docstring.
   # See: kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md
   if not force and _is_backward_transition(old_lane, canonical_lane):
       emit_force = True
       if emit_reason is None or emit_reason.startswith("move-task: "):
           reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
           if review_feedback_pointer and review_feedback_pointer != "force-override":
               reason_parts.append(review_feedback_pointer)
           emit_reason = ": ".join(reason_parts)
   ```

4. Preserve everything around this block. Do not touch the `_lane_targets_for_emit` closure (other than its constant reference per T001), the `transition_targets` assignment, or the downstream emit loop.

**Files**:

- `src/specify_cli/cli/commands/agent/tasks.py` (modify — single block addition; total diff ~30 lines including T001)

**Validation**:

- [ ] Block reads correctly when viewed with `git diff -- src/specify_cli/cli/commands/agent/tasks.py`.
- [ ] `uv run ruff check src/specify_cli/cli/commands/agent/tasks.py` exits 0.
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` exits 0.
- [ ] Existing `uv run pytest tests/specify_cli/cli/commands/agent/test_tasks.py -q` exits 0 (no regression in existing move-task tests).
- [ ] A manual sanity check: from a test scratch dir, drive `move_task` for `approved → planned` without `--force` and inspect the emitted event in `status.events.jsonl` — `force` should be `true`, `reason` should start with `"backward rewind: approved -> planned"`. (Optional during implement; WP02 codifies this.)

## Integration Verification

After T001 + T002 land in the worktree:

```bash
cd <lane-worktree>
uv run pytest tests/specify_cli/cli/commands/agent/test_tasks.py -q
uv run ruff check src/specify_cli/cli/commands/agent/tasks.py
uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py  # if project standard
```

All three exit 0.

## Definition of Done

- [ ] `_is_backward_transition` helper added.
- [ ] Auto-promote block inserted at the hotspot.
- [ ] No edits outside `src/specify_cli/cli/commands/agent/tasks.py`.
- [ ] Existing tests still pass (no regression).
- [ ] Lint + type-check clean.
- [ ] Subtasks marked: `spec-kitty agent tasks mark-status T001 T002 --status done --mission backward-transition-cli-emit-01KRV8GC`
- [ ] WP moved to `for_review`: `spec-kitty agent tasks move-task WP01 --to for_review --note "Auto-promote backward emit fix landed; existing tests pass" --mission backward-transition-cli-emit-01KRV8GC`
- [ ] Commit message: `feat(WP01): auto-promote force=True with canonical reason on backward move-task`

## Risks

| Risk | Mitigation |
|---|---|
| Extracting `_FORWARD_ORDER` triggers an import cycle | Fall back to duplicating the literal inside `_is_backward_transition`. Both pass FR-001. |
| Some pre-existing test indirectly relies on `force=False` for backward moves | Research R-004 found none; WP02 + the full-suite gate catch any miss. |
| `review_feedback_pointer` is not in scope at the modification site | Research confirmed it's set at line 1538 and remains in scope through line ~1810 (the emit loop). If genuinely out of scope, fall back to omitting the feedback-ref segment. |
| User passes `--note "move-task: ..."` text that happens to match the generic fallback prefix | Acceptable — the rewrite produces a strictly more informative reason. Documented in research R-003 as accepted trade-off. |

## Reviewer Guidance

A reviewer should:

1. Confirm the diff is ~30 lines, localized to `tasks.py`.
2. Confirm the `_is_backward_transition` predicate matches the contract's Decision Procedure (lanes outside `FORWARD_ORDER` return False; equal returns False; backward returns True).
3. Confirm the auto-promote block:
   - Does NOT fire when `force=True` (explicit-force path preserved, FR-011).
   - Does NOT fire on forward moves (FR-004).
   - Does NOT mutate user-supplied `--note` text (R-003).
   - Sets `emit_force = True` on backward + non-force.
   - Synthesizes the canonical reason shape with optional feedback-ref.
4. Confirm `_lane_targets_for_emit` semantics are unchanged (only the constant reference was moved out).
5. Run the existing test suite to confirm zero regression: `uv run pytest tests/specify_cli/cli/commands/agent/test_tasks.py -q`.

## Activity Log

- 2026-05-17T15:36:19Z – claude:opus:python-pedro:implementer – shell_pid=3059 – Assigned agent via action command
- 2026-05-17T15:41:24Z – claude:opus:python-pedro:implementer – shell_pid=3059 – Backward detector + auto-promote block landed; existing tests pass; smoke OK
- 2026-05-17T15:42:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=4206 – Started review via action command
- 2026-05-17T15:43:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=4206 – Review passed: backward detector + auto-promote block landed correctly; _FORWARD_ORDER extracted DRY; only tasks.py touched; no new imports; existing tests + ruff + mypy clean; helper smoke 9/9.
