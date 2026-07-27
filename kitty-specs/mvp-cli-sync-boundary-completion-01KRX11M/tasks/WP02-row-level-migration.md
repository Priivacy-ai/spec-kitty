---
work_package_id: WP02
title: 'Row-level queue migration: body uploads + idempotence'
dependencies: []
requirement_refs:
- FR-006
- FR-007
- NFR-001
- NFR-002
planning_base_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
merge_target_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/mvp-sync-boundary-cli-01KRVCQS. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/mvp-sync-boundary-cli-01KRVCQS unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "codex:gpt-5:reviewer-rita:reviewer"
shell_pid: "46404"
history:
- at: '2026-05-18T08:00:00Z'
  actor: planner
  note: Initial generation
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/queue.py
execution_mode: code_change
mission_id: 01KRX11MCY70M5NFBBHT4DQHJ2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
owned_files:
- src/specify_cli/sync/queue.py
- tests/sync/test_queue_row_level_migration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, run the `ad-hoc-profile-load` skill to adopt the assigned profile (`implementer-ivan`, role: `implementer`). The profile sets the identity, governance scope, and boundaries for the work in this WP.

## Objective

Close two parts of sub-issue #1090's strict acceptance: row-level migration from legacy → scoped queue must (a) work when the scoped DB already contains unrelated rows, and (b) cover `body_upload_queue` rows on the same terms as event rows. Also make the migration idempotent so retries are safe.

## Context

- The PR (#1107) already lands `_migrate_legacy_queue_to_scope()` (`src/specify_cli/sync/queue.py:706`) and `detect_legacy_rows_for_scope()` (`:744`).
- The existing migration handles `sync_events`-class rows but does not iterate `body_upload_queue` rows.
- A subtle existing bug: if the scoped DB is non-empty, body-upload rows can be stranded in legacy — this is exactly the strict acceptance the PR body promises to close.
- Retries should be safe: re-running migration on the same legacy + scoped pair must be a no-op (no duplicate rows, no errors).
- Existing tests live in `tests/sync/test_queue_row_level_migration.py` (lines 190, 231, 320 are the named anchors). Extend rather than replace.

## Branch strategy

- Planning/base branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107).
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Execution worktree: allocated per computed lane from `lanes.json` by `finalize-tasks`. This WP can run in parallel with WP01 (different files / different lanes).

## Subtasks

### T006 — Extend `_migrate_legacy_queue_to_scope` to walk both row classes

**Purpose**: Cover `body_upload_queue` migration in addition to `sync_events`-class rows.

**Steps**:

1. Read the current `_migrate_legacy_queue_to_scope(...)` implementation in `src/specify_cli/sync/queue.py:706`. Grep for the table name in the migration loop to confirm only event rows are iterated today.
2. Add a second migration loop (or parameterize the existing loop) for `body_upload_queue`. The iteration filter MUST use the same scope predicate as the event-row loop (the `(server_url, team_or_user)` tuple or equivalent the existing code already uses).
3. Preserve any existing transactional boundary so both row classes commit/rollback together.
4. Do not introduce a new schema or column.

**Files**:
- `src/specify_cli/sync/queue.py` (edited; +~30 lines, maybe -10 if refactored to a loop helper)

**Validation**:
- `mypy --strict src/specify_cli/sync/` exits 0.
- Adjacent tests still pass: `uv run pytest tests/sync/test_queue_row_level_migration.py -q`.

### T007 — Switch inserts to `INSERT OR IGNORE` keyed on primary keys

**Purpose**: Make retries idempotent so a partial migration that re-runs does not duplicate rows.

**Steps**:

1. For each migration insert (events and body uploads), change SQL to `INSERT OR IGNORE INTO <table>(...) VALUES (...)`. SQLite uses the table's primary key (or UNIQUE constraints) to decide.
2. Confirm the primary keys for `sync_events` and `body_upload_queue` are sufficient for idempotence (event_id and upload_id respectively). If the existing schema does not have a primary key or UNIQUE on the natural id, file an explicit `[NEEDS CLARIFICATION: <topic>]` marker AND open a decision via `spec-kitty agent decision open` — do not silently change schema. Otherwise proceed.
3. After the migration loop, verify-by-count: the scoped DB row count for the scope = old scoped count + legacy-in-scope count − duplicates already present. The test in T009 asserts this directly.

**Files**:
- `src/specify_cli/sync/queue.py` (edited; same area as T006, ~10 lines)

**Validation**:
- Running the migration twice in a row on the same legacy + scoped pair yields identical row counts the second time (T009 covers this).
- No schema change.

### T008 — Extend `detect_legacy_rows_for_scope` to return event/body-upload subtotals

**Purpose**: Surface the two subtotals to `sync status --check` (WP03 will consume them) and to the preflight (WP01 already imports).

**Steps**:

1. Read the current signature/return of `detect_legacy_rows_for_scope()` in `src/specify_cli/sync/queue.py:744`.
2. Extend the return to be a structured dataclass (or `TypedDict`) with two integer fields: `event_rows: int` and `body_upload_rows: int`. Convenience property/total: `total_rows = event_rows + body_upload_rows`.
3. If existing callers use the old return shape, provide a thin backwards-compat shim returning `total_rows` from the structured result, or update each caller (small number) to use the new shape directly. Prefer updating the small number of callers over a permanent shim.
4. Coordinate with WP01's `run_preflight`: it consumes `legacy_event_rows` and `legacy_body_upload_rows`. The contract in `contracts/sync-boundary-preflight.md` already names them.

**Files**:
- `src/specify_cli/sync/queue.py` (edited; +~25 lines)

**Validation**:
- Existing callers (search via grep) compile / type-check.
- Tests in T009 assert on both subtotals independently.

### T009 — Extend tests with body-upload, non-empty scoped, and idempotence cases

**Purpose**: Lock the new behavior with regression tests.

**Steps**:

1. Open `tests/sync/test_queue_row_level_migration.py`. Find the existing anchors (`:190`, `:231`, `:320`).
2. Add the following test cases (isolate the operator's home directory in a cross-platform way per C-008: prefer `monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)` over bare `monkeypatch.setenv("HOME", ...)` so the same fixture works on Windows `USERPROFILE` and POSIX `HOME`; use the existing fixture factories for legacy and scoped DBs):
   - `test_body_upload_migration_with_non_empty_scoped_db`: scoped DB has unrelated rows; legacy DB has 2 body-upload rows for the current scope and 1 for a different scope. After migration: scoped DB contains its prior rows plus the 2 current-scope body-upload rows; the other-scope body-upload row remains in legacy.
   - `test_migration_is_idempotent_on_retry`: run migration twice in a row on the same legacy + scoped pair. Assert second-run row counts are identical to first-run.
   - `test_detect_legacy_rows_for_scope_returns_subtotals`: stage 3 event rows + 2 body-upload rows for current scope; assert returned struct has `event_rows == 3`, `body_upload_rows == 2`, `total_rows == 5`.
   - `test_migration_atomic_failure_rolls_back_body_uploads_too`: simulate a failure between event-loop and body-upload-loop (or inside the body-upload loop). Assert neither set of rows lands in the scoped DB and legacy is unchanged. If atomicity is not currently guaranteed, escalate via a decision rather than silently relax.

**Files**:
- `tests/sync/test_queue_row_level_migration.py` (extended; +~130 lines)

**Validation**:
- `uv run pytest tests/sync/test_queue_row_level_migration.py -q` exits 0 with all new and existing cases passing.
- Coverage on `src/specify_cli/sync/queue.py` for the migration + detection functions ≥ 90 % (NFR-001).

## Definition of Done

- [ ] All four subtasks complete.
- [ ] `uv run pytest tests/sync/test_queue_row_level_migration.py -q` exits 0.
- [ ] `uv run mypy --strict src/specify_cli/sync/` exits 0 with no new errors.
- [ ] Coverage ≥ 90 % on the changed surfaces inside `queue.py`.
- [ ] No SQLite schema change introduced.
- [ ] No new `[NEEDS CLARIFICATION]` markers without a corresponding open decision.

## Risks

- **R2 (research.md)**: Duplicate-row bug on retry. Mitigation: `INSERT OR IGNORE` + dedicated idempotence test.
- **Existing PK assumption**: If the schema does not have a PK or UNIQUE on the natural id, the idempotence guarantee fails silently. T007 step 2 mandates an explicit decision rather than a silent schema change.
- **Caller breakage from `detect_legacy_rows_for_scope` return change**: Small. Grep callers and update inline.

## Reviewer guidance

- Verify both loops share the same scope predicate (do not double-filter; do not under-filter).
- Verify SQL strings use `INSERT OR IGNORE` for both loops.
- Verify the `detect_legacy_rows_for_scope` return shape matches the contract in `contracts/sync-boundary-preflight.md` (field names `event_rows`, `body_upload_rows`; total available as property).
- Run the new idempotence test by hand once: see counts unchanged on second migration.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <name> --mission mvp-cli-sync-boundary-completion-01KRX11M
```

## Activity Log

- 2026-05-18T09:06:26Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=37694 – Started implementation via action command
- 2026-05-18T09:14:12Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=37694 – Row-level body-upload migration + idempotence landed; preflight subtotal coordination updated
- 2026-05-18T09:14:44Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=42551 – Started review via action command
- 2026-05-18T09:19:20Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=42551 – Moved to planned
- 2026-05-18T09:19:27Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=44793 – Started implementation via action command
- 2026-05-18T09:22:37Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=44793 – Cycle 2: dst commits before src; durability guaranteed under partial-failure
- 2026-05-18T09:23:11Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=46404 – Started review via action command
- 2026-05-18T09:30:13Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=46404 – Cycle 2 review approved (codex verdict): durability fix verified — dst.commit before src.commit; test_migration_durability_dst_commit_first regression test in place. 11 migration tests pass; mypy strict clean on the diff.
