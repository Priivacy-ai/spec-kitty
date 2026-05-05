# Issue Matrix: stable-320-release-blocker-cleanup-01KQW4DF

| Issue | Scope | Verdict | Evidence ref |
|-------|-------|----------|--------------|
| #952 | Successful local lifecycle commands leaked non-fatal SaaS final-sync diagnostics into command output. | fixed | WP01; `src/specify_cli/sync/diagnostics.py`; `tests/sync/test_final_sync_diagnostics.py`; CI `fast-tests-sync` and `integration-tests-sync` passed on PR #981. |
| #783 | `spec-kitty agent tasks mark-status` did not resolve task IDs outside checkbox rows. | fixed | WP02; `src/specify_cli/cli/commands/agent/tasks.py`; `tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py`; CI `fast-tests-status` passed on PR #981. |
| #975 | Cross-repo E2E contract-drift scenario failed before product behavior on uv-managed Python. | fixed | WP03; `spec-kitty-end-to-end-testing` commit `7e1ce3a`; `scenarios/contract_drift_caught.py`; post-merge E2E gate passed with SaaS endpoint exception documented in `mission-exception.md`. |
| #976 | `spec-kitty merge --dry-run` did not report a missing mission branch prerequisite. | fixed | WP04; `src/specify_cli/cli/commands/merge.py`; `tests/merge/test_merge_preflight_mission_branch.py`; CI `fast-tests-merge` and `integration-tests-merge` passed on PR #981. |
| #971 | Tracker rollout machinery. Explicitly out of scope for this release-blocker cleanup mission. | deferred-with-followup | Deferred to GitHub issue #971; see spec non-goal and constraint C-001. |
