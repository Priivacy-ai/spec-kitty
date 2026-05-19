## Investigation outcome — 14-day window

Investigation per `mission-exception.md` `## Follow-up` operator commitment, mission `investigate-canary-followups-1142-1141-01KS02TV`. Cheapest-first hypothesis sweep H4 → H3 → H2 → H1 per spec C-004.

### Hypothesis tested

- **H4 — fixture state error**: RULED OUT.
- **H3 — sequencing race**: RULED OUT.
- **H2 — canary assertion drift**: PARTIALLY RULED OUT (force-contract dimension matches current spec-kitty; the captured failure is upstream of the force-check).
- **H1 — CLI regression (silent fan-out failure on backward emission)**: **LIKELY** (most plausible root cause; not fully bisected — full bisect requires a trusted-runner workstation with live SaaS auth).

### Commands run

```bash
# H4 — read scenario 4 fixture end-to-end
$EDITOR /tmp/sk-canary-1142/canary-repo/tests/identity_boundary/test_scenario_4_review_rejection_contract.py

# H3 — inspect peek logic (lines 231-294 of the same file) and verify it's a separate subprocess

# H2 — cross-check canary force-contract vs current spec-kitty contract source
grep -n 'backward rewind\|emit_force = True' src/specify_cli/cli/commands/agent/tasks.py
# tasks.py:1751-1759 — matches the canary's expectation

# H1 — git-log walk over the rollback emission surface
git log --oneline --since='2026-02-01' -- \
  src/specify_cli/status/store.py \
  src/specify_cli/status/emit.py \
  src/specify_cli/cli/commands/agent/tasks.py \
  src/specify_cli/status/adapters.py \
  src/specify_cli/sync/events.py \
  src/specify_cli/sync/__init__.py

# Trace the full emission pipeline: tasks.py:1751 → emit_status_transition →
# _saas_fan_out → fire_saas_fanout → _saas_fanout_handler → emit_wp_status_changed →
# OfflineQueue.enqueue
```

### Evidence

**H4 — RULED OUT** (`h4-evidence-1141.md`):

The captured failure (per `mission-exception.md`):

```
AssertionError: peeked row is not the rollback we triggered:
  from='for_review' to='in_review' payload=...
  at test_scenario_4_review_rejection_contract.py:543
```

`for_review → in_review` is itself a transition INTO `in_review`. Its presence in the queue proves the fixture reached `in_review` as designed. The fixture is not the problem.

**H3 — RULED OUT** (`h3-evidence-1141.md`):

The peek (`_peek_latest_wp_status_changed`, scenario file lines 231–294) runs in a subprocess via `run_spec_kitty_python` AFTER the `move-task` subprocess has exited. The offline queue is SQLite-backed with WAL; by the time the move-task process exits, any rows it wrote have been flushed. A race would manifest as intermittent results; the issue body describes the failure as deterministic.

**H2 — PARTIALLY RULED OUT** (`h2-evidence-1141.md`):

The canary's contract expectations match current spec-kitty code:

```python
# src/specify_cli/cli/commands/agent/tasks.py:1751-1759
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

Furthermore, the canary's FR-018 path (scenario 4 lines 553–567) handles the contract-drift case explicitly: if a row is enqueued without `force=True + reason`, it fails loudly with `failure_reason` naming `spec-kitty-events#32`. The captured failure is at **line 543** (the from/to_lane shape assertion), which fires BEFORE the FR-018 force-check. So the rollback row is simply not in the queue — the contract-drift dimension is not the failure axis here.

**H1 — LIKELY** (`h1-evidence-1141.md`):

The complete intended emission pipeline:

```
spec-kitty agent tasks move-task <wp> --to planned --note "<feedback>"
└─ tasks.py:1751  (auto-promote backward to emit_force=True)
   └─ emit_status_transition(...)  [status/emit.py:259]
      ├─ Step 5: _store.append_event_verified(...)  ← writes status.events.jsonl
      └─ Step 7: _saas_fan_out(event, ...)  [emit.py:483]
         └─ fire_saas_fanout(**kwargs)  [status/adapters.py:112]
            └─ for handler in _saas_handlers: handler(**kwargs)
               └─ _saas_fanout_handler  [sync/__init__.py adapter registration]
                  └─ emit_wp_status_changed(**kwargs)  [sync/events.py:204]
                     └─ OfflineQueue.enqueue(...)  ← the row the canary peek expects
```

Every link is currently present in `origin/main` (`commit 2881dfe94`). No commits since the parent mission landed (`fdca93e14`) have touched `status/emit.py`, `status/adapters.py`, `sync/__init__.py` or `sync/events.py`, so the pipeline as-shipped on `main` IS the same as when the canary captured its failure.

**The most plausible root cause is a silent fan-out failure.** `fire_saas_fanout` swallows all handler exceptions:

```python
# src/specify_cli/status/adapters.py:121-126
for handler in _saas_handlers:
    try:
        handler(**kwargs)
    except Exception:
        logger.warning("SaaS fan-out handler failed; canonical status log unaffected", exc_info=True)
```

If `_saas_fanout_handler` → `emit_wp_status_changed` → `OfflineQueue.enqueue` raises (DB lock, schema mismatch, daemon-ensure error, auth check on first write, etc.), the canonical event log gets the row but the offline queue does not. The canary's peek then finds the previous-latest row (`for_review → in_review`) and fails the line-543 shape assertion. This pattern is consistent with all observed evidence.

### Conclusion

LIKELY — H1 (silent fan-out failure on the backward emission code path). Not fully bisected: pinning the exact source requires a trusted-runner workstation with live SaaS auth, instrumented logging at `fire_saas_fanout` entry, and a re-run of scenario 4. That work is itself a follow-up mission, not part of this investigation.

### Recommendation

**A — open a new 1-WP follow-up mission** to instrument and fix. Proposed scope:

1. Add an info-level logging breadcrumb at `fire_saas_fanout` entry (`adapters.py:112`) and around `_saas_fanout_handler` so silent fan-out failures surface in operator logs.
2. Add a unit test (`tests/specify_cli/status/test_emit_backward_transition.py`) asserting a backward `in_review → planned` transition writes exactly one new row to a temp OfflineQueue.
3. Run scenario 4 from a trusted-runner workstation with the new logging; pin the exact handler step where the rollback emission fails.
4. Land the targeted fix and re-verify scenario 4 turns green.

Estimated: 1 WP, 4 subtasks, ~1–2 operator-days. Same shape as the original three CLI bugs that this mission's parent (`unblock-sync-identity-boundary-canary-01KRZJ07`) addressed.

---

*Investigated by claude:opus-4-7:researcher-robbie:implementer (orchestrated by HiC) within the 14-day window of mission `investigate-canary-followups-1142-1141-01KS02TV`. Outcome record: `kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/outcome-1141.md`. Hypothesis evidence files in the same directory: `h4-evidence-1141.md`, `h3-evidence-1141.md`, `h2-evidence-1141.md`, `h1-evidence-1141.md`.*
