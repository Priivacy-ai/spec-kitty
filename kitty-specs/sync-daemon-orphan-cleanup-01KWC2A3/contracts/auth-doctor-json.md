# Contract: `auth doctor` JSON output

**Surface**: `src/specify_cli/cli/commands/auth.py` (`doctor`) → `_auth_doctor.py` (`doctor_impl`)
**Requirements**: FR-004, FR-005, FR-009

The command stays **read-only without `--reset`** (read-only invariant preserved). `--reset` is the only mutating path. A new `--force` flag is added (D-02).

## `--json` (read-only scan) — FR-004

`schema_version` bumps **1 → 2**. Each entry in `orphans[]` is extended to a full
identity record (additive, superset of today's `{port,pid,package_version,protocol_version}`):

```json
{
  "schema_version": 2,
  "generated_at": "2026-06-30T10:59:00+00:00",
  "auth_root": "/Users/<u>/.spec-kitty",
  "session": { "present": true, "user_email": "u@example.com", "...": "..." },
  "refresh_lock": { "held": false, "...": "..." },
  "daemon": { "active": true, "pid": 4321, "port": 9400, "package_version": "3.2.4", "protocol_version": 1 },
  "orphans": [
    {
      "daemon_family": "sync",
      "pid": 5001, "port": 9401,
      "protocol_version": 1, "package_version": "3.2.2",
      "singleton_scope_id": "/Users/<u>/.spec-kitty",
      "daemon_root": "/Users/<u>/.spec-kitty",
      "queue_db_path": "/Users/<u>/.spec-kitty/queues/queue-aaaaaaaa.db",
      "auth_scope": "https://…|u@example.com|t-private",
      "server_url": "https://…", "owner_present": true,
      "identity_source": "health_self_report",
      "executable_summary": "…/bin/python",
      "spawn_shape_ok": true,
      "self_report_matches_listener": true,
      "is_recorded_singleton": false,
      "cleanup_class": "safe_auto",
      "skip_reason": null
    },
    {
      "daemon_family": "sync", "pid": null, "port": 9405,
      "package_version": "3.2.3", "singleton_scope_id": null,
      "identity_source": "cmdline_marker", "owner_present": false,
      "cleanup_class": "operator_required", "skip_reason": "pre_marker"
    }
  ],
  "findings": [ { "id": "F-002", "severity": "warn", "summary": "…", "remediation": { "command": "spec-kitty auth doctor --reset" } } ]
}
```

- Consumers MUST switch on `cleanup_class`; counts alone are non-conformant (FR-004).
- `never_touch` listeners (third-party / out-of-range) are excluded from `orphans[]`.

## `--reset --json` — FR-005, FR-009

Adds a top-level `reset_result` object with three explicit arrays:

```json
{
  "schema_version": 2,
  "reset_result": {
    "swept":   [ { "pid": 5001, "port": 9401, "package_version": "3.2.2", "protocol_version": 1, "cleanup_path": "http_shutdown", "reason": "safe_auto stale-version" } ],
    "skipped": [ { "pid": null, "port": 9405, "cleanup_class": "operator_required", "skip_reason": "pre_marker" } ],
    "failed":  [ { "pid": 5009, "port": 9402, "failure_reason": "process survived terminate+kill" } ]
  }
}
```

- Without `--force`: `operator_required` candidates appear in `skipped[]` with their
  `cleanup_class`/`skip_reason`. Human output prints a one-line remediation hint
  (`… run with --force to clean N operator_required daemon(s)`), satisfying FR-009.
- With `--force` (or interactive `y`): `operator_required` candidates are attempted;
  successes move to `swept[]`, survivors to `failed[]`.
- `cleanup_path` ∈ `{http_shutdown, terminate, kill}` records which escalation step closed the port.

## Human output (FR-004/FR-005)

The existing "Orphans" table gains a `class` column (`safe_auto`/`operator_required`)
and a `reason` column; `--reset` prints compact swept/skipped/failed lines mirroring the
JSON. Count-only output is removed.

## Back-compat note

The `schema_version` bump to `2` is the signal for consumers. Fields are additive on
`orphans[]`; the pre-existing keys remain present, so a v1 reader degrades gracefully.
