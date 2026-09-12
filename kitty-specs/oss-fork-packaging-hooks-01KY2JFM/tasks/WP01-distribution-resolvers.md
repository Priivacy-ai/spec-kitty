---
work_package_id: WP01
title: Distribution package name + upgrade provider resolvers
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-017
tracker_refs: []
planning_base_branch: feat/oss-fork-packaging-hooks
merge_target_branch: feat/oss-fork-packaging-hooks
branch_strategy: Planning artifacts for this mission were generated on feat/oss-fork-packaging-hooks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/oss-fork-packaging-hooks unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "cursor"
shell_pid: "70782"
history:
- at: '2026-07-21T15:03:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/distribution/
create_intent:
- src/specify_cli/distribution/__init__.py
- src/specify_cli/distribution/package_name.py
- src/specify_cli/distribution/upgrade_provider.py
- tests/specify_cli/distribution/__init__.py
- tests/specify_cli/distribution/test_package_name.py
- tests/specify_cli/distribution/test_upgrade_provider.py
execution_mode: code_change
owned_files:
- src/specify_cli/distribution/__init__.py
- src/specify_cli/distribution/package_name.py
- src/specify_cli/distribution/upgrade_provider.py
- tests/specify_cli/distribution/__init__.py
- tests/specify_cli/distribution/test_package_name.py
- tests/specify_cli/distribution/test_upgrade_provider.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Distribution Resolvers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Ship `specify_cli.distribution` with:

1. `resolve_cli_package_name()` — entry point → `packages_distributions` owning `specify_cli` → `"spec-kitty-cli"`. Never env-controlled.
2. `resolve_upgrade_provider()` — `spec_kitty.upgrade_provider` entry points → `PyPIProvider` fallback; multi → `SPEC_KITTY_UPGRADE_PROVIDER` else alphabetical; never raises.
3. Process-level memoization with a test clear-hook.
4. `__all__` on public modules; ruff + mypy clean; focused pytest green.

## Context

Read: `spec.md` FR-001–004, `plan.md` IC-01, `contracts/entry-points.md`, `research.md` (supersede sibling WIP algorithm under `session_presence/upgrade_provider.py` in the other worktree — **do not** leave the resolver only there).

Port the sibling resolution algorithm into `distribution/upgrade_provider.py`. Do not wire call sites in this WP (WP02/WP04).

## Branch Strategy

Planning/base and merge target: `feat/oss-fork-packaging-hooks`. Implement via `spec-kitty agent action implement WP01 --agent <name>`.

## Subtasks

- **T001**: Create package skeleton + `__all__`.
- **T002**: RED tests for name precedence (string EP, callable EP, object.attr, packages_distributions, default).
- **T003**: Implement `resolve_cli_package_name`.
- **T004**: RED tests for provider discovery (0/1/N, env select, bad load → PyPI).
- **T005**: Implement `resolve_upgrade_provider` + memo.
- **T006**: Run focused pytest/ruff/mypy on owned paths.

## Definition of Done

- All T001–T006 complete; no call-site wiring outside `distribution/`.
- Stock defaults match today’s hardcoded names/providers.
- No fork hostnames committed.

## Reviewer Guidance

Check never-raise contract, env-not-for-name invariant, and that sibling `session_presence` copy is not required for these APIs.

## Activity Log

- 2026-07-21T15:19:54Z – cursor – shell_pid=64794 – Assigned agent via action command
- 2026-07-21T15:28:19Z – cursor – shell_pid=64794 – Ready for review: distribution resolvers + 17 unit tests
- 2026-07-21T15:30:12Z – cursor – shell_pid=70782 – Started review via action command
- 2026-07-21T15:32:05Z – user – shell_pid=70782 – Review passed: resolvers match FR-001–004; 17 unit tests; never-raise + stock fallback; no env for package name; memo + clear hooks present.
