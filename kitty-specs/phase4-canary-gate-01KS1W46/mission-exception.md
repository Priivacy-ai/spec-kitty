# Gate 3 Operator Exception — Cross-Repo Deployed-Dev E2E Gate

**Operator**: Robert (robert@spec-kitty.ai)
**Date**: 2026-05-20

## Failing Scenario

**Test path**: `tests/identity_boundary/` — all 4 deployed_dev scenarios
**Failing assertion**: Both spec-kitty#1141 and spec-kitty#1182 are OPEN; canary cannot run against deployed-dev

## Narrative

The deployed-dev identity-boundary scenarios cannot pass while the two Phase-4 blocker issues remain open. This is not a code defect — the test harness unit tests (20/20 pass) and smoke tests (6/6 pass) confirm the harness itself is functional.

The deployed-dev scenarios require a CLI built from a SHA that includes fixes for both blockers. spec-kitty-cli==3.2.0rc15 was verified to fail 3/4 scenarios in rc15-attempt1. This is an environmental blocker, not a regression introduced by this mission.

## Reproduction Command

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SK_E2E_SPEC_KITTY_BIN=/Users/robert/.local/bin/spec-kitty \
  uv run pytest tests/identity_boundary/ -m sync_identity_boundary_deployed_dev -q
```

## Follow-Up

Both blocker issues must be closed and a post-rc15 RC published before Gate 3 can clear. See `re-activation.md` for the exact re-run sequence.
