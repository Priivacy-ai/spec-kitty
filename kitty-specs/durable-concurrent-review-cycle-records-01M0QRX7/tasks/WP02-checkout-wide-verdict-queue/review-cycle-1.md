---
affected_files: []
cycle_number: 1
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T05:01:23Z'
reviewer_agent: user
wp_id: WP02
---

**Issue 1 — Non-finite timeouts violate the bounded-wait contract.**

`src/specify_cli/review/verdict_commit_queue.py:100` rejects only values `<= 0`. Both `math.nan` and `math.inf` pass that check. With another process holding the queue, a `math.nan` contender remained blocked beyond a two-second subprocess deadline instead of returning a typed refusal, so the public API can violate its documented bounded-interval guarantee. Validate that `timeout_seconds` is finite as well as positive (for example with `math.isfinite`) before creating/acquiring the lock. Add focused tests for `nan`, positive infinity, negative infinity, zero, and negative values; every invalid value must fail before lock acquisition.

**Issue 2 — The checked-in tests do not prove live cross-process exclusion or wait-in-line acquisition.**

`tests/review/test_verdict_commit_queue.py:147` terminates the spawned owner before the parent attempts acquisition, while `test_default_timeout_is_forwarded_and_filelock_timeout_is_typed` replaces `FileLock` with a fake. Consequently, the suite would still pass if the production primitive failed to exclude a second live process. Add a portable `spawn` test in which process A holds the real queue while process B/parent attempts the real queue and receives `VerdictSaveBusy` after a short finite timeout. Also release A normally and prove a waiting contender then acquires, so the user-confirmed “wait in line wins” behavior is causal rather than inferred from post-death cleanup. Use bounded joins and assert both child exit codes.

**Review checklist evidence.**

- Dead code: N/A for this deliberately foundational WP; WP03/WP04 are the explicitly declared production integration dependents. Recheck live production callers before those packages are approved.
- Synthetic-fixture test: FAIL for the cross-process contention behavior described in Issue 2; the timeout-mapping unit test uses a fake lock and the process-death test does not contend while the owner is alive.
- Silent empty return: PASS; none found.
- Requirement coverage: FAIL for FR-002's real contention/refusal behavior until Issue 2 is covered. Keying/topology behavior is otherwise exercised with real repositories and linked worktrees.
- Frozen surface: PASS; no generic status lock, Git-topology, cycle, or command-orchestration file was modified by the WP implementation commits.
- Locked decisions: PASS; no daemon, retry loop, isolated index, placement authority, or unrelated-commit serialization was introduced.
- Shared-file ownership: PASS; implementation commits modify only the two declared owned files.
- Production fragility: FAIL for the unbounded non-finite timeout path in Issue 1; the typed timeout/reentrancy raises themselves are documented and appropriate.

Declared gates passed locally: 9 focused tests, Ruff, and strict mypy. A manual live-contender probe produced `VerdictSaveBusy` for a finite `0.2`-second timeout, confirming the implementation's ordinary finite path works; a `nan` contender hung past the independent two-second deadline, reproducing Issue 1.
