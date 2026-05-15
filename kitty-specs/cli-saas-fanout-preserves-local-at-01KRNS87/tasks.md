---
description: "Work packages for cli-saas-fanout-preserves-local-at-01KRNS87"
---

# Work Packages

## WP01: Thread occurred_at through SaaS fan-out (P0)

**Goal**: StatusEvent.at survives end-to-end to the SaaS envelope.

### Subtasks
- [x] T001 Add occurred_at param to Emitter._emit (use it for envelope timestamp when set, else mint fresh) (WP01)
- [x] T002 Add occurred_at param to Emitter.emit_wp_status_changed and forward to _emit (WP01)
- [x] T003 Add occurred_at param to module emit_wp_status_changed in sync/events.py (WP01)
- [x] T004 Update _saas_fanout_handler in sync/__init__.py to forward occurred_at (WP01)
- [x] T005 Update _saas_fan_out in status/emit.py to pass event.at as occurred_at (WP01)
- [x] T006 Add tests/specify_cli/sync/test_emitter_occurrence_time.py (WP01)
- [x] T007 Run pytest (targeted), ruff (WP01)

**Prompt**: `tasks/WP01-thread-occurred-at.md`
