---
work_package_id: WP07
title: Issue-matrix verdict command
dependencies:
- WP05
- WP03
requirement_refs:
- FR-003
- FR-012
- NFR-001
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T032
- T033
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/issue_verdict.py
- tests/specify_cli/cli/commands/agent/test_issue_verdict_command.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/issue_verdict.py
- tests/specify_cli/cli/commands/agent/test_issue_verdict_command.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2583'
---

# Work Package Prompt: WP07 – Issue-matrix verdict command

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Ship a deterministic `issue-verdict` command that sets a row's per-item status/verdict on the structured `issue-matrix.json`, routed via `write_target(ISSUE_MATRIX)` through the WP03 helper (#2583).

## Context

- The structured schema, canonical writer, and recognition map land in **WP05** (dependency). This WP adds only the CLI command over them — a thin per-kind wrapper on the one seam (no bespoke compute-and-commit path).
- Idempotent + `--json` structured output naming the row + destination surface (FR-012); zero product-source reads (NFR-001).

## Subtasks

### T032 — `issue-verdict` command
Create `src/specify_cli/cli/commands/agent/issue_verdict.py`: `--mission <handle> --issue "#1726" --status verified|... --wp WP01 --actor claude --json`. It loads via WP05's canonical reader, sets the row's per-item status, and writes via `write_target(ISSUE_MATRIX)` through the WP03 helper. A legacy `.md` mission is migrated on this first structured write (WP05 migrate-on-write).

### T033 — Idempotence + tests
Re-run with identical inputs = no-op. `tests/specify_cli/cli/commands/agent/test_issue_verdict_command.py`: sets a status deterministically; JSON result names row + surface; re-run is a no-op; a legacy `.md` mission migrates on first write.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP07` (depends on WP05, WP03).

## Definition of Done
- Command lands over WP05's writer; idempotent; structured `--json`.
- `ruff`/`mypy` clean; complexity ≤ 15; tests green.

## Risks / Reviewer guidance
- **No independent compute-and-commit path** — must route through the one seam (WP03 helper + WP05 writer). Reject any duplicate write logic.
- Keep derived/computed fields authoritative; the command sets stored per-item status only.
- **Commit the completed command + tests** so worktree progress is durable.
