---
work_package_id: WP05
title: Issue-matrix structured core + migration
dependencies:
- WP03
requirement_refs:
- C-008
- FR-002
- FR-013
- NFR-006
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tasks/
create_intent:
- src/specify_cli/tasks/issue_matrix_migration.py
- tests/specify_cli/tasks/test_issue_matrix_structured.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tasks/issue_matrix.py
- src/mission_runtime/artifacts.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/specify_cli/cli/commands/review/_issue_matrix.py
- src/specify_cli/tasks/issue_matrix_migration.py
- tests/specify_cli/tasks/test_issue_matrix_structured.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2583'
- '1738'
---

# Work Package Prompt: WP05 – Issue-matrix structured core + migration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Migrate the issue-matrix from free markdown to `issue-matrix.json` as the **single canonical artifact** with a structured schema and per-item statuses; add the canonical writer routed via `write_target(ISSUE_MATRIX)`; teach the basename→kind recognition map about `.json` (**B2**); migrate the finalize scaffold off `.md`-on-PRIMARY (**B3**); and ship the migration sub-module hosting the **one canonical reader** (**M7**, FR-013).

## Context — three load-bearing traps

- **B2 (recognition linchpin):** `src/mission_runtime/artifacts.py:200 _MISSION_FILE_KIND_BY_BASENAME` maps basenames → kind via `kind_for_mission_file`, consumed by `auto_rebase:227`, `commit_router`, coherence. If the writer emits `.json` but the map only knows `.md`, `kind_for_mission_file("issue-matrix.json")` → `None` → the file is not staged to coord / not row-merged / treated as primary residue (silent split-brain, vacuously green in kind-constructing unit tests).
- **B3 (greenfield scaffold):** `cli/commands/agent/mission_finalize.py:355 _scaffold_issue_matrix_if_present` → `tasks/issue_matrix.py:94` scaffolds `issue-matrix.md` on the planning dir for **every** new mission before any structured write → FR-013 migrate-on-write never fires greenfield → permanent split-brain on the wrong partition.
- **M7 (one reader):** `validate_issue_matrix` (`review/_issue_matrix.py:194`) is shared by doctor/review/finalize-lint/move-task. Migration must host a single canonical `load_issue_matrix()→rows` (failover-read inside) that every read site calls — else whack-a-field across 5 sites.
- `detect_issue_references` currently reads `spec.md` only (`issue_matrix.py:51`) — the multi-file generalization is **WP08's** (a new module); leave the single-file function here in place (WP08 supersedes it at the call sites).

## Subtasks

### T019 — B2: recognition map (red-first, first slice)
In `src/mission_runtime/artifacts.py` the map opens at `:195`; the `issue-matrix.md` entry is at `:200`. Add `"issue-matrix.json" → ISSUE_MATRIX` **beside** the `.md` entry (keep `"issue-matrix.md"` for failover — `.json` recognition is genuinely absent today). Positive test: `kind_for_mission_file("issue-matrix.json") == ISSUE_MATRIX`. Negative test: an unknown basename → `None`. This is the **opening red-first test** of the WP.

### T020 — Structured schema + canonical writer
In `tasks/issue_matrix.py`, define the `issue-matrix.json` schema (rows keyed by canonicalized issue ref, per-item statuses) and the canonical writer routed via the WP03 helper `write_target(ISSUE_MATRIX)`. NO `issue-matrix.md` is emitted going forward.

### T021 — B3: migrate the finalize scaffold
Change `mission_finalize.py:355` / `issue_matrix.py:94` to author `issue-matrix.json` via `write_target(ISSUE_MATRIX)` on **COORD**, not `.md` on the planning dir. Red-first: a newly finalized mission has `issue-matrix.json` on coord and **no** `issue-matrix.md` on primary.

### T022 — Migration sub-module (FR-013)
Create `src/specify_cli/tasks/issue_matrix_migration.py`: failover-read (read legacy `issue-matrix.md` when `.json` absent), migrate-on-write (first structured write converts a legacy mission), and a bulk-migration command (`spec-kitty issue-matrix migrate [--mission <handle>] --json`). NFR-006 back-compat.

### T023 — M7: one canonical **dir-based** reader
Host `load_issue_matrix(feature_dir) → rows` in the migration sub-module — **dir-based** (takes `feature_dir`, resolves `.json` then failover-reads `.md`), NOT path-based. Re-point `review/_issue_matrix.py:194 validate_issue_matrix` to call it. **Consumers do NOT inherit JSON automatically** (B-1): each builds its own `feature_dir / "issue-matrix.md"` and `.exists()`-prechecks before reading, so the reader-internals swap is dead code behind those prechecks. Therefore:
- **finalize-lint** (`mission_finalize.py:93/397`, owned by this WP): switch to `load_issue_matrix(feature_dir)` and **delete the `.md` `.exists()` precheck**.
- **doctor + `tasks_parsing_validation.py`** switch in WP08 (T043); **post-merge review** switches in WP09 (T044). Those files are owned there — coordinate, do not edit them here.
The dir-based signature + precheck deletion is the load-bearing contract: if the reader stays path-based, the failover is inert.

### T024 — Tests
`tests/specify_cli/tasks/test_issue_matrix_structured.py`: schema round-trip; recognition (T019); scaffold-on-coord greenfield (T021); migrate-on-write + failover-read + bulk migrate (T022); canonical reader returns rows for both `.json` and legacy `.md`.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP05` (depends on WP03).

## Definition of Done
- `.json` recognized (B2); writer + scaffold on COORD (B3); migration sub-module + one canonical reader (M7); no `.md` emitted going forward.
- `ruff`/`mypy` clean; complexity ≤ 15; tests green; `commit_router`/`auto_rebase` recognition stays green.

## Risks / Reviewer guidance
- **B2 first** — the recognition assertion (both directions) must land before the writer, or split-brain hides behind green unit tests.
- Confirm the scaffold no longer writes `.md` on primary for a greenfield mission.
- Confirm exactly one `load_issue_matrix` definition; no second reader.
- **Commit each slice** (B2, writer, B3, migration, reader) so worktree progress is durable.
