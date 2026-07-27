# Phase 1 Data Model: Unblock Sync Identity-Boundary Canary

**Mission**: `unblock-sync-identity-boundary-canary-01KRZJ07`
**Date**: 2026-05-19

## Scope

This mission introduces no new persisted entities. The audit and sync fixes either read existing on-disk shapes or render existing in-memory state. The "data-model" surface consists of:

1. The shape contract for rows in `status.events.jsonl` (already exists; we are *naming* the lifecycle row family explicitly in the registry).
2. The `DaemonOwnerRecord` shape (already exists; consumed unchanged by `doctor restart-daemon`).
3. The `sync status --check` boundary-row classification (which rows are "path fields" vs "tabular identity fields").

## E1 — `status.events.jsonl` row families (existing; named here)

Each line of `status.events.jsonl` is one JSON object. Two row families coexist; the audit must distinguish them.

### Family A — Status-transition row

```json
{
  "actor": "claude",
  "at": "2026-02-08T12:00:00+00:00",
  "event_id": "01HXYZ...",
  "feature_slug": "<mission-slug>",
  "from_lane": "planned",
  "to_lane": "claimed",
  "wp_id": "WP01",
  "execution_mode": "worktree",
  "force": false,
  "reason": null,
  "review_ref": null,
  "evidence": null
}
```

**Discriminator**: presence of `from_lane` AND `to_lane`.
**Owner module**: `src/specify_cli/status/store.py` (write), `src/specify_cli/status/reducer.py` (read).
**FORBIDDEN_KEYS rule applies**: `event_type`, `event_name` must not appear.

### Family B — Mission-lifecycle row

```json
{
  "aggregate_id": "01KRZJ079...",
  "aggregate_type": "Mission",
  "event_id": "01KRZJ09...",
  "event_type": "MissionCreated",
  "payload": {"...": "..."},
  "occurred_at": "2026-05-19T07:25:29+00:00"
}
```

**Discriminator**: `aggregate_type == "Mission"` AND presence of `event_type`.
**Owner modules**: `src/specify_cli/status/lifecycle_events.py`, `src/specify_cli/invocation/propagator.py`, `src/specify_cli/dossier/`, `src/specify_cli/next/_internal_runtime/engine.py`, `src/specify_cli/retrospective/events.py`.
**FORBIDDEN_KEYS rule does NOT apply** to `event_type` / `event_name` on this family.

### Invariant

A row that is both a status-transition row AND a lifecycle row is malformed. The audit MUST still flag a row that carries `from_lane` / `to_lane` together with `event_type` (it does not match Family B because Family B does not carry `from_lane` / `to_lane`).

### Validation

- Family classifier is implemented as a function in `src/specify_cli/audit/shape_registry.py` named for clarity (e.g. `is_mission_lifecycle_row(row: Mapping[str, Any]) -> bool`).
- Detector consults this classifier before applying `FORBIDDEN_KEYS`.

## E2 — `DaemonOwnerRecord` (existing; consumed unchanged)

Fields relevant to `doctor restart-daemon`:

| Field | Type | Usage |
|-------|------|-------|
| `package_version` | str | Reported in boundary mismatch; identifies the foreground at write time. |
| `executable_path` | Path | Path to the `spec-kitty` binary that launched the daemon; respawn target. |
| `source_path` | Path | The `specify_cli` source tree; respawn target. |
| `server_url` | str | URL of the SaaS endpoint the daemon is bound to. |
| `queue_db_path` | Path | The SQLite queue file the daemon owns. |
| (process metadata) | — | pid, socket location, used for graceful stop. |

`doctor restart-daemon` reads this record, drives a stop using the existing stop primitive, then relaunches using the existing daemon launcher with the same `executable_path` / `source_path`.

## E3 — `sync status --check` boundary row classification

Each row rendered in the boundary view is one of:

| Row kind | Examples | Renderer in WP02 |
|----------|----------|------------------|
| Identity scalar | package version string, server URL, foreground/daemon parity flag | Rich `Table` (preserves tabular layout). |
| Canonical file path | queue DB path, executable path, source path | Plain `Console.print(f"{label}: {value}")` outside the Table. |

The split is determined by row kind at render time, not by string-length heuristics. Adding a new path-bearing row in the future picks "outside the Table" by virtue of being a path-kind row.

## No schemas to migrate

There are no on-disk schema migrations. All changes are additive (registry entry, new subcommand, rendering refactor) and operate on pre-existing data shapes.
