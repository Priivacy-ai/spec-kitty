# WP04 Single-Run Canary Result

**Date**: 2026-05-20
**Agent**: claude:sonnet-4-6:implementer:implementer

## Pre-run State

- Installed CLI: `spec-kitty-cli==3.2.0rc15` (WP02 gate: no post-rc15 RC available)
- Blockers: #1141 OPEN, #1182 OPEN (WP01 confirmed)
- SaaS: /health/ready/ 200, terminal_failed=0, business_rule=22 (WP03 confirmed)

## T017: Environment Variables

✅ All required env vars set:
```
SK_E2E_SPEC_KITTY_BIN=/Users/robert/.local/bin/spec-kitty → v3.2.0rc15
SK_E2E_SPEC_KITTY_PYTHON=/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python
SPEC_KITTY_ENABLE_SAAS_SYNC=1
SPEC_KITTY_E2E_TRUSTED_RUNNER=1
SK_E2E_SPEC_KITTY_REPO=/nonexistent
```

## T018: uv sync

✅ e2e dependencies resolved (18 packages, 0 changes)

## T019: Orphan Daemon Kill

✅ No orphan sync daemons found

## T020: Harness Unit Test Preflight

**Result**: 31 passed, 2 failed

Failures (environment-specific, not canary blockers):
- `test_workspace_repo_resolvers_find_sibling_clones_in_fresh_prep_workspace[spec-kitty-spec_kitty_repo_root]`
  — expects fallback to `uv run spec-kitty` in a fresh-clone context; not applicable when pipx-installed CLI is present
- `test_resolve_spec_kitty_command_falls_back_to_uv_for_fresh_clone_without_venv`
  — same root cause; tests a fallback path for workspaces without a venv; does not affect standard installed-CLI canary execution

Script syntax check: OK

These are harness edge-case tests, not blockers per WP04 T020 guidance.

## T021–T023: DEFERRED

**Gate condition**: WP02 RC install gate is blocked (latest prerelease is still v3.2.0rc15).

Running the canary with rc15 would reproduce the known 3/4-fail result from `artifacts/sync_identity_boundary/rc15-attempt1/` without providing new diagnostic signal. Additionally, canary execution creates SaaS state (test missions, sync events) that would unnecessarily consume resources.

Per WP04 spec: "Run using the post-rc15 RC installed in WP02." Since WP02 did not install a new RC, T021 is deferred.

**Existing evidence**: `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/rc15-attempt1/run-1.json` confirms rc15 3/4 status (scenario 3 pass, 1+2+4 fail).

## Summary

WP04 is in WAITING state. Setup verified clean (env vars, uv sync, no daemons, harness mostly healthy). The live canary cannot run until:
1. Both #1141 and #1182 are closed with substantive fixes
2. A post-rc15 RC (v3.2.0rc16+) is cut and published
3. WP02 is re-run and completes T009-T012

Next action: Re-run WP04 after WP02 installs a post-rc15 RC.
