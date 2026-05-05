# Contract: Refresh-Lock Hermeticity

## Scope

Applies to `tests/auth/concurrency/test_machine_refresh_lock.py` and related fixtures that validate local refresh-lock behavior.

## Required Behavior

```
developer shell sets SPEC_KITTY_SAAS_URL
  |
  v
run auth refresh-lock concurrency test
  |
  +-- fake session already has Private Teamspace OR membership hook is patched out
  |
  +-- no real hosted /api/v1/me request
  |
  v
test completes within 60 seconds
```

## Assertions

- With `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev`, the focused concurrency suite makes zero real hosted membership requests.
- With `SPEC_KITTY_SAAS_URL` unset, the same focused suite still passes.
- Tests that intentionally contact hosted SaaS are named, marked, or invoked as dev smoke tests and are not part of default hermetic concurrency coverage.

## Allowed Fix Shapes

- Include a Private Teamspace in refreshed fake sessions.
- Monkeypatch `_apply_post_refresh_membership_hook()` in concurrency fixtures where membership rehydrate is out of scope.
- Clear hosted auth environment only inside the test fixture and assert the no-network invariant.

## Disallowed Fix Shapes

- Depend on `https://spec-kitty-dev.fly.dev` in the default concurrency suite.
- Remove production post-refresh membership rehydrate behavior to make a test pass.
- Treat this diagnosis as proof that the refresh-lock algorithm is broken without a separate failing fixture.
