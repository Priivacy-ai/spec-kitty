---
work_package_id: WP01
title: Row-level legacy to scoped queue migration
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-002
- C-001
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mvp-sync-boundary-cli-01KRVCQS
base_commit: e07accf7de330f47720ddc2c9f09947c3d3711d7
created_at: '2026-05-17T16:46:14.473851+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Queue
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "58351"
history:
- timestamp: '2026-05-17T16:42:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/sync/queue.py
- tests/sync/test_queue_row_level_migration.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 — Row-level legacy→scoped queue migration

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Replace `_migrate_legacy_queue_to_scope` in `src/specify_cli/sync/queue.py` with an idempotent row-level merge per [data-model.md](../data-model.md). Remove the whole-DB emptiness guard. Migrate event-queue rows, body upload rows, and (if present) body upload failure/history rows by stable key. Delete legacy rows only after they exist in the scoped DB.

Done means:
- `_migrate_legacy_queue_to_scope` performs row-level merge over `queue`, `body_upload_queue`, and any failure/history table that exists. Stable key per table; conflict-resolution via `INSERT OR IGNORE`. Legacy rows are deleted in a second pass after verifying the row exists in scoped.
- The function is callable with no scope arg; it discovers tables and migrates everything that fits.
- Idempotent: a second run produces zero new migrations.
- Per-row info log: `migrated row legacy→scoped: table=<t> key=<stable-key>` (no payload contents).
- No regression in any currently-passing `tests/sync/` test.
- New tests at `tests/sync/test_queue_row_level_migration.py` cover:
  - Empty scoped + legacy with N body_upload rows → all N migrate; legacy is empty after.
  - Scoped has unrelated rows + legacy has mission rows → mission rows still migrate; existing scoped rows untouched.
  - Re-run after a successful migration → 0 new migrations; legacy still empty.
  - Authenticated foreground can detect legacy rows that belong to the active scope (helper `detect_legacy_rows_for_scope(scope) -> dict[str, int]` returning per-table counts, used by WP03 status check).
- `mypy --strict src/specify_cli/sync/queue.py` passes.

## Context & Constraints

- Spec: `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/spec.md` (FR-001..FR-004, FR-013 partial, C-001, C-004).
- Data model: `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/data-model.md` (row-key strategy, pseudocode).
- Current code: `src/specify_cli/sync/queue.py` lines ~527-543 (the function to rewrite). Lines 661-668 `ensure_body_queue_schema` for schema reference. Lines 491-512 `_table_row_count` and helpers reusable.
- Constraints: C-001 (no raw SQL surgery as the product fix — the fix IS code), C-004 (no new top-level deps).
- Test isolation: NFR-001 — every test MUST use tmp HOME or `SPEC_KITTY_HOME` env, never the operator's live `~/.spec-kitty`.

## Subtasks

### T001 — Enumerate live schema
- Read the current schemas: open `src/specify_cli/sync/queue.py` (queue table schema), `src/specify_cli/sync/body_queue.py` (body upload schema). Identify the stable key for each table that needs migration. Document the chosen keys as a module-level constant `_MIGRATION_TABLES` per the pseudocode in data-model.md.

### T002 — Rewrite `_migrate_legacy_queue_to_scope`
- Replace the function body with row-level merge:
  - Open src + dst SQLite connections.
  - For each table in `_MIGRATION_TABLES`: if table exists in src, fetch rows; insert into dst with INSERT OR IGNORE; for each row that landed (either newly inserted or already present by key), delete the row from src.
  - Return total migrated row count for tests/diagnostics.
- Drop the `_queue_db_has_content(scoped_db_path)` early-return.
- Preserve the existing function signature (no new args) so all callers keep working.

### T003 — Structured log per row
- Use `logging.getLogger("specify_cli.sync.queue")` (or existing module logger) to emit one `info` line per migrated row: `migrated row legacy→scoped: table=<t> key=<stable-key>`. Do NOT log payload contents.

### T004 — Tests
- Create `tests/sync/test_queue_row_level_migration.py`:
  - Use `pytest.fixture(tmp_path)` and `monkeypatch.setenv("HOME", str(tmp_path))` to isolate.
  - Build a tiny legacy DB by hand (SQLite INSERTs matching the existing schema). Build a tiny scoped DB. Call `_migrate_legacy_queue_to_scope(scoped_db_path)`. Assert dst row counts; assert src is empty.
  - Test: scoped has rows for other scopes (unrelated) → migration still copies all from legacy.
  - Test: rerun migration → returns 0; idempotent.
  - Test: helper `detect_legacy_rows_for_scope(scope)` returns per-table counts. (Add the helper in this WP or as a new pure function.)

### T005 — Validation
- `uv run pytest tests/sync` — green.
- `uv run mypy --strict src/specify_cli/sync/queue.py` — green.

## Branch Strategy

Planning base: `main`. Final merge target: `main`. Worktree allocated per lane in `lanes.json`.

## Definition of Done

- [ ] `_MIGRATION_TABLES` constant with stable keys
- [ ] `_migrate_legacy_queue_to_scope` rewritten per data-model
- [ ] `detect_legacy_rows_for_scope(scope)` helper added and exported
- [ ] Per-row info log emitted
- [ ] All four scenarios in T004 pass
- [ ] No regression in existing `tests/sync/`
- [ ] `mypy --strict src/specify_cli/sync/queue.py` passes
- [ ] Owned files only: `src/specify_cli/sync/queue.py`, `tests/sync/test_queue_row_level_migration.py`

## Risks

- **Schema drift**: stable keys are inferred from current schema. Mitigated by T001 explicit enumeration and clear comment listing the chosen keys.
- **Crash mid-migration**: delete-after-insert ordering ensures the worst case is duplicate rows in scoped (which INSERT OR IGNORE handles on retry).
- **Test isolation**: NFR-001 — never touch `~/.spec-kitty`.

## Reviewer Guidance

- `git diff` should show changes only to `src/specify_cli/sync/queue.py` and the new test file.
- Confirm: no whole-DB emptiness guard remains.
- Confirm: INSERT OR IGNORE used; delete only after row exists in dst.
- Run the new test file in isolation: < 5s.
- Confirm no new deps added.

## Activity Log

- 2026-05-17T16:46:15Z – claude:opus-4-7:python-pedro:implementer – shell_pid=54665 – Assigned agent via action command
- 2026-05-17T16:54:45Z – claude:opus-4-7:python-pedro:implementer – shell_pid=54665 – Ready for review: row-level migration + helper + tests
- 2026-05-17T16:55:13Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=58351 – Started review via action command
