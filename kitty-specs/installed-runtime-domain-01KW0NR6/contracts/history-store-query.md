# Contract: UpgradeAttemptStore query interface

**Module**: `src/specify_cli/compat/history.py`
**FR**: FR-013, FR-015, NFR-005, NFR-006, NFR-007
**Consumers**: `readiness/upgrade_ux.py` (`_default_upgrade_runner`)

---

## Write contract: append()

```python
def append(self, record: UpgradeAttemptRecord) -> None:
```

**Guarantees**:
1. Best-effort: any `sqlite3.Error`, `OSError`, or other exception is swallowed silently (fail-safe for appends). Callers MUST NOT depend on the append succeeding.
2. Idempotent write: a record with an `attempt_id` already present in the store is silently ignored (`INSERT OR IGNORE`).
3. Retention: after a successful insert, the store runs a trim to keep the last 200 records per `install_method`. The trim is part of the same transaction.
4. WAL mode: the store opens with `PRAGMA journal_mode=WAL` before any DML.

**NFR-007 enforcement**: implementors MUST NOT store `sys.executable`, user paths, project slugs, hostnames, or machine IDs in any column. Only `install_method` (a StrEnum value), `intent`, `outcome`, `exit_code`, `target_version` (a version string matching `[A-Za-z0-9.\-+]{1,64}` or None), `attempt_id` (ULID), and `timestamp` (UTC ISO datetime) are permitted.

---

## Read contract: is_idempotent()

```python
def is_idempotent(self, attempt: UpgradeAttemptRecord) -> bool:
```

**Semantics**: Returns True iff a record with `outcome == 'success'` AND the same `install_method` AND the same `target_version` already exists in the store.

**Edge cases**:
- `attempt.target_version is None` → always returns False (cannot deduplicate unknown version).
- Store unreachable → returns False (fail-open).

**Acceptance scenario** (FR-013, User Story 3, scenario 2):
> Given two consecutive upgrade attempts with identical install_method and target_version, when the history store is queried, then `is_idempotent(attempt)` returns True for the second attempt if the first was a success.

---

## Read contract: consecutive_failure_count()

```python
def consecutive_failure_count(
    self,
    install_method: InstallMethod,
    *,
    window_seconds: int = 300,
) -> int:
```

**Semantics**: Returns the number of consecutive `outcome == 'failure'` records at the tail of the recent history for `install_method`, within `window_seconds` of now. Stops counting at the first non-failure record.

**Scan bound**: at most the last 100 records per `install_method` (SC-004). Records outside `window_seconds` are excluded before counting.

**Edge cases**:
- No records → returns 0.
- Store unreachable → returns 0 (fail-open).

**Acceptance scenario** (FR-015, User Story 3, scenario 3):
> Given three consecutive failed attempts in a 5-minute window, when the history store is queried, then the store reports `consecutive_failures=3` and the caller can apply a backoff policy without re-reading the NagCache.

---

## Read contract: last_success_timestamp()

```python
def last_success_timestamp(
    self, install_method: InstallMethod
) -> datetime | None:
```

**Semantics**: Returns the UTC `datetime` of the most recent record with `outcome == 'success'` for the given `install_method`, or None if no such record exists.

**Edge cases**:
- No success records → returns None.
- Store unreachable → returns None (fail-open).

---

## Path resolution: default_history_db_path()

```python
def default_history_db_path() -> Path:
```

**Resolution order** (same pattern as NagCache `_resolve_cache_dir()`):
1. `SPEC_KITTY_HISTORY_DB_PATH` env var, if set and non-empty.
2. `platformdirs.user_cache_dir("spec-kitty") / "upgrade-history.db"`.
3. Manual XDG/OS fallback:
   - Linux: `$XDG_CACHE_HOME/spec-kitty/upgrade-history.db` or `~/.cache/spec-kitty/upgrade-history.db`
   - macOS: `~/Library/Caches/spec-kitty/upgrade-history.db`
   - Windows: `%LOCALAPPDATA%\spec-kitty\Cache\upgrade-history.db`

**NFR-009**: This path is SEPARATE from `upgrade-nag.json` (NagCache) and SEPARATE from `~/.spec-kitty/queue.db` (OfflineQueue). The NagCache schema is NOT extended.

---

## Security properties

| Check | Enforcement |
|-------|-------------|
| NFR-007 (no PII) | `attempt_id` is a ULID (not derived from any path or user identity); `target_version` matches version regex or is None; no path columns |
| NFR-006 (concurrent-write safety) | WAL journal mode; `INSERT OR IGNORE` for idempotent writes |
| NFR-005 (idempotency on read) | `UNIQUE` index on `attempt_id`; `INSERT OR IGNORE` |
| Fail-safe appends | All `sqlite3.Error` swallowed with `# noqa: BLE001` |
| Fail-open reads | All `sqlite3.Error` swallowed; return default (False / 0 / None) |
| File creation | `db_path.parent.mkdir(parents=True, exist_ok=True)` before first open |
