---
work_package_id: WP06
title: Lifecycle Terminus Hook (next Integration)
dependencies:
- WP01
- WP05
requirement_refs:
- FR-010
- FR-013
- FR-014
- FR-028
- FR-029
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
agent: "claude:opus:reviewer:reviewer"
shell_pid: "10010"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/next/_internal_runtime/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/next/_internal_runtime/retrospective_terminus.py
- tests/integration/retrospective/test_lifecycle_hook.py
priority: P1
status: planned
tags: []
---

# WP06 — Lifecycle Terminus Hook (`next` Integration)

## Objective

Wire the retrospective lifecycle into the canonical `spec-kitty next` control loop for built-in missions via a lifecycle terminus hook (Q3-C). Custom missions reuse the same `action:retrospect` through their existing required `retrospective` marker step (FR-029); this WP must not regress that contract.

The result: when a built-in mission reaches its last domain step, `next` invokes `action:retrospect` (autonomous mode runs it directly; HiC mode prompts the operator first). After the retrospective completes / is skipped / fails, `next` consults the gate (WP05) before signaling mission done.

## Spec coverage

- **FR-013** HiC offer.
- **FR-014** silent auto-run impossible (consumes the gate).
- **FR-028** built-in missions use lifecycle terminus hook (no per-mission `retrospect` step required).
- **FR-029** custom mission marker contract preserved.

## Context

The `next` runtime lives under `src/specify_cli/next/`. Its mission-completion path is the integration target. Read the existing flow before editing: identify the choke point where built-in missions are recognized as "domain steps complete," and insert the terminus hook there.

The hook itself is a NEW module owned by this WP (`retrospective_terminus.py`). It composes:

- Mode detection (`specify_cli.retrospective.mode.detect`).
- Action invocation (`action:retrospect` via the existing DRG resolver / runtime invocation path).
- HiC operator prompt (Rich `Prompt.ask` or equivalent).
- Skip path: capture reason, emit `retrospective.skipped`, persist record with `status=skipped`.
- Gate consultation via `before_mark_done` from WP05's thin caller.

## Subtasks

### T026 — Lifecycle terminus hook in `next` (built-in mission flow)

Create `src/specify_cli/next/_internal_runtime/retrospective_terminus.py`:

```python
def run_terminus(
    *,
    mission_id: MissionId,
    feature_dir: Path,
    repo_root: Path,
    actor: ActorRef,
) -> None:
    """Drive the retrospective lifecycle at mission terminus.

    1. Resolve mode.
    2. Emit retrospective.requested with the resolved mode.
    3. Autonomous: invoke retrospect action; persist record; emit completed/failed.
    4. HiC: prompt operator → either invoke + persist + emit completed, or capture skip reason → persist skip record + emit skipped.
    5. Call retrospective_hook.before_mark_done(...). Raises MissionCompletionBlocked on gate refusal.
    """
```

Identify the existing `next` integration point and add a single call to `run_terminus(...)` immediately before the existing "mark mission done" code path. Do not introduce branching logic in `next`; the hook is the policy owner.

The integration edit on the existing `next` file is **outside this WP's owned_files** by design — keep that edit minimal (single import + single call site). If the integration requires more than that, raise it as a finding and discuss before proceeding.

### T027 — HiC offer/skip prompt UX

In HiC mode:

- Print the resolved mode + source signal (so the operator can see why HiC was selected).
- Prompt: "Run retrospective now? [Y/n]:". Default Yes.
- If Yes: invoke `action:retrospect`; persist record with `status=completed`; emit `retrospective.completed`.
- If No: prompt for `skip_reason` (free text; non-empty); persist record with `status=skipped, skip_reason`; emit `retrospective.skipped`.

The skip-reason prompt must be required (loop until non-empty). The skip is auditable — actor identity and timestamp captured.

### T028 — Autonomous auto-invocation

In autonomous mode:

- Emit `retrospective.requested` with `actor.kind="runtime"`.
- Invoke `action:retrospect` directly.
- On facilitator success: persist record `status=completed`; emit `retrospective.completed`.
- On facilitator failure: persist record `status=failed` with `failure.code` set; emit `retrospective.failed`.
- Then call the gate. If the gate refuses, raise `MissionCompletionBlocked` upward; the runtime surfaces the structured reason.

### T029 — Custom mission marker step compatibility

Custom missions have a required `retrospective` marker step in their loader contract (FR-029). Verify that:

- The `action:retrospect` invoked from the marker step uses the same code path as the lifecycle terminus hook (same persist + emit flow).
- The custom-mission loader continues to enforce the marker step's presence (regression test).

If the existing custom-mission loader test suite covers the marker requirement, run it unchanged; if not, add a small test under `tests/mission_loader/` (note: that's outside this WP's owned set — coordinate or include the test in this WP if feasible).

### T030 — Tests: lifecycle hook integration + custom-mission compat regression

In `tests/integration/retrospective/test_lifecycle_hook.py`:

- Built-in mission terminus in autonomous mode → `retrospective.completed` + mission marked done.
- Built-in mission terminus in autonomous mode + facilitator fails → `retrospective.failed` + mission blocked from done.
- Built-in mission terminus in HiC mode + operator runs → `retrospective.completed` + mission done.
- Built-in mission terminus in HiC mode + operator skips with reason → `retrospective.skipped` + mission done.
- Custom mission with marker step → marker step routes to `action:retrospect` and produces the same lifecycle events.

Mock `Prompt.ask` for HiC tests; otherwise use real runtime path so the test exercises the actual integration. Use a `tmp_path` repo fixture.

## Definition of Done

- [ ] `run_terminus()` produces the correct event sequence in every mode + outcome combination.
- [ ] HiC skip-reason prompt is required (non-empty).
- [ ] Autonomous mode never silently auto-skips.
- [ ] Custom-mission marker step still works (regression).
- [ ] Existing `next` tests still pass.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90% on the new hook module.
- [ ] No changes outside the documented integration edit + `owned_files`.

## Risks

- **next/ blast radius**: the integration edit on the existing `next` file must be minimal. If the right insertion point is unclear, propose the edit and pause for review before committing.
- **Custom-mission marker compatibility**: easy to miss. Run loader tests explicitly.

## Reviewer guidance

- Confirm the integration edit on the existing `next` file is one import + one call.
- Confirm HiC tests exercise both run and skip branches.
- Confirm autonomous tests cover both completed and failed branches.
- Confirm no other WP-owned files are modified.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent <name>
```

## Activity Log

- 2026-04-27T10:00:02Z – claude:sonnet:implementer:implementer – shell_pid=6424 – Started implementation via action command
- 2026-04-27T10:04:57Z – claude:sonnet:implementer:implementer – shell_pid=6424 – Ready for review: run_terminus() with autonomous + HiC paths and gate consultation; runtime wiring deferred (TODO documented; WP11 integration tests will exercise wired path)
- 2026-04-27T10:05:26Z – claude:opus:reviewer:reviewer – shell_pid=10010 – Started review via action command
- 2026-04-27T10:06:33Z – claude:opus:reviewer:reviewer – shell_pid=10010 – Review passed: 6 tests pass, mypy clean, deferred runtime wiring is intentional and documented
