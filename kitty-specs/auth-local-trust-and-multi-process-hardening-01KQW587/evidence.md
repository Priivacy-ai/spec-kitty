# WP05 Integrated Evidence And Smoke

## 1. Mission summary and commit range under review

Mission: `auth-local-trust-and-multi-process-hardening-01KQW587`.

Planning/root workspace at WP05 fix cycle start: `4cb69ecc` (`chore: Start WP05 implementation`).

Approved implementation lane heads used for integrated evidence:

- WP01 lane A: `9099a032` (`fix(WP01): classify logged-out sync as unauthenticated`)
- WP02-WP04 lane B: `306bc815` (`fix(WP04): bypass hot path for non-file storage`)

Evidence was run in a temporary detached integration worktree at `/tmp/spec-kitty-wp05-integrated`, based on lane B `306bc815` with lane A `9099a032` merged using `git merge --no-commit --no-ff`. The merge applied cleanly and was not committed. This was necessary because the planning root contains mission status artifacts while the approved implementation code remains on lane branches until mission merge.

## 2. Focused command results

### Diagnostic classification and logged-out guidance

Command:

```bash
uv run pytest tests/sync/test_batch_error_surfacing.py tests/sync/test_body_transport.py tests/sync/test_team_ingress_resolver.py tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_service.py tests/cli/commands/test_sync_routes.py -q
```

Result: PASS. `203 passed, 2 skipped in 23.47s`.

Key assertions covered: sync, direct-ingress, tracker SaaS client/service, and CLI sync routes preserve specific auth/private-team/transport/server categories and include login recovery guidance where auth is missing.

### Refresh-lock hermeticity with hosted URL set

Command:

```bash
SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60
```

Actual command run on this machine:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60
```

Result: PASS. `2 passed in 1.47s`.

Key assertion covered: the refresh-lock suite stays hermetic even when `SPEC_KITTY_SAAS_URL` points at the dev deployment; it completes under the 60 second timeout.

### Refresh-lock hermeticity with hosted URL unset

Command:

```bash
env -u SPEC_KITTY_SAAS_URL \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60
```

Result: PASS. `2 passed in 1.48s`.

Key assertion covered: the same refresh-lock suite also passes in the default hosted-URL-unset environment.

### Auth/storage BLE001 guardrail

Command:

```bash
uv run pytest tests/review/ -q
```

Result: PASS. `153 passed in 1.75s`.

Command:

```bash
uv run ruff check src/specify_cli/auth src/specify_cli/cli/commands/auth.py src/specify_cli/cli/commands/_auth_doctor.py src/specify_cli/cli/commands/_auth_login.py src/specify_cli/cli/commands/_auth_logout.py src/specify_cli/cli/commands/_auth_status.py src/specify_cli/cli/commands/review.py
```

Result: PASS. Ruff reported `All checks passed!`.

Key assertions covered: unjustified auth/storage `BLE001` suppressions fail with actionable file/line output, and scoped auth/review paths pass the guard/lint gate.

### Local session hot path, secure storage, and packaging

Command:

```bash
uv run pytest tests/auth/concurrency tests/auth/stress/test_file_storage_concurrent.py tests/auth/secure_storage tests/packaging/test_windows_no_keyring.py -q
```

Result: PASS. `30 passed, 2 skipped in 10.98s`.

Key assertions covered: multi-process refresh coordination, local session hot-path handoff/fallback behavior, file-backed secure storage, stress coverage, and packaging exclusion of keyring-style credential-manager dependencies.

### FR-011 shipped-auth regression slice

Command:

```bash
uv run pytest tests/auth/test_token_manager.py tests/auth/test_refresh_flow.py tests/auth/test_revoke_flow.py tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py tests/cli/commands/test_auth_status.py tests/cli/commands/test_auth_logout.py -q
```

Result: PASS. `146 passed in 1.25s`.

Key assertions covered: shipped browser/device login-adjacent token manager behavior, refresh replay, revoke/logout, auth status, and server-session doctor report/repair/offline behavior remain supported in the integrated lane-A + lane-B context.

## 3. Issue #829 evidence

Evidence: the diagnostic classification command passed with the WP01 lane integrated. The covered sync/tracker route tests include logged-out hosted state paths that require `spec-kitty auth login` guidance instead of vague tracker, sync, or server-error wording.

Acceptance mapping:

- FR-001: covered categories are asserted in sync/tracker fixtures.
- FR-002 / SC-002: logged-out Teamspace/tracker-bound flows include `spec-kitty auth login` recovery guidance.

## 4. Issue #907 evidence

Evidence: the same diagnostic suite passed, including tracker SaaS client/service coverage.

Acceptance mapping:

- FR-001 / SC-001: tracker-bound CLI/SaaS failure fixtures retain deterministic machine-facing categories for unauthenticated, authorization/private-team, transport, and server failures.
- Hosted tracker/sync behavior remains CLI-owned in this mission; no tracker package rollout gate is introduced here.

## 5. Issue #889 evidence

Evidence: the diagnostic suite passed, including direct-ingress/private-team classification tests in sync batch/body transport/team resolver coverage.

Acceptance mapping:

- FR-003 / SC-003: missing Private Teamspace direct-ingress paths preserve the direct-ingress/private-team classification and do not collapse to `server_error`.

## 6. Issue #977 evidence

Evidence:

- Hosted-URL-set refresh-lock command passed: `2 passed in 1.47s`.
- Hosted-URL-unset refresh-lock command passed: `2 passed in 1.48s`.

Acceptance mapping:

- FR-004 / FR-005 / SC-004: the focused refresh-lock suite remains hermetic and finishes within the 60 second timeout both with `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev` and with that variable unset.
- NFR-001: both environment variants completed well under 60 seconds in the integrated worktree.

## 7. CLI-side SaaS #77 evidence

Evidence:

- Auth concurrency and hot-path suite passed: `30 passed, 2 skipped in 10.98s`.
- Review guardrail and scoped Ruff checks passed.
- Packaging check `tests/packaging/test_windows_no_keyring.py` passed as part of the local session/security suite.
- FR-011 shipped-auth regression slice passed: `146 passed in 1.25s`.

Acceptance mapping:

- FR-006 / FR-007 / SC-005: auth/storage broad exception suppressions are accountable through the review guard.
- FR-008 / SC-006: no Keychain, keyring, Secret Service, or OS credential-manager dependency was introduced in the covered packaging check.
- FR-009 / FR-010 / SC-007: concurrency and hot-path tests demonstrate coordinated refresh/handoff behavior and stale-handoff fallback without token material in observable output.
- FR-011: the shipped-auth regression slice passed in the integrated lane context, including auth status/logout behavior that previously failed before WP04 lane B was fixed.

## 8. Hosted smoke commands and environment

Hosted auth/tracker/sync commands run from this machine used `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

Command:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run spec-kitty auth status
```

Result: PASS. The command returned authenticated local auth status using encrypted session file storage. The evidence intentionally omits user-identifying fields and session identifiers from the command output.

## 9. Pre-existing failures and issue links

No pre-existing verification failure was accepted as baseline, so no pre-existing-failure issue link is required.

Historical rejected review artifacts for WP01 and WP04 remain in their task directories as review history. Current integrated evidence uses the approved lane heads `9099a032` and `306bc815`.

## 10. Final acceptance checklist

- PASS: Every success criterion in `spec.md` has direct passing evidence in this file.
- PASS: Hosted auth/sync smoke used `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- PASS: Hermetic tests were kept separate from hosted smoke.
- PASS: Failing commands were triaged as introduced vs pre-existing.
- PASS: No pre-existing failure was accepted without an issue link.
