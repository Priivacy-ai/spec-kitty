# Spec: MVP Sync Boundary — CLI

**Mission**: `mvp-sync-boundary-cli-01KRVCQS`
**Target branch**: `main`
**Source**: `/Users/robert/spec-kitty-dev/spec-kitty-20260517-165635-WafwWc/start-here.md` (sections "Agent Prompt: Queue Scope Migration", "Daemon Ownership", "Sync Status / Doctor", "Setup-Plan Sync Evidence") and Priivacy-ai/spec-kitty issues #1090, #1088, #1087, #1089.

## Purpose

Restore the single-identity boundary across foreground CLI auth, scoped queue DB, body upload queue, daemon ownership, and setup-plan emission so that authenticated CLI work cannot be stranded in a legacy unauthenticated queue, owned by a stale daemon from a temp checkout, or silently routed to the wrong scope. Make `sync status --check` truthful about the actual coherence of the boundary.

## Background

The 2026-05-17 incident showed four CLI-side breaks:

1. The foreground CLI reported authenticated but four `body_upload_queue` rows for the active mission lived in legacy `~/.spec-kitty/queue.db`, because `_migrate_legacy_queue_to_scope` in `src/specify_cli/sync/queue.py` returns early if the destination scoped DB has ANY rows (even unrelated). (#1090)
2. The registered daemon was running package version `3.2.0rc9` from an old temp checkout while the foreground CLI was `3.2.0rc8`; multiple stale daemon processes were alive on different ports. (#1088)
3. `sync status` reported "authenticated/connected" while hiding the legacy queue rows, daemon version mismatch, and queue-scope mismatch. (#1087)
4. `spec-kitty agent mission setup-plan` emitted body uploads that landed in the legacy queue rather than the active scoped queue, so SaaS never materialized the mission. (#1089)

This mission fixes all four. It depends on the `WPStatusChanged` contract locked by mission `wpstatuschanged-backward-transition-contract-01KRV7SC` in `spec-kitty-events` (already merged).

## Scope (in)

- Row-level idempotent legacy→scoped migration covering event queue rows, `body_upload_queue` rows, and body upload failure/history rows. Safe to run repeatedly. Deletes from legacy only after successful copy.
- Stable daemon owner metadata (PID, port, token, package version, executable path, source checkout path, server URL, auth principal/team/scope, queue DB path, start time). Replacement, retirement, and orphan-detection semantics.
- `sync status` and `sync status --check` that surface the foreground/daemon mismatch shape, legacy stranding, and queue-scope mismatch as errors. `--check` returns non-zero on incoherence.
- `setup-plan` SaaS-evidence guarantee: when SaaS sync is enabled and the foreground is authenticated, setup-plan MUST emit body uploads + canonical events into the active scoped queue. When unauthenticated, it MUST fail loudly with a blocking diagnostic rather than silently strand work in legacy.
- Tests against tmp HOME / `SPEC_KITTY_HOME` for every behaviour. No use of the operator's live `~/.spec-kitty` as a fixture.

## Scope (out / non-goals)

- NG-1: Changing the canonical `WPStatusChanged` event contract or any event semantics. That lives in `spec-kitty-events` (already merged).
- NG-2: SaaS server-side behaviour (materializer, drain, readiness). Those are `spec-kitty-saas#205/204/206`, separate mission.
- NG-3: Killing live operator daemon processes during tests. Use fake process metadata or controlled subprocesses.
- NG-4: Modifying the operator's `~/.spec-kitty` directory.
- NG-5: Backfilling the 22 historical `terminal_failed` rows on production.
- NG-6: Adding new auth flows or token shapes.

## Locked decisions

- D-1: Migration is **row-level merge**, not whole-DB copy. Each event row is keyed by stable identity (`event_id` for events; `(table, upload_id)` or equivalent for body upload tables). Duplicate keys are skipped. After successful copy + verification, legacy rows are deleted.
- D-2: A daemon owner record includes: `pid`, `port`, `token`, `package_version`, `executable_path`, `source_checkout_path`, `server_url`, `auth_principal`, `auth_team`, `auth_scope`, `queue_db_path`, `started_at`. Owner records live under `~/.spec-kitty/daemon/owner.json` (or scoped path under `SPEC_KITTY_HOME`).
- D-3: Foreground CLI MUST refuse to start a sync action when the registered daemon owner reports a mismatched `package_version`, `executable_path`, `server_url`, `auth_scope`, or `queue_db_path` versus the foreground's current values. The remediation message MUST name the specific mismatched field(s).
- D-4: A "stale daemon" is one whose owner record exists but whose `pid` is not alive OR whose `executable_path` no longer exists on disk. The doctor and status commands surface and offer to retire stale owners.
- D-5: `setup-plan` MUST refuse to proceed when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` AND the foreground is not authenticated (no valid session + no valid credentials). The error message MUST explain that SaaS sync cannot be guaranteed.
- D-6: `setup-plan` MUST route every body upload and canonical event through `default_queue_db_path()` (which already picks the active scoped queue when authenticated). No setup-plan code path may bypass `default_queue_db_path()`.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `src/specify_cli/sync/queue.py` `_migrate_legacy_queue_to_scope` MUST perform row-level merge into the scoped DB for tables `queue`, `body_upload_queue`, and any body upload failure/history table. Deduplicate by stable key (`event_id` for queue; `(table, upload_id)` for upload tables). Delete from legacy only after the row exists in scoped. | Approved |
| FR-002 | Migration MUST be idempotent: running it twice produces the same scoped state with no duplicate rows. | Approved |
| FR-003 | Migration MUST run on every `default_queue_db_path()` call when an active scope is resolvable AND the legacy DB has any of the named tables; no whole-DB emptiness guard. | Approved |
| FR-004 | Migration MUST emit a structured log line per legacy row migrated (level: info) including the table name and stable key (no sensitive payload contents). | Approved |
| FR-005 | Daemon start MUST write an owner record at `<sync_root>/daemon/owner.json` containing the fields in D-2. | Approved |
| FR-006 | Daemon health endpoint MUST return the owner record (excluding `token`) so foreground can compare without reading the lock file directly. | Approved |
| FR-007 | When the foreground attempts a sync action and the daemon owner's `package_version`, `executable_path`, `server_url`, `auth_scope`, or `queue_db_path` does not match the foreground, the CLI MUST refuse the action and emit a remediation message naming the mismatched field(s). | Approved |
| FR-008 | `sync status` MUST report: foreground CLI version, foreground executable path, server URL, auth principal/team/scope, active scoped queue DB path and event count, active scoped body-upload count, legacy queue DB path and event/body-upload counts, daemon PID/port/version/executable/source path/server URL/auth scope/queue DB path, foreground/daemon mismatch diagnostics, and orphan daemon count. | Approved |
| FR-009 | `sync status --check` MUST return non-zero exit code when (a) foreground and daemon disagree on any D-3 field, OR (b) legacy DB has any rows for the active scope (any tables checked by migration), OR (c) ≥1 orphan daemon is detected. | Approved |
| FR-010 | `doctor` (or equivalent) MUST list orphan daemons and offer a retirement command. | Approved |
| FR-011 | `spec-kitty agent mission setup-plan` MUST refuse to proceed when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` AND the foreground is unauthenticated. The error MUST cite missing auth and explain that SaaS sync cannot be guaranteed. | Approved |
| FR-012 | `setup-plan` body uploads and canonical events MUST route through `default_queue_db_path()` so they land in the active scoped queue when authenticated. No setup-plan code path may write directly to `_legacy_queue_db_path()`. | Approved |
| FR-013 | `sync status` MUST detect when setup-plan body uploads from the current mission have ended up in legacy and surface this as a specific diagnostic (overlaps with FR-009 (b); FR-013 additionally tags it with "setup-plan stranded mission slug X"). | Approved |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All new tests use temp HOME / `SPEC_KITTY_HOME`; none read or write the operator's live `~/.spec-kitty`. | grep over new test files returns 0 hits on `os.path.expanduser("~/.spec-kitty")` outside of a fixture-helper. | Approved |
| NFR-002 | `uv run pytest tests/sync tests/status tests/runtime` passes on `main` after merge. | 0 failures, 0 errors. | Approved |
| NFR-003 | Aggregate runtime for the new test files < 30 seconds. | `--durations=10` shows new tests under 30s aggregate. | Approved |
| NFR-004 | `mypy --strict src/specify_cli/sync/ src/specify_cli/cli/commands/sync/ src/specify_cli/cli/commands/agent/` passes. | Exit 0. | Approved |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | MUST NOT use raw SQL surgery or operator-side manual queue edits as the product fix. The fix lives in code, exercised by tests. | Approved |
| C-002 | MUST NOT kill live operator daemon processes during tests. Use fake metadata or controlled subprocesses. | Approved |
| C-003 | MUST NOT modify the events repo or SaaS repo from this mission. Cross-mission dependencies are handled at program level. | Approved |
| C-004 | MUST NOT add new top-level dependencies to pyproject.toml. | Approved |
| C-005 | Code under `src/specify_cli/sync/` MUST pass `mypy --strict` after this mission. | Approved |
| C-006 | Daemon owner record file MUST be atomically written or locked (existing file-locking primitives in `sync/`) to avoid two daemons racing on writes. | Approved |

## Success criteria

- SC-1: With legacy queue rows for mission X and an authenticated foreground in scope Y, running `default_queue_db_path()` returns scope Y's path AND moves the legacy rows for any mission into scope Y, deleting them from legacy.
- SC-2: With legacy rows that don't match the active scope, migration still copies them (by stable identity, not by scope).
- SC-3: With a daemon started from checkout A and a foreground from checkout B, `sync status --check` fails with a remediation message naming `executable_path` and `source_checkout_path` mismatches.
- SC-4: With `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth, `spec-kitty agent mission setup-plan` exits non-zero before writing any body upload row anywhere.
- SC-5: With `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and a valid session, setup-plan writes body uploads to the active scoped queue (verified by counting rows in scope path vs legacy path).
- SC-6: `sync status` lists ≥1 orphan daemon when an owner record's PID is dead.

## Key entities

- **Legacy queue DB**: `~/.spec-kitty/queue.db` (pre-scope). Owned by `_legacy_queue_db_path()`.
- **Scoped queue DB**: `~/.spec-kitty/queues/<scope>.db`. Owned by `scope_db_path(scope)`.
- **Daemon owner record**: JSON file under `~/.spec-kitty/daemon/owner.json` capturing the D-2 fields.
- **Foreground identity**: derived from `_get_package_version()`, `sys.executable`, current server URL, current scope.
- **Orphan daemon**: owner record whose `pid` is not alive OR whose `executable_path` no longer exists on disk.

## Dependencies

- Upstream: `wpstatuschanged-backward-transition-contract-01KRV7SC` (merged to spec-kitty-events main; locks the event contract this CLI emits).
- Downstream: `spec-kitty-saas` mission #205/204/206; `spec-kitty-end-to-end-testing` mission #41.
