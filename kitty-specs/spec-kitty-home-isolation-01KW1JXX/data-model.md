# Phase 1 Data Model: SPEC_KITTY_HOME State Isolation

This fix introduces no new persisted entities. The "data model" here is the **path
resolution model** — the authoritative root and the state surfaces derived from it.

---

## Entity: `RuntimeRoot` (existing — `src/specify_cli/paths/windows_paths.py`)

Frozen dataclass; the single source of the global-state base directory.

| Field / property | Type | Meaning | Change in this mission |
|------------------|------|---------|------------------------|
| `platform` | `Literal["win32","darwin","linux"]` | Resolved OS | unchanged |
| `base` | `Path` | Authoritative global-state root | **Now honors `SPEC_KITTY_HOME`** |
| `auth_dir` | `Path` (`base/auth`) | Auth store dir | unchanged (derives from base) |
| `sync_dir` | `Path` (`base/sync`) | Daemon sync dir | unchanged |
| `daemon_dir` | `Path` (`base/daemon`) | Windows daemon dir | unchanged |
| `tracker_dir` | `Path` (`base/tracker`) | Windows tracker dir | unchanged |
| `cache_dir` | `Path` (`base/cache`) | Cache dir | unchanged |

### Resolution rule (`get_runtime_root()`)

```
env := os.environ.get("SPEC_KITTY_HOME")
if env (non-empty):     base = Path(env)            # all platforms
elif platform == win32: base = platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)
else:                   base = Path.home() / ".spec-kitty"
```

**Invariants**
- **INV-1 (purity)**: resolution performs no filesystem I/O and creates no directories (NFR-002).
- **INV-2 (env precedence)**: a non-empty `SPEC_KITTY_HOME` wins on every platform (FR-011).
- **INV-3 (empty = unset)**: empty string falls through to the platform default (FR-012).
- **INV-4 (no migration)**: changing the root never moves existing data (C-001).

---

## State Surface Map (relative to `base`)

The contract is **the suffix below stays constant per platform**; only `base` changes when
`SPEC_KITTY_HOME` is set. POSIX = flat; Windows = normalized onto the platformdirs base
(decision DM-01KW1KDHVGWZ0QERDMV1CRJ15S).

| Surface | Module (call site) | POSIX suffix (preserved) | FR |
|---------|--------------------|--------------------------|----|
| Sync config | `sync/config.py` SyncConfig | `config.toml` | FR-001 |
| Credentials (sync) | `sync/queue.py` `_credentials_path` | `credentials` | FR-001/008 |
| Auth session dir (queue) | `sync/queue.py` `_auth_session_store_dir` | `auth` | FR-002 |
| Legacy queue DB | `sync/queue.py` `_legacy_queue_db_path` | `queue.db` | FR-004 |
| Scoped queue dir | `sync/queue.py` `_scoped_queue_dir` | `queues/` | FR-005 |
| Active queue scope | `sync/queue.py` `_active_scope_path` | `active_queue_scope` | FR-005 |
| Daemon root | `sync/daemon.py` `_daemon_root` | `` (base, flat) | FR-006 |
| Daemon sync root | `sync/daemon.py` `_sync_root` | `sync/` | FR-006 |
| Daemon constant | `sync/daemon.py` `SPEC_KITTY_DIR` | `` (→ make lazy) | FR-006 |
| Lamport clock | `sync/clock.py` default + `load()` | `clock.json` | FR-007 |
| Auth store (POSIX) | `auth/secure_storage/file_fallback.py` | `auth/` | FR-002 |
| Auth store (Windows) | `auth/secure_storage/windows_storage.py` | `auth/` (normalized) | FR-002 |
| Refresh lock | `auth/token_manager.py` `_refresh_lock_path` | `auth/refresh.lock` | FR-003 |
| Tracker creds | `tracker/credentials.py` `_tracker_root` | `` → `credentials` | FR-008 |
| Tracker DB | `tracker/store.py` `_spec_kitty_dir`/`_trackers_dir` | `trackers/` | FR-008 |
| Doctor global-sync | `state/doctor.py` (`~141`, `~253`) | `` (base) + surface patterns | FR-009 |
| Contract GLOBAL_SYNC | `state/contract.py` STATE_SURFACES | declarative patterns (unchanged); resolution honors base | FR-009/010 |

**Note**: `state/contract.py` defines the *relative* surface patterns and remains the
single source of those patterns; `state/doctor.py` is where absolute resolution must adopt
`get_runtime_root().base`.

---

## Out-of-model (explicitly NOT global state)

- `src/specify_cli/review/lock.py` — `.spec-kitty` is a **worktree-local** review lock
  (`worktree / ".spec-kitty"`), not `~/.spec-kitty`. Untouched.
- `get_kittify_home()` asset home (`.kittify`) — separate concept; already honors the env
  var. Untouched except as the consistency reference for the read idiom.
