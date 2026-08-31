---
affected_files: []
cycle_number: 4
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T11:16:47Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 Review Feedback — Cycle 4

## Verdict

Rejected after the first native PR run exposed missing cross-platform readiness and insufficient failure evidence in the acceptance harness.

## Hosted evidence

- macOS passed all three exact nodes.
- Ubuntu failed the baseline in round 2 with `unproven_refusal`.
- Windows failed the baseline in round 0 with `unproven_refusal` and the event mutant before both spawned workers reached the stale-preimage seam.
- Run: https://github.com/Priivacy-ai/spec-kitty/actions/runs/32719727958

## Required corrections

1. Make the busy oracle validate the actual production envelope: nonzero exit, `result="error"`, `verdict_durably_persisted=false`, `durability_classification="busy"`, `durability_reason="verdict_save_busy"`, null evidence/destination refs, and monotonic elapsed time of at least 9.5 seconds. Independently prove that reviewer produced no event or evidence. Do not parse broad human error text.
2. Replace the invented synthetic `{error: {code: busy, timeout_seconds: 10}}` fixture with the real envelope and add a negative assertion proving the obsolete invented shape is not accepted.
3. Add an explicit spawn-worker readiness handshake. `_sc004_start_workers` must not return until both persistent workers have completed process startup and are ready to receive requests. Do not paper over Windows startup with a retry-to-green.
4. Preserve each `_sc004_get_pair` result and include reviewer, exit code, parsed payload, elapsed time, seam hits, and bounded command output in assertion diagnostics. A hosted `unproven_refusal` must identify its actual child outcome.
5. Keep the exact baseline and both causal mutants unchanged in strength: 50 rounds, `spawn`, real command entry point, and no skip/xfail/retry.
6. Add/adjust focused tests proving the production-envelope oracle, readiness handshake, and diagnostic projection without accepting any new terminal outcome.

This is test-only remediation. If the detailed rerun reveals a generic commit/event error rather than the valid typed busy envelope, reject the owning production WP with that exact evidence; do not speculate or patch production from WP01.

## Required evidence

- Exact three-node suite passes locally.
- Windows, macOS, and Linux hosted jobs each complete successfully on the corrected oracle/harness.
- Mutation nodes still turn red for their intended causal removals.
- Ruff and strict mypy pass on the owned integration test.
