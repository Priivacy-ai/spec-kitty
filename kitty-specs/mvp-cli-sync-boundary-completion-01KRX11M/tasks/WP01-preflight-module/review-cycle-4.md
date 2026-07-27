---
affected_files: []
cycle_number: 4
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T08:52:17Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-05-18T09:06:07Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Cycle 3 review passed (codex reviewer verdict approve, recorded verbally — sandbox blocked artifact write). Preflight is strictly read-only and never calls SaaS endpoints. Regression test trip-wires rehydrate_membership_if_needed and resolve_private_team_id_for_ingress. 24/24 tests pass, mypy --strict clean, 92% coverage on preflight.py."
---

**Issue 1**: `collect_foreground_identity()` still has an indirect SaaS round-trip path, so the read-only/no-SaaS contract is not fully corrected.

`src/specify_cli/sync/preflight.py` calls `read_queue_scope_from_session()` in both `collect_foreground_identity()` and `_resolve_queue_db_path_readonly()`. That helper calls `resolve_private_team_id_for_ingress()`, which calls `TokenManager.rehydrate_membership_if_needed()` when the current session has no Private Teamspace in memory. That rehydrate path fetches `/api/v1/me`, violating the contract in `contracts/sync-boundary-preflight.md`: “The helper does not mutate state and does not call SaaS endpoints.”

Fix by resolving the foreground auth/scope for preflight from local, already-persisted state only. Do not call helpers that can rehydrate membership or otherwise contact SaaS. Add a regression test that monkeypatches the token manager/session so `rehydrate_membership_if_needed()` raises, then calls `run_preflight(repo_root=..., foreground=None, require_auth=True)` and asserts no rehydrate/SaaS path is invoked.

Evidence: with a fake current session that lacks a private team, calling `collect_foreground_identity(Path.cwd())` reaches `rehydrate_membership_if_needed()`. The existing tests only guard owner-record writes and legacy migration, not the indirect SaaS round-trip path required by T003.
