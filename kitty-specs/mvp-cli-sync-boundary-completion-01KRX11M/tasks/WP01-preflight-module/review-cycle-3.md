**Issue 1**: `collect_foreground_identity()` still has an indirect SaaS round-trip path, so the read-only/no-SaaS contract is not fully corrected.

`src/specify_cli/sync/preflight.py` calls `read_queue_scope_from_session()` in both `collect_foreground_identity()` and `_resolve_queue_db_path_readonly()`. That helper calls `resolve_private_team_id_for_ingress()`, which calls `TokenManager.rehydrate_membership_if_needed()` when the current session has no Private Teamspace in memory. That rehydrate path fetches `/api/v1/me`, violating the contract in `contracts/sync-boundary-preflight.md`: “The helper does not mutate state and does not call SaaS endpoints.”

Fix by resolving the foreground auth/scope for preflight from local, already-persisted state only. Do not call helpers that can rehydrate membership or otherwise contact SaaS. Add a regression test that monkeypatches the token manager/session so `rehydrate_membership_if_needed()` raises, then calls `run_preflight(repo_root=..., foreground=None, require_auth=True)` and asserts no rehydrate/SaaS path is invoked.

Evidence: with a fake current session that lacks a private team, calling `collect_foreground_identity(Path.cwd())` reaches `rehydrate_membership_if_needed()`. The existing tests only guard owner-record writes and legacy migration, not the indirect SaaS round-trip path required by T003.
