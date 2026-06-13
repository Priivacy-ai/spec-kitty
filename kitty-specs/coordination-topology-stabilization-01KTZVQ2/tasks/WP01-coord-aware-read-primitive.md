---
work_package_id: WP01
title: Coordination-Aware Read Primitive
dependencies: []
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T048
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "12342"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/software_dev/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/software_dev/_substantive.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/missions/software_dev/mission.py
- tests/specify_cli/test_is_committed_coord_aware.py
- tests/architectural/test_no_primary_anchored_gates.py
priority: P1-Critical
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

This scopes your governance context, toolguides, and behavioral boundaries for this work package.

---

## Objective

Add a `placement`-aware overload to `is_committed()` in `src/specify_cli/missions/software_dev/_substantive.py` so that all planning-phase gate checks treat artifacts committed to the mission's coordination branch as valid committed artifacts — not just those on primary `HEAD`.

This is the foundational fix for **issue #1884** and is a prerequisite for WP06 (accept gate) and WP09 (ff-merge treadmill). Every other gate IC builds on this primitive.

**Do not start implementation without first checking PR #1895** (branch `stijn-dejongh/spec-kitty`, mission `name-vs-authority-remediation-01KTYGTE`) — it may already contain a partial fix for the FR-001 slice. If it has landed, scope this WP to extend/harden rather than re-implement.

---

## Context

### The Bug (Issue #1884)

`is_committed(file, repo_root)` at `_substantive.py:214–239` calls:
```
git show HEAD:<relative-path>
```
This always anchors to the primary checkout's `HEAD`. When the coordination topology is active (mission has a `kitty/mission-<slug>-<mid8>` coordination branch), spec/plan/tasks artifacts are committed to that branch — not to `HEAD`. The gate sees them as uncommitted, blocks `setup-plan`, and forces a workaround of also committing to primary `main`.

### The Fix Design

Add a `placement: PlacementResult | None = None` parameter. When `placement` is provided and a coordination branch exists, check `git cat-file -e <coord_ref>:<rel>` first. Fall back to `HEAD` for flat topology or when coord branch lookup fails.

```python
# Before:
def is_committed(file: Path, repo_root: Path) -> bool:
    ...

# After:
def is_committed(
    file: Path,
    repo_root: Path,
    placement: "PlacementResult | None" = None,
) -> bool:
    if placement is not None:
        coord_ref = placement.coordination_branch_ref  # e.g. "kitty/mission-foo-01KTABCD"
        rel = file.relative_to(repo_root)
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{coord_ref}:{rel}"],
            cwd=repo_root, capture_output=True,
        )
        if result.returncode == 0:
            return True
    # Fall back to primary HEAD
    rel = file.relative_to(repo_root)
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{rel}"],
        cwd=repo_root, capture_output=True,
    )
    return result.returncode == 0
```

**Key invariant**: OR logic — a file committed to either branch is considered committed. This is backward-compatible: flat-topology callers that pass no `placement` get the existing behavior.

### PlacementResult Location

`resolve_placement_only` already exists in `src/specify_cli/placement/`. Import it; do not re-implement placement logic in `_substantive.py`.

---

## Subtasks

### T001 — Add placement-aware `is_committed()` overload in `_substantive.py`

1. Read `src/specify_cli/missions/software_dev/_substantive.py` lines 200–260.
2. Read `src/specify_cli/placement/__init__.py` (or wherever `PlacementResult` is exported) to confirm the type shape.
3. Modify `is_committed()` to accept `placement: PlacementResult | None = None`.
4. Add the `git cat-file -e <coord_ref>:<rel>` check before the existing `HEAD` check.
5. Guard against `AttributeError`/`None` on `placement.coordination_branch_ref` — if the attribute is absent or None, fall through to `HEAD` check.
6. Type-annotate the new parameter using `TYPE_CHECKING` guard if needed to avoid circular imports.
7. Run `mypy --strict src/specify_cli/missions/software_dev/_substantive.py` — zero issues required.

**Do not** change the function signature in a way that breaks existing callers (the new param is keyword-only with `None` default).

### T002 — Migrate `setup-plan` entry gate to use coord-aware `is_committed()`

1. Grep for callers of `is_committed(` in `src/specify_cli/cli/commands/agent/mission.py`.
2. Identify the setup-plan entry gate (the call that checks whether `spec.md` is committed).
3. Resolve the `PlacementResult` for the current mission at that call site (use `resolve_placement_only` or the existing resolver already in scope).
4. Pass `placement=placement` to `is_committed()`.
5. If `resolve_placement_only` raises on flat topology (no coordination branch), catch and pass `placement=None` (safe fallback).

### T003 — Convert `_planning_commit_worktree` silent fallbacks to structured errors

1. Read `src/specify_cli/missions/software_dev/mission.py` lines 595–625.
2. Locate the silent fallbacks in `_planning_commit_worktree` — these return `False` or silently swallow exceptions instead of surfacing the cause.
3. Replace silent `return False` / bare `except` clauses with logged structured errors (use `rich.console.Console().print_exception()` or existing logger pattern; do not use `print()`).
4. The fallback must still result in a recoverable state (don't raise hard; log and return False), but the error must be visible in the CLI output.

### T004 — Regression test: setup-plan passes with spec only on coord branch

File: `tests/specify_cli/test_is_committed_coord_aware.py` (new file)

Write a pytest test that:
1. Creates a temporary git repo with a coordination branch (`kitty/mission-test-01AABBCC`).
2. Commits a mock `spec.md` to the coordination branch only (not to `main` HEAD).
3. Calls `is_committed(spec_path, repo_root, placement=mock_placement)`.
4. Asserts `True`.
5. Calls `is_committed(spec_path, repo_root)` (no placement) → asserts `False` (backward-compat check).
6. Also asserts that a file committed to both branches returns `True` in both call forms.

Use `subprocess.run(["git", ...])` to set up the fixture git state — do not use `GitPython` for the fixture if it adds a dependency not already in test scope.

### T048 — Pre-flight: verify PR #1895 scope before starting implementation

Run this before writing any code:

1. Query PR #1895: `gh pr view 1895 --json state,title,files | jq '{state,title,files:[.files[].path]}'`
2. Scan the file list for changes to `_substantive.py`, `is_committed`, or `_planning_commit_worktree`.
3. If PR #1895 is open and overlaps this WP's scope:
   - Read its diff: `gh pr diff 1895 | head -200`
   - Scope your implementation to extend/harden rather than re-implement.
   - Note the overlap explicitly in your PR description.
4. If PR #1895 is closed/merged: confirm its changes are incorporated in `main` before beginning, then proceed normally.
5. Also check WP03 — PR #1895 is cited there too. Share findings with WP03 implementer if working in parallel.

**This subtask gates T001 — do not write code until the PR disposition is known.**

Also applies to WP03 (see WP03 risk section): WP01 implementer should relay the PR #1895 status to the WP03 implementer if both WPs are dispatched simultaneously.

### T005 — Architectural lint: no new callers of the 2-arg `is_committed` form

File: `tests/architectural/test_no_primary_anchored_gates.py` (new file)

Write a pytest test that:
1. Uses `ast.parse` + `ast.walk` to find all `Call` nodes where the function is `is_committed`.
2. Asserts that every call site in `src/specify_cli/` passes either 0 or 2 positional args with the `placement` keyword argument, OR has already been migrated to the 3-arg form.
3. Allows a grace list for the existing 2-arg call in the wrapper itself.

The test fails if a new caller uses the old 2-arg form without a `placement=` argument. This is the ratchet — it prevents future callers from silently regressing.

---

## Branch Strategy

**Planning base**: `main`
**Merge target**: `main`
**Worktree**: Allocated by `finalize-tasks` via `lanes.json`. Run:
```bash
spec-kitty agent action implement WP01 --agent <name>
```
to enter the correct lane worktree. Do NOT manually create a branch or worktree.

---

## Definition of Done

- [ ] PR #1895 disposition verified before any code is written (T048)
- [ ] `is_committed()` accepts `placement: PlacementResult | None = None`
- [ ] Coord-branch lookup uses `git cat-file -e <coord_ref>:<rel>`
- [ ] Flat-topology callers (no `placement`) behave identically to before
- [ ] `setup-plan` entry gate passes `placement` to `is_committed()`
- [ ] `_planning_commit_worktree` silent fallbacks now log structured errors
- [ ] `test_is_committed_coord_aware.py` passes (new)
- [ ] `test_no_primary_anchored_gates.py` passes (new ratchet)
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues
- [ ] No `# noqa` or `# type: ignore` added

## Risks

- **Circular import**: `PlacementResult` import may create a circular dependency. Use `TYPE_CHECKING` guard and string annotation.
- **PR #1895 collision**: If PR #1895 has already partially fixed the FR-001 slice, extend rather than overwrite. Read its diff before writing any code.
- **`AttributeError` on None placement**: `placement` fields may be None even when the object is not None — guard each attribute access individually.

## Reviewer Guidance

Focus review on:
1. The `git cat-file -e` OR-logic — confirm it cannot produce false-positives.
2. The `placement=None` default — confirm it is truly backward-compatible at every existing call site.
3. The architectural ratchet test — confirm it would catch a regressing 2-arg call.

## Activity Log

- 2026-06-13T07:58:42Z – claude:sonnet-4-6:implementer:implementer – shell_pid=54198 – Assigned agent via action command
- 2026-06-13T08:10:25Z – claude:sonnet-4-6:implementer:implementer – shell_pid=54198 – Ready for review: coord-aware is_committed() implemented
- 2026-06-13T08:11:09Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=12342 – Started review via action command
- 2026-06-13T08:14:47Z – user – shell_pid=12342 – Review passed: coord-aware is_committed() correct, flat topology preserved, architectural ratchet in place. --force used: kitty-specs/ commits on lane branch are administrative no-op restore commits; file state identical to mission branch.
