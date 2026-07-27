---
work_package_id: WP03
title: Higher-touch repoints + consolidation verification
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-005
- FR-008
tracker_refs: []
planning_base_branch: fix/merge-base-diff-ssot
merge_target_branch: fix/merge-base-diff-ssot
branch_strategy: Planning artifacts for this mission were generated on fix/merge-base-diff-ssot. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-base-diff-ssot unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 2 - Repoints
shell_pid: "2624934"
history:
- timestamp: '2026-07-09T20:30:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
mission_id: 01KX44SDZPWMA4N7RPKNR3TQT1
owned_files:
- src/specify_cli/lanes/stale_check.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/acceptance/__init__.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Do not touch code until the profile is loaded and acknowledged.

# Work Package Prompt: WP03 – Higher-touch repoints + consolidation verification

## Objective

Route the three copies that carry extra behaviour to preserve through the WP01 surface, each with named acceptance criteria, then verify the whole consolidation is complete (zero residual copies across all 5 sites). Parallel-safe with WP02 (disjoint files).

## Context & Constraints

- Depends on WP01. Import from `specify_cli.core.vcs.git`.
- Read `../spec.md` (FR-003, FR-005, FR-008), `../plan.md` (IC-02b), `../research.md` (Decisions 3–5). NFR-001 is load-bearing — no expected-value test edits.
- Two touched files are god-modules (`acceptance/__init__.py` ~1751 LOC). **Repoint ONLY the named function; do not expand into their other debt** (C-004).

## Subtasks & Detailed Guidance

### Subtask T009 – Repoint `lanes/stale_check` primitives
- File: `src/specify_cli/lanes/stale_check.py` (~L85-108). Delete `_git_merge_base` and `_git_diff_names`; repoint their callers to `git_merge_base(repo_root, ref_a, ref_b)` and `git_diff_names(repo_root, base, head)` (this is the **2-ref** site — neither ref is HEAD, so use the primitives, not the convenience).
- Adapt the caller boundary back to `set[str]` (`set(git_diff_names(...))`). Preserve the `None`/empty degradation exactly.
- This is the only site *gaining* the C-002 kwargs (`encoding`/`errors`). Assert real-repo output is byte-identical (the `test_stale_check.py` real-repo suite proves this).
- Deleting the two `_git_*` symbols may trip a dead-symbol / architectural guard — update the relevant allowlist/guard **in this WP** so it stays green (do not leave it red for a later WP).

### Subtask T010 – Repoint `tasks_shared._list_wp_branch_mission_specs_changes` first pass
- File: `src/specify_cli/cli/commands/agent/tasks_shared.py` (~L664-705). Replace ONLY the first-pass `merge-base HEAD <base>` + `diff --name-only <mb>..HEAD -- kitty-specs/` with `merge_base_changed_files(worktree_path, base_branch, pathspec="kitty-specs/")`.
- **Preserve verbatim**: the `startswith("kitty-specs/")` belt-and-suspenders filter, the `seen`/dedup loop, and the FR-007/#2274 **content re-check second pass** (`git diff <planning_tip> HEAD -- <path>`). Only the first-pass diff *call* delegates; everything after it is unchanged.

### Subtask T011 – Repoint `acceptance._changed_workflow_files` (the 5th copy)
- File: `src/specify_cli/acceptance/__init__.py` (~L1088-1116). Replace the inline `merge-base HEAD <base>` + `diff --name-only --diff-filter=AMR <mb>...HEAD -- .github/workflows` with `merge_base_changed_files(worktree, base_ref, pathspec=".github/workflows", diff_filter="AMR")`.
- The current three-dot `<mb>...HEAD` is byte-equivalent to the convenience's two-arg `mb HEAD` **because `mb` is an ancestor of HEAD** — add/keep a test pinning this equivalence for this site. Preserve the `sorted({...})` return shape.

### Subtask T012 – Verify + closeout gate
- Run the `stale_check`, `tasks_shared` (lane-hygiene content-diff), and `acceptance` workflow-evidence suites — green, no expected-value edits.
- **Grep-verify zero residual copies** (SC-001/NFR-002): `git merge-base` + `git diff --name-only` in the 5 site files return only helper calls (the `--is-ancestor`, `--cached`, and non-merge-base diffs are legitimately different and stay).
- **Aggregate closeout** (mission-level): full `tests/architectural/` sweep; `pytest tests/architectural/test_no_legacy_terminology.py`; `ruff check .`; `mypy` on all touched files.

## Branch Strategy

- Planning/base = merge target = `fix/merge-base-diff-ssot`. `spec-kitty agent action implement WP03 --agent <name>` (depends on WP01).

## Definition of Done

- [ ] All three sites route through the WP01 surface; per-site behaviour preserved (set/list/sorted returns; degradation).
- [ ] `tasks_shared` filter+dedup+content re-check preserved verbatim; `acceptance` three-dot↔two-arg equivalence pinned.
- [ ] `stale_check` dead-symbol/arch guard updated and green.
- [ ] Grep shows zero residual merge-base/diff copies across all 5 sites; `tests/architectural/` + terminology + ruff + mypy all clean.

## Risks & Reviewer Guidance

- Reviewer: verify T010 did NOT drop the content re-check second pass (that would reintroduce the #2274 false-positive-after-rebase bug). Verify T011's equivalence rests on `mb` being an ancestor of HEAD. Verify the god-modules gained no scope beyond the single repoint.

## Activity Log

- 2026-07-09T22:56:43Z – claude:sonnet:python-pedro:implementer – shell_pid=2503977 – Assigned agent via action command
- 2026-07-09T23:21:02Z – claude:sonnet:python-pedro:implementer – shell_pid=2503977 – Ready (handoff completed by orchestrator after implementer loop-stalled on full arch sweep): 3 repoints committed c7dbb1ff5; acceptance diff_filter=AMR + sorted() preserved; tasks_shared content re-check 2nd pass preserved verbatim; stale_check _git_* symbols fully removed (no dead-symbol guard red); only residual merge-base is --is-ancestor (out of scope). ruff exit 0; 85 affected tests green. REVIEWER: scrutinize test_tasks_shared_seam.py + test_acceptance_regressions.py edits for NFR-001; run full tests/architectural/ sweep (not completed inline).
- 2026-07-09T23:21:46Z – claude:opus:reviewer-renata:reviewer – shell_pid=2624934 – Started review via action command
