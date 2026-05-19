# #1141 Hypothesis 2 (canary assertion drift) — PARTIALLY RULED OUT

**Claim**: The canary encoded a contract that was true at one point but is no longer correct.

## Evidence

The scenario 4 docstring explicitly cites a current, authoritative spec-kitty source line as its contract anchor:

> spec-kitty repo source line:
>   `src/specify_cli/cli/commands/agent/tasks.py:1747-1759`
>   "Auto-promote backward transitions to force=True with canonical reason shape" — sets `emit_force = True` and composes the `reason` from the rollback feedback pointer.

Inspection of the cited code confirms the canary's contract IS the current contract:

```python
# Auto-promote backward transitions to force=True with canonical reason shape.
# Contract: spec-kitty-events docs/consumer-contract-dossier-v2.4.0.md
# § "Backward Transitions: The Review-Rejection Family".
if not force and _is_backward_transition(old_lane, canonical_lane):
    emit_force = True
    original_reason = None if emit_reason is None or emit_reason.startswith("move-task: ") else emit_reason
    reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
    if review_feedback_pointer and review_feedback_pointer != "force-override":
        reason_parts.append(review_feedback_pointer)
    if original_reason:
        reason_parts.append(original_reason)
    emit_reason = ": ".join(reason_parts)
```

The downstream `emit_status_transition(...)` call (`status/emit.py:259`) writes the canonical event then fans out via `_saas_fan_out` → `fire_saas_fanout` → `_saas_fanout_handler` → `emit_wp_status_changed` (`sync/__init__.py` adapter registration block + `sync/events.py:204`). The fan-out passes `force=event.force` and `reason=event.reason` through, so a correctly-functioning pipeline produces a `WPStatusChanged` queue row with `payload["force"] == True` and `payload["reason"]` non-empty.

**Furthermore, the canary's own FR-018 path handles the contract-drift case** (scenario 4 lines 553–567):

```python
if force_value is True and isinstance(reason_value, str) and reason_value.strip():
    force_branch = "emitted"  # ASSERT FR-011.emitted
else:
    # Row was enqueued but does NOT carry force=True or a non-empty reason —
    # FR-018: fail loudly without relaxing the assertion.
    upstream_gap_reason = (
        "rollback row enqueued without force=True + reason "
        f"(force={force_value!r}, reason={reason_value!r}); "
        f"events_package_version={canary_run.events_package_version!r}; "
        f"upstream ref: spec-kitty-events#32"
    )
```

The captured assertion in `mission-exception.md` is at scenario 4 **line 543**, which is the **upstream** assertion (`from_lane == "in_review" and to_lane == "planned"`), not the FR-018 force-check. So the failure happens BEFORE the force-contract check.

If the failure were canary drift on `force` semantics, the FR-018 branch would fire instead. The failure being at line 543 (the from/to_lane shape check) tells us the rollback row **is not present in the queue at all** — the peek found a stale `for_review → in_review` row.

## Verdict

**Partially RULED OUT.** The canary's `force=True + reason` contract IS the current spec-kitty contract (no drift on that dimension). The captured failure is at a different assertion (line 543, from/to_lane shape), which proves the rollback row never reached the offline queue. The investigation moves to H1.
