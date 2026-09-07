# Contract: Decision events reach the decision log on every engine-facing path

**Modules**: `src/runtime/next/runtime_bridge.py`, `src/specify_cli/events/decision_log.py`
**Durable record**: `kitty-specs/<mission>/decisions.events.jsonl` (coordination partition)

## Rules

| # | Rule | Before | After | Test |
|---|---|---|---|---|
| F1 | On a strict-policy advance (`enabled and timing == "before_completion" and failure_policy == "block"`) whose decision is `decision_required`, the buffered `DecisionInputRequested` is appended to the decision log exactly once after the flush. | dropped (flushed into plain seam) | appended once | `test_strict_policy_decision_required_reaches_decision_log` (red→green) |
| F2 | On composition dispatch, a `DecisionInputRequested` raised by `advance_run_state_after_composition` is appended to the decision log, regardless of policy. | dropped (plain seam passed) | appended once | `test_composition_dispatch_decision_required_reaches_decision_log` (red→green) |
| F3 | On a strict-policy terminal advance whose gate refuses, nothing is appended to the decision log and no `MissionRunCompleted` reaches any sink; run state is rolled back. | holds | holds | `test_strict_policy_refused_terminal_gate_writes_nothing` (green→green) |
| F4 | A single gated `decision_required` advance yields exactly one decision-log entry (no duplicate from flush + direct emit). | n/a | holds | `test_gated_flush_does_not_duplicate` |
| F5 | Non-decision moments buffered on the gated path pass through `DecisionGitLog` to `inner` in original order. | holds via plain seam | holds via wrap | existing buffer tests + F1 fixture asserts order |
| F6 | `DecisionGitLog.seed_from_snapshot(snapshot)` delegates to `inner.seed_from_snapshot` when present, otherwise no-op; never raises. | absent | present | `tests/specify_cli/events/test_decision_log.py` (new case) |
| F7 | The bridge source contains no engine-facing reference to the plain seam: neither `flush(ctx.sync_emitter)` nor `sync_emitter=ctx.sync_emitter`. | violated ×2 | holds | `tests/architectural/test_runtime_emitter_seam.py` |

## Code changes that satisfy the rules

- `runtime_bridge.py:2187` — `buffer.flush(ctx.sync_emitter)` → `buffer.flush(ctx.emitter_for_engine)` (F1, F4, F5).
- `runtime_bridge.py:1976` — `sync_emitter=ctx.sync_emitter` → `sync_emitter=ctx.emitter_for_engine` (F2).
- `decision_log.py` — add `seed_from_snapshot` pass-through (F6; required by F2 because `runtime_bridge_engine.py:344` seeds the emitter it receives).

## Disclosure

CHANGELOG `[Unreleased] - 3.2.7rc1` → `### Fixed`: one entry stating that decision requests raised under the strict retrospective policy and on composition dispatch were never written to the mission's decision log, that they now are, and that the no-op emitter seam was consolidated onto the canonical runtime Protocol (ADR 2026-09-06-2).
