# Baseline Refresh — P0 Test Failures

**Date**: 2026-06-01
**Commit SHA**: 29a34c70884f5082e0c4e5d6e144d94a55c6a0fc
**Full suite result**: Full suite run in progress at time of targeted analysis (see note below)

## Targeted Cluster Results

The four P0 clusters were run individually with `--tb=short` to get fast, clean failure
evidence. The full suite run was initiated concurrently but had not completed by the time
targeted analysis was finished (still at ~44% through the suite).

| Issue | Cluster | Targeted failures | Status |
|-------|---------|-------------------|--------|
| #1301 | tests/sync/ + tests/contract/ | 1 | STILL REPRODUCES |
| #1303 | tests/charter/synthesizer/ | 0 | STALE (resolved by prior commits) |
| #1304 | tests/doctrine/ | 0 | STALE (resolved by prior commits) |
| #1305 | tests/next/ | 0 | STALE (resolved by prior commits) |

### Cluster Details

**#1301 — STILL REPRODUCES**

Command: `pytest tests/sync/ tests/contract/ -q --tb=short -p no:cacheprovider`
Result: `1 failed, 1949 passed, 9 skipped, 17 warnings in 125.47s`

Failing test:
```
FAILED tests/sync/test_runtime_event_emitter.py::TestSyncRuntimeEventEmitter::test_adapter_emits_mission_run_and_lifecycle_sequence
```

Root cause: The adapter emits 6 events but the test expects 8. Specifically,
`DecisionInputRequested` and `DecisionInputAnswered` events are missing from the emitted
sequence. The assertion diff shows:

```
At index 4 diff: 'MissionRunCompleted' != 'DecisionInputRequested'
Right contains 2 more items, first extra item: 'MissionRunCompleted'
```

This confirms the shared-package events adapter does not implement
`emit_decision_input_requested` / `emit_decision_input_answered` handlers (or they do not
enqueue events). This is a genuine #1301 defect.

**#1303 — STALE**

Command: `pytest tests/charter/synthesizer/ -q --tb=short -p no:cacheprovider`
Result: `372 passed in 19.77s`

All synthesizer tests pass. The non-determinism issue described in #1303 is resolved.

**#1304 — STALE**

Command: `pytest tests/doctrine/ -q --tb=short -p no:cacheprovider`
Result: `1975 passed, 84 warnings in 56.88s`

All doctrine/glossary tests pass. Anchor drift issue described in #1304 is resolved.

**#1305 — STALE**

Command: `pytest tests/next/ -q --tb=short -p no:cacheprovider`
Result: `464 passed, 4 warnings in 67.63s`

All `next` tests pass. The exit-code regressions described in #1305 are resolved.

## Fix Scope

WPs to execute: **#1301** — 1 failing test in `tests/sync/test_runtime_event_emitter.py`

WPs to skip (stale): #1303, #1304, #1305 — all resolved by prior commits

## Out-of-Scope Failures

From the cluster #1301 targeted run, `tests/contract/` had 0 failures (all 1949
tests/contract + tests/sync tests ran, 1 failed in tests/sync only).

The full suite is still running. Any failures outside the four clusters that surface in the
full suite result are **out of scope** for this mission. If the full suite result is
available before WP02 begins, it should be appended to this document.

## Recommendation

Only **WP02 and beyond** need to address the single remaining failure. WPs targeting #1303,
#1304, and #1305 can be marked as skipped/stale. Mission scope is effectively reduced to
fixing `tests/sync/test_runtime_event_emitter.py::TestSyncRuntimeEventEmitter::test_adapter_emits_mission_run_and_lifecycle_sequence`.
