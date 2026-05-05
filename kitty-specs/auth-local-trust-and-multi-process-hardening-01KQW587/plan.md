# Implementation Plan: Auth Local Trust And Multi-Process Hardening

**Branch**: `main` | **Date**: 2026-05-05 | **Spec**: [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/spec.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/spec.md)
**Input**: Mission specification from `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/spec.md`

## Summary

Close the CLI-side auth-adjacent hardening gaps left after shipped browser/device OAuth: make tracker-bound and hosted-sync commands report logged-out, unauthorized or missing Private Teamspace, retryable transport, and true server failures truthfully; make direct-ingress 403/missing-private-team handling stop collapsing into `server_error`; make refresh-lock concurrency tests hermetic even when hosted SaaS URLs are configured in the developer shell; enforce justified broad exception suppressions in auth/storage paths; and design a cross-process local session hot path that preserves encrypted file-only storage as the durable root of trust.

Engineering alignment: keep changes inside the CLI repository. Do not alter the shipped SaaS auth contract, do not reintroduce Keychain/keyring/Secret Service, and do not edit `spec-kitty-tracker` unless investigation proves tracker owns a specific failure. Current branch at plan start is `main`; planning/base branch is `main`; completed changes merge into `main`; `branch_matches_target=true`.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: typer, rich, httpx, pytest, pytest-asyncio, ruff, mypy, existing `spec-kitty-tracker` package contract  
**Storage**: Existing encrypted file-only auth storage under `~/.spec-kitty/auth/`; repository-local mission/tracker/sync metadata; optional local session handoff/cache must be derived from and invalidated by durable encrypted session state  
**Testing**: Focused pytest coverage for auth concurrency, token manager membership rehydrate behavior, sync/direct-ingress classification, tracker-bound logged-out diagnostics, secure-storage packaging, and BLE001 guardrail behavior; final checks include focused auth/sync suites plus ruff/mypy slices where touched  
**Target Platform**: Spec Kitty CLI on macOS/Linux/Windows 10+  
**Project Type**: Python CLI/library repository with mission planning artifacts  
**Performance Goals**: Default auth concurrency suite completes within 60 seconds in hosted-URL-set and hosted-URL-unset environments; typical CLI commands remain below the charter's 2 second target; many short-lived local processes avoid repeated expensive session work once the hot path is available  
**Constraints**: No server auth contract changes; no Keychain/keyring/Secret Service/credential-manager dependencies; no token material in output; tests are hermetic by default; hosted auth/tracker/sync CLI testing on this computer must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; `spec-kitty-tracker` remains context-only unless ownership evidence is found  
**Scale/Scope**: CLI mission covering issues #829, #907, #889, #977, and CLI-side SaaS #77; expected work spans auth, sync, tracker-bound command surfaces, tests, and a small lint/review guardrail

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter standard | Plan response | Status |
|---|---|---|
| Python 3.11+ and existing CLI stack | Work stays in the Python CLI/library codebase and existing dependency set. | PASS |
| pytest coverage and mypy strict quality | Each workstream carries focused pytest acceptance checks; touched typed surfaces must remain mypy-compatible. | PASS |
| CLI operations under typical 2 second target | Hot-path work is intended to reduce repeated local-process overhead; diagnostics and guards must not run on every normal command unless explicitly invoked or scoped. | PASS |
| External package boundary | `spec-kitty-tracker` remains an external package dependency; this mission changes CLI behavior first and only opens tracker work if ownership is proven. | PASS |
| Central CLI-SaaS API contract | No hosted route, request, response, auth-header, websocket, sync payload, or tracker control-plane contract change is planned. | PASS |
| Branch strategy | Current branch `main`; planning/base branch `main`; completed changes merge into `main`; `branch_matches_target=true`. | PASS |
| SaaS sync local machine rule | Hosted auth, tracker, SaaS, or sync CLI test commands on this computer must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | PASS |
| Mission terminology canon | New planning artifacts use Mission as canonical product language except where quoting existing command names, issue text, or code paths. | PASS |
| User customization preservation | No command/skill installer, upgrade, or package-managed asset cleanup mutation is planned. | PASS |

## Project Structure

### Documentation (this mission)

```
/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- ble001-guardrail.md
|   |-- diagnostic-classification.md
|   |-- refresh-lock-hermeticity.md
|   `-- session-hot-path.md
|-- checklists/
|   `-- requirements.md
`-- tasks/
    `-- README.md
```

### Source Code (repository root)

```
/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/
|-- src/specify_cli/auth/
|   |-- token_manager.py
|   |-- refresh_transaction.py
|   |-- session.py
|   |-- secure_storage/
|   |-- flows/
|   `-- http/
|-- src/specify_cli/cli/commands/
|   |-- auth.py
|   |-- _auth_doctor.py
|   |-- _auth_login.py
|   |-- _auth_logout.py
|   |-- _auth_status.py
|   |-- sync.py
|   `-- tracker.py
|-- src/specify_cli/sync/
|   |-- _team.py
|   |-- batch.py
|   |-- body_transport.py
|   |-- client.py
|   |-- emitter.py
|   `-- queue.py
|-- src/specify_cli/tracker/
|   |-- saas_client.py
|   |-- saas_service.py
|   |-- store.py
|   `-- ticket_context.py
|-- src/specify_cli/cli/commands/review.py
|-- tests/auth/
|   |-- concurrency/
|   |-- secure_storage/
|   |-- integration/
|   `-- test_token_manager.py
|-- tests/cli/commands/
|-- tests/sync/
|-- tests/sync/tracker/
|-- tests/packaging/
`-- tests/review/
```

**Structure Decision**: Use the existing CLI/auth/sync/tracker source layout. Add helper modules only where they create a clear local boundary: diagnostic classification can live near the command or sync surface that consumes it; hot-path session coordination should live under `src/specify_cli/auth/` if implementation needs a new local helper; BLE001 guardrail should extend the existing review/check tooling instead of adding an unrelated lint system.

## Phase 0 Research Findings

See [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/research.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/research.md).

Key decisions:

- Treat #977 as a hermetic test isolation bug. The refresh-lock algorithm is not assumed broken by the local hosted call.
- Keep diagnostic classification CLI-owned unless a focused investigation proves tracker package ownership.
- Extend existing direct-ingress categories rather than introducing a new generic auth error taxonomy.
- Preserve encrypted file-only durable storage; any hot-path handoff is derived, bounded, and invalidatable.
- Reuse the existing BLE001 audit direction in review tooling, but make the scoped auth/storage guard testable and actionable.

## Phase 1 Design

See:

- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/data-model.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/data-model.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/diagnostic-classification.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/diagnostic-classification.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/refresh-lock-hermeticity.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/refresh-lock-hermeticity.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/ble001-guardrail.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/ble001-guardrail.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/session-hot-path.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/session-hot-path.md)
- [/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/quickstart.md](/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/quickstart.md)

## Planned Work Packages

### WP01 Diagnostic Classification And Logged-Out Guidance

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/sync.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/sync/_team.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/sync/batch.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/sync/body_transport.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/sync/client.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/tracker/saas_client.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/sync/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/sync/tracker/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/cli/commands/`

Plan:

- Identify every user-facing command path that needs hosted sync/tracker state and currently can report a vague sync/tracker/server failure when auth is missing.
- Normalize the observable categories to unauthenticated, missing Private Teamspace or unauthorized, retryable transport failure, and true server failure.
- Fix #889 by ensuring direct-ingress missing Private Teamspace remains `direct_ingress_missing_private_team` or its existing category peer, never `server_error`.
- Fix #829 by making tracker-bound or Teamspace-bound logged-out flows display `spec-kitty auth login`.
- Keep machine-facing JSON/category output compatible where possible; add explicit peer fields rather than silently changing existing fields if consumers exist.

Tests:

- `uv run pytest tests/sync/test_batch_error_surfacing.py tests/sync/test_body_transport.py tests/sync/test_team_ingress_resolver.py`
- `uv run pytest tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_service.py`
- `uv run pytest tests/cli/commands/test_sync_routes.py tests/cli/commands/test_auth_status.py`

### WP02 Refresh-Lock Hermeticity And Membership Rehydrate Isolation

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/concurrency/test_machine_refresh_lock.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/concurrency/conftest.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/test_token_manager.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/test_refresh_flow.py`

Plan:

- Reproduce the known isolation condition with `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev` in the environment, but prevent live hosted dependency in the regression.
- Make fake refreshed sessions in the concurrency tests include a Private Teamspace or explicitly patch the post-refresh membership hook when membership rehydrate is outside the test purpose.
- Add a failing guard that proves the concurrency test does not call hosted `/api/v1/me` under configured hosted URL.
- Preserve existing post-refresh membership rehydrate behavior for production and targeted token-manager tests.
- Treat production auth files as read-only reference for this WP; production token-manager or refresh-transaction changes belong to WP04 if later proven necessary.

Tests:

- `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60`
- `env -u SPEC_KITTY_SAAS_URL uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60`
- `uv run pytest tests/auth/test_token_manager.py tests/auth/test_refresh_flow.py`

### WP03 Auth/Storage Broad Exception Guardrail

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/auth.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_doctor.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_login.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_logout.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_status.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/flows/revoke.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/transport.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/http/transport.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/review.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/review/`

Plan:

- Define the scoped paths for auth/storage broad exception guardrails.
- Reuse or extract the existing BLE001 audit from review tooling so it can be tested without running an entire mission review.
- Require a specific inline reason after `noqa: BLE001`; reject empty reasons and generic text such as "ignore" or "broad catch".
- Extend tests so one justified suppression passes and one unjustified suppression fails with file and line.
- Clean up existing scoped suppressions in WP03-owned auth command and auth transport/revoke files that fail the new standard.
- Leave suppressions in WP04-owned auth hot-path files to WP04, which depends on WP03 and must run the guard after its auth edits.

Tests:

- `uv run pytest tests/review/`
- `uv run ruff check src/specify_cli/auth src/specify_cli/cli/commands/auth.py src/specify_cli/cli/commands/_auth_*.py src/specify_cli/cli/commands/review.py`

### WP04 Local Session Hot Path And Cross-Process Coordination

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/token_manager.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/refresh_transaction.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/secure_storage/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/session.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/concurrency/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/auth/stress/test_file_storage_concurrent.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/tests/packaging/test_windows_no_keyring.py`

Plan:

- Measure or characterize the repeated expensive session work across many short-lived processes before changing behavior.
- Make that characterization mandatory: record a baseline and prove the final representative many-process scenario performs fewer repeated durable-session operations than the baseline.
- Design a minimal local handoff/cache that is invalidated by durable session changes, never replaces encrypted file-only storage, and does not expose raw tokens in output.
- Keep refresh coordination under the existing machine-wide lock semantics unless there is concrete evidence that a new lock boundary is needed.
- Preserve benign replay and stale-grant handling from existing auth concurrency behavior.
- Add packaging/dependency regression coverage proving no Keychain/keyring/Secret Service dependency appears.
- Run the WP03 BLE001 guard after auth edits and clean up any scoped suppressions in WP04-owned auth files before review.

Tests:

- `uv run pytest tests/auth/concurrency tests/auth/stress/test_file_storage_concurrent.py`
- `uv run pytest tests/auth/secure_storage tests/packaging/test_windows_no_keyring.py`
- Add a representative many-process hot-path test that asserts fallback to encrypted storage when the handoff is stale or invalid.

### WP05 Integrated Evidence And Smoke

Owner surface:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/quickstart.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/`
- focused test suites touched by WP01-WP04

Plan:

- Run focused auth, sync, tracker, review, packaging, and hot-path suites.
- Run hosted-auth/tracker/sync smoke commands only with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this computer.
- Record any pre-existing failures by opening a GitHub issue before accepting them as baseline, per charter.
- Produce final evidence showing #829, #907, #889, #977, and CLI-side #77 acceptance checks.

## Execution Lanes

```
WP01 Diagnostic Classification And Logged-Out Guidance
WP02 Refresh-Lock Hermeticity
WP03 BLE001 Guardrail
  \       |       /
   \      |      /
    \     |     /
     WP04 Local Session Hot Path (depends on WP02 and WP03)
          |
        WP05 Integrated Evidence And Smoke
```

WP01, WP02, and WP03 can start independently. WP04 starts after WP02's test isolation boundary and WP03's guardrail are clear because it touches auth concurrency/storage files that must satisfy the new guard. WP05 waits for all implementation WPs.

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| #977 framing | Test isolation bug first | The known hang occurs when fake refreshed sessions trigger a real membership rehydrate because hosted URL leaks from the shell; no evidence yet proves refresh locking is algorithmically broken. |
| Diagnostic ownership | CLI-owned unless proven otherwise | User-facing classification and recovery guidance happen in CLI command/sync surfaces. Tracker package changes require concrete ownership evidence. |
| Direct-ingress category | Preserve existing missing-private-team category | Existing tests and sync helper already name `direct_ingress_missing_private_team`; the bug is collapse into `server_error`, not absence of a domain category. |
| BLE001 guard | Extend existing review/check surface | The repository already has a review BLE001 audit; reuse the local pattern and make it testable rather than introducing a parallel lint framework. |
| Hot-path authority | Encrypted file-only storage remains authority | Any cache/handoff is performance coordination only and must fall back to durable encrypted storage. |
| Hosted smoke | Explicit, not default | Default tests must be hermetic; hosted commands on this computer use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. |

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No charter violations require justification. This plan stays inside existing CLI repository boundaries, dependencies, branch strategy, and storage constraints.

## Post-Design Charter Re-check

| Charter standard | Result |
|---|---|
| Existing Python CLI stack retained | PASS |
| Tests planned for all new behavior | PASS |
| No server contract changes | PASS |
| External tracker package boundary respected | PASS |
| Encrypted file-only root of trust preserved | PASS |
| Branch contract explicit: `main` to `main`, `branch_matches_target=true` | PASS |
| No task generation in plan phase | PASS |
