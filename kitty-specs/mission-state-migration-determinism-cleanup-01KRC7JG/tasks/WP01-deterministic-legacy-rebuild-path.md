---
work_package_id: WP01
title: Deterministic Legacy Rebuild Path
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Determinism
assignee: ''
agent: ''
history:
- timestamp: '2026-05-11T19:20:00Z'
  agent: system
  action: Prompt generated for Mission 8 (migration determinism cleanup)
authoritative_surface: src/specify_cli/migration/rebuild_state.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/rebuild_state.py
- tests/specify_cli/migration/test_rebuild_state.py
tags: []
---

# Work Package Prompt: WP01 — Deterministic Legacy Rebuild Path

## Why this WP exists

`src/specify_cli/migration/rebuild_state.py` is reachable from public migration entry points
(`migration/runner.py:420`, `migration/normalize_mission_lifecycle.py:20`, the package `__init__`
re-exports) but still uses a random ULID factory and `datetime.now(UTC)` for synthetic events.
That means two runs against the same legacy fixture produce different `event_id`s and slightly
different `at` timestamps — so a migration commit cannot be reproduced byte-for-byte from this
path. This WP makes the legacy path deterministic and warns callers that the canonical path is
`mission_state.repair_repo`.

## Files touched

- `src/specify_cli/migration/rebuild_state.py`
- `tests/specify_cli/migration/test_rebuild_state.py`

## Tasks

- **T001** — Add a module-private `_deterministic_id(*parts: str) -> str` helper that sha256s the
  joined parts with a stable separator (`"|"`) and renders the digest as a 26-char Crockford ULID
  (use the same alphabet as `mission_state._CROCKFORD`).
- **T002** — Replace every `_generate_ulid()` call in `rebuild_state.py` with a deterministic
  invocation seeded from stable inputs: for synthetic chain events use `(feature_slug, wp_code,
  from_lane, to_lane, "chain", str(index))`; for the corrective synthetic event use
  `(feature_slug, wp_code, log_lane or "", auth_lane, "corrective")`. Keep the
  `_generate_ulid()` shim only if needed for external compatibility — otherwise delete it.
- **T003** — Replace `migration_ts = datetime.now(UTC).isoformat()` with a module-level constant
  `_MIGRATION_EPOCH = "2026-01-01T00:00:00+00:00"` and pass it down. Keep the existing offset
  arithmetic in `_make_migration_timestamp` so synthetic chains stay strictly ordered. The
  corrective event uses `_MIGRATION_EPOCH` directly.
- **T004** — At module import time, emit
  `warnings.warn("specify_cli.migration.rebuild_state is deprecated; use specify_cli.migration.mission_state.repair_repo for canonical, deterministic mission-state repair.", DeprecationWarning, stacklevel=2)`.
  Use `warnings.warn` (not `DeprecationWarning` raised). Do not break existing tests that import
  this module.
- **T005** — Add a determinism test in `tests/specify_cli/migration/test_rebuild_state.py`:
  build an in-memory legacy fixture (frontmatter lanes + status.json), call `rebuild_event_log`
  twice in two distinct `feature_dir` copies, and assert the two resulting
  `status.events.jsonl` files are byte-identical. Also assert the `DeprecationWarning` fires on
  import using `pytest.warns(DeprecationWarning)` with `importlib.reload`.

## Acceptance

- All existing tests in `tests/specify_cli/migration/test_rebuild_state.py` still pass.
- New determinism test passes.
- A `DeprecationWarning` is emitted on import (verified by the new test).
- No new external dependencies introduced.

## Boundaries (do not touch)

- Do not delete `rebuild_state.py` — only deprecate.
- Do not modify `mission_state.py` or its tests in this WP.
- Do not change public re-exports in `migration/__init__.py`.
