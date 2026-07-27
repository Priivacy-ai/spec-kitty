---
affected_files: []
cycle_number: 3
mission_slug: private-teamspace-ingress-safeguards-01KQH03Y
reproduction_command:
reviewed_at: '2026-05-01T11:33:07Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

**Issue 1**: `tests/sync/test_strict_json_stdout.py` does not implement the required strict-JSON regression for WP05. The WP explicitly requires a subprocess test for `spec-kitty agent mission create ... --json` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, isolated shared-only auth state, and sync forced into the diagnostic/failure path so stdout proves parseable while sync diagnostics stay off stdout. The submitted test instead runs `agent tasks status --json` with SaaS sync defaulted to `0`, so it does not exercise the WebSocket/sync failure path that caused AC-006/NFR-003.

Fix: replace `test_agent_tasks_status_json_is_strict_parseable` with the requested `agent mission create ... --json` regression. Provide an isolated temp home/auth fixture (or equivalent simulator) so the subprocess does not use the developer's real auth/session state, force `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, and assert `json.loads(result.stdout)` succeeds while the structured sync diagnostic appears on stderr and no connection diagnostic appears on stdout.

**Issue 2**: The new subprocess test is not deterministic or isolated. Running the focused WP05 tests fails because the subprocess imports the installed `/opt/homebrew/.../site-packages/specify_cli` package and writes under `/Users/robert/.kittify/cache/.update.lock`, producing `PermissionError: [Errno 1] Operation not permitted`. This violates the WP risk guidance that the test must avoid real auth/global state and must consistently run against the in-tree implementation.

Fix: set the subprocess environment/cwd so it executes the in-tree package deterministically (for example by setting `PYTHONPATH` to this repo's `src` path or using the repository's established test helper), and point all Spec Kitty home/cache/auth locations at `tmp_path`-scoped directories. The corrected focused command should pass:

`pytest tests/sync/test_client_integration.py::test_ws_token_rehydrates_when_session_lacks_private tests/sync/test_client_integration.py::test_ws_token_skipped_when_no_private_team_after_rehydrate tests/sync/test_client_integration.py::test_ws_token_healthy_session_no_rehydrate tests/sync/test_strict_json_stdout.py -q`
