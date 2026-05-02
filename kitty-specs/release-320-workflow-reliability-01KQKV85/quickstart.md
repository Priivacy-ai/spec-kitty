# Quickstart: 3.2.0 Workflow Reliability Blockers

This quickstart describes the validation path for the plan artifacts. It does not generate work packages or start implementation.

## Repository

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty
```

## Confirm Mission Planning State

```bash
spec-kitty agent mission check-prerequisites --mission release-320-workflow-reliability-01KQKV85 --json
spec-kitty agent decision verify --mission release-320-workflow-reliability-01KQKV85
```

Expected:

- Prerequisites report `valid: true`.
- Decision verification reports no deferred decisions or stale markers.

## Commit Plan Phase

After `plan.md` has a real Technical Context, run:

```bash
spec-kitty agent mission setup-plan --mission 01KQKV85G0STH8VF1RB66TW8DJ --json
```

Expected:

- `phase_complete` is `true`.
- Branch contract reports current branch `main`, planning/base branch `main`, merge target `main`, and `branch_matches_target: true`.

## Planned Test Families

Run focused tests as work packages land:

```bash
uv run pytest tests/status tests/tasks -q
uv run pytest tests/review tests/integration/review -q
uv run pytest tests/policy -q
uv run pytest tests/sync -q
uv run pytest tests/merge tests/integration -q
```

For any command path that exercises SaaS, tracker, hosted auth, or sync behavior on this computer, use:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <command>
```

Regression tests should still mock external services unless the work package explicitly scopes a hosted integration check.

## End-of-Mission Smoke Target

The final mission must prove a fresh path can run without manual Python status-event emission:

```text
init -> specify -> plan -> tasks -> implement/review -> merge -> PR
```

## Stop Point

After this planning phase, stop. The next phase starts only when the user invokes `/spec-kitty.tasks`.
