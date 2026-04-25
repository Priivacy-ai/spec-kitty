# Tasks: Phase 6 Composition Stabilization

**Mission**: phase6-composition-stabilization-01KQ2JAS
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Created**: 2026-04-25
**Branch contract**: current=`main`, planning_base=`main`, merge_target=`main`, `branch_matches_target=true`

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Audit runtime_bridge.py flow; lock in single-dispatch design | WP01 | | [D] |
| T002 | Add `_advance_run_state_after_composition(...)` helper | WP01 | | [D] |
| T003 | Make `_dispatch_via_composition(...)` return `Decision` on success | WP01 | | [D] |
| T004 | Update `decide_next_via_runtime(...)` to short-circuit on composition success | WP01 | | [D] |
| T005 | Add negative-condition + advancement + non-composed regression tests | WP01 | | [D] |
| T006 | Verify focused pytest + ruff + mypy --strict for WP01 surface | WP01 | | [D] |
| T007 | Extend `ProfileInvocationExecutor.invoke(...)` signature with keyword-only `action_hint` | WP02 | | [D] |
| T008 | Apply `action_hint` truthiness inside `profile_hint`-branch; preserve legacy fallback | WP02 | | [D] |
| T009 | Add direct unit + e2e tests for action_hint behavior in `test_invocation_e2e.py` | WP02 | | [D] |
| T010 | Verify focused pytest + ruff + mypy --strict for WP02 surface | WP02 | | [D] |
| T011 | Pass `action_hint=selected_contract.action` from `StepContractExecutor.execute(...)` | WP03 | |
| T012 | Wrap per-step body in `try/except/else`; close invocation with `done`/`failed` | WP03 | |
| T013 | Add a one-line code comment at the close site documenting the trail-only outcome semantic | WP03 | |
| T014 | Add lifecycle-pairing tests (success, failure, multi-step) in `test_software_dev_composition.py` | WP03 | |
| T015 | Add governance-context-uses-contract-action test (FR-013) and call-site-uses-action-hint test (FR-014) | WP03 | |
| T016 | Verify focused pytest + ruff + mypy --strict for WP03 surface; run the full focused suite | WP03 | |

`[P]` is reserved for cross-file parallelism within a single WP. WP01, WP02, and WP03 each own a different source-code area, so the WPs themselves can be lane-scheduled in parallel where their dependencies allow. WP03 depends on WP02 because WP03 calls `invoke(action_hint=...)`, which only exists after WP02 lands.

## Work Packages

### WP01 — Runtime Bridge: Stop Legacy DAG Fall-Through (#786)

**Goal**: Make composition-backed `software-dev` actions single-dispatch in `runtime_bridge.py`. After composition success, advance run state, lane events, and prompt progression via a new `_advance_run_state_after_composition(...)` helper, and return a `Decision` directly without falling through to `runtime_next_step(...)`.

**Priority**: P0 — must land first; explicit blocker on `#505`.

**Independent test**: `tests/specify_cli/next/test_runtime_bridge_composition.py` passes its existing tests AND its new negative-condition tests for the 5 composed actions, with no edits required in any other file outside this WP's `owned_files`.

**Implementation prompt**: [tasks/WP01-runtime-bridge-single-dispatch.md](tasks/WP01-runtime-bridge-single-dispatch.md)

**Owned files**:
- `src/specify_cli/next/runtime_bridge.py`
- `tests/specify_cli/next/test_runtime_bridge_composition.py`

**Authoritative surface**: `src/specify_cli/next/`

**Dependencies**: none

**Included subtasks**:
- [x] T001 Audit runtime_bridge.py flow; lock in single-dispatch design (WP01)
- [x] T002 Add `_advance_run_state_after_composition(...)` helper (WP01)
- [x] T003 Make `_dispatch_via_composition(...)` return `Decision` on success (WP01)
- [x] T004 Update `decide_next_via_runtime(...)` to short-circuit on composition success (WP01)
- [x] T005 Add negative-condition + advancement + non-composed regression tests (WP01)
- [x] T006 Verify focused pytest + ruff + mypy --strict for WP01 surface (WP01)

**Implementation sketch**:
1. Read `runtime_bridge.py` lines 393–486 and 980–991 to confirm the seams (`_dispatch_via_composition(...)`, `_check_composed_action_guard(...)`, `decide_next_via_runtime(...)`, `runtime_next_step(...)`).
2. Add `_advance_run_state_after_composition(...)` that reuses the same primitives `runtime_next_step(...)` uses for lane status events, mission-state advancement, and next-public-step computation. Do NOT call any legacy DAG action handler.
3. Have `_dispatch_via_composition(...)` call the new helper after `_check_composed_action_guard(...)` and return its `Decision`.
4. Update `decide_next_via_runtime(...)`: when `_dispatch_via_composition(...)` returns a non-`None` `Decision`, return it immediately. Non-composed actions still fall through to `runtime_next_step(...)`.
5. Add tests asserting (a) legacy dispatch handler is **not** entered after composition success for each of `{specify, plan, tasks, implement, review}`; (b) lane events and next-step advancement still occur; (c) the `Decision` field set is unchanged; (d) non-composed actions still reach `runtime_next_step(...)`; (e) when the helper raises, the error surfaces via the existing `Decision` error shape and legacy dispatch is not entered as a fallback.
6. Verify the focused pytest, ruff, and mypy --strict commands from `plan.md` all pass.

**Risks**:
- Duplicate lane events. Mitigation: enumerate emissions before adding the helper; assert each event fires exactly once per action.
- Re-introducing the P0 fixed `tasks` guard regression. Mitigation: keep `_check_composed_action_guard(...)` BEFORE the new helper and unchanged; existing `tasks_*` guard tests must pass without modification.

### WP02 — `ProfileInvocationExecutor.invoke(...)` Action Hint Parameter (#794, partial)

**Goal**: Add a keyword-only `action_hint: str | None = None` to `ProfileInvocationExecutor.invoke(...)`. When `profile_hint` and a truthy `action_hint` are both supplied, record `action_hint` as the action; otherwise preserve the existing role-default-verb derivation. The router-backed branch is untouched.

**Priority**: P1 — independent of WP01; lands before WP03 so the lifecycle-close work writes correct action records.

**Independent test**: `tests/specify_cli/invocation/test_invocation_e2e.py` passes its existing tests AND new direct unit/E2E tests for `action_hint` behavior, without any edits in `mission_step_contracts/`.

**Implementation prompt**: [tasks/WP02-invocation-action-hint.md](tasks/WP02-invocation-action-hint.md)

**Owned files**:
- `src/specify_cli/invocation/executor.py`
- `tests/specify_cli/invocation/test_invocation_e2e.py`

**Authoritative surface**: `src/specify_cli/invocation/`

**Dependencies**: none

**Included subtasks**:
- [x] T007 Extend `ProfileInvocationExecutor.invoke(...)` signature with keyword-only `action_hint` (WP02)
- [x] T008 Apply `action_hint` truthiness inside `profile_hint`-branch; preserve legacy fallback (WP02)
- [x] T009 Add direct unit + e2e tests for action_hint behavior in `test_invocation_e2e.py` (WP02)
- [x] T010 Verify focused pytest + ruff + mypy --strict for WP02 surface (WP02)

**Implementation sketch**:
1. Update the signature of `ProfileInvocationExecutor.invoke(...)` to add `*, action_hint: str | None = None` after `mode_of_work`.
2. Inside the `if profile_hint is not None:` branch, replace the unconditional `_derive_action_from_request(...)` call with a truthiness guard:
   - if `action_hint` is truthy → `action = action_hint`;
   - else → `action = self._derive_action_from_request(request_text, profile.role)`.
3. Do NOT modify the router-backed branch.
4. Add tests:
   - parametrized `test_invoke_with_action_hint_and_profile_hint_records_hint[specify|plan|tasks|implement|review]` — started JSONL has `"action": "<key>"` and the returned payload exposes the same.
   - `test_invoke_profile_hint_only_falls_back_to_derived_action` — legacy fallback unchanged.
   - `test_invoke_empty_action_hint_falls_back` — `action_hint=""` is treated as legacy fallback (EDGE-005).
   - `test_invoke_router_branch_unchanged_with_action_hint` — `profile_hint=None, action_hint="anything"` does not affect router-backed action.
5. Verify the focused pytest, ruff, and mypy --strict commands from `plan.md` pass on this WP's owned surface.

**Risks**:
- Positional-arg drift. Mitigation: `*` separator makes `action_hint` keyword-only; mypy --strict catches drift.
- Silent change to the legacy fallback. Mitigation: keep the truthiness check; explicit empty-string fallback test.

### WP03 — Composition Executor: Pass `action_hint` and Close Invocation Lifecycles (#794 completion + #793)

**Goal**: In `StepContractExecutor.execute(...)`, (a) pass `action_hint=selected_contract.action` on every `invoke(...)` call; (b) wrap each per-step body in `try/except/else` and close every invocation it starts via `complete_invocation(...)` with `outcome="done"` on success or `outcome="failed"` on exception (then re-raise). No direct JSONL writes from this module.

**Priority**: P1 — depends on WP02 for `action_hint`. Completes both #794 and #793.

**Independent test**: `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` passes its existing tests AND new tests for FR-014, FR-013, FR-006, FR-007, FR-008, EDGE-001, EDGE-004; the focused pytest suite (`runtime_bridge_composition` + `software_dev_composition` + `invocation_e2e` + `writer`) is green.

**Implementation prompt**: [tasks/WP03-step-contract-executor-lifecycle.md](tasks/WP03-step-contract-executor-lifecycle.md)

**Owned files**:
- `src/specify_cli/mission_step_contracts/executor.py`
- `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py`

**Authoritative surface**: `src/specify_cli/mission_step_contracts/`

**Dependencies**: WP02

**Included subtasks**:
- [ ] T011 Pass `action_hint=selected_contract.action` from `StepContractExecutor.execute(...)` (WP03)
- [ ] T012 Wrap per-step body in `try/except/else`; close invocation with `done`/`failed` (WP03)
- [ ] T013 Add a one-line code comment at the close site documenting the trail-only outcome semantic (WP03)
- [ ] T014 Add lifecycle-pairing tests (success, failure, multi-step) in `test_software_dev_composition.py` (WP03)
- [ ] T015 Add governance-context-uses-contract-action test (FR-013) and call-site-uses-action-hint test (FR-014) (WP03)
- [ ] T016 Verify focused pytest + ruff + mypy --strict for WP03 surface; run the full focused suite (WP03)

**Implementation sketch**:
1. In `StepContractExecutor.execute(...)`, on every `self._invocation_executor.invoke(...)` call (the one at the existing site for each composed contract step), add `action_hint=selected_contract.action`.
2. Immediately after the `invoke(...)` call, wrap the existing per-step body in:
   ```python
   try:
       # existing per-step body
       ...
   except Exception:
       self._invocation_executor.complete_invocation(payload.invocation_id, outcome="failed")
       raise
   else:
       self._invocation_executor.complete_invocation(payload.invocation_id, outcome="done")
   ```
3. Add a one-line code comment at the `else` branch capturing the trail-only outcome semantic: that `"done"` describes the composition-step trail, not host-LLM generation.
4. Add tests:
   - `test_step_contract_executor_passes_action_hint` — every `invoke(...)` call from the executor receives `action_hint=selected_contract.action`.
   - `test_governance_context_uses_contract_action_when_hint_supplied` — composed `software-dev/specify` records `action="specify"` in started JSONL.
   - `test_composed_action_pairs_started_with_completed` — every JSONL produced by a composed action has paired `started` + `completed` (`outcome="done"`).
   - `test_composed_step_failure_writes_failed_completion` — per-step body patched to raise; JSONL has `started` + `failed`; original exception still propagates.
   - `test_composed_action_multistep_pairing` — composed action with ≥2 invocations pairs each independently.
   - `test_executor_uses_complete_invocation_api_only` — monkey-patches verify the executor reaches `complete_invocation`, never `InvocationWriter.write_*` directly.
   - `test_composed_action_outcome_is_done_even_though_composition_does_not_run_llm` — naming-as-documentation regression guard.
5. Verify the focused pytest suite, ruff, and mypy --strict from `plan.md` all pass.

**Risks**:
- Per-step body raising a non-`Exception` (`BaseException`) bypasses close. Mitigation: existing semantics; `KeyboardInterrupt`/`SystemExit` are catastrophic and consistent with charter expectations.
- `complete_invocation` itself raising in the `else` branch (writer/IO failure). Mitigation: existing failure mode; we do NOT nest a second try/except — the original step body has already returned normally.
- Reviewer mistakes outcome `"done"` for "host LLM finished generation". Mitigation: the explicit named test from step 4 is the durable documentation.

## Phase Ordering

There are no setup or polish phases for this tranche — it is a focused bug-fix mission with three parallelizable code surfaces. Per dependency:

```
WP01 (independent) ──────────────────────────┐
                                             ├──► merge
WP02 (independent) ──► WP03 (depends WP02) ──┘
```

Lane allocation will be computed by `finalize-tasks`. Expected: at least two lanes (one for WP01, one for the WP02→WP03 sequence).

## Parallel Opportunities

- **WP01 and WP02** can be implemented in parallel: they share no `owned_files`.
- **WP03** must wait for WP02's `action_hint` kwarg landing.
- Within each WP, subtasks are sequential by design — they touch the same file(s).

## MVP Scope

This entire tranche is the MVP. Each WP delivers a single FR cluster:
- WP01 → FR-001..FR-005, FR-015
- WP02 → FR-009..FR-012, EDGE-005
- WP03 → FR-006..FR-008, FR-013, FR-014, FR-016, FR-017, EDGE-001, EDGE-004

Without all three, `#505` cannot proceed credibly.

## Verification (mission-level, after all WPs)

Run from repo root:

```bash
uv sync --python 3.13 --extra test

uv run --python 3.13 --extra test python -m pytest \
  tests/specify_cli/next/test_runtime_bridge_composition.py \
  tests/specify_cli/mission_step_contracts/test_software_dev_composition.py \
  tests/specify_cli/invocation/test_invocation_e2e.py \
  tests/specify_cli/invocation/test_writer.py \
  -q

uv run --python 3.13 python -m ruff check \
  src/specify_cli/next/runtime_bridge.py \
  src/specify_cli/mission_step_contracts/executor.py \
  src/specify_cli/invocation/executor.py \
  tests/specify_cli/next/test_runtime_bridge_composition.py \
  tests/specify_cli/mission_step_contracts/test_software_dev_composition.py \
  tests/specify_cli/invocation/test_invocation_e2e.py

uv run --python 3.13 python -m mypy --strict \
  src/specify_cli/next/runtime_bridge.py \
  src/specify_cli/mission_step_contracts/executor.py \
  src/specify_cli/invocation/executor.py
```

All commands MUST exit zero. Coverage on changed lines MUST be ≥90%.

## Branch Strategy

- Current branch at workflow start: `main`
- Planning / base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`

Execution worktrees will be allocated per computed lane via `lanes.json` after `finalize-tasks` runs.
