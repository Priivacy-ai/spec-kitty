---
work_package_id: WP02
title: Create mission-steps/ directory structure + move command templates
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 8e2c75f037d5009848cbd2e5557710d56a28bb0f
created_at: '2026-05-30T19:25:43.494610+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3129655"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission-steps/
- src/specify_cli/missions/
- tests/doctrine/missions/test_mission_steps_layout.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP02 — Create mission-steps/ directory structure + move command templates

## Context

All step prompt templates currently live in `src/specify_cli/missions/*/command-templates/`. FR-010 requires them to be moved verbatim to `src/doctrine/missions/mission-steps/` as built-in `MissionStep` artifacts. The old `command-templates/` directories must be deleted afterwards.

This WP creates the on-disk directory structure and populates it with the moved prompt templates and new `step.yaml` descriptors.

## Objective

Create the `src/doctrine/missions/mission-steps/` directory tree, move all command-template Markdown files verbatim into it (without editing content), add `step.yaml` descriptors, and delete the old `command-templates/` directories.

## On-Disk Layout

```
src/doctrine/missions/mission-steps/
├── software-dev/
│   ├── specify/
│   │   ├── step.yaml
│   │   ├── prompt.md       ← verbatim from old command-templates/specify.md
│   │   └── guidelines.md   ← optional, if a guidelines file exists
│   ├── plan/
│   │   ├── step.yaml
│   │   └── prompt.md
│   ├── tasks/
│   │   ├── step.yaml
│   │   └── prompt.md
│   ├── implement/
│   │   ├── step.yaml
│   │   └── prompt.md
│   └── review/
│       ├── step.yaml
│       └── prompt.md
├── documentation/
│   └── … (same pattern)
├── research/
│   └── … (same pattern)
└── plan/
    └── … (same pattern)
```

## Subtasks

### T010 — Enumerate existing command-template files

List all files under `src/specify_cli/missions/*/command-templates/`. For each mission type (software-dev, documentation, research, plan), record:
- The list of Markdown file names (these become step IDs)
- Whether any guidelines or supplemental files exist

This enumeration drives the directory layout in T011–T014.

### T011 — Create mission-steps/ directory structure

Create the `src/doctrine/missions/mission-steps/` directory and all required subdirectories per mission type and step ID found in T010. Use the exact directory names:
- Mission type directories: `software-dev/`, `documentation/`, `research/`, `plan/`
- Step ID directories: derived from the command-template filename stem (e.g., `specify.md` → `specify/`)

### T012 — Move software-dev command templates verbatim

For each file in `src/specify_cli/missions/software-dev/command-templates/`:
- Move it to `src/doctrine/missions/mission-steps/software-dev/{stem}/prompt.md`
- Do NOT edit the file content — move verbatim (FR-010 explicit requirement)
- If a corresponding guidelines file exists, move it as `guidelines.md` in the same step directory

### T013 — Move documentation, research, plan command templates verbatim

Repeat the same process for:
- `src/specify_cli/missions/documentation/command-templates/` → `mission-steps/documentation/`
- `src/specify_cli/missions/research/command-templates/` → `mission-steps/research/`
- `src/specify_cli/missions/plan/command-templates/` → `mission-steps/plan/`

Move verbatim; do not edit content.

### T014 — Author step.yaml descriptors

For each step directory created, author a `step.yaml` file with this schema:

```yaml
id: <step_id>               # e.g., specify
display_name: "<Human Name>" # e.g., "Specification"
step_type: agent             # all built-in steps are agent type
prompt_template: prompt.md   # relative path within this directory
agent_profile: null          # fill in only if a specific profile should be used
guidance: null
delegates_to: []
depends_on: []
```

Use the `step_type: agent` for all built-in steps (the `human_in_loop` and `integration` types are reserved for custom steps).

Suggested display names for software-dev steps:
- `specify` → "Specification"
- `plan` → "Implementation Plan"
- `tasks` → "Task Breakdown"
- `implement` → "Implementation"
- `review` → "Review"

### T015 — Delete old command-templates/ directories

After all content has been moved (verify with `diff` or similar):
1. Delete `src/specify_cli/missions/software-dev/command-templates/`
2. Delete `src/specify_cli/missions/documentation/command-templates/`
3. Delete `src/specify_cli/missions/research/command-templates/`
4. Delete `src/specify_cli/missions/plan/command-templates/`

If a `command-templates/` directory is empty after moving, it is safe to delete the whole `missions/*/` tree if no other files remain; but check first — there may be other mission-type files (e.g., `mission.yaml`) that must not be deleted.

### T016 — Write layout verification tests

Write `tests/doctrine/missions/test_mission_steps_layout.py` with tests that verify:
- Each of the four built-in mission types has a `mission-steps/<type>/` directory
- Each step directory contains a `step.yaml` and `prompt.md`
- Each `step.yaml` is valid YAML parseable into the `MissionStep` model (from WP01)
- `step.yaml` `id` field matches the directory name (invariant from spec)
- No old `command-templates/` directories exist under `src/specify_cli/missions/`

## Acceptance Criteria

- [ ] `src/doctrine/missions/mission-steps/` tree is complete with `step.yaml` and `prompt.md` for every step of every built-in mission type
- [ ] All `step.yaml` files are valid per the unified `MissionStep` model from WP01
- [ ] Old `src/specify_cli/missions/*/command-templates/` directories are deleted
- [ ] No prompt content was modified during the move (verbatim copy verified)
- [ ] `tests/doctrine/missions/test_mission_steps_layout.py` passes
- [ ] No `src/specify_cli/missions/` content outside `command-templates/` was touched

## References

- FR-010: Template migration requirement
- FR-011: MissionStep model (step.yaml schema)
- data-model.md §"MissionStep (unified)" — directory structure
- research.md §"Research Task 5" — deployment pipeline context

## Activity Log

- 2026-05-30T19:25:44Z – claude:sonnet:python-pedro:implementer – shell_pid=3118626 – Assigned agent via action command
- 2026-05-30T19:30:30Z – claude:sonnet:python-pedro:implementer – shell_pid=3118626 – Ready for review: mission-steps/ directory structure created, 12 software-dev command templates moved verbatim, step.yaml descriptors authored, old command-templates/ deleted, layout tests passing (124 tests)
- 2026-05-30T19:30:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=3129655 – Started review via action command
