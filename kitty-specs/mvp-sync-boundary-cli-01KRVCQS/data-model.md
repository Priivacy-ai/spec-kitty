# Data Model: MVP Sync Boundary — CLI

## DaemonOwnerRecord (NEW)

JSON file at `<sync_root>/daemon/owner.json`. Single-instance record (the daemon process atomically writes it on start, atomically replaces it on shutdown).

```python
@dataclass(frozen=True)
class DaemonOwnerRecord:
    pid: int
    port: int
    token: str
    package_version: str
    executable_path: str         # sys.executable
    source_checkout_path: str    # Path(__file__).resolve().parents[N] — repo root of the installed package
    server_url: str
    auth_principal: str | None
    auth_team: str | None
    auth_scope: str | None       # canonical queue scope per build_queue_scope()
    queue_db_path: str           # default_queue_db_path() for the daemon's session
    started_at: str              # ISO-8601 UTC
```

### Invariants

- Atomic write: `tempfile.NamedTemporaryFile(delete=False, dir=<sync_root>/daemon)` → `os.replace(tmp, owner.json)`.
- Health endpoint returns a dict that omits `token`.
- On daemon shutdown, the file is removed; if shutdown is unclean, the file remains and the foreground's orphan-detection logic identifies it.

### Foreground identity (computed at runtime)

| Field | Source |
|---|---|
| `package_version` | `_get_package_version()` (existing) |
| `executable_path` | `sys.executable` |
| `source_checkout_path` | `Path(specify_cli.__file__).resolve().parents[2]` (or equivalent — same algorithm both sides) |
| `server_url` | `_read_server_url_for_scope()` (existing) |
| `auth_scope` | `read_queue_scope_from_session()` or `read_queue_scope_from_credentials()` |
| `queue_db_path` | `default_queue_db_path()` |

### Mismatch fields (D-3 / FR-007)

A foreground sync action MUST refuse and emit a remediation message when ANY of these fields differs between foreground and daemon:

- `package_version`
- `executable_path` (full path equality)
- `server_url`
- `auth_scope` (None vs non-None counts as a mismatch)
- `queue_db_path`

Other fields (PID, port, token, started_at, source_checkout_path, auth_principal, auth_team) are informational on `sync status` but do not trigger refuse-to-act.

## Row-key strategy for legacy → scoped migration (FR-001/002)

| Source table | Stable key | Conflict resolution |
|---|---|---|
| `queue` | `event_id` (column) | `INSERT OR IGNORE INTO scoped.queue SELECT * FROM legacy.queue WHERE event_id NOT IN (SELECT event_id FROM scoped.queue)` |
| `body_upload_queue` | (`event_id`, `body_kind`) composite (or `upload_id` if present) — check existing schema | Same `INSERT OR IGNORE` pattern, then delete from legacy after row exists in scoped |
| `body_upload_failure_log` (if present) | (`event_id`, `failure_at`) composite — check schema | Same `INSERT OR IGNORE`, copy first, delete from legacy after |

Pseudocode:

```python
def _migrate_legacy_queue_to_scope(scoped_db_path: Path) -> int:
    """Idempotent row-level merge from legacy queue.db into the scoped DB.

    Returns count of rows migrated across all tables.
    """
    legacy_db = _legacy_queue_db_path()
    if not legacy_db.exists():
        return 0
    scoped_db_path.parent.mkdir(parents=True, exist_ok=True)
    migrated = 0
    with sqlite3.connect(legacy_db) as src, sqlite3.connect(scoped_db_path) as dst:
        # Ensure dst schema exists (run existing _ensure_schema / ensure_body_queue_schema)
        _ensure_schema(dst)
        for table, key_columns in _MIGRATION_TABLES:
            if not _table_exists(src, table):
                continue
            rows = list(src.execute(f"SELECT * FROM {table}"))
            for row in rows:
                key = tuple(row[c] for c in key_columns)
                # INSERT OR IGNORE preserves uniqueness; we additionally check the
                # row landed before deleting the legacy copy.
                inserted = _insert_or_ignore(dst, table, row)
                if inserted or _row_exists(dst, table, key_columns, key):
                    src.execute(f"DELETE FROM {table} WHERE {_where_clause(key_columns)}", key)
                    migrated += 1
                    _log_migrated(table, key)
        src.commit()
        dst.commit()
    return migrated


_MIGRATION_TABLES: list[tuple[str, tuple[str, ...]]] = [
    ("queue", ("event_id",)),
    ("body_upload_queue", ("event_id", "body_kind")),  # confirm against current schema
    ("body_upload_failure_log", ("event_id", "failure_at")),  # confirm against current schema; skip table if not present
]
```

Concrete key column choices must be verified against the live schema in `src/specify_cli/sync/queue.py` and `body_queue.py` during implementation. The implementer's first step is to enumerate the tables and pick the schema-canonical primary/unique key for each.

## Setup-plan code-path audit (FR-012)

The implementing agent for WP04 must:

1. Locate every place in the setup-plan code path that opens or writes to a queue DB (search for `sqlite3.connect`, `_legacy_queue_db_path`, `default_queue_db_path`, `OfflineQueue`).
2. Confirm every body-upload-emitting call uses `default_queue_db_path()` (directly or via `OfflineQueue`).
3. Add a regression test that, given an authenticated tmp HOME with a scoped queue, running `setup-plan` produces no rows in `_legacy_queue_db_path()` and ≥1 row in the scoped DB.
4. Add a second regression test that, given `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and an unauthenticated tmp HOME, `setup-plan` exits non-zero with the FR-011 diagnostic before any DB write.
