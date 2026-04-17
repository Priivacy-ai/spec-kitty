---
work_package_id: WP01
title: Charter Ownership Invariant Test
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ownership-consolidation-and-neutrality-hardening-01KPD880
base_commit: 443e4dc7b2f58b49bf9a4b7bfa6862272336c41d
created_at: '2026-04-17T09:22:57.402818+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 — Foundational
assignee: ''
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "9746"
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/test_charter_ownership_invariant.py
execution_mode: code_change
owned_files:
- tests/charter/test_charter_ownership_invariant.py
tags: []
---

# Work Package Prompt: WP01 – Charter Ownership Invariant Test

## Objective

Install an executable invariant that asserts **exactly one real definition** of `build_charter_context` and `ensure_charter_bundle_fresh` exists across `src/`. This is the machine-enforced form of SC-001 and the tripwire that will catch any future PR that silently reintroduces duplicate ownership.

## Context

A baseline audit (research.md R-001) found:

- `build_charter_context` defined once at `src/charter/context.py:67`.
- `ensure_charter_bundle_fresh` defined once at `src/charter/sync.py:66`.

The codebase already satisfies the invariant. This WP installs the test that keeps it true. The contract is spelled out in detail at `/Users/robert/spec-kitty-dev/charter/spec-kitty/kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/charter-ownership-invariant-contract.md`.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. When the runtime dispatches this WP, the execution worktree will be allocated per the lane computed by `finalize-tasks` and `lanes.json`. Do not guess worktree paths — consume the resolver output.

## Implementation Sketch

### Subtask T001 — Author the invariant test file

**File**: `tests/charter/test_charter_ownership_invariant.py` (new, ~90 lines).

Follow the skeleton in `contracts/charter-ownership-invariant-contract.md` section "Machine-enforced assertion" verbatim, with the following concrete expectations:

- Module-level constant `CANONICAL_OWNERS: dict[str, str]` with exactly these two entries:
  ```python
  CANONICAL_OWNERS: dict[str, str] = {
      "build_charter_context": "src/charter/context.py",
      "ensure_charter_bundle_fresh": "src/charter/sync.py",
  }
  ```
- Helper `_find_defs(repo_root: Path, name: str) -> list[Path]` walks `src/**/*.py`, excludes `__pycache__` and `.worktrees`, parses each file with `ast.parse`, and collects `FunctionDef` / `AsyncFunctionDef` nodes whose `name` matches — at **any nesting level** (use `ast.walk`, not just module-level).
- A `repo_root` pytest fixture (or module-level derivation via `pathlib.Path(__file__).resolve().parents[N]`) that lands on the repo root regardless of whether tests run from the repo root or a worktree.
- The single test case `test_charter_ownership_invariant(repo_root)` iterates the registry and fails with a message naming every file containing a matching `FunctionDef` plus the canonical location, following the failure-output format in the contract.

**Error message shape** (required — reviewers will grep for it):

```
Charter ownership invariant violated for 'build_charter_context':
  canonical location: src/charter/context.py
  definitions found in:
    src/charter/context.py            (canonical)
    src/legacy/charter_helper.py     (DUPLICATE — remove or rename)
```

The formatting does not need to be byte-exact, but it MUST name each offending file and identify the canonical location.

### Subtask T002 — Verify on baseline

Run `pytest tests/charter/test_charter_ownership_invariant.py -v` in the worktree. Expected: **pass**. If it fails on the baseline, do NOT modify the test to accommodate the failure — root-cause the unexpected duplicate and raise it as a blocker.

### Subtask T003 — Document the registry update protocol

Add a docstring at the top of the test file explaining:

- The registry is explicitly **narrow** in this mission (only two entries).
- Adding a new canonical function name to `CANONICAL_OWNERS` is a per-mission decision — never add one just to accommodate a failing test.
- The fix for any failure is **always** to consolidate back to the canonical location, never to add an exception.
- The `Non-contract` bullet from the contract applies: class-attached methods with the same name (`Foo.build_charter_context`) are NOT counted — the invariant is module-level free functions only. If this invariant ever needs to extend to methods, that is a new contract, not an ad-hoc test modification.

## Files

- **New**: `tests/charter/test_charter_ownership_invariant.py`

## Definition of Done

- [ ] Test file exists at the specified path.
- [ ] `pytest tests/charter/test_charter_ownership_invariant.py -v` passes in the worktree.
- [ ] `mypy --strict tests/charter/test_charter_ownership_invariant.py` passes (type hints on helpers required).
- [ ] Docstring explains the registry-update protocol per T003.
- [ ] No changes to `src/charter/` or `src/specify_cli/charter/` — this WP is test-only.

## Risks

- **Path resolution**: `pathlib.Path(__file__).resolve().parents[N]` with the wrong `N` will land outside the repo root and cause the test to report zero hits for everything. Prefer a `conftest.py`-provided `repo_root` fixture, or resolve via `Path.cwd()` then walk up until finding `pyproject.toml`.
- **Worktree false positives**: If the worktree is at `.worktrees/charter-ownership-consolidation-and-neutrality-hardening-01KPD880-lane-a/`, ensure the `src/` walk still finds the expected canonical files. It should, because the worktree is a full checkout.

## Reviewer Checklist

- [ ] `CANONICAL_OWNERS` contains exactly the two entries above, no more.
- [ ] `_find_defs` uses `ast.walk` (catches nested definitions) and excludes `__pycache__`.
- [ ] Failure message names both the canonical location and all offending files.
- [ ] Docstring covers the three protocol points in T003.
- [ ] Test passes on the clean baseline.

## Activity Log

- 2026-04-17T09:22:58Z – claude:sonnet-4-6:implementer:implementer – shell_pid=5163 – Assigned agent via action command
- 2026-04-17T09:35:41Z – claude:sonnet-4-6:implementer:implementer – shell_pid=5163 – Ready for review: invariant passes on baseline, mypy --strict clean
- 2026-04-17T09:39:16Z – claude:opus-4-6:reviewer:reviewer – shell_pid=9746 – Started review via action command
