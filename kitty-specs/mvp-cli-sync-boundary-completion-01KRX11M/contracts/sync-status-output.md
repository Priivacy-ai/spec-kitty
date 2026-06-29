# Contract: `sync status --check` output and exit code

**Module**: `src/specify_cli/cli/commands/sync.py` (existing — extended)
**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`

This contract specifies the printed fields, exit code, and `--json` shape of `spec-kitty sync status --check` after this mission lands.

## Exit code

| Condition | Exit code |
|---|---|
| Boundary coherent, auth present (when `SPEC_KITTY_ENABLE_SAAS_SYNC=1`), no orphans, no legacy rows for scope | `0` |
| Foreground vs daemon mismatch on any of: `daemon_package_version`, `daemon_executable_path`, `daemon_source_path`, `daemon_server_url`, `daemon_team_or_user`, `daemon_queue_db_path` | `2` |
| Orphan daemon owner record present | `2` |
| Legacy queue contains rows belonging to current scope (`legacy_rows_for_scope > 0`) | `2` |
| `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set but no authenticated identity available | `2` |

Multiple conditions remain `2` (no mapping per condition); the body of the output names every failing field/category.

## Default (human-readable) printed fields

Every invocation of `sync status --check`, regardless of exit code, MUST print exactly these fields, in this order, with these labels:

```
Identity boundary:
  Foreground:
    Package version : <foreground.package_version>
    Executable path : <foreground.executable_path>
    Source path     : <foreground.source_path>
    Server URL      : <foreground.server_url or "<unset>">
    Team/User       : <foreground.team_or_user or "<unset>">
    Queue DB path   : <foreground.queue_db_path>

  Daemon owner record:
    Status          : <"present" | "absent" | "orphan">
    PID             : <record.pid or "<absent>">
    Port            : <record.port or "<absent>">
    Package version : <record.package_version or "<absent>">
    Executable path : <record.executable_path or "<absent>">
    Source path     : <record.source_path or "<absent>">
    Server URL      : <record.server_url or "<absent>">
    Team/User       : <record.team_or_user or "<absent>">
    Queue DB path   : <record.queue_db_path or "<absent>">

  Active queue:
    Path            : <foreground.queue_db_path>
    Event count     : <N>
    Body upload cnt : <M>

  Legacy queue:
    Path            : <legacy_queue_db_path>
    Event count     : <K>
    Body upload cnt : <L>
    Rows in scope   : <legacy_rows_for_scope>

  Mismatches      : <0..6>
  Orphan records  : <0..N>
```

When exit code is `2`, a "Mismatches" subsection lists each failing field with foreground and daemon values plus a one-line remediation hint per the preflight contract.

## `--json` mode

When the command is invoked with `--check --json`, the human-readable block is suppressed and the output is a single JSON object on stdout:

```json
{
  "ok": false,
  "exit_code": 2,
  "foreground": {
    "package_version": "3.2.0rc11",
    "executable_path": "/usr/local/bin/uv",
    "source_path": "/Users/.../site-packages/specify_cli",
    "server_url": "https://spec-kitty-dev.fly.dev",
    "team_or_user": "team:abc123",
    "queue_db_path": "/Users/.../.spec-kitty/scopes/team-abc123/queue.db",
    "pid": 12345
  },
  "daemon_owner_record": {
    "status": "present",
    "pid": 67890,
    "port": 8765,
    "package_version": "3.2.0rc10",
    "executable_path": "/usr/local/bin/uv",
    "source_path": "/Users/.../site-packages/specify_cli",
    "server_url": "https://spec-kitty-dev.fly.dev",
    "team_or_user": "team:abc123",
    "queue_db_path": "/Users/.../.spec-kitty/scopes/team-abc123/queue.db"
  },
  "active_queue": {
    "path": "/Users/.../.spec-kitty/scopes/team-abc123/queue.db",
    "event_count": 0,
    "body_upload_count": 0
  },
  "legacy_queue": {
    "path": "/Users/.../.spec-kitty/queue.db",
    "event_count": 3,
    "body_upload_count": 1,
    "rows_in_scope": 4
  },
  "mismatches": [
    {
      "field": "daemon_package_version",
      "foreground_value": "3.2.0rc11",
      "daemon_value": "3.2.0rc10",
      "remediation_hint": "Run `spec-kitty doctor restart-daemon` ..."
    }
  ],
  "orphan_records": []
}
```

Field names match the dataclass field names in `data-model.md` and `contracts/sync-boundary-preflight.md`.

## Test surface

Tests SHALL cover:

- Coherent host → exit 0 and prints all required fields (none absent).
- Daemon version drift → exit 2 and prints the `daemon_package_version` mismatch with foreground+daemon values.
- Each remaining canonical mismatch field independently → exit 2 with that field named.
- Orphan owner record → exit 2 with orphan count ≥ 1 and `status="orphan"` (or `"present"` plus orphan list per implementation).
- Legacy queue rows in scope → exit 2 with `legacy_queue.rows_in_scope > 0`.
- `--check --json` produces a single JSON object on stdout with the documented shape.

Test files: `tests/sync/test_sync_status_boundary_check.py` (existing — extended).

## Backwards compatibility

- The current `sync status` (without `--check`) output is unchanged outside the identity-boundary subsection.
- Previously detected non-zero conditions remain non-zero; this contract only *adds* fields and refusal conditions.

## Event Journal Extension (#2124/#2131)

The `event-sync-retention-delivery-01KVYWRG` mission extends this contract
**purely additively** (WP11, plan concern IC-08). Every existing top-level field
documented above — `ok`, `exit_code`, `foreground`, `daemon_owner_record`,
`active_queue`, `legacy_queue`, `mismatches`, `orphan_records` — remains
available and **unrenamed** for old consumers. The extension only *adds* the
seven nested sections below; it removes and renames nothing (SC-010).

Assembly lives in `src/specify_cli/delivery/status_report.py`
(`build_status_report(...)`); the `sync status` CLI wiring stays thin and merges
these sections onto the existing payload (WP12).

Required new JSON sections (exact keys):

- `target_authority`: `configured_server_url`, `env_server_url`, `override_mode`,
  `resolved_server_url`, `user_id`, `team_slug`, `derived_queue_scope`,
  `queue_db_path`, `active_queue_scope_status`. Makes env/config target
  disagreement observable and non-silent **before** any hosted network call.
- `event_journal`: `retained_event_count`, `archived_event_count`,
  `oldest_retained_event_at` (`null` when empty), `journal_size_bytes`,
  `gc_suggested` (bool), `gc_suggestion` (object with `reason` /
  `retained_event_count` / `journal_size_bytes`, or `null`).
- `delivery_targets`: `current` (the resolved active target's identity — URL +
  scope; `target_id` is `null` when that target is not yet registered) and
  `previous` (a list of every other known target that has received deliveries,
  each with its identity and a `delivered_count`).
- `delivery_ledger`: `delivered_current_target`, `delivered_previous_target`,
  `pending`, `rejected`, `transient` — per-status counts.
- `terminal_failures`: `count` plus an `events` list (`event_id`, `target_id`,
  `last_error`) of selector-excluded permanent failures (FR-015) that remain
  inspectable and are never deleted.
- `migration_conflicts`: `count`, `cleanup_blocked` (bool), and a `conflicts`
  list of unresolved divergent-duplicate `event_id`s; while present, source-DB
  cleanup is blocked (FR-018).
- `body_upload_compatibility`: `body_upload_queue_count` and
  `body_upload_failure_log_count`, owned by `sync/queue.py` and labeled to keep
  them **explicitly separate** from event-journal/ledger counts (C-006/NFR-006).
  No `event_journal` or `delivery_ledger` field is ever sourced from the
  body-upload tables.

**Distinct counts (SC-003, US4):** the retained event count, current-target
delivered count, previous-target delivered count, terminal-failed count,
body-upload count, and the oldest retained timestamp are each a separate value in
its semantically-correct section above — none is a derived alias of another. For
example, 124 events retained and delivered only to a *previous* target read as
`event_journal.retained_event_count = 124`,
`delivery_ledger.delivered_previous_target = 124`,
`delivery_ledger.delivered_current_target = 0`, with a populated
`event_journal.oldest_retained_event_at`.

**Bounded-growth visibility (NFR-004):** `event_journal.journal_size_bytes` is
surfaced on *every* invocation so "explicit-only retention" never degrades into
silent unbounded growth. The `gc_suggested` flag is gated: it is `true` **only**
when the retained payloads are large (at or above a defined threshold, default
50 MiB) **and** every retained event is fully delivered to all known targets.
With zero known targets the suggestion never fires.

**Retention (FR-010, contract §3):** `sync gc` / `sync archive` (logic in
`src/specify_cli/delivery/retention.py`) are the only destructive payload
operations and run **only** under explicit operator action — never as a side
effect of `sync now`. Archive stamps the journal's archived marker
(non-destructive); GC purges payload bytes only for events already delivered
somewhere, preserving undelivered durability. Both **preserve the
`delivery_ledger` history and provenance**.
