# Contract: State Surface → Path Mapping

Each global-state surface resolves to `get_runtime_root().base / <suffix>`. The suffix is
**fixed per surface/platform** and MUST NOT change when `SPEC_KITTY_HOME` is set (only
`base` moves). POSIX suffixes below are the byte-identical contract for NFR-001.

| Surface | Resolved path (relative to `base`) | Requirement | Per-surface test obligation |
|---------|-----------------------------------|-------------|------------------------------|
| Sync config file | `config.toml` | FR-001 | `SyncConfig().config_file` under env root; absent from default home |
| Auth session store (POSIX) | `auth/` | FR-002 | `file_fallback.default_store_dir()` under env root |
| Auth session store (Windows) | `auth/` (normalized) | FR-002 | `WindowsFileStorage` default under env root (not `Path.home()`) |
| Token refresh lock | `auth/refresh.lock` | FR-003 | `_refresh_lock_path()` under env root on POSIX + Windows |
| Unauthenticated queue DB | `queue.db` | FR-004 | `default_queue_db_path()` (unauth) under env root |
| Scoped queue DB dir | `queues/` | FR-005 | `default_queue_db_path()` (auth) + `_scoped_queue_dir()` under env root |
| Active queue scope | `active_queue_scope` | FR-005 | `_active_scope_path()` under env root |
| Daemon state/log/lock | `` (flat, POSIX) / `daemon/` (Windows) | FR-006 | `_daemon_root()`, `_sync_root()`, lazy `SPEC_KITTY_DIR` under env root |
| Lamport clock | `clock.json` | FR-007 | `LamportClock.load()` default + dataclass default under env root |
| Tracker credentials | `credentials` (POSIX flat) / `tracker/` (Windows) | FR-008 | `_tracker_root()` under env root |
| Tracker DB | `trackers/` | FR-008 | `store._trackers_dir()` / `default_tracker_db_path()` under env root |
| State doctor report | `base` + surface patterns | FR-009 | `state doctor` reported global-sync root == `get_runtime_root().base` |

## End-to-end CLI contract (SC-001 / SC-002)

```
HOME=<tmpA>  SPEC_KITTY_HOME=<tmpB>  SPEC_KITTY_ENABLE_SAAS_SYNC=1
  spec-kitty sync server https://example.invalid
⇒ <tmpB>/config.toml EXISTS
⇒ <tmpA>/.spec-kitty/config.toml ABSENT
```

This is the literal reproduction from issue #2171, inverted into the passing assertion.
