# Quickstart: Auth Local Trust And Multi-Process Hardening

Run commands from:

`/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty`

## Hermetic Refresh-Lock Repro

```bash
SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60

env -u SPEC_KITTY_SAAS_URL \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60
```

Expected result: both commands pass, and the hosted-URL-set run performs zero real `/api/v1/me` calls.

## Diagnostic Classification Checks

```bash
uv run pytest \
  tests/sync/test_batch_error_surfacing.py \
  tests/sync/test_body_transport.py \
  tests/sync/test_team_ingress_resolver.py \
  tests/sync/tracker/test_saas_client.py \
  tests/sync/tracker/test_saas_service.py \
  tests/cli/commands/test_sync_routes.py
```

Expected result: missing Private Teamspace and logged-out tracker-bound paths do not surface as generic `server_error`.

## Auth/Storage Guardrail Checks

```bash
uv run pytest tests/review/

uv run ruff check \
  src/specify_cli/auth \
  src/specify_cli/cli/commands/auth.py \
  src/specify_cli/cli/commands/_auth_doctor.py \
  src/specify_cli/cli/commands/_auth_login.py \
  src/specify_cli/cli/commands/_auth_logout.py \
  src/specify_cli/cli/commands/_auth_status.py \
  src/specify_cli/cli/commands/review.py
```

Expected result: scoped broad exception suppressions either have specific inline safety reasons or fail with file and line.

## Local Session Hot-Path Checks

```bash
uv run pytest \
  tests/auth/concurrency \
  tests/auth/stress/test_file_storage_concurrent.py \
  tests/auth/secure_storage \
  tests/packaging/test_windows_no_keyring.py
```

Expected result: many-process session behavior is coordinated, durable encrypted storage remains authoritative, and forbidden credential-manager dependencies stay absent.

## Hosted Smoke Rule On This Computer

When a command path touches hosted auth, tracker, SaaS, or sync behavior for dev smoke testing on this computer, set:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <command>
```

Default unit and concurrency tests should not require hosted SaaS. Hosted smoke evidence must be explicit and separate from hermetic suites.

## Final Evidence Bundle

Before `/spec-kitty.review`, collect:

- Focused test output for WP01-WP04.
- Evidence that `SPEC_KITTY_SAAS_URL` does not make refresh-lock tests call hosted `/api/v1/me`.
- Evidence that #889 missing Private Teamspace does not classify as `server_error`.
- Evidence that logged-out Teamspace/tracker-bound flows show `spec-kitty auth login`.
- Evidence that no Keychain/keyring/Secret Service dependency was introduced.
- Any pre-existing failure issue links required by the charter.
