# Contract: `ProfileInvocationExecutor.invoke(...)`

**Source file**: `src/specify_cli/invocation/executor.py`
**Spec coverage**: FR-009, FR-010, FR-011, FR-012, FR-013, EDGE-005

## Signature (post-change)

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
    ...
```

The `*` separator makes `action_hint` keyword-only. Default `None` is preserved across all existing callers.

## Behavioral Matrix

| Inputs | Branch entered | Action source |
|--------|----------------|---------------|
| `profile_hint` set, `action_hint` is a non-empty string | `profile_hint`-branch | `action_hint` verbatim |
| `profile_hint` set, `action_hint` is `None` | `profile_hint`-branch | `_derive_action_from_request(request_text, profile.role)` (legacy) |
| `profile_hint` set, `action_hint == ""` | `profile_hint`-branch | `_derive_action_from_request(...)` (legacy fallback per EDGE-005) |
| `profile_hint` not set | router-backed branch | `result.action` from router decision (legacy, unchanged) |

## Invariants

1. **Backwards compatibility**: any call site that does not pass `action_hint` produces byte-identical output to the pre-change code (FR-011, FR-012).
2. **Hint truthiness**: empty-string `action_hint` is treated as if the kwarg were not supplied (EDGE-005). Non-empty strings are passed through verbatim.
3. **Router branch is untouched**: `action_hint` has no effect when `profile_hint` is `None` (FR-012).
4. **`InvocationRecord.action`** is set to the chosen action key in all branches (already true; this contract just changes which value is chosen).
5. **Governance context assembly** reads `action` from the record; therefore FR-013 follows automatically when FR-010 holds.

## Test Surface

| Test name | File | Asserts |
|-----------|------|---------|
| `test_invoke_with_action_hint_and_profile_hint_records_hint[specify\|plan\|tasks\|implement\|review]` | `test_invocation_e2e.py` | parametrized over the 5 contract actions; `started` JSONL has `"action": "<key>"` |
| `test_invoke_profile_hint_only_falls_back_to_derived_action` | `test_invocation_e2e.py` | `invoke(profile_hint=...)` without `action_hint` records the role-default verb |
| `test_invoke_empty_action_hint_falls_back` | `test_invocation_e2e.py` | `action_hint=""` is treated as legacy fallback |
| `test_invoke_router_branch_unchanged_with_action_hint` | `test_invocation_e2e.py` | When `profile_hint` is `None`, `action_hint` is ignored |
| existing advise/ask/do tests | `test_invocation_e2e.py` and friends | Continue to pass without modification (FR-012) |

## Failure Modes

- **Type mismatch on `action_hint`**: callers passing a non-string non-`None` value will fail mypy --strict; runtime `TypeError` is acceptable for clearly-buggy callers (no runtime validation needed beyond what mypy enforces).
- **Bogus action string**: this contract does not validate the value of `action_hint` against any allow-list; downstream consumers (governance context, trail format) accept any string. Validation is the caller's responsibility.

## Non-Goals

- Validating `action_hint` against a fixed enum of contract actions.
- Changing the `InvocationRecord` shape, the JSONL format, or the writer surface.
- Affecting the router-backed branch.
