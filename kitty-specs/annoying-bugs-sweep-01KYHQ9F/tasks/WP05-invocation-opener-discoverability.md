---
work_package_id: WP05
title: Invocation opener discoverability
dependencies: []
requirement_refs:
- C-005
- C-007
- FR-013
planning_base_branch: fix/annoying-bugs-sweep
merge_target_branch: fix/annoying-bugs-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/annoying-bugs-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/annoying-bugs-sweep unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-annoying-bugs-sweep-01KYHQ9F
base_commit: f6935e0ef7b94dac30776b645e4057dab08336ee
created_at: '2026-07-27T14:46:04.934884+00:00'
subtasks:
- T031
- T023
- T024
- T025
- T026
phase: Phase 2 - Agent guidance
history:
- at: '2026-07-27T13:34:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/profile_invocation.py
create_intent: []
execution_mode: code_change
model: gpt-5.6-terra
owned_files:
- src/specify_cli/cli/commands/profile_invocation.py
- tests/specify_cli/invocation/cli/test_complete.py
role: implementer
tags: []
tracker_refs:
- '#2984'
---

# Work Package Prompt: WP05 - Invocation opener discoverability

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, resolve `python-pedro` with
`spec-kitty agent profile show python-pedro`, and load
`spec-kitty charter context --action implement --json`.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## Objective

Make the standalone invocation lifecycle discoverable in both directions: the existing closer
`profile-invocation complete` must expose that standalone Ops are opened with
`spec-kitty dispatch`, without adding an alias or changing completion metadata.

## Context And Constraints

- The opener already works. This is a help-surface defect only.
- Add the pointer to the Typer group epilog, not `help=`.
- Do not add `profile-invocation dispatch`.
- The completion manifest schema excludes epilog; prove it remains unchanged.

## Branch Strategy

- **Planning base**: `fix/annoying-bugs-sweep`
- **Merge target**: `fix/annoying-bugs-sweep`
- Use the finalized execution workspace.

## Subtasks

### T031 - Open the WP: tracker, ownership, and campsite

Before edits, assign #2984 to the current Human-in-Charge and add a tracker comment naming this
mission. Re-check the intended diff against C-005 and all other WP ownership, then perform a bounded
domain-matched Sonar/complexity scout of the owned Typer and test surfaces. Apply necessary
behavior-preserving cleanup first with focused tests, or record a clean finding. Stop and revise
ownership before touching an undeclared file.

### T023 - Add epilog guidance

Add concise help text explaining:

```text
Open:  spec-kitty dispatch "<request>"
Close: spec-kitty profile-invocation complete --invocation-id <id> --outcome <outcome>
```

Use Typer's supported epilog mechanism and keep the existing group name/help stable.

### T024 - Help regression test

Invoke `profile-invocation --help` through the real CLI app and assert `spec-kitty dispatch` is
visible. Keep the assertion robust to Rich whitespace wrapping.

### T025 - Metadata non-regression

Pin the relevant completion-manifest entry or run the existing manifest-generation comparison and
prove the epilog edit causes no diff. Do not update the manifest to make the test pass.

### T026 - Gates

```bash
PWHEADLESS=1 pytest tests/specify_cli/invocation/cli/test_complete.py -q
ruff check src/specify_cli/cli/commands/profile_invocation.py tests/specify_cli/invocation/cli/test_complete.py
mypy src/specify_cli/cli/commands/profile_invocation.py
```

## Definition Of Done

- Group help names the correct opener.
- Existing close behavior is unchanged.
- No alias, new command, or completion-manifest churn.
- Focused tests and static checks pass.
- The actual changed-file set remains disjoint from every other WP.

## Reviewer Guidance

Inspect the Typer constructor and the generated metadata diff. Reject any implementation that
changes `help=`, adds a command, or updates a manifest instead of proving it unchanged.
