# Phase 1 Data Model: MVP CLI Sync Boundary Completion

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`

This mission introduces no new persistent storage and no SQLite schema changes. The data model below describes the *in-memory* entities the new preflight helper exchanges with existing helpers, plus the existing on-disk shapes the preflight reads.

## Entity: `ForegroundIdentity`

Describes the foreground (operator-invoked) CLI process for comparison against a daemon owner record.

| Field | Type | Source | Notes |
|---|---|---|---|
| `package_version` | `str` | `spec_kitty.__version__` (or equivalent) | e.g., `3.2.0rc11` |
| `executable_path` | `Path` | `sys.executable` | Absolute path to the python interpreter or installed entry point |
| `source_path` | `Path` | resolved from `__file__` of the CLI entry point | Site-packages or editable checkout |
| `server_url` | `str \| None` | active hosted-auth config | `None` when unauthenticated |
| `team_or_user` | `str \| None` | active hosted-auth config | Canonical id, never bare display name |
| `queue_db_path` | `Path` | `default_queue_db_path()` (existing) | Scoped DB when authenticated, legacy fallback otherwise |
| `pid` | `int` | `os.getpid()` | Used only for orphan disambiguation; never to kill processes |

**Invariants**:
- `executable_path` and `source_path` are absolute.
- `team_or_user` is set if and only if `server_url` is set.
- `queue_db_path` is set unconditionally; the value differs between authenticated and unauthenticated foreground.

## Entity: `DaemonOwnerRecord`

Existing on-disk record at `owner_record_path()` (see `src/specify_cli/sync/owner.py:121`).

| Field | Type | Notes |
|---|---|---|
| `pid` | `int` | Daemon process pid |
| `port` | `int` | Daemon health-endpoint port |
| `package_version` | `str` | Daemon's reported CLI package version |
| `executable_path` | `Path` | Daemon's interpreter / entry point |
| `source_path` | `Path` | Daemon's source path |
| `server_url` | `str \| None` | Hosted-auth endpoint daemon authenticated against |
| `team_or_user` | `str \| None` | Canonical team or user id |
| `queue_db_path` | `Path` | Scoped queue DB the daemon owns |
| `started_at` | `datetime` | UTC ISO timestamp |

**Invariants** (unchanged):
- Record presence implies daemon was at one point alive with this configuration.
- `is_orphan(record)` (existing) returns `True` when `record.pid` is no longer alive.

## Entity: `OwnerMismatch`

New, in-memory. Returned by `SyncBoundaryPreflight` when a field diverges between foreground and daemon owner record.

| Field | Type | Notes |
|---|---|---|
| `field` | `Literal[...]` | One of the canonical field names: `daemon_package_version`, `daemon_executable_path`, `daemon_source_path`, `daemon_server_url`, `daemon_team_or_user`, `daemon_queue_db_path` |
| `foreground_value` | `str` | Pretty-rendered foreground value |
| `daemon_value` | `str` | Pretty-rendered daemon value |
| `remediation_hint` | `str` | Short, actionable hint pointing to a CLI subcommand |

**Invariants**:
- `field` is one of exactly six canonical names; no free-form fields.
- `foreground_value` and `daemon_value` are non-empty strings (use `<unset>` placeholder when a value is `None`).

## Entity: `PreflightResult`

New, in-memory. Returned by `SyncBoundaryPreflight.run_preflight(...)`.

| Field | Type | Notes |
|---|---|---|
| `ok` | `bool` | `True` only when boundary coherence holds and auth requirement is satisfied |
| `mismatches` | `list[OwnerMismatch]` | Empty when no daemon record exists *and* there is no other coherence violation |
| `orphan_records` | `list[DaemonOwnerRecord]` | From `list_orphan_records()` (existing) |
| `legacy_rows_for_scope` | `int` | From extended `detect_legacy_rows_for_scope()`; sum of event-class and body-upload rows |
| `legacy_event_rows` | `int` | Subtotal, surfaced for `sync status --check` printed fields |
| `legacy_body_upload_rows` | `int` | Subtotal, surfaced for `sync status --check` printed fields |
| `auth_present` | `bool` | `True` iff foreground has an authenticated identity |
| `auth_required` | `bool` | Echoed input; `True` for SaaS-producing commands when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` |

**Invariants**:
- `ok == (mismatches == [] and orphan_records == [] and legacy_rows_for_scope == 0 and (auth_present or not auth_required))`.
- The result is frozen / hashable for snapshotting in tests.

## Existing entity (unchanged): scoped `OfflineQueue` DB

SQLite database at `default_queue_db_path()` (see `src/specify_cli/sync/queue.py:789`).

Tables of interest:
- `sync_events` — primary key `event_id` (existing)
- `body_upload_queue` — primary key `upload_id` (existing)

**No schema change**. Row-level migration uses `INSERT OR IGNORE` keyed on the primary keys.

## Existing entity (unchanged): legacy queue DB

SQLite database at `_legacy_queue_db_path()` (see `src/specify_cli/sync/queue.py:374`). Same table shapes as scoped DB.

## State / lifecycle

The preflight is read-only against persistent state. It produces a `PreflightResult` and either lets the caller proceed or refuses with non-zero exit. No state transitions are owned by the preflight itself.

The row-level migration *does* mutate the scoped DB by inserting rows from the legacy DB. The migration is idempotent: re-running it on the same legacy + scoped pair is a no-op (`INSERT OR IGNORE`).

## Externally visible events

None new. SaaS events emitted by sync-producing commands are unchanged in shape; only the *gating* before they are emitted changes.

## Cross-platform note (C-008)

All entities in this model are `pathlib.Path`-based for file-system fields. Code and tests must run identically on Linux, macOS, and Windows 10+ per the project charter and C-008. In particular:

- `executable_path`, `source_path`, `queue_db_path`, and `owner_record_path()` are `Path` values, not raw strings — separator handling is the runtime's responsibility.
- Home-directory isolation in tests redirects `pathlib.Path.home()` (which resolves `USERPROFILE` on Windows and `HOME` on POSIX) rather than mutating only `HOME`.
- The `SPEC_KITTY_ENABLE_SAAS_SYNC=1` env var is set with shell-appropriate syntax (`export …=1` on POSIX, `set …=1` in `cmd.exe`, `$env:… = 1` in PowerShell).
