---
work_package_id: WP05
title: Legacy Record Migration
dependencies:
- WP01
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "36023"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_*_op_record_schema_v2.py
- tests/upgrade/test_op_record_schema_v2_migration.py
role: implementer
tags: []
---

# WP05 — Legacy Record Migration

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Ship an upgrade migration that converts legacy `kitty-ops/` Op records to the v2 event schema: salvageable records rewritten per the data-model mapping table, unsalvageable files deleted, atomic rewrites, idempotent re-runs. This is the **sole** sanctioned in-place mutation of Op records (C-004 exception). User-confirmed posture: very few legacy records exist and none are precious — deletion over heroics.

## Context

- Spec: FR-011, NFR-004. Data model: "Migration mapping (legacy → v2)" table is normative. Research R6.
- Migration framework: modules under `src/specify_cli/upgrade/migrations/` with `detect()` / `apply()`; study a recent example (e.g. the session-presence migration) for registration, naming (`m_<version>_*`), and runner expectations. Adjust the filename's version segment to the actual next release version at implementation time if `3_2_1` is stale — match the convention of the newest existing migration.
- Scope of scan: `kitty-ops/*.jsonl` **excluding** `ops-index.jsonl`, `lifecycle.jsonl`, `propagation-errors.jsonl` (different schemas, untouched).
- This migration does NOT touch agent directories — do not use `get_agent_dirs_for_project()`.

## Subtasks

### T019 — Migration scaffold (detect/apply)

**Purpose**: correctly registered, correctly triggered.

**Steps**:
1. Create the migration module following the framework pattern: `detect()` returns True iff `kitty-ops/` exists and contains at least one per-op JSONL file with a legacy line (started event lacking required v2 fields is fine to key on; simplest reliable signal: a `completed` event without `closed_by`, or a `started` event missing `mode_of_work` — check both, see T020 classification).
2. `apply()` walks the eligible files and dispatches each to rewrite/delete/skip per T020/T021.
3. Register in whatever index/registry the framework uses (mirror the newest migration's registration exactly).

**Validation**: migration appears in `spec-kitty upgrade` plan output for a fixture project with legacy records; absent for a clean/new project.

### T020 — Legacy→v2 rewrite mapping

**Purpose**: salvage everything salvageable, per the normative table.

**Steps**: per file, parse lines as dicts and classify:
1. **Started event** with `invocation_id` (26 chars) and `profile_id` → emit `OpStartedEvent`: carry all present fields; `mode_of_work` missing/null → `"task_execution"`. **Binding rule for missing identity fields**: when `actor` or `action` is missing or empty in the legacy record, emit the literal `"unrecorded"` — never fabricate a plausible value; v2 only requires non-empty, and `"unrecorded"` preserves honesty.
2. **Completed event** with non-null `outcome` → `OpCompletedEvent` with that outcome, `closed_by="agent"`, `completed_at` carried (missing → started_at as best-effort, flag in migration report).
3. **Completed event with null `outcome`** (the old auto-close artifacts this mission exists to kill) → `OpCompletedEvent` with `outcome="abandoned"`, `closed_by="agent"`.
4. `artifact_link` / `commit_link` / `glossary_checked` lines pass through byte-identical.
5. Already-v2 file (every completed line has `closed_by`; started has `mode_of_work`) → skip untouched (idempotency).

**Validation**: table-driven unit tests, one per row of the mapping table, asserting exact output lines.

### T021 — Deletion, atomicity, idempotency

**Purpose**: unsalvageable files go away cleanly; re-runs are no-ops.

**Steps**:
1. Delete the whole file when the started event is unparseable JSON, missing, or lacks `invocation_id`/`profile_id`. Record deletions in the migration's summary output (operator-visible: count + filenames).
2. Atomic rewrite: write to `<file>.tmp` in the same directory, `os.replace()` over the original. Never partially rewritten files.
3. Idempotency (NFR-004): second `apply()` over a migrated dir changes zero bytes and reports zero actions. `detect()` returns False post-migration.
4. `ops-index.jsonl` consistency: deleted files leave dangling index entries — verify the index reader already tolerates missing files (it falls back gracefully); if it does, leave the index alone and note it; if it crashes, filter the index in the same migration.

**Validation**: double-run test (byte-compare the directory between runs); deletion test; tmp-file cleanup on simulated failure.

### T022 — Migration tests

**Purpose**: full coverage of the disposition matrix.

**Steps**: `tests/upgrade/test_op_record_schema_v2_migration.py` with fixture builders for each legacy shape: full happy rewrite; null-outcome completed → abandoned; missing mode_of_work; pass-through link events; unsalvageable → deleted + reported; already-v2 → skipped; double-run idempotency; detect() true/false matrix; excluded files (`ops-index.jsonl`, `lifecycle.jsonl`, `propagation-errors.jsonl`) untouched.

**Validation**: `.venv/bin/pytest tests/upgrade -q -k op_record` green; mypy --strict + ruff clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json`. Implement via `spec-kitty agent action implement WP05 --agent <name>` (depends on WP01; parallel with WP02/WP03).

## Definition of Done

- [ ] Migration registered and triggered only when legacy records exist; never touches the three excluded files.
- [ ] Every mapping-table row implemented and tested; deletions reported to the operator.
- [ ] Atomic rewrites; double-run is a byte-identical no-op; detect() false after migration.
- [ ] ≥90% coverage on the migration; mypy --strict + ruff clean.

## Risks & Reviewer Guidance

- **The `"unrecorded"` placeholder** for missing actor/action is a deliberate honesty marker — reviewer should reject any mapping that fabricates plausible-looking values for missing identity fields.
- **Version-segment in filename**: confirm against the actual next release version and the newest migration's convention at implementation time.
- **Don't migrate `lifecycle.jsonl`**: it uses `ProfileInvocationRecord`, a different model that this mission does not touch.

## Activity Log

- 2026-06-10T21:10:17Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Assigned agent via action command
- 2026-06-10T21:18:04Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Ready for review: legacy migration rewrite-or-delete, idempotent, mapping table covered
- 2026-06-10T21:18:30Z – claude:fable:reviewer-renata:reviewer – shell_pid=36023 – Started review via action command
- 2026-06-10T21:20:48Z – user – shell_pid=36023 – Review passed: legacy kitty-ops migration implements every normative mapping row (unrecorded placeholder, null-outcome->abandoned/closed_by=agent, completed_at->started_at fallback flagged), atomic tmp+os.replace rewrites with cleanup, operator-visible deletion reporting, byte-identical double-run idempotency, excluded files untouched; 528 upgrade tests pass, ruff+mypy --strict clean on owned files; ops-index left alone verified safe (reader catches OSError)
