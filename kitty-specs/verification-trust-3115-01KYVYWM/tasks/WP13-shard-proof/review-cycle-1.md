---
affected_files: []
cycle_number: 1
mission_slug: verification-trust-3115-01KYVYWM
reproduction_command:
reviewed_at: '2026-08-01T09:43:20Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP13
---

# WP13 unblock — dependencies satisfied

WP13 was parked in `blocked` while its declared dependencies were outstanding. All four are now
approved:

- **WP03** — the width guard and the fold proof (FR-003, FR-004)
- **WP05** — the sync-cone leak guard (FR-007)
- **WP07** — the token-manager verdict, applied (FR-009)
- **WP12** — the default per-test timeout (FR-016, FR-017)

No review feedback is outstanding against WP13; it has never been implemented or reviewed. This
transition is a dependency unblock, not a rejection response.

## One correction WP13 must carry, and it changes its node-id list

`#3115`'s issue body names `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`
as an affected case. **That test has never exhibited the failure.** Established by WP06 from the live
CI log (job `91126025663`, run `30621215287`, `fast-tests-sync`, Python 3.12.3, `-n auto --dist
loadfile`, head `bb2020fea9`) and confirmed by two independent reviewers:

```
tests/sync/tracker/test_saas_client.py:534: in test_exponential_backoff_intervals
    assert len(sleep_calls) == 3
E   assert 71 == 3                                                            [gw5]

tests/sync/tracker/test_saas_client_origin.py:261: in test_429_retries_then_raises
    mock_sleep.assert_called_once_with(2.0)
E   AssertionError: Expected 'sleep' to be called once. Called 556 times.     [gw2]
```

The wrong node propagated from the issue into `spec.md`, the WP files, WP06's ten floor selections
and every orchestrator brief, through three adversarial squads and eleven analysis passes — because
each layer inherited it and nobody re-opened the log.

**WP13's enumerated node-id list comes from the same issue text and must be corrected before it is
used as acceptance evidence.** The full record is at
`kitty-specs/verification-trust-3115-01KYVYWM/notes/sleep-count-attribution.md`.

Also relevant to WP13's shard proof: the sync half is deferred (`#3136`), and `fast-tests-status` is
skipped by a job-dependency gate rather than a path filter (`#3127`), so it will be absent from any
shard enumeration unless `fast-tests-sync` goes green.
