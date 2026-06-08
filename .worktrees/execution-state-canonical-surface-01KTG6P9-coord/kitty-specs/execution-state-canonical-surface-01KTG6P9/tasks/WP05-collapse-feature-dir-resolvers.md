---
work_package_id: WP05
title: Collapse duplicate feature-dir resolvers
dependencies:
- WP04
requirement_refs:
- FR-010
- NFR-002
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T019
- T020
- T021
phase: Phase 3 - Strangle
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2771228"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/specify_cli/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Collapse duplicate feature-dir resolvers

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

The canonical example of semantic compression: 8 implementations of the same behavior → 1. Map the behavioral envelope of each copy first; only delete a copy once its callers use the canonical resolver and the ratchet proves equivalence.

## Objectives & Success Criteria

Collapse the 8 duplicate `_resolve_feature_dir`/feature-dir resolver implementations to a single canonical resolver and delete the rest.

- FR-010. NFR-002. SC-004 (partial), SC-007.

## Context & Constraints

- Known copies (verify current state): `workspace/context.py`, `task_utils/support.py`, `cli/commands/verify.py`, `cli/commands/agent/status.py` (×2), `dashboard/scanner.py`, `missions/feature_dir_resolver.py` (canonical candidate).
- Prefer routing through `mission_runtime.resolve_action_context` where callers actually need full context; use `missions/feature_dir_resolver.resolve_feature_dir_for_mission` where only the dir is needed.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T019 – Inventory + select canonical
- **Steps**: List all current feature-dir resolver implementations; diff their behavior; pick the canonical one.
- **Files**: the 8 sites above.

### Subtask T020 – Repoint call sites [P]
- **Steps**: Replace each redundant call with the canonical resolver.

### Subtask T021 – Delete redundant implementations
- **Steps**: Remove the now-unused copies; no dead code.

## Test Strategy

- Existing unit/integration tests for the affected commands green; WP01 ratchet green.

## Risks & Mitigations

- Subtle behavioral differences between copies → diff each against the canonical before deleting; add a unit test where behavior was ambiguous.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Confirm exactly one resolver remains and no caller kept a local copy. Reject partial collapses.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T08:16:41Z – claude:opus:randy-reducer:implementer – shell_pid=2755078 – Started implementation via action command
- 2026-06-08T08:28:37Z – claude:opus:randy-reducer:implementer – shell_pid=2755078 – Ready for review: collapsed slug->dir feature-dir resolvers to one canonical home (missions/feature_dir_resolver.py); deleted 2 true duplicates (workspace/context.py, task_utils/support.py); renamed verify adapter + status authority helpers to dispel name collisions; dashboard discovery resolver retained as distinct surface. NFR-002 behavior-preserving; ratchet+FR-036 green; ruff/mypy clean on new code.
- 2026-06-08T08:29:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=2771228 – Started review via action command
- 2026-06-08T08:34:43Z – user – shell_pid=2771228 – Review passed (reviewer-renata + paula-patterns). Single-homed: slug->dir family now lives ONLY in missions/feature_dir_resolver.py (resolve_feature_dir_for_slug/resolve_feature_dir_for_mission/candidate_feature_dir_for_mission, __all__). 2 true duplicates deleted (workspace/context.py, task_utils/support.py) and repointed to canonical. Per-surface verdict: (1) agent/status.py _resolve_status_surface[_for_repo] = GENUINELY DISTINCT (MissionStatus.load().read_dir, slug validation + fail-closed coord authority FR-004, 3-tuple, typer.Exit) - body unchanged, rename only. (2) dashboard/scanner.py resolve_feature_dir = GENUINELY DISTINCT (id-keyed multi-mission FS scan via gather_feature_paths, Path|None). (3) verify.py _existing_feature_dir = GENUINELY DISTINCT (existence-gated Path|None presentation adapter; was ALREADY delegating to candidate_feature_dir_for_mission pre-WP05 - rename only, never a copy). NO partial collapse. ratchet+FR-036 green (21 passed). ruff clean; mypy: WP05 removed 1 pre-existing no-any-return (6->5), introduced 0; remaining 5 are pre-existing untouched-line debt. tests/missions 7 failures = known sparse-checkout asset-layout set, WP05 touched 0 files there. No dead code (all symbols have live prod callers). No terminology regression (internal feature_dir identifiers per Regression Vigilance carve-out; verify --feature unchanged hidden alias).
