---
affected_files: []
cycle_number: 5
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-11T17:00:51Z'
reviewer_agent: user
wp_id: WP07
---

# WP09 aggregate review finding — changes requested from WP07

The real public opt-out surfaces do not invoke the existing durable
`settle_attempts_for_opt_out` authority. After `disable_checkout_sync()` returns,
a PREPARED attempt remains `prepared` with no result, and a response-uncertain
attempt remains `unknown` with no terminal result. A late worker can therefore
remain recoverable after explicit revocation.

Reproduction:

`uv run --extra test pytest -q tests/sync/test_transport_revocation_matrix.py --maxfail=2`

Wire the canonical consent opt-out action to settle that project's attempts
after the refusal is durably written and before the action returns. Preserve the
existing lease, deadline, cancellation, and terminal-unknown semantics; do not
reimplement settlement in routing or in the WP09 test harness.
