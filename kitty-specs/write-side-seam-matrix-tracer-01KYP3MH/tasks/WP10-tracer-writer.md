---
work_package_id: WP10
title: Tracer finding writer
dependencies:
- WP03
requirement_refs:
- C-002
- FR-006
- NFR-003
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T036
- T037
- T038
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent:
- src/specify_cli/retrospective/tracer_writer.py
- src/specify_cli/cli/commands/agent/tracer_append.py
- tests/specify_cli/retrospective/test_tracer_writer.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/retrospective/tracer_writer.py
- src/specify_cli/cli/commands/agent/tracer_append.py
- tests/specify_cli/retrospective/test_tracer_writer.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2980'
- '2549'
- '2960'
---

# Work Package Prompt: WP10 – Tracer finding writer

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Build the mission's one genuine must-build: a lane-origin `tracer-append` command that routes a dated, attributed `traces/` finding to the **coordination surface** via the WP03 helper / `commit_for_mission`, leaving **zero** `kitty-specs/` commits on the lane branch and not blocking a later `move-task` (#2980/#2549).

## Context

- `TRACER_FILE` is COORD-classified (`artifacts.py:181`, `"traces"` map) but has only a **reader** (`retrospective/generator.py:268/282`). Agents currently append into the mission dir directly — on a lane that means the lane worktree's `kitty-specs/`, committed on the lane branch (the #2980/#2549 barrier). `TRACER_FILE` classification is **unchanged** (C-002) — this builds the routed *writer*, it does not reclassify.
- **Ledger-M16**: the new writer sits beneath the `read_dir(RETROSPECTIVE)` short-circuit → it MUST call the leaf / `write_target` directly, **never** `read_dir`.
- `retrospective/writer.py` is the retrospective *record* writer — distinct from `traces/`. Put the tracer writer in a **new** module `retrospective/tracer_writer.py`.
- **Attribution guard (#2960):** an `agent:""` annotation silently blanks attribution (the reducer guards `is not None`). Guard `agent` presence so findings are correctly attributed.

## Subtasks

### T036 — Tracer writer
Create `src/specify_cli/retrospective/tracer_writer.py`: append a dated, attributed finding (category: tooling-friction / approach / design-decision) to `traces/`, routed to COORD via the WP03 helper (`write_target(TRACER_FILE)` + `commit_for_mission`). Use the leaf directly (Ledger-M16). Idempotent (identical content twice = no duplicate).

### T037 — `tracer-append` command
Create `src/specify_cli/cli/commands/agent/tracer_append.py`: `--mission <handle> --category tooling-friction --entry "..." --actor claude --json`. Reject/guard a blank `actor`/`agent` so attribution never blanks (#2960).

### T038 — Tests
`tests/specify_cli/retrospective/test_tracer_writer.py`: from a lane, an append lands on the coord surface, the lane branch has **no** new `kitty-specs/` commit, and a subsequent `move-task` is not blocked; identical content twice → no duplicate; blank actor → guarded error, not a blanked entry.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP10` (depends on WP03).

## Definition of Done
- Lane-origin tracer append routes to coord; zero lane `kitty-specs/` commit; `move-task` unblocked; attribution guarded.
- `ruff`/`mypy` clean; complexity ≤ 15; tests green.

## Risks / Reviewer guidance
- **Never** use the `read_dir(RETROSPECTIVE)` short-circuit (Ledger-M16 recursion).
- Confirm no lane-branch `kitty-specs/` commit is produced (the whole point of #2980/#2549).
- **Commit the completed slice** so worktree progress is durable.
