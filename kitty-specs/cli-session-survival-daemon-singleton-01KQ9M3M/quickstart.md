# Quickstart — CLI Session Survival and Daemon Singleton

This document describes how to **run, verify, and reproduce the incident**
that this mission fixes. It is the operator-facing companion to
`plan.md` / `spec.md` / `research.md`.

## Local development setup

This mission is implemented inside the `spec-kitty` CLI repository.
There is no SaaS deployment to stand up for Tranche 1 — the network
side is mocked at the test boundary. **Do not** run the test suite or
the CLI against the dev SaaS deployment without
`SPEC_KITTY_ENABLE_SAAS_SYNC=1` (C-003).

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260428-102808-qXl2TZ/spec-kitty

# Standard editable install
uv sync

# Or pip:
pip install -e '.[dev]'
```

## Run the focused test set

```bash
# All tests touching this mission's surfaces:
PWHEADLESS=1 pytest \
  tests/core/test_file_lock.py \
  tests/auth/test_token_manager.py \
  tests/auth/test_auth_doctor_report.py \
  tests/auth/test_auth_doctor_repair.py \
  tests/auth/test_auth_doctor_offline.py \
  tests/auth/concurrency/ \
  tests/sync/test_daemon_self_retirement.py \
  tests/sync/test_orphan_sweep.py \
  -v
```

The full project suite remains the source of truth for regression
absence:

```bash
PWHEADLESS=1 pytest tests/ -q
```

## Reproduce the incident manually (development sanity check)

This procedure simulates the rotate-then-stale-grant ordering from
`spec.md` §"Scenario 2".

> **Prerequisites**: a populated `~/.spec-kitty/auth/session.json`. If
> you do not have one, run `spec-kitty auth login` first against a
> non-production SaaS (with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`). The
> repro itself does not call the SaaS — it uses an in-process fake
> refresh server.

This repro is automated by
`tests/auth/concurrency/test_incident_regression.py` (WP07). The
manual procedure here is for human eyeballing, not for CI.

1. **Spawn worker A**: a long-running Python process holding a
   `TokenManager` pointed at a temp auth root. Trigger
   `await tm.refresh_if_needed()` while the access token is expired.
   Worker A rotates the token.
2. **Hold worker B**: a second process with its own `TokenManager`
   already loaded from disk **before** A's rotation. Worker B's
   in-memory session still holds the old refresh token.
3. **Drive worker B to refresh**: the fake server returns
   `400 invalid_grant` for the rotated-out refresh token.
4. **Observe**: pre-fix, the local session file is deleted. Post-fix
   (FR-005, FR-006), `~/.spec-kitty/auth/session.json` is intact and
   carries A's rotated material. Worker B's
   `RefreshTokenExpiredError`-handler returns `StaleRejectionPreserved`.

The deterministic, bounded version of this procedure is the
multiprocess regression test (NFR-005, ≤30 s).

## Verify each Success Criterion (SC)

After the mission lands, verify each spec-level success criterion.

### SC-001 — 24-hour multi-checkout stability

Manual; not in CI. Run the CLI from three temp clones for a working
day. Inspect `~/.spec-kitty/auth/session.json` mtime: it should change
on rotations only, not flap; `auth status` should never report
"not authenticated" without a legitimate cause.

### SC-002 — Incident regression test passes

```bash
pytest tests/auth/concurrency/test_incident_regression.py -v
```

### SC-003 — Legitimate re-login carries clear reason

After `auth doctor` reports `F-001`, the printed remediation must
name the cause: e.g. "refresh token expired (server-revoked)" or
"refresh token expired (absolute lifetime)". The exact wording is
asserted by `tests/auth/test_token_manager.py::test_clear_message_*`.

### SC-004 — Doctor returns within seconds

```bash
time spec-kitty auth doctor
```

Should complete in < 3 s on a typical local state (NFR-006).
`tests/auth/test_auth_doctor_report.py::test_runs_under_three_seconds`
asserts this in CI.

### SC-005 — Single-command orphan recovery

```bash
spec-kitty auth doctor                # see F-002 warn
spec-kitty auth doctor --reset        # sweep
spec-kitty auth doctor                # F-002 absent
```

### SC-006 — One refresh, not N

`tests/auth/concurrency/test_machine_refresh_lock.py::test_concurrent_refresh_one_network_call`
asserts the network is hit exactly once when N processes share an
expired session.

## Diagnostics for incident triage

If a future user reports "lost CLI auth", first request:

```bash
spec-kitty auth doctor --json > /tmp/auth-doctor.json
```

The JSON includes everything needed to diagnose:

- session present? expiration windows? backend?
- refresh-lock holder PID, age, host
- active daemon's PID/port/version
- orphan list with PID/port/version
- findings + suggested remediation

## Rollback / recovery

This mission is additive. To roll back:

1. Revert the merge commit on `main`.
2. The `~/.spec-kitty/auth/refresh.lock` file becomes harmless
   (older CLI ignores it).
3. The daemon state file is unchanged shape; older daemons read it
   normally.
4. The `auth doctor` command disappears; `auth status` is unaffected.

No data migration is required. No persisted user state is lost.

## What this mission does NOT do (carry-over from spec)

- Server-side refresh-token family/generation tracking (Tranche 2).
- RFC 7009-style revocation endpoint and CLI logout truthfulness (Tranche 2).
- WebSocket auth-contract changes (Tranche 3).
- OS keychain backends and SECRET_KEY separation (Tranche 4).
- Privileged-action gating, API-key scopes, connector OAuth, rate-limit hardening (Tranche 5).
- Adversarial validation suite, soak runbook, release gate (Tranche 6).

The remaining tranches are scheduled in the program brief at
`/Users/robert/spec-kitty-dev/spec-kitty-20260428-102808-qXl2TZ/start-here.md`.
