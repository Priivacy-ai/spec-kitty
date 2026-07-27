# Contract: `StepContractExecutor.execute(...)` Invocation Lifecycle

**Source file**: `src/specify_cli/mission_step_contracts/executor.py`
**Spec coverage**: FR-006, FR-007, FR-008, FR-014, EDGE-001, EDGE-004

## Lifecycle Invariant

For every composed step `s` executed inside `StepContractExecutor.execute(...)`:

> The invocation file produced by `ProfileInvocationExecutor.invoke(...)` for `s` MUST contain exactly one `started` record AND exactly one closing record.

The closing record is:
- `completed` with `outcome="done"` if the per-step body returns normally.
- `failed` with `outcome="failed"` if the per-step body raises.

No other outcome values are produced by this path.

## Pseudocode (post-change)

```python
for selected_contract in contracts_to_run:
    payload = self._invocation_executor.invoke(
        request_text=...,
        profile_hint=...,
        actor=...,
        mode_of_work=...,
        action_hint=selected_contract.action,   # FR-014
    )
    try:
        # existing per-step body — unchanged
        ...
    except Exception:
        # NOTE: outcome="done" or "failed" reflects whether the
        # *composition* step ran cleanly; it does NOT imply the host LLM
        # finished generation. The composition is a governance/trail unit.
        self._invocation_executor.complete_invocation(
            payload.invocation_id,
            outcome="failed",
        )
        raise
    else:
        self._invocation_executor.complete_invocation(
            payload.invocation_id,
            outcome="done",
        )
```

## Closure API

- Use `ProfileInvocationExecutor.complete_invocation(invocation_id, outcome=...)`.
- Do **not** import `InvocationWriter` from this module.
- Do **not** write to `.kittify/events/profile-invocations/*.jsonl` directly.
- These constraints satisfy FR-008, C-006, and C-007.

## Outcome Semantics

| Path | Outcome value | Why |
|------|---------------|-----|
| Per-step body returns normally | `"done"` | Existing literal; composition step completed without error |
| Per-step body raises | `"failed"` | Existing literal; composition step raised; original exception is re-raised after close |
| User cancellation (out of scope here) | `"abandoned"` | Reserved for user-initiated cancellation flows; **not produced by this path** |

The "completion does not imply host LLM finished generation" semantic is documented:
- as a one-line code comment at the close site;
- as an explicit test name (`test_composed_action_outcome_is_done_even_though_composition_does_not_run_llm`).

## Multi-Step Pairing (EDGE-004)

Each composed step has its own `try/except/else` block. Pairing is per-step:
- if step 1 succeeds and step 2 raises, step 1 is closed with `done`, step 2 with `failed`.
- if all steps succeed, every step is closed with `done`.
- the executor never re-uses a single try/except across multiple steps.

## Test Surface

| Test name | File | Asserts |
|-----------|------|---------|
| `test_composed_action_pairs_started_with_completed` | `test_invocation_e2e.py` and `test_software_dev_composition.py` | every JSONL produced by a composed action has exactly one `started` and one `completed` line (FR-006, Scenario B) |
| `test_composed_step_failure_writes_failed_completion` | `test_invocation_e2e.py` | per-step body patched to raise; JSONL has `started`+`failed`; original exception still propagates (FR-007, Scenario C, EDGE-001) |
| `test_executor_uses_complete_invocation_api_only` | `test_software_dev_composition.py` | monkey-patches verify `complete_invocation` is called from the executor; `InvocationWriter.write_*` is never called from this module (FR-008) |
| `test_step_contract_executor_passes_action_hint` | `test_software_dev_composition.py` | each `invoke(...)` call from the executor passes `action_hint=selected_contract.action` (FR-014) |
| `test_governance_context_uses_contract_action_when_hint_supplied` | `test_software_dev_composition.py` | governance context for a composed `software-dev/specify` reads `action="specify"` (FR-013) |
| `test_composed_action_outcome_is_done_even_though_composition_does_not_run_llm` | `test_invocation_e2e.py` | naming-as-documentation: outcome is `"done"` for composition success regardless of host execution |
| `test_composed_action_multistep_pairing` | `test_software_dev_composition.py` | composed action with ≥2 invocations pairs each independently (EDGE-004) |

## Failure Modes

- **`complete_invocation(...)` raises in the `else` branch** (e.g. writer IO failure): existing failure mode for the writer; the per-step body has already returned normally so no original exception is masked. Acceptable; not a new failure mode introduced by this contract.
- **Per-step body raises a `BaseException` (e.g. `KeyboardInterrupt`)**: the `except Exception` clause does NOT catch it; the invocation is left unclosed. This matches existing semantics for catastrophic interruption and is consistent with charter expectations (don't swallow `BaseException`).

## Non-Goals

- Inventing a new outcome value (`"composed"`, `"governance_only"`, etc.).
- Adding a JSONL field describing host LLM execution status.
- Adding retry / backoff around the close call.
- Changing the `complete_invocation(...)` signature.
