---
affected_files: []
cycle_number: 4
mission_slug: private-teamspace-ingress-safeguards-01KQH03Y
reproduction_command:
reviewed_at: '2026-05-01T11:03:14Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

**Issue 1**: `src/specify_cli/sync/queue.py:222-224` constructs a fresh `TokenManager` for every `read_queue_scope_from_session()` call and then passes that transient instance to `resolve_private_team_id_for_ingress()`. That bypasses the process-wide negative cache and lock that NFR-001 relies on. `TokenManager._membership_negative_cache` is instance-local (`src/specify_cli/auth/token_manager.py:106`), and the helper contract says the caller should pass the shared manager so a shared-only session gets at most one `/api/v1/me` rehydrate per CLI process. With the current queue implementation, two queue scope reads in the same process can perform two `/api/v1/me` calls when SaaS still returns no Private Teamspace.

Fix: make the queue path use the process-wide/shared `TokenManager` for this helper call, or otherwise preserve one shared manager/cache for the process. Keep the strict skip behavior, but do not allocate a new manager per scope read. Add a queue regression test that invokes `read_queue_scope_from_session()` twice for a shared-only session where `/api/v1/me` returns no private team and asserts the `/api/v1/me` route was called exactly once.
