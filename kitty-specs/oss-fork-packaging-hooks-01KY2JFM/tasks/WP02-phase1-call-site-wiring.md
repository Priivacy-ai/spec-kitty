---
work_package_id: WP02
title: Phase 1 call-site wiring + docs stub
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: feat/oss-fork-packaging-hooks
merge_target_branch: feat/oss-fork-packaging-hooks
branch_strategy: Planning artifacts for this mission were generated on feat/oss-fork-packaging-hooks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/oss-fork-packaging-hooks unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T012
agent: "cursor"
shell_pid: "78454"
history:
- at: '2026-07-21T15:03:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/
create_intent:
- tests/core/test_resolve_cli_package_name.py
execution_mode: code_change
owned_files:
- src/specify_cli/session_presence/upgrade_check.py
- src/specify_cli/session_presence/manager.py
- src/specify_cli/version_utils.py
- src/specify_cli/__init__.py
- tests/specify_cli/session_presence/test_upgrade_checker.py
- tests/core/test_resolve_cli_package_name.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Phase 1 Call-Site Wiring

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` before continuing.

## Objectives & Success Criteria

Wire Phase 1 consumers to WP01 resolvers and stub packager docs:

1. Session-presence background refresh uses `resolve_upgrade_provider()` + `resolve_cli_package_name()`.
2. `version_utils.get_version()` uses resolved name (leave multi-alias completion to WP04 if needed).
3. `--version` banner label uses resolved name.
4. Stock regression proves unchanged behaviour with no entry points.
5. (Docs stub deferred to WP05 to avoid ownership overlap.)

## Context

Read FR-005–008, IC-02, quickstart Phase 1. Grep for hardcoded `spec-kitty-cli` / pypi.org in owned session-presence files before editing.

If a local `session_presence/upgrade_provider.py` exists from sibling WIP, prefer deleting it and importing from `specify_cli.distribution` (record rationale if a thin re-export shim is temporarily required).

## Branch Strategy

Depends on WP01. Implement via `spec-kitty agent action implement WP02 --agent <name>`.

## Subtasks

- **T007**: RED refresh tests with fake provider entry point.
- **T008**: Wire refresh worker/check code.
- **T009**: Wire `get_version()`.
- **T010**: Wire banner (locate actual `--version` emission path under owned `__init__.py` or adjacent if strictly required — stay in owned_files; if banner lives elsewhere, add a minimal shared helper call from the owned surface or expand owned_files with finalize approval).
- **T012**: Stock-path regression tests.

## Definition of Done

FR-005–007 satisfied (FR-008 docs in WP05); stock tests green; no private index URLs in upstream defaults.

## Reviewer Guidance

Confirm no runtime env var sets package name; session-presence still never raises / never blocks on network.

## Activity Log

- 2026-07-21T15:36:31Z – cursor – shell_pid=74382 – Assigned agent via action command
- 2026-07-21T15:41:06Z – cursor – shell_pid=74382 – Ready for review: Phase 1 wiring + 34 tests
- 2026-07-21T15:42:03Z – cursor – shell_pid=78454 – Started review via action command
- 2026-07-21T15:42:17Z – user – shell_pid=78454 – Review passed: refresh/get_version/banner wired to distribution resolvers; stock tests green.
