---
work_package_id: WP01
title: Canonical merge-base/diff surface + direct tests
dependencies: []
requirement_refs:
- FR-001
- FR-006
tracker_refs: []
planning_base_branch: fix/merge-base-diff-ssot
merge_target_branch: fix/merge-base-diff-ssot
branch_strategy: Planning artifacts for this mission were generated on fix/merge-base-diff-ssot. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-base-diff-ssot unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
shell_pid: "2495818"
history:
- timestamp: '2026-07-09T20:30:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/core/vcs/
create_intent:
- tests/specify_cli/core/vcs/test_merge_base_diff_surface.py
execution_mode: code_change
mission_id: 01KX44SDZPWMA4N7RPKNR3TQT1
owned_files:
- src/specify_cli/core/vcs/git.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This applies your identity, governance scope, boundaries, and initialization declaration for this work package. Do not read further or touch code until the profile is loaded and its initialization declaration is acknowledged.

# Work Package Prompt: WP01 – Canonical merge-base/diff surface + direct tests

## Objective

Create the single source of truth for the `git merge-base` → `git diff --name-only` idiom in `src/specify_cli/core/vcs/git.py`, so the five current copies can consolidate onto it. This WP delivers **only the surface + its direct tests**; the repoints are WP02/WP03. Everything downstream depends on this WP.

## Context & Constraints

- Read `../spec.md` (FR-001, FR-006), `../plan.md` (IC-01), `../research.md` (the 5 API-shape decisions), and `../contracts/merge-base-diff-surface.md` (the behavioural contract) before coding.
- `core/vcs/git.py` already exists (~1277 LOC, `GitVCS` + module-level git helpers). Add three **module-level** functions near the other module-level helpers. Do NOT touch `GitVCS`'s internal merge-base at ~L415 (that is a different, out-of-scope comparison — C-004).
- Standardize subprocess kwargs: `capture_output=True, text=True, encoding="utf-8", errors="replace", check=False` (C-002).
- ruff + mypy zero issues; complexity ≤15 (NFR-003). New-code coverage ≥ repo gate (NFR-004).

## Subtasks & Detailed Guidance

### Subtask T001 – `git_merge_base`
- **Signature**: `git_merge_base(repo: Path, ref_a: str, ref_b: str) -> str | None`
- Runs `git merge-base <ref_a> <ref_b>` in `repo`. Return the stripped SHA on success; `None` on non-zero exit OR empty stdout. Never raise for a git non-zero exit.

### Subtask T002 – `git_diff_names`
- **Signature**: `git_diff_names(repo: Path, base: str, head: str, *, pathspec: str | None = None, diff_filter: str | None = None) -> tuple[str, ...]`
- Runs `git diff --name-only [--diff-filter=<diff_filter>] <base> <head> [-- <pathspec>]` in `repo`. **Use the two-arg form `<base> <head>`** (equivalent to `<base>..<head>` for `--name-only`; the range-string callers switch to this). Return a tuple of stripped, non-empty paths; empty tuple on non-zero exit.
- `pathspec` → `-- <pathspec>`; `diff_filter` → `--diff-filter=<value>`. Both optional/None → omitted.

### Subtask T003 – `merge_base_changed_files` (HEAD-relative convenience)
- **Signature**: `merge_base_changed_files(worktree: Path, base_ref: str, *, pathspec: str | None = None, diff_filter: str | None = None) -> tuple[str, ...]`
- `mb = git_merge_base(worktree, "HEAD", base_ref)`; if `mb is None` → return `()`; else `git_diff_names(worktree, mb, "HEAD", pathspec=pathspec, diff_filter=diff_filter)`.
- **Do NOT** add a branch-target variant here — `tasks_dependency_graph` (WP02) must call the primitives directly, not this convenience.

### Subtask T004 – Direct tests: core branches
- New file `tests/specify_cli/core/vcs/test_merge_base_diff_surface.py`.
- Cover: normal diff (N files), empty merge-base stdout → `None`/`()`, `git merge-base` non-zero → `None`/`()`, `git diff` non-zero → `()`, `pathspec` restricts output, `diff_filter` passes `--diff-filter`. Prefer a real temp git repo for behaviour; mock subprocess only where a failure exit is hard to stage.

### Subtask T005 – Direct tests: F1 fence + equivalence
- **Non-HEAD branch-target** (fences F1): build a temp repo with commits on a side branch that HEAD does NOT have; assert `git_diff_names(repo, mb, side_branch)` returns the side-branch files — proving the primitive diffs an arbitrary `head`, not HEAD. This is the test that makes a lazy swap of `tasks_dependency_graph` to the HEAD convenience fail red.
- **Range↔two-arg equivalence**: on the same real repo, assert `git_diff_names(repo, mb, "HEAD")` (two-arg) == the paths from a raw `git diff --name-only <mb>..HEAD`. Documents the silent rewrite three sites undergo.

## Branch Strategy

- **Planning/base branch**: `fix/merge-base-diff-ssot` · **Final merge target**: `fix/merge-base-diff-ssot` (later PR to origin/main).
- Execution worktree is allocated per computed lane from `lanes.json`; run `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done

- [ ] Three functions added to `core/vcs/git.py`; ruff + mypy clean; complexity ≤15.
- [ ] All 8 FR-006 branches (normal, empty-mb, mb-fail, diff-fail, pathspec, diff_filter, non-HEAD branch-target, range↔two-arg equivalence) covered by direct tests, green.
- [ ] `GitVCS` internal merge-base (~L415) untouched.
- [ ] No repoints in this WP (WP02/WP03 own those).

## Risks & Reviewer Guidance

- Reviewer: confirm the two-arg `<base> <head>` form is used (not `<base>..<head>` range strings) and that the equivalence test actually pins it. Confirm the branch-target test uses `head != HEAD`. Confirm `diff_filter`/`pathspec` both thread through the convenience.

## Activity Log

- 2026-07-09T22:45:40Z – claude:sonnet:python-pedro:implementer – shell_pid=2485496 – Assigned agent via action command
- 2026-07-09T22:50:41Z – claude:sonnet:python-pedro:implementer – shell_pid=2485496 – Ready for review: 3-fn surface + direct tests incl. F1 branch-target + range/two-arg equivalence; ruff+mypy clean; git diff --name-only --diff-filter=AMR HEAD | rg '\.py$' | xargs -r uv run ruff check -> exit 0
- 2026-07-09T22:51:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=2495818 – Started review via action command
- 2026-07-09T22:55:21Z – user – shell_pid=2495818 – Review passed: 3 module-level fns (git_merge_base, git_diff_names, merge_base_changed_files) with exact signatures + None/() degradation, never raise on git non-zero. git_diff_names uses TWO-ARG form cmd.extend([base,head]) (verified in code, not range string); standardized subprocess kwargs (encoding=utf-8,errors=replace,check=False). GitVCS internal merge-base ~L415 UNTOUCHED (single diff hunk appended at L1275). NO repoints (surface-only per scope). F1 non-HEAD branch-target test is REAL: commits src/side_only.py on side branch, checks out main, asserts git_diff_names(repo,mb,'HEAD')==() AND git_diff_names(repo,mb,'side')==('src/side_only.py',) with head=side != HEAD, so a lazy HEAD-convenience swap fails red. Range/two-arg equivalence test REAL: compares helper two-arg to raw 'git diff --name-only <mb>..HEAD' on a live temp repo. 14/14 tests green; ruff exit 0; mypy clean on the 3 new fns (L905 no-any-return in is_repo confirmed pre-existing on base). Scope clean: git.py + new test file + __init__.py only. Filled mission issue-matrix (#2450/#2438 -> in-mission) to clear the approval gate.
