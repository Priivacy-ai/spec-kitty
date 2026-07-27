# Feature Specification: CLI SaaS Fan-Out Preserves Local Time

**Feature Branch**: `cli-saas-fanout-preserves-local-at-01KRNS87`
**Created**: 2026-05-15
**Status**: Draft
**Input**: GitHub issue Priivacy-ai/spec-kitty#1064.

## Background

`StatusEvent.at` already carries a canonical local lane-transition time. The CLI's `_saas_fan_out()` and `emit_wp_status_changed()` ignore it and let the sync emitter mint `datetime.now(UTC).isoformat()` in `_emit()`. That lands in the canonical envelope's `timestamp` which after #188 becomes `Event.occurred_at` on SaaS — so non-historical events get sync-emission time as canonical occurrence time.

This mission threads `StatusEvent.at` through `_saas_fan_out` → `fire_saas_fanout` → `emit_wp_status_changed` (convenience) → `Emitter.emit_wp_status_changed` → `Emitter._emit`. `_emit` accepts an optional `occurred_at`; when provided it is used, otherwise the current `datetime.now(UTC)` behavior is preserved (for genuinely new events at emission time).

## User Scenarios

### US-1 — Local `at` survives SaaS fan-out (P1)
A `StatusEvent` with `at = "2026-01-01T00:00:00+00:00"` triggers `_saas_fan_out`; the resulting envelope's `timestamp` equals `"2026-01-01T00:00:00+00:00"`.

### US-2 — Sync emitter accepts explicit occurrence timestamp (P1)
`Emitter._emit(..., occurred_at="2026-01-01T00:00:00+00:00")` produces an envelope whose `timestamp` is that value.

### US-3 — Truly new events still get fresh timestamps (P1)
Emit paths that don't pass `occurred_at` (dossier, build heartbeat, etc.) keep current behavior.

## Requirements

### Functional

| ID | Requirement |
|----|-------------|
| FR-001 | `Emitter._emit` accepts optional `occurred_at: str \| None = None`; when provided, envelope `timestamp` = that value; when omitted, mint fresh `datetime.now(UTC).isoformat()` as today. |
| FR-002 | `Emitter.emit_wp_status_changed` accepts optional `occurred_at` and forwards to `_emit`. |
| FR-003 | Module-level `emit_wp_status_changed` in `specify_cli/sync/events.py` accepts `occurred_at` and forwards. |
| FR-004 | `_saas_fan_out` in `specify_cli/status/emit.py` MUST include `event.at` as `occurred_at` in the kwargs passed to `fire_saas_fanout`. |
| FR-005 | `_saas_fanout_handler` in `specify_cli/sync/__init__.py` MUST forward `occurred_at` into `emit_wp_status_changed`. |
| FR-006 | Tests cover US-1, US-2, US-3. |

### Non-Functional

| ID | Threshold |
|----|-----------|
| NFR-001 | <3s wall-time increase. |
| NFR-002 | Ruff clean. |

### Constraints

| ID | Constraint |
|----|------------|
| C-001 | Wire format unchanged. |
| C-002 | Existing callers continue to work (`occurred_at` everywhere optional). |
| C-003 | No new runtime deps. |

## Success Criteria

- **SC-001**: StatusEvent.at survives end-to-end through fan-out to SaaS envelope `timestamp`.
- **SC-002**: Existing CLI tests still pass.
- **SC-003**: Ruff clean.
