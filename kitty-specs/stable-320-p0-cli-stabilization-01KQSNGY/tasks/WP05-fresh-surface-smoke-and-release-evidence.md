---
work_package_id: WP05
title: Fresh Surface Smoke And Release Evidence
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-015
- NFR-001
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
history:
- at: '2026-05-04T14:55:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/
execution_mode: planning_artifact
lane: planned
owned_files:
- kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/quickstart.md
- kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/release-evidence.md
- kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/checklists/**
tags: []
task_type: implement
---

# Work Package Prompt: WP05 - Fresh Surface Smoke And Release Evidence

## Objective

Run the combined local validation and compile release-ready evidence for #967, #904, #968, and #964 after WP01-WP04 are complete.

## Context

Read:

- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/quickstart.md`
- WP01-WP04 final reports and changed tests
- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/spec.md`

This WP should not implement major product fixes. If validation exposes a bug in WP01-WP04, return that WP for rework unless the repair is a tiny evidence/test harness adjustment.

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty agent action implement WP05 --agent <name>`
- Depends on WP01, WP02, WP03, and WP04.
- Execution worktrees are allocated later from `lanes.json`; do not create worktrees manually.

## Subtasks

### T021 - Run status evidence

Run:

```bash
uv run pytest tests/status -q --timeout=30
```

Record pass/fail and relevant diagnostics in `release-evidence.md`.

### T022 - Run review consistency evidence

Run the focused review/post-merge/tasks tests selected by WP02. At minimum start from:

```bash
uv run pytest tests/post_merge tests/review tests/tasks -q
```

If this selection is too broad for local iteration, document the narrower focused subset and why it covers #904.

### T023 - Run command and skill surface evidence

Run the focused runtime/specify_cli tests selected by WP03 and WP04. Evidence must prove no retired checklist command is generated and generated skills include frontmatter.

### T024 - Run lint, type checking, and broader gates

Run:

```bash
uv run ruff check src tests
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

Run additional selected tests based on touched files. If pre-existing failures appear, follow the charter: open a GitHub issue before treating them as accepted baseline.

### T025 - Compile release evidence

Create `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/release-evidence.md` with sections for #967, #904, #968, and #964. Include commands, outcomes, and any known limitations.

## Definition of Done

- [ ] Evidence maps directly to all four scoped issues.
- [ ] Default validation remains local and offline.
- [ ] Any hosted sync command used on this computer sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- [ ] Pre-existing failures are handled according to the charter.
- [ ] `release-evidence.md` is ready for acceptance review.

## Reviewer Guidance

Reject incomplete evidence that cannot close each scoped issue. Verify this WP did not introduce unrelated product changes.
