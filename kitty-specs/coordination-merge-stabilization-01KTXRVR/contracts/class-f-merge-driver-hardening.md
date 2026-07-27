# Contract: Class F — Merge-Driver Hardening (#1736 residuals)

**Surfaces**: `lanes/merge.py` (subprocess environment), `coordination/status_transition.py:399-400` (exception discipline), `tests/status/test_event_log_merge.py` (schema ratchet).

## F-1: Single environment authority (FR-008b)

GIVEN any subprocess invocation inside the lane-merge pipeline (`_merge_branch_into` and peers)
THEN its environment is produced by `_make_merge_env()` (extracted helper) — no inline `os.environ` copies with ad-hoc PATH/GIT_* mutations.
Ratchet (AC-F1): test asserting every subprocess call site in the module routes through the helper.

## F-2: Deterministic mixed-schema event sort (FR-008c)

GIVEN an event log containing entries with `at`, entries with legacy `timestamp`, and entries with neither
WHEN `merge_event_payloads` sorts them
THEN the order is deterministic and total (documented tie-break), identical across repeated runs.
Ratchet (AC-F2): `test_merge_event_payloads_mixed_at_timestamp_neither` in `tests/status/test_event_log_merge.py`.

## F-3: Narrow exception mask (FR-008d)

GIVEN the lane status read at `coordination/status_transition.py:399-400`
THEN only `(ValueError, FileNotFoundError)` trigger the documented GENESIS fallback; all other exceptions propagate.
Ordering (C-004): lands with/after the Class B resync so stale-worktree reads don't newly throw.
Ratchet (AC-F3): test injecting a non-expected exception and asserting propagation; test for each expected type asserting fallback.
