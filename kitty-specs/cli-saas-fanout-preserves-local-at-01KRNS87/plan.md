# Implementation Plan: CLI SaaS Fan-Out Preserves Local Time

**Branch**: main | **Date**: 2026-05-15

## Summary

Thread the local `StatusEvent.at` through the SaaS fan-out by adding an optional `occurred_at` parameter at each layer (`_saas_fan_out` → `fire_saas_fanout` → `_saas_fanout_handler` → `emit_wp_status_changed` (module) → `Emitter.emit_wp_status_changed` → `Emitter._emit`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing (Pydantic event models, ULID, pytest)
**Storage**: N/A (CLI library)
**Testing**: pytest (existing `tests/specify_cli/sync/`, `tests/specify_cli/status/`)
**Target Platform**: spec-kitty CLI library
**Project Type**: single (Python package)
**Performance Goals**: <3s new-test wall-time increase
**Constraints**: Wire unchanged (C-001); all callers continue to work (C-002); no new deps (C-003)
**Scale/Scope**: 4 files touched + 1 test module. ~80 net lines.

## Charter Check

Follows the repo's CLAUDE.md conventions; pure additive parameter passthrough. **Pass**.

## Project Structure

```
src/specify_cli/status/emit.py            # _saas_fan_out: pass occurred_at=event.at
src/specify_cli/sync/__init__.py          # _saas_fanout_handler: forward occurred_at
src/specify_cli/sync/events.py            # module emit_wp_status_changed: accept + forward
src/specify_cli/sync/emitter.py           # Emitter.emit_wp_status_changed + _emit: accept + use
tests/specify_cli/sync/test_emitter_occurrence_time.py   # new
```
