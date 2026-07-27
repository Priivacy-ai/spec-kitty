# Implementation Plan: Phase 6 Composition Stabilization

**Mission**: phase6-composition-stabilization-01KQ2JAS
**Spec**: [spec.md](./spec.md)
**Created**: 2026-04-25
**Branch contract**: current=`main`, planning_base=`main`, merge_target=`main`, `branch_matches_target=true`

## Engineering Alignment

Narrow bug-fix tranche on three seams of the just-landed `software-dev` composition path. Implementation is constrained by `start-here.md`, the spec, and the current code shape:

- **Composer stays a composer.** `StepContractExecutor` does not run shell, does not run an LLM, does not pretend command steps ran (C-005).
- **`ProfileInvocationExecutor` is the single invocation primitive** for governance context, trail writing, and glossary checks (C-006).
- **Local-first trail.** `.kittify/events/profile-invocations/<id>.jsonl` is canonical; no remote sync added (C-007).
- **No second mission runner.** Composition advancement reuses the primitives the legacy DAG path already uses (NFR-005).
- **`Decision` shape is stable.** Public return shape from `runtime_bridge.decide_next_via_runtime(...)` is unchanged (FR-005).
- **`mission-runtime.yaml` files stay frozen** unless a regression test proves no other correct implementation (FR-004).

## Summary

Three bug fixes that together restore single-dispatch semantics, paired invocation lifecycles, and contract-action recording for the live `software-dev` composition path:

1. `#786` — `runtime_bridge.py` stops falling through to `runtime_next_step(...)` after a successful composition dispatch; instead, a new `_advance_run_state_after_composition(...)` helper performs run-state, lane, and prompt progression and a `Decision` is returned directly.
2. `#794` — `ProfileInvocationExecutor.invoke(...)` gains a keyword-only `action_hint: str | None = None` parameter that, when truthy alongside `profile_hint`, replaces the role-default-verb derivation. `StepContractExecutor.execute(...)` passes `action_hint=selected_contract.action`.
3. `#793` — `StepContractExecutor.execute(...)` wraps each composed step in `try/except/else` and calls `complete_invocation(payload.invocation_id, outcome="done"|"failed")` to close every invocation it starts.

## Technical Context

**Language/Version**: Python 3.13 (charter, `uv run --python 3.13 ...`)
**Primary Dependencies**: existing only — `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict`
**Storage**: filesystem only — `.kittify/events/profile-invocations/*.jsonl` (existing local-first trail)
**Testing**: `pytest` with the focused command from `start-here.md`; ≥90% coverage for new code (charter)
**Target Platform**: spec-kitty CLI (cross-platform Python)
**Project Type**: single project (CLI library)
**Performance Goals**: no perceptible change; bug-fix tranche
**Constraints**: see C-001 through C-011 in `spec.md`
**Scale/Scope**: 3 source files touched, 4 test files extended; ~3 work packages

### NEEDS CLARIFICATION

None. All open points were resolved against the source (see `research.md`).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded for `plan` (bootstrap mode):

- **DIRECTIVE_003 (Decision Documentation)** — applied. Each material design decision is recorded here with rationale (see "Implementation Approach" sections per issue) and in `research.md`.
- **DIRECTIVE_010 (Specification Fidelity)** — applied. Every plan section maps to FR/NFR/C IDs in `spec.md`. No deviations from the spec.
- **Tactic: requirements-validation-workflow** — applied via FR→test mapping below.
- **Tactic: premortem-risk-identification** — applied (see "Risks & Pre-mortems").
- **Charter policy summary**: `pytest` ≥90% coverage for new code, `mypy --strict` clean, `ruff` clean — gated as NFR-002/NFR-003/NFR-004.
- **Charter Check status**: PASS. No conflicts with charter; no Complexity Tracking violations.

## Phase 0 — Research Summary

Full notes in [research.md](./research.md). Key resolved decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `complete_invocation(...)` outcome value for composed steps | `"done"` on success, `"failed"` on exception | Matches existing `Literal["done", "failed", "abandoned"]` set in `invocation/record.py:34`; `"abandoned"` is reserved for user-initiated cancellation. The "completion does not imply host LLM did the requested generation" semantic is captured in tests/comments per `start-here.md`. |
| Where to break the legacy fall-through | In `decide_next_via_runtime(...)` after `_dispatch_via_composition(...)` returns | Composition success returns a `Decision` directly; non-composed actions still fall through to `runtime_next_step(...)`. Minimizes blast radius into the legacy path. |
| How to advance run-state without re-running legacy DAG action | New `_advance_run_state_after_composition(...)` helper in `runtime_bridge.py` reusing the same primitives `runtime_next_step(...)` uses for state/lane/prompt progression | Brief explicitly suggests this; satisfies NFR-005. |
| Where to add `action_hint` parameter | `ProfileInvocationExecutor.invoke(..., *, action_hint: str | None = None)` (keyword-only) | Matches `start-here.md` "Likely implementation direction"; default `None` preserves all existing call sites. |
| Empty-string `action_hint` semantics | Treat as `None` (legacy fallback) | EDGE-005 in spec; conservative. |
| `StepContractExecutor` try/except shape | Wrap each `invoke()`+per-step body in `try/except/else`; close with `"done"` on success, `"failed"` on exception, then re-raise | Closes lifecycle on both paths; preserves error propagation through the existing `Decision` error shape. |
| Frozen files | `mission-runtime.yaml` (both copies), `tasks.step-contract.yaml`, `record.py`, `writer.py`, `modes.py` | FR-004 holds; the existing fixed `tasks` guard is keyed by `legacy_step_id` and does not need to change. |

## Phase 1 — Design Artifacts

- [data-model.md](./data-model.md) — entities and invariants for invocation lifecycle pairing, action-hint widening, and the single-dispatch invariant.
- [contracts/invocation_executor_invoke.md](./contracts/invocation_executor_invoke.md) — `ProfileInvocationExecutor.invoke(...)` contract.
- [contracts/runtime_bridge_dispatch.md](./contracts/runtime_bridge_dispatch.md) — runtime-bridge dispatch contract.
- [contracts/step_contract_executor_lifecycle.md](./contracts/step_contract_executor_lifecycle.md) — `StepContractExecutor.execute(...)` lifecycle contract.
- [quickstart.md](./quickstart.md) — operator quickstart: how to verify the three behaviors locally.

## Project Structure

### Documentation (this feature)

```
kitty-specs/phase6-composition-stabilization-01KQ2JAS/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── invocation_executor_invoke.md
│   ├── runtime_bridge_dispatch.md
│   └── step_contract_executor_lifecycle.md
├── checklists/
│   └── requirements.md
└── tasks/             # populated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── next/
│   └── runtime_bridge.py                         # (touched) FR-001, FR-002, FR-005
├── mission_step_contracts/
│   └── executor.py                               # (touched) FR-008, FR-014
├── invocation/
│   ├── executor.py                               # (touched) FR-009..FR-013
│   ├── writer.py                                 # (read-only)
│   ├── record.py                                 # (read-only)
│   └── modes.py                                  # (read-only)
└── ... rest of tree unchanged ...

tests/specify_cli/
├── next/
│   └── test_runtime_bridge_composition.py        # (extended)
├── mission_step_contracts/
│   └── test_software_dev_composition.py          # (extended)
└── invocation/
    ├── test_invocation_e2e.py                    # (extended)
    └── test_writer.py                            # (touched only if writer surface changes — it does not)
```

**Structure Decision**: Single Python project. Existing layout is preserved; no new packages or modules.

## Implementation Approach (per issue)

### #786 — Stop legacy DAG fall-through (FR-001 / FR-002 / FR-003 / FR-004 / FR-005)

**Where**: `src/specify_cli/next/runtime_bridge.py`.

**Current behavior**: `_dispatch_via_composition(...)` returns `None` on success (line 485); `decide_next_via_runtime(...)` then falls through to `runtime_next_step(...)` (lines 986–991), which advances run state AND executes the legacy DAG dispatch handler — effectively double-dispatching the action.

**Fix**:

1. Make `_dispatch_via_composition(...)` return a `Decision` (not `None`) on the success path. The new `Decision` carries the same shape the legacy path produces, constructed from a new helper `_advance_run_state_after_composition(...)`.
2. The new helper reuses the same primitives `runtime_next_step(...)` uses internally for: emitting lane status events (via the same `SyncRuntimeEventEmitter`), recording mission-state advancement, and computing the next public step. It does **not** call any legacy DAG action handler.
3. Update `decide_next_via_runtime(...)` so that when `_dispatch_via_composition(...)` returns a non-`None` `Decision`, that `Decision` is returned immediately without falling through to `runtime_next_step(...)`.
4. Preserve the fixed `tasks` guard semantics exactly (FR-003): the guard already runs in `_check_composed_action_guard(...)` AFTER composition runs but BEFORE this advancement helper. Keep that ordering.
5. Public `Decision` shape and the legacy non-composed code path are unchanged (FR-005).

**Tests** (extend `tests/specify_cli/next/test_runtime_bridge_composition.py`):

- **Negative condition (FR-015)**: For each composed action (`specify`, `plan`, `tasks`, `implement`, `review`), patch the legacy DAG dispatch entry point and assert it is **not called** when `_dispatch_via_composition(...)` succeeds.
- **Run-state still advances (FR-002)**: Assert lane events are emitted and the returned `Decision` reflects progression to the next public step.
- **`Decision` shape unchanged (FR-005)**: Snapshot the `Decision` field set against a reference dict.
- **`tasks` guard semantics preserved (FR-003)**: existing `tasks_outline` / `tasks_packages` / `tasks_finalize` guard tests must continue to pass without modification.
- **Non-composed actions regression (EDGE-002)**: Assert legacy `runtime_next_step(...)` is still called for an action that is NOT in the composition allow-list.
- **Composition success but advancement raises (EDGE-003)**: Patch the new helper to raise; assert the raised error is surfaced through the existing `Decision` error shape and that legacy dispatch is **not** entered as a fallback.

### #794 — Preserve contract action with `profile_hint` (FR-009 – FR-014)

**Where**: `src/specify_cli/invocation/executor.py` (signature change), `src/specify_cli/mission_step_contracts/executor.py` (call site update).

**Fix in `invocation/executor.py`**:

1. Extend `invoke(...)` signature with a keyword-only `action_hint`:
   ```python
   def invoke(
       self,
       request_text: str,
       profile_hint: str | None = None,
       actor: str = "unknown",
       mode_of_work: ModeOfWork | None = None,
       *,
       action_hint: str | None = None,
   ) -> InvocationPayload:
   ```
2. Inside the `if profile_hint is not None:` branch, replace the unconditional derivation with:
   ```python
   if action_hint:
       action = action_hint
   else:
       action = self._derive_action_from_request(request_text, profile.role)
   ```
3. The router-backed branch is unchanged.
4. The `InvocationRecord(action=action, ...)` shape is unchanged — only the value supplied to `action` changes when `action_hint` is set.
5. Governance context assembly already reads from the record's `action`, so FR-013 follows for free.

**Fix in `mission_step_contracts/executor.py`**:

6. In `StepContractExecutor.execute(...)`, pass `action_hint=selected_contract.action` to every `invoke(...)` call (FR-014).

**Tests**:

- **Hint preserved (FR-010, Scenario D)**: parametrized over `{specify, plan, tasks, implement, review}`; assert started JSONL `action == <key>` and payload exposes the same.
- **Legacy fallback (FR-011, Scenario E)**: `invoke(profile_hint=...)` without `action_hint` keeps the derived role-default verb.
- **Empty-string `action_hint` (EDGE-005)**: `invoke(profile_hint=..., action_hint="")` falls back to derivation.
- **No regression for non-`profile_hint` callers (FR-012)**: existing `advise`/`ask`/`do` tests must pass unchanged.
- **End-to-end (FR-014)**: composed `software-dev/specify` action records `action="specify"`, not the role-default verb.

### #793 — Close invocation lifecycles (FR-006 / FR-007 / FR-008 / EDGE-001 / EDGE-004)

**Where**: `src/specify_cli/mission_step_contracts/executor.py`.

**Fix**:

1. In `StepContractExecutor.execute(...)`, wrap each composed step's `invoke(...)` + post-invoke body in `try/except/else`:
   ```python
   payload = self._invocation_executor.invoke(
       ...,
       action_hint=selected_contract.action,
   )
   try:
       # existing per-step body
       ...
   except Exception:
       self._invocation_executor.complete_invocation(
           payload.invocation_id, outcome="failed",
       )
       raise
   else:
       self._invocation_executor.complete_invocation(
           payload.invocation_id, outcome="done",
       )
   ```
2. Use only `complete_invocation(...)` — no direct JSONL writes (FR-008).
3. One-line code comment at the close site captures the "completion does not imply host LLM did the requested generation" semantic.
4. EDGE-004 (multiple composed steps): the try/except is per-step, so each invocation pairs independently.
5. EDGE-001 (mid-step exception): `failed` close runs before `raise`; the runtime bridge surfaces the error via the existing `Decision` error shape.

**Tests**:

- **Success closes (FR-006, Scenario B)**: every JSONL file produced by a composed action has paired `started` + `completed` (`outcome="done"`).
- **Failure closes (FR-007, Scenario C)**: per-step body patched to raise; JSONL has `started` + `failed`; original exception still propagates.
- **No orphan started-only files**: per-action sweep asserts paired counts.
- **Multi-step pairing (EDGE-004)**: composed action with ≥2 invocations; every invocation paired independently.
- **Lifecycle uses public API only (FR-008)**: monkey-patch `complete_invocation` and `InvocationWriter.write_*`; assert only `complete_invocation` is reached from the executor.

## Test Strategy

### Coverage Map (FR → tests)

| FR | Test file(s) | Test name (proposed) |
|----|--------------|----------------------|
| FR-001, FR-015 | `test_runtime_bridge_composition.py` | `test_composition_success_skips_legacy_dispatch[<action>]` (parametrized) |
| FR-002 | `test_runtime_bridge_composition.py` | `test_composition_success_advances_run_state_and_lane_events` |
| FR-003 | `test_runtime_bridge_composition.py` | existing `test_tasks_*_guard_*` (must pass unchanged) |
| FR-004 | implicit — diff inspection + ruff/mypy |
| FR-005 | `test_runtime_bridge_composition.py` | `test_decision_shape_unchanged_for_composed_action` |
| FR-006, FR-016 | `test_invocation_e2e.py`, `test_software_dev_composition.py` | `test_composed_action_pairs_started_with_completed` |
| FR-007, EDGE-001 | `test_invocation_e2e.py` | `test_composed_step_failure_writes_failed_completion` |
| FR-008 | `test_software_dev_composition.py` | `test_executor_uses_complete_invocation_api_only` |
| FR-009, FR-010 | `test_invocation_e2e.py` | `test_invoke_with_action_hint_and_profile_hint_records_hint[<action>]` |
| FR-011, EDGE-005 | `test_invocation_e2e.py` | `test_invoke_profile_hint_only_falls_back_to_derived_action`, `test_invoke_empty_action_hint_falls_back` |
| FR-012 | existing advise/ask/do tests (must pass unchanged) |
| FR-013 | `test_software_dev_composition.py` | `test_governance_context_uses_contract_action_when_hint_supplied` |
| FR-014 | `test_software_dev_composition.py` | `test_step_contract_executor_passes_action_hint` |
| FR-017 | covered above |

### Verification commands

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

## Risks & Pre-mortems

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Composition advancement helper accidentally re-emits a duplicate lane event already emitted by the composer. | Medium | Medium | Pre-implementation: enumerate which events the composer / guard already emit; test asserts each event fires exactly once per action. |
| `complete_invocation("done")` semantic looks wrong to a future reader who reads it as "host LLM finished generation". | Medium | Low | One-line code comment at the close site referencing this plan + spec; explicit test name `test_composed_action_outcome_is_done_even_though_composition_does_not_run_llm`. |
| Adding `action_hint` to `invoke()` collides with a downstream caller passing positional args. | Low | Low | Keyword-only (`*` separator); existing positional callers untouched; mypy --strict catches drift. |
| `tasks` guard ordering changes when we restructure dispatch flow. | Medium | High | Treat `_check_composed_action_guard(...)` call site as fixed; new advancement helper appended after it, never before; existing `tasks_*` guard tests must pass without modification. |
| "No direct JSONL writes from executor" assertion is brittle if implemented as code-grep. | Low | Low | Use a behavioral monkey-patch test that verifies only `complete_invocation` is the close path. |
| Composition fails AFTER per-step body but BEFORE the `else` branch (e.g. exception in `else` itself). | Very low | Medium | The `else` branch contains only a single `complete_invocation(..., "done")` call; if it raises, that is the existing writer/IO failure mode. We do not nest a second try/except. |
| `_derive_action_from_request` behavior changes silently because we added the guard. | Low | Low | Only triggered when `action_hint` is truthy; legacy path is byte-identical. Snapshot test on the legacy path. |

## Migration / Compatibility

- **Backwards compatible.** The `action_hint` kwarg defaults to `None`; every existing caller continues to work unchanged.
- **Trail format unchanged.** No new JSONL fields, no new outcome values, no new file naming.
- **No `mission-runtime.yaml` edits.** Packaged runtime collapse to the public `tasks` step (landed in PR #795) is preserved.
- **No `.kittify/charter/` edits.**
- **No CLI surface changes.**

## Out of Scope (re-affirmed from spec)

- `#505` custom mission loader (C-009).
- `#787` charter context compact mode regression.
- Research / documentation mission rewrites (`#504`, `#502`).
- Retrospective work (`#506`–`#511`), Phase 7 (`#469`), `spec-kitty explain`, Phase 4/5 reopen.
- Edits to `spec-kitty-events`, `spec-kitty-runtime`, `src/spec_kitty_events/`, `.kittify/charter/`.

## Complexity Tracking

*No Charter Check violations. Section intentionally empty.*

## Branch Contract (re-stated)

- Current branch at plan start: `main`
- Planning / base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`
- Summary: "Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main."

## Next Step

Run `/spec-kitty.tasks` to materialize the WP outline. Expected split:

- **WP01** — `#786` runtime bridge single-dispatch + `_advance_run_state_after_composition` helper (must land first; blocker for `#505`).
- **WP02** — `#794` `action_hint` kwarg on `ProfileInvocationExecutor.invoke(...)` + `StepContractExecutor` call-site update (lands before WP03 so completion records carry correct action).
- **WP03** — `#793` invocation lifecycle close in `StepContractExecutor.execute(...)`.

Dependency graph: WP01 independent; WP02 independent; WP03 depends on WP02.
