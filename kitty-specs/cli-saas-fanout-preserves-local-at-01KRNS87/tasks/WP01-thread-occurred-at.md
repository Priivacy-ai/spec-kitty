---
work_package_id: WP01
title: Thread occurred_at through SaaS fan-out
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-saas-fanout-preserves-local-at-01KRNS87
base_commit: 7ed001bb8c43d2b1140811e03d8aa35ecee0ffdd
created_at: '2026-05-15T12:22:16.583833+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1
assignee: ''
agent: "claude:opus-4-7:reviewer:reviewer"
shell_pid: "62952"
history:
- timestamp: '2026-05-15T12:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/sync/__init__.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/emitter.py
- tests/specify_cli/sync/test_emitter_occurrence_time.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# WP01: Thread occurred_at through SaaS fan-out

## Objectives

1. **T001 `Emitter._emit`** (`src/specify_cli/sync/emitter.py:1421`): add `occurred_at: str | None = None`. In the envelope dict, set `"timestamp": occurred_at if occurred_at is not None else datetime.now(UTC).isoformat()`.
2. **T002 `Emitter.emit_wp_status_changed`** (same file, line ~766): add `occurred_at: str | None = None` and pass it to `self._emit(..., occurred_at=occurred_at)`.
3. **T003 module `emit_wp_status_changed`** (`src/specify_cli/sync/events.py:202`): add `occurred_at: str | None = None` and forward to `get_emitter().emit_wp_status_changed(..., occurred_at=occurred_at)`.
4. **T004 `_saas_fanout_handler`** (`src/specify_cli/sync/__init__.py`, the function defined inside the `with _contextlib.suppress(ImportError)` block): leave it as `def _saas_fanout_handler(**kwargs)`; it already passes kwargs through. Only verify it does NOT filter out the new `occurred_at` kwarg.
5. **T005 `_saas_fan_out`** (`src/specify_cli/status/emit.py:626`): in the `fire_saas_fanout(...)` call, add `occurred_at=event.at`. (`StatusEvent.at` is already ISO-8601 UTC.)
6. **T006 Tests**: `tests/specify_cli/sync/test_emitter_occurrence_time.py`. Cover:
   - `Emitter._emit(..., occurred_at=ISO)` → envelope `timestamp == ISO`.
   - `Emitter._emit(...)` (no occurred_at) → envelope `timestamp` parses to a recent UTC time (delta < 5s from now).
   - `Emitter.emit_wp_status_changed(..., occurred_at=ISO)` → envelope `timestamp == ISO`.
   - Module `emit_wp_status_changed(occurred_at=ISO)` → envelope `timestamp == ISO`.
   - End-to-end: build a `StatusEvent` with `at=ISO`, call `_saas_fan_out(event, mission_slug, repo_root)` with a registered fake handler, assert the handler's received `occurred_at` kwarg equals ISO.
7. **T007 Quality gates**: `pytest tests/specify_cli/sync/test_emitter_occurrence_time.py tests/specify_cli/sync/ tests/specify_cli/status/ -q` and `ruff check src/specify_cli/status/emit.py src/specify_cli/sync/__init__.py src/specify_cli/sync/events.py src/specify_cli/sync/emitter.py tests/specify_cli/sync/test_emitter_occurrence_time.py`.

## Constraints

- C-001: Do not change envelope shape. The field stays `timestamp` at top level.
- C-002: `occurred_at` is optional everywhere. No existing caller breaks.

## Review Guidance

- [ ] All 5 layers accept the optional param.
- [ ] `_emit` uses `occurred_at` when set, else mints fresh `datetime.now(UTC).isoformat()`.
- [ ] `_saas_fan_out` passes `event.at` as `occurred_at`.
- [ ] New tests cover all 5 cases.
- [ ] No regressions in existing sync/status tests.
- [ ] Ruff clean.

## Activity Log
- 2026-05-15T12:30:00Z – system – lane=planned – Prompt created
- 2026-05-15T12:22:18Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=54513 – Assigned agent via action command
- 2026-05-15T12:35:39Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=54513 – All 7 subtasks done. 5 new tests + 2 existing mock assertions updated for the occurred_at kwarg. Sync + status tests: 80 passed in touched files. Pre-existing orphan_sweep and origin_integration failures are unrelated to this mission (verified on main).
- 2026-05-15T12:35:52Z – claude:opus-4-7:reviewer:reviewer – shell_pid=62952 – Started review via action command
- 2026-05-15T12:35:54Z – claude:opus-4-7:reviewer:reviewer – shell_pid=62952 – Review passed. 5 layers threaded; existing tests updated; no production behavior regression.
