# Phase 1 Data Model: Safe Sync Daemon Orphan Cleanup

**Mission**: `sync-daemon-orphan-cleanup-01KWC2A3`

These are in-process domain objects and on-wire/structured payloads — there is no relational schema. Field names are normative for the contracts in `contracts/`.

## Entity: DaemonIdentityRecord

The per-candidate identity produced by the scan for **each inspected listener** in the sync range. Satisfies **FR-001**.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `daemon_family` | `"sync"` | constant for this engine | DD-02; hard family tag (C-001/C-002) |
| `pid` | `int \| None` | listener owner via `psutil`/`lsof` | `None` ⇒ `missing_pid` skip reason |
| `port` | `int` | range scan `[9400,9450)` | in-range invariant (NFR-001) |
| `protocol_version` | `int \| None` | `/api/health` | `DAEMON_PROTOCOL_VERSION` when responsive |
| `package_version` | `str \| None` | `/api/health` | e.g. `"3.2.2"`; mismatch ⇒ stale evidence (FR-008) |
| `singleton_scope_id` | `str \| None` | cmdline daemon-root marker | resolved `_daemon_scope_root()`; the **primary kill authority** |
| `daemon_root` | `str \| None` | resolved runtime root | per-daemon scope path |
| `queue_db_path` | `str \| None` | owner record | reporting only |
| `auth_scope` | `str \| None` | owner record | reporting only |
| `server_url` | `str \| None` | owner record | reporting only |
| `owner_present` | `bool` | owner record existed | reporting only — **not** kill authority (FR-003) |
| `identity_source` | `enum` | how identity was proven | `health_self_report` \| `cmdline_marker` \| `owner_record` \| `none` |
| `executable_summary` | `str \| None` | `_process_executable_scopes` | exe/argv0/exec-marker digest |
| `spawn_shape_ok` | `bool` | `_cmdline_has_daemon_spawn_signature` | production spawn-shape present |
| `self_report_matches_listener` | `bool` | health pid/port vs actual | required for `safe_auto` (D-01) |
| `is_recorded_singleton` | `bool` | state file pid/port | live daemon ⇒ never cleaned |
| `cleanup_class` | `CleanupClass` | classifier verdict | see below |
| `skip_reason` | `SkipReason \| None` | classifier | present when not `safe_auto` |

### Invariants
- `port` ∈ `[9400, 9450)` for every record the sync engine emits (out-of-range ⇒ never scanned/recorded).
- `cleanup_class == safe_auto` ⇒ `is_recorded_singleton is False` **and** `singleton_scope_id` matches the foreground scope **and** `self_report_matches_listener is True` **and** `spawn_shape_ok is True`.
- `skip_reason is None` ⇔ `cleanup_class == safe_auto`.
- `owner_present` never influences `cleanup_class` (FR-003).

## Value object: CleanupClass (enum)

| Value | Meaning | Acted on by |
|-------|---------|-------------|
| `safe_auto` | Provably-ours, same-scope, responsive, not the singleton | startup auto-clean **and** `--reset` |
| `operator_required` | Looks like SK sync but ambiguous (pre-marker, cross-root, missing pid, pid/port mismatch, or wedged) | `--reset` **with `--force`/confirmation** (D-02); never startup |
| `never_touch` | Not identifiable as SK sync / dashboard / third-party / out-of-range | nothing, ever (C-004) |

## Value object: SkipReason (enum)

`is_recorded_singleton` · `pre_marker` (no daemon-root marker) · `cross_root` (marker ≠ foreground scope) · `missing_pid` · `pid_port_mismatch` · `unresponsive` (wedged, D-01) · `not_spec_kitty` · `out_of_range` · `dashboard_family` · `third_party`.

## Classification decision table (normative)

Evaluated top-to-bottom; first match wins.

| # | Condition | `cleanup_class` | `skip_reason` |
|---|-----------|-----------------|---------------|
| 1 | port ∉ `[9400,9450)` | `never_touch` | `out_of_range` |
| 2 | not identifiable as SK sync (no spawn-signature **and** no SK self-report) | `never_touch` | `not_spec_kitty` / `third_party` |
| 3 | `is_recorded_singleton` | (excluded from cleanup; reported as live) | `is_recorded_singleton` |
| 4 | `pid is None` | `operator_required` | `missing_pid` |
| 5 | no daemon-root marker | `operator_required` | `pre_marker` |
| 6 | marker ≠ foreground scope | `operator_required` | `cross_root` |
| 7 | no live health self-report (wedged) — **D-01** | `operator_required` | `unresponsive` |
| 8 | health pid/port ≠ listener | `operator_required` | `pid_port_mismatch` |
| 9 | else (marker==scope, responsive, spawn-shape ok, not singleton; version/exe mismatch **allowed** as stale evidence — **FR-008**) | `safe_auto` | — |

> Note on **FR-008**: a non-matching `package_version`/`executable_summary` does **not** appear as a skip condition. Once rows 1–8 pass, version/executable mismatch is treated as stale-version *evidence* and the daemon is `safe_auto`.

## Entity: ResetResult

Structured outcome of `auth doctor --reset`. Satisfies **FR-005**.

| Field | Type | Per-entry fields |
|-------|------|------------------|
| `swept` | `list` | `pid`, `port`, `package_version`, `protocol_version`, `cleanup_path` (`http_shutdown`\|`terminate`\|`kill`), `reason` |
| `skipped` | `list` | `pid` (nullable), `port`, `skip_reason`, `cleanup_class` |
| `failed` | `list` | `pid` (nullable), `port`, `failure_reason` |

- `operator_required` entries appear in `skipped` (with `cleanup_class=operator_required`) unless `--force`/confirmation was given, in which case successful ones move to `swept` and survivors to `failed`.
- `never_touch` candidates are never listed in `swept`/`failed`; they may appear in the read-only `auth doctor` scan view but are out of `--reset` scope.

## State transitions: sync daemon self-retirement (FR-010/FR-011)

```
        spawn
          │
          ▼
   ┌─────────────┐  becomes superseded (state-file pid/port ≠ self)
   │  ACTIVE     │──────────────┐
   │ (singleton) │              ▼
   └─────────────┘        ┌───────────────┐  no sync work in flight
          │ idle ≥        │  SUPERSEDED   │──────────────────────► RETIRED (exit)
          │ SYNC_DAEMON_  └───────────────┘
          │ IDLE_RETIRE-
          │ MENT_SECONDS
          ▼ (no auth / no work)
       RETIRED (exit)
```

- **SUPERSEDED → RETIRED** is prompt (no full idle wait) once `sync.is_running` is false and the queue is drained.
- **ACTIVE → RETIRED** (general idle) only after `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS` of no auth/no work; constant is patchable in tests (FR-011).
- A daemon with **active sync work in flight never retires** (FR-010 guard).

## Externally visible surfaces (no new network events)

This mission changes **local** CLI output and loopback `/api/health` shape only — no SaaS/protocol changes (C-007). The `/api/health` payload gains `daemon_family` (and the existing redacted `owner` block is unchanged); see `contracts/health-payload.md`.
