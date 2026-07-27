---
work_package_id: WP04
title: 'Workspace Resolution: Fall-Through Is Failure'
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
agent: "claude:fable-5:reviewer-renata:reviewer"
shell_pid: "85818"
history:
- '2026-06-12: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/workspace/
execution_mode: code_change
owned_files:
- src/specify_cli/workspace/context.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/status/doctor_husks.py
- tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py
role: implementer
tags: []
---

# WP04 — Workspace Resolution: Fall-Through Is Failure

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its initialization declaration, boundaries, and governance scope for this WP.

## Objective

Enforce one invariant at three trust boundaries: **a resolved lane workspace must be an actual git worktree** (FR-003/004/005, #1833 residuals). A "husk" — a directory under `.worktrees/` with no `.git` entry — must produce a structured, named resolution failure instead of git commands silently falling through to the primary repository. Ship a doctor check that lists/removes husks so operator recovery is one command (FR-007).

## Context

Read first: [contracts/class-d-workspace-resolution.md](../contracts/class-d-workspace-resolution.md), [research.md](../research.md) R4/R5, Class D section of [validation/debbie-analysis.md](../validation/debbie-analysis.md).

Mechanism (verified at HEAD `956ab0e3e` — re-verify lines): husk dirs pass bare `Path.exists()` checks (`workspace/context.py:148-150`; `cli/commands/agent/tasks.py:1346`); git invoked with `-C <husk>` walks up and operates on the PRIMARY repo — yielding misattributed verdicts ("No implementation commits on lane branch!", primary-dirty complaints). `ReviewLock` is acquired before the workspace exists, and a failed `git worktree add` is only a warning (`cli/commands/agent/workflow.py:2237/2243/2265`). The husk-minting naming trigger (F-001) was already fixed in PR #1850 — your scope is the fall-through guards.

Note: git worktrees have a `.git` **file** (not directory) — check for the entry's existence, not `is_dir()`.

Constraint **C-001**: no allocator unification, no ReviewLock redesign, no resolver API change — guards only.

## Subtasks

### T018 — Red test (FIRST)

`tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py`: fixture plants `.worktrees/<slug>-<mid8>-lane-a/` containing a stray file but no `.git`. Assertions (AC-D1):
- move-task (approval path) fails with a structured resolution error naming the husk path and the failed check.
- The error is NOT "No implementation commits on lane branch!" and NOT a primary-repo dirty verdict.
- Zero git subprocess calls execute against the primary repo from the husk resolution (assert via the error arriving before any such call, or monkeypatched subprocess recorder).
Commit red before fixes.

### T019 — `.git`-marker existence

`workspace/context.py:148-150`: `ResolvedWorkspace.exists` returns True only when the path contains a `.git` entry. Audit `exists` consumers in this module for behavior that relied on bare-directory truthiness (e.g. "exists → reuse" paths must now treat a husk as ABSENT-but-blocked: prefer a structured error over silently recreating on top — recreating over a husk hides the anomaly).

### T020 — Lock-after-create; creation failure is failure

`cli/commands/agent/workflow.py` review-claim path (`:2237/:2243/:2265`): reorder so `ReviewLock.acquire` happens only after the workspace existence/creation block succeeds; promote `git worktree add` failure from warning to a hard structured error (include git's stderr). Ensure no lock is left held on the failure path (test it).

### T021 — move-task toplevel assertion

`cli/commands/agent/tasks.py:1346`: before the first git invocation against a resolved workspace, assert `git -C <path> rev-parse --show-toplevel` resolves to `<path>` itself; mismatch → the same structured resolution-failure error (NFR-003: name resolved path + actual toplevel). This is the last-line defense for paths arriving from other resolver lineages (R4).

### T022 — Doctor husk check (FR-007)

New check (suggested module `src/specify_cli/status/doctor_husks.py` — but FIRST inspect how existing doctor checks register in the doctor command surface and follow that pattern exactly; if checks live in a registry module, extend it and adjust `owned_files` accordingly with a one-line rationale):
- Report mode: list `.worktrees/*` entries lacking a `.git` entry, annotated with whether `git worktree list` registers them.
- `--fix`: remove ONLY unregistered husks (R5 — never remove a registered worktree, even a broken one; report those for manual `git worktree repair/remove`).
- JSON + human output consistent with sibling doctor checks.

### T023 — AC-D2/D3 assertions + recovery text

Extend T018's test: `ResolvedWorkspace.exists` False for husk; no `ReviewLock` held after failed claim; worktree-add failure is an error (AC-D2); doctor reports the planted husk and `--fix` removes it while a registered real worktree survives (AC-D3). The structured errors' text tells the operator the recovery command (`spec-kitty doctor … --fix`).

## Branch Strategy

Planning base and merge target are both `main`. Execution worktree/branch come from `lanes.json` via `spec-kitty agent action implement WP04 --agent <name>`. Landing on origin/main via PR only (C-005).

## Definition of Done

- [ ] T018 red → green; AC-D1 misattribution gone
- [ ] `.git`-marker check in `exists`; husk ≠ reusable workspace (T019)
- [ ] Lock-after-create; creation failure hard-errors; no orphaned lock (T020)
- [ ] Toplevel assertion guards move-task (T021)
- [ ] Doctor check: report + safe `--fix`; registered worktrees never removed (T022, AC-D3)
- [ ] Error texts name path/check/recovery (NFR-003); ruff + mypy --strict zero suppressions; ≥90% changed-line coverage; existing ratchets green; terminology guard before push

## Risks & Reviewer Guidance

- **Deletion safety in T022**: reviewer, demand the registered-worktree survival test before approving `--fix`.
- T019 may change behavior for legitimate-but-odd states (e.g. mid-creation races) — reviewer: check the #1357 lock in `CoordinationWorkspace.resolve` patterns for how creation races are serialized; the lane-workspace path should fail loudly, not auto-heal.
- Pre-existing husks on real machines start erroring after this lands — release notes line required (hand to reviewer for CHANGELOG).
- If doctor-check registration forces edits outside `owned_files`, record the one-line rationale in the PR (no-overlap rule is the hard constraint — verify WP05/WP02 don't own the touched file).

## Activity Log

- 2026-06-12T11:58:07Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – Assigned agent via action command
- 2026-06-12T12:35:15Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – WP04 done: husk fall-through guards at 3 boundaries + doctor workspaces check. Red test committed first (58a361bc7, 13 failed), green at 0ace55423. Verification: husk suite 23 passed (exit 0); post-rebase sanity 73 passed (exit 0); broad sweep 9 failed/7059 passed — all 9 confirmed pre-existing at base (wrapper_delegation x2 cwd-dependent, readme_governance x4, upgrade dry-run contract, command_renderer snapshots x2). ruff exit 0; mypy --strict 5 files exit 0; terminology guard 2 passed. Changed-line coverage 92.2%. Out-of-scope edits: cli/commands/doctor.py (doctor checks register as typer subcommands there; no registry module; not owned by WP02/03/05) + 3 test fixture files (fabricated worktrees via bare mkdir now rejected by design). Release-notes line needed: pre-existing husks now error; recover with 'spec-kitty doctor workspaces --fix'.
- 2026-06-12T12:40:08Z – user – shell_pid=83268 – WP04 complete at 7a1ac457f (lane-c, rebased on mission branch). Gates: husk suite test_workspace_husk_resolution_1833.py -x -q = 23 passed (exit 0); agent suites = 258 passed, 2 failed (env-only: test_wrapper_delegation implement tests fail only when pytest cwd is inside a worktree, pre-existing is_worktree_context guard; both pass from /tmp cwd, exit 0); doctor suites -k doctor = 75 passed (exit 0); diff-scoped ruff = exit 0; mypy --strict on 5 changed src files = no issues (exit 0), zero new suppressions; terminology guard = 2 passed (exit 0). doctor.py edit = minimal pre-authorized T022 registration (not owned by WP02/03/05).
- 2026-06-12T12:41:06Z – claude:fable-5:reviewer-renata:reviewer – shell_pid=85818 – Started review via action command
- 2026-06-12T12:45:38Z – user – shell_pid=85818 – Review passed: AC-D1/D2/D3 verified. Husk suite 23 passed; doctor -k suite 75 passed; registered-worktree survival tests present and green (test_fix_never_removes_registered_broken_worktree, test_fix_removes_unregistered_husk_and_preserves_registered_worktree); --fix deletes only unregistered .git-less entries. Lock-after-create proven (no lock on failure); worktree-add failure hard-errors with stderr; toplevel assertion guards move-task; doctor workspaces live-verified. ruff 0, mypy --strict 0, no new suppressions, terminology guard 2 passed; wrapper_delegation passes from /tmp cwd (env-only claim confirmed). doctor.py edit is pre-authorized registration-only wrapper (not owned by WP02/03/05). REMINDER for final mission PR: CHANGELOG/release-notes line — pre-existing husks now produce structured errors; recover with 'spec-kitty doctor workspaces --fix'. Minor non-blocking hardening idea: _registered_worktree_paths returns empty set when 'git worktree list' itself fails (fail-open); consider aborting --fix on listing failure.
