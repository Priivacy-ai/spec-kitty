---
work_package_id: WP04
title: Close deadlock class at accept/acceptance sites
dependencies:
- WP02
- WP03
requirement_refs:
- FR-001
- FR-003
- FR-009
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T018
phase: Phase 3 - Class Closure
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3153043"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent: []
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/acceptance/__init__.py
- tests/cross_cutting/misc/test_acceptance_support.py
role: implementer
tags: []
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Close the remaining two sibling deadlock sites (`accept` and `acceptance._commit_acceptance_meta`). They
currently `assert_not_protected_branch → raise typer.Exit(1)` **before** any materialization. Route them
through WP02's shared `coordination/commit_router.commit_for_mission(...)` so they **materialize-then-retry**.
(record-analysis — the third sibling — moved to WP02 because it lives in `mission.py`.)

## Context & Constraints

- Depends on WP02's `commit_for_mission(...)` (the shared helper) and WP01's `ProtectionPolicy`.
- **FR-009 provenance (SF-1/SF-2)**: these sites reach protection via `assert_not_protected_branch`, whose
  body read (`commit_helpers.py:527`) is rerouted through `ProtectionPolicy` by WP01. So your job is the
  materialize-then-retry **control flow** + the test rewrite; the input-provenance is delivered by WP01. Add a
  one-line assertion that `assert_not_protected_branch` is no longer the decision gate on the protected path.
- **Pair the behavior flip with its test rewrite IN THIS WP** (the L2 landmine).

## Subtasks & Detailed Guidance

### Subtask T015 — `accept.py:366`
- Replace the `assert_not_protected_branch` raise path with materialize-then-retry via `commit_for_mission`.
- **Files**: `src/specify_cli/cli/commands/accept.py`.

### Subtask T016 — `acceptance._commit_acceptance_meta` (`:1202`)
- This commits `meta.json` directly via `run_git(["commit"…])` on `summary.repo_root` (`:1224`) after the
  assert (`:1202`). Route it through `commit_for_mission` so a protected primary materializes the coord worktree.
- **Files**: `src/specify_cli/acceptance/__init__.py`.

### Subtask T018 — REWRITE landmine L2
- `tests/cross_cutting/misc/test_acceptance_support.py:519` `test_accept_protected_branch_no_mutation`
  monkeypatches `accept.assert_not_protected_branch`→raise (`:544`) and asserts `exit_code == 1` + no mutation
  (`:554-556`). Rewrite to assert materialize-then-retry (or, if a genuinely-cannot-proceed path remains, pin
  the new actionable error). Include a provenance assertion (FR-009).
- **Files**: `tests/cross_cutting/misc/test_acceptance_support.py`.

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- `accept` + `acceptance._commit_acceptance_meta` materialize-then-retry on a protected primary (no raise-and-exit).
- L2 rewritten + a provenance assertion green. ruff + mypy clean; complexity ≤ 15.

## Risks & Reviewer Guidance
- Confirm no `assert_not_protected_branch`-then-`Exit` deadlock remains at these two sites, reuse of WP02's
  helper (no parallel materialization), and that L2 asserts the NEW behavior + provenance.

## Activity Log

- 2026-06-21T09:56:52Z – claude:sonnet:python-pedro:implementer – shell_pid=3125723 – Assigned agent via action command
- 2026-06-21T10:24:18Z – claude:sonnet:python-pedro:implementer – shell_pid=3125723 – WP04 (lane-d): accept + acceptance materialize-then-retry via commit_for_mission; L2 rewritten+mutation-verified; deadlock gone
- 2026-06-21T10:24:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=3153043 – Started review via action command
- 2026-06-21T10:31:27Z – user – shell_pid=3153043 – Review passed (reviewer-renata, opus): deadlock closed at accept/acceptance via commit_for_mission, protected-detection correct, L2 mutation-verified, 8 pre-existing teamspace failures out-of-scope
