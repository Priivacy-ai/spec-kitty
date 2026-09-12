---
affected_files: []
cycle_number: 1
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T05:20:12Z'
reviewer_agent: user
wp_id: WP01
---

**Issue 1 — Refusal classification is vacuous and can accept unrelated or exit-zero failures.**

`tests/integration/test_review_durability_matrix.py:1850-1861` treats the one non-success result as a valid refusal when any occurrence of `state`, `transition`, `busy`, or `timeout` appears anywhere in stdout, exception text, or an arbitrary JSON object. It never requires `refusal.exit_code != 0`, a structured error envelope, a stable error code/classification, or proof that the current state actually prohibits the requested transition. An exit-zero warning/malformed payload, worker exception mentioning “state”, or unrelated transition error can therefore satisfy the allowed one-success-plus-refusal outcome. Require nonzero exit, a parseable repository error envelope with an allowlisted stable reason, false/absent durability, and causal evidence: a busy refusal must consume the configured acquisition bound, while a state refusal must name the exact authoritative pre-state/requested transition and be independently validated against production transition policy. Add focused negative-oracle cases proving exit-zero, missing payload, broad substring, unrelated exception, and immediate timeout-shaped failures are rejected.

**Issue 2 — The event mutant can report the expected class without proving the evidence leg stayed intact.**

The task contract requires both committed evidence records before accepting `missing_authoritative_event`, but `_sc004_oracle` checks exact events first (`:1874-1892`) and returns immediately when one event is missing, before executing either `git show` check (`:1895-1906`). The current product still has the shared-index evidence race that this mission exists to fix, so the event-mutant run can lose an evidence commit as well and nevertheless pass with the requested event classification. Before judging the event mutant, independently prove both command results are durable-success envelopes, both distinct pointers resolve via `git show` at the governed ref, and both blobs match reviewer/body. Then prove exactly the event leg is absent. Also assert every selected lock binding was seam-hit (`lock:tasks` plus `lock:emit` for fallback; `lock:tasks` plus `lock:transaction` for coordination), not only one of each pair.

**Issue 3 — The evidence mutant is incompatible with the planned production read-back protection.**

`test_sc004_evidence_commit_mutant_reports_missing_committed_evidence:2095-2098` requires both mutated commands to exit zero. WP03/WP04 are explicitly planned to verify governed-ref content and return a nonzero persistence refusal when the router fabricates `committed` without writing Git. Once that protection lands, this negative control will fail for the wrong reason and cannot remain the stable SC-004 mutation proof. Keep the commit seam-hit requirement, but make the mutation oracle accept and distinguish the two correct protection layers: (a) a lying success is killed by independent `missing_committed_evidence` read-back, or (b) production itself returns a structured nonzero `persistence_failed`/missing-evidence refusal with no authoritative event and no durability claim. In both cases assert the ordinary baseline acceptance classifier rejects the mutated round for the exact evidence cause; do not hard-code exit-zero as a precondition.

**Review evidence and checklist.**

- Exact baseline node: expected red, failing on round 0 with `authoritative_event_mismatch` because the returned event has no `review_result`.
- Exact fallback+coord event mutant node: passed and reported the expected event classification, but causal isolation fails Issue 2.
- Exact evidence mutant node: passed against current production, but is not stable under the specified downstream fix (Issue 3).
- Ruff: passed for the owned test file.
- Dead code: N/A; this WP adds tests/helpers only, no public production API.
- Synthetic-fixture test: FAIL due Issues 1 and 2; the command surface is real, but the oracle can accept non-causal shapes.
- Silent empty return: N/A for production; no production code changed.
- FR coverage: FAIL until refusal non-vacuity and independent mutation causality are enforced.
- Frozen surface: PASS; commit `983018e04` changes only the owned integration test.
- Locked decisions: PASS; uses `spawn`, the Typer reviewer command, governed placement, exact event IDs, and no test-only product lock.
- Shared-file ownership: PASS; only `tests/integration/test_review_durability_matrix.py` changed.
- Production fragility: N/A; no production raises added.

The worker itself does not directly call `create_rejected_review_cycle` or append the event store. Existing direct-writer/`fork` tests elsewhere in the same legacy module are outside the new SC-004 worker and were not introduced by this WP.
