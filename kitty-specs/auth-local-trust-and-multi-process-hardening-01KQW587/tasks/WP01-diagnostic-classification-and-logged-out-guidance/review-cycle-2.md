---
affected_files: []
cycle_number: 2
mission_slug: auth-local-trust-and-multi-process-hardening-01KQW587
reproduction_command:
reviewed_at: '2026-05-05T14:14:01Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-05-05T14:25:19Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Review passed: cycle 3 verified prior no-token sync blocker fixed; unauthenticated failures/report agree and queue preserved; focused sync/tracker tests passed"
---

**Issue 1**: Logged-out hosted sync still has no machine-facing `unauthenticated` classification.

`BackgroundSyncService._perform_full_sync()` returns a fresh empty `BatchSyncResult()` when `_fetch_access_token_sync()` returns `None` (`src/specify_cli/sync/background.py:311-315`). `spec-kitty sync now` then infers the logged-out state later from "queue non-empty but no progress" (`src/specify_cli/cli/commands/sync.py:999-1009`). That makes the human output include `spec-kitty auth login`, but the result has `error_count == 0`, no failed results, and no `category_counts["unauthenticated"]`; `--report` also says there are no failures. This misses FR-001/T002 because no usable local session must map deterministically to `unauthenticated`, and user-facing output and machine-facing classification must agree.

Fix by returning/propagating a `BatchSyncResult` for the no-token hosted-sync path that records the queued events as failed or otherwise exposes a deterministic machine-facing `unauthenticated` category without draining the durable queue. Adjust `sync now` so the summary/report path reflects that category instead of first showing `Errors: 0`, and add a regression test using the real `BackgroundSyncService` no-token path rather than only mocking `service.sync_now()` to return an empty result.

**Rebase warning**: WP05 depends on WP01. Rebase or re-read WP01 after this feedback is addressed before collecting integrated evidence.
