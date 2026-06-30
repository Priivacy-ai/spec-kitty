# Contract: `/api/health` payload (extended)

**Surface**: `SyncDaemonHandler.handle_health` (`src/specify_cli/sync/daemon.py:487-520`)
**Requirements**: FR-001, FR-003

The loopback-only health endpoint gains a single field: `daemon_family`. Everything
else is unchanged (the redacted `owner` block already carries the identity fields).

```json
{
  "status": "ok",
  "token": "<redacted>",
  "daemon_family": "sync",
  "protocol_version": 1,
  "package_version": "3.2.4",
  "sync": { "running": false, "last_sync": null, "consecutive_failures": 0 },
  "websocket_status": "Offline",
  "owner": {
    "pid": 4321, "port": 9400,
    "package_version": "3.2.4",
    "executable_path": "…/bin/python",
    "source_checkout_path": "…",
    "server_url": "https://…",
    "auth_principal": "u@example.com", "auth_team": "t-private",
    "auth_scope": "https://…|u@example.com|t-private",
    "queue_db_path": "…/queues/queue-aaaaaaaa.db",
    "started_at": "2026-06-30T10:40:00+00:00"
  }
}
```

## Rules

- `daemon_family` is always `"sync"` for the sync daemon. It lets a scanner confirm
  family from the self-report (defense-in-depth on top of port-range isolation).
- The endpoint remains **unauthenticated and loopback-only** (`127.0.0.1`); do not
  add auth or non-loopback exposure (Sonar loopback exception applies — keep it).
- `owner` is **reporting data only**. Classification authority is the daemon-root
  scope marker in the process cmdline, never this payload (FR-003). A daemon that
  returns `owner` but whose cmdline marker can't be proven is still `operator_required`.
- `self_report_matches_listener` (in the identity record) is computed by comparing
  `owner.pid`/`owner.port` here against the actual listener pid/port — a daemon that
  misreports is downgraded to `operator_required` (`pid_port_mismatch`).
