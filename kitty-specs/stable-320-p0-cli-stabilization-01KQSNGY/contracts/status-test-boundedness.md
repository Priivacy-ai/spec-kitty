# Contract: Status Test Boundedness

## Scope

This contract covers #967 status bootstrap and emit behavior for local and CI validation.

## Required Behavior

- Previously hanging status bootstrap and emit paths must complete or fail within 30 seconds when run with the mission validation timeout.
- Timeout failures must include enough diagnostics to identify the hanging test path.
- Fixture or adapter hardening must preserve the semantics of status events and materialized status.
- Default validation must not require hosted auth, tracker, SaaS sync, or network access.

## Acceptance Checks

```bash
uv run pytest tests/status -q --timeout=30
```

The implementation should add narrower checks if root cause lands outside the current status test files.

## Non-Goals

- Broad status store redesign.
- Hosted sync protocol changes.
- Weakening status assertions to make tests pass.
