# Data Model — CLI Session Survival and Daemon Singleton

This document makes the four conceptual entities from `spec.md` §"Key
Entities" concrete. It defines field-level types, identity rules, and
lifecycle states. No new persisted shape is invented for entities the
existing code already owns.

## 1. AuthSession (existing — unchanged)

The persisted authenticated session. Already defined as `StoredSession`
in `src/specify_cli/auth/session.py`. **No field changes** in this
mission. Listed here for completeness because the refresh transaction
reasons over it.

| Field | Type | Identity? |
|---|---|---|
| `user_id` | `str` | no |
| `email` | `str` | no |
| `name` | `str` | no |
| `teams` | `list[Team]` | no |
| `default_team_id` | `str` | no |
| `access_token` | `str` | no |
| `refresh_token` | `str` | **yes (combined with `session_id`)** |
| `session_id` | `str` | **yes (combined with `refresh_token`)** |
| `issued_at` | `datetime (UTC)` | no |
| `access_token_expires_at` | `datetime (UTC)` | no |
| `refresh_token_expires_at` | `datetime (UTC) \| None` | no |
| `scope` | `str` | no |
| `storage_backend` | `Literal["file"]` | no |
| `last_used_at` | `datetime (UTC)` | no |
| `auth_method` | `Literal["authorization_code","device_code"]` | no |

**Identity rule** (used by the refresh transaction reload-and-compare):
two `StoredSession`s refer to the same material iff
`(s.session_id, s.refresh_token)` are byte-equal. The transaction never
needs to compare any other field.

**Lifecycle states**:

```
        login        rotate
  none ───────▶ V0 ───────▶ V1 ───────▶ V2 ─ ... ─▶ Vn
                │                                      │
                │                clear (logout / current rejection)
                ▼                                      ▼
              none                                   none
```

Each rotation produces a new `StoredSession` instance with new
`access_token` and `refresh_token` values. Persistence is atomic via
the secure-storage backend's `write()`.

## 2. MachineRefreshLock (new)

A process-coordination artifact under the auth-store root.

- **On-disk path**: `~/.spec-kitty/auth/refresh.lock` (POSIX);
  `%LOCALAPPDATA%\spec-kitty\auth\refresh.lock` (Windows, via the
  `RuntimeRoot` helper).
- **OS-level lock primitive**: `fcntl.flock(LOCK_EX | LOCK_NB)` on
  POSIX; `msvcrt.locking(LK_NBLCK)` on Windows. Held for the duration
  of one refresh transaction.
- **Content schema** (JSON, atomically written via
  `specify_cli.core.atomic.atomic_write` after acquiring the OS lock):

```json
{
  "pid": 12345,
  "started_at": "2026-04-28T10:30:00+00:00",
  "host": "robert-mbp.local",
  "version": "3.2.0a5"
}
```

- **Identity**: the lock-file path itself is identity. A single
  `MachineRefreshLock` exists per auth-store root.
- **Lifecycle states**: `unheld` ⇄ `held(record)` ⇄ `stale(record,
  age>stale_after_s)`.
- **Hold ceiling** (NFR-002): 10 s. The transaction must release within
  this window or the helper raises and unlocks.
- **Stale threshold** (consumed by `auth doctor --unstick-lock`):
  default 60 s, configurable in `core/file_lock.py`. A `stale` lock can
  be adopted by any process or force-released by an explicit
  `--unstick-lock` invocation.

## 3. UserDaemon (existing — extended)

The single sync-daemon process per OS user. Identity record persisted
as `DAEMON_STATE_FILE` (today: `~/.spec-kitty/sync-daemon`). **No
schema change** in Tranche 1; the file format remains four lines:

```
http://127.0.0.1:9400
9400
<bearer-token-hex>
<pid>
```

What changes is **behavior**:

- **New runtime field (in-memory)**: `self.port` — the port this
  daemon process is bound to.
- **New tick task**: every `DAEMON_TICK_SECONDS=30`, the daemon reads
  `DAEMON_STATE_FILE`. If `parsed.port != self.port`, the daemon
  invokes `server.shutdown()` and exits with code `0`.

| State | Meaning | Transition trigger |
|---|---|---|
| `starting` | Process is launching, has not bound the port yet. | → `active` once `_check_sync_daemon_health` returns true. |
| `active` | This daemon is the user-level singleton. | → `retiring` if next tick observes `state_file.port != self.port`. → `terminating` on `SIGTERM` / `/api/shutdown`. |
| `retiring` | Self-retirement initiated. | → terminal (process exit) once the HTTP server's `serve_forever` loop returns. |
| `terminating` | External shutdown in progress. | → terminal. |

## 4. OrphanDaemon (new conceptual entity)

Not a persisted record — derived at probe time. Discovered by
`enumerate_orphans()` in `sync/orphan_sweep.py`.

- **Identity**: `(pid, port)`. PID is best-effort: read from any
  state-file present, otherwise from `psutil.net_connections()` lookup
  against the listening socket.
- **Identification rule** (D7): a port in `[9400, 9450)` is a
  Spec Kitty daemon iff `GET /api/health` returns 200 with both
  `protocol_version` and `package_version` JSON keys. Of those, an
  orphan is any daemon whose port ≠ `DAEMON_STATE_FILE.port`.
- **Lifecycle**: orphans only exist transiently between detection and
  termination. They have no persisted state.

```
                detect (probe)        terminate (sweep)
  (anonymous) ───────────────▶ orphan ──────────────▶ removed
```

## 5. DoctorReport (new)

The structured output of `auth doctor`. Two surfaces: a human-rendered
Rich layout and a JSON payload (`--json`).

- **Identity**: `(invocation_timestamp_iso, auth_root_path)`. The
  report is ephemeral — never persisted — but it carries timestamps
  and paths so logs and bug reports stay self-describing.

### JSON schema (consumed by `auth doctor --json`)

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-28T10:30:00+00:00",
  "auth_root": "/Users/robert/.spec-kitty/auth",
  "session": {
    "present": true,
    "session_id": "01KQ82XDNTRM3FRSQH98XP4PHW",
    "user_email": "rob@robshouse.net",
    "access_token_remaining_s": 3540,
    "refresh_token_remaining_s": 7689600,
    "storage_backend": "file",
    "in_memory_drift": false
  },
  "refresh_lock": {
    "held": false,
    "holder_pid": null,
    "started_at": null,
    "age_s": null,
    "stuck": false,
    "stuck_threshold_s": 60
  },
  "daemon": {
    "active": true,
    "pid": 54321,
    "port": 9400,
    "package_version": "3.2.0a5",
    "protocol_version": 1
  },
  "orphans": [
    {"pid": 99999, "port": 9401, "package_version": "3.2.0a4"}
  ],
  "findings": [
    {
      "id": "F-002",
      "severity": "warn",
      "summary": "1 orphan daemon detected on port 9401",
      "remediation": {
        "command": "spec-kitty auth doctor --reset",
        "description": "Sweep orphan daemons in the reserved port range."
      }
    }
  ]
}
```

### Severity ladder

- `info` — observation, no action required (e.g. "lock unheld",
  "session healthy").
- `warn` — action recommended (orphans present; access token already
  expired but refresh still valid).
- `critical` — action required (no session; storage corrupted; lock
  stuck and age > threshold).

When `findings` is empty, the report ends with the line `No problems
detected.` and exits 0.

## 6. Identity rule summary

| Entity | Identity tuple | Where stored |
|---|---|---|
| `AuthSession` | `(session_id, refresh_token)` | encrypted file under `~/.spec-kitty/auth/` |
| `MachineRefreshLock` | lock-file path | `~/.spec-kitty/auth/refresh.lock` |
| `UserDaemon` | state-file `(pid, port)` | `~/.spec-kitty/sync-daemon` |
| `OrphanDaemon` | `(pid, port)` | derived at probe time |
| `DoctorReport` | `(generated_at, auth_root)` | ephemeral |

## 7. Backward compatibility

- Existing `StoredSession` shape is **unchanged** (NFR-007).
- Existing `DAEMON_STATE_FILE` shape is **unchanged** (NFR-007).
- Two new files appear: `~/.spec-kitty/auth/refresh.lock` and (per
  daemon process) no new file at all — the daemon-singleton tick reads
  the existing state file.
- A CLI version that does not understand `refresh.lock` will simply
  not see it and continue with the legacy in-process refresh path
  (which is the bug we're fixing). Per NFR-007 this is documented and
  accepted; the only path out is a CLI upgrade.
