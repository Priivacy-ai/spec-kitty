# locate_project_root Split-Brain Consolidation

**Mission ID:** 01KV5SX17ERG3B9YEVJ1NF6FX9  
**Mission Type:** software-dev  
**Status:** Implementation Ready  
**Parent Issue:** [#1971](https://github.com/Priivacy-ai/spec-kitty/issues/1971) · [#1932](https://github.com/Priivacy-ai/spec-kitty/issues/1932)

---

## Overview

Three implementations of `locate_project_root` currently exist with divergent behavior. The authoritative implementation in `core/paths.py` honors the `SPECIFY_REPO_ROOT` environment variable and follows git worktree pointers; a reduced implementation in `core/project_resolver.py` performs only a plain `.kittify` directory walk. The reduced implementation is re-exported by `core/__init__.py` and used by four callers — `cli/helpers.py`, `cli/commands/lint.py`, `compat/planner.py`, and `core/__init__.py` — which silently misresolve the project root in CI/CD environments and git worktrees.

This mission eliminates the split by making the reduced implementation delegate to the authoritative one via a deferred import (a pattern already established in `paths.py` itself), and by adding the test coverage that would have detected and prevented this divergence.

---

## Problem Statement

When a developer or automated system runs `spec-kitty` commands from inside a git worktree, or when `SPECIFY_REPO_ROOT` is set (the standard CI/CD override), the four callers of the reduced `locate_project_root` produce incorrect results:

- `get_project_root_or_exit` terminates with a misleading "project root not found" error, making `status`, `merge`, `review`, and other commands unusable from worktrees.
- The compatibility planner silently classifies the project as `NO_PROJECT`, causing migration gates and upgrade nags to bypass entirely.
- The `lint` command runs `ruff` and `mypy` with the wrong working directory, silently applying the wrong project configuration.

The divergence has been active since commit `2e071e8ad` (2026-05-31) when `SPECIFY_REPO_ROOT` support was added to `paths.py` without a corresponding update to `project_resolver.py`. It was acknowledged and tracked in commit `8431dd931` (2026-06-15) as issue #1971.

---

## User Scenarios & Testing

### Primary Scenario — Worktree Command Execution

**Actor:** Developer working in a git worktree (e.g., running `spec-kitty status` from `.worktrees/my-feature-01J6XW9K-lane-a/`)  
**Trigger:** Any `spec-kitty` CLI command that resolves the project root via `get_project_root_or_exit`  
**Current outcome:** Hard exit 1 with "Unable to locate the Spec Kitty project root (.kittify directory not found)" — even though the project exists in the main repo  
**Expected outcome after fix:** Command succeeds; root resolves to the main repo via the worktree `.git` file pointer

### Secondary Scenario — CI/CD with SPECIFY_REPO_ROOT

**Actor:** CI/CD pipeline with `SPECIFY_REPO_ROOT=/workspace/repo` set and working directory at `/workspace`  
**Trigger:** `spec-kitty lint` or any command routed through `cli/helpers.py`  
**Current outcome:** Root resolves to `None` (no `.kittify` at `/workspace`); `get_project_root_or_exit` exits 1; `lint` falls back to `Path.cwd()` as `ruff`/`mypy` working directory  
**Expected outcome after fix:** Root resolves to `SPECIFY_REPO_ROOT` value; all commands use the correct project directory

### Tertiary Scenario — Planner Migration Gate in Worktree

**Actor:** Any `spec-kitty` command that invokes the compatibility planner from a worktree session  
**Trigger:** `_plan_impl` with default `project_root_resolver`  
**Current outcome:** Planner receives `None` root → classifies project as `NO_PROJECT` → migration block and upgrade nag bypass silently  
**Expected outcome after fix:** Planner receives correct main repo root → project state classified accurately → migration gates fire as intended

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Every caller that imports `locate_project_root` from `specify_cli.core.project_resolver` or `specify_cli.core` receives the same resolution result as a caller that imports from `specify_cli.core.paths`, for all inputs and all environment conditions | Proposed |
| FR-002 | When `SPECIFY_REPO_ROOT` is set to an existing directory path, `locate_project_root` returns that path regardless of which import path the caller uses | Proposed |
| FR-003 | When the caller's working directory is inside a git worktree (`.git` is a file, not a directory), `locate_project_root` resolves to the main worktree root, regardless of which import path the caller uses | Proposed |
| FR-004 | The public contract of `project_resolver.locate_project_root` (function signature, return type `Path \| None`, and `start` parameter) is preserved unchanged — no caller import-site modification is required | Proposed |
| FR-005 | `get_project_root_or_exit` in `cli/helpers.py` succeeds (does not exit 1) when invoked from a git worktree where the main repo contains a `.kittify` directory | Proposed |
| FR-006 | `spec-kitty lint` uses the correct project root as the working directory for `ruff` and `mypy` when `SPECIFY_REPO_ROOT` is set | Proposed |
| FR-007 | The compatibility planner (`compat/planner.py`) correctly classifies project state when invoked from a git worktree or with `SPECIFY_REPO_ROOT` set, using the default `project_root_resolver` | Proposed |
| FR-008 | A test suite covering env-var resolution, worktree pointer resolution, and normal `.kittify` walk resolution exists for `project_resolver.locate_project_root` and passes | Proposed |
| FR-009 | A test covering `get_project_root_or_exit` behavior in a real worktree filesystem context (not mocked) exists and passes | Proposed |
| FR-010 | A test covering `spec-kitty lint` behavior when `SPECIFY_REPO_ROOT` is set and CWD is outside the project directory exists and passes | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | No existing passing test is broken by the change | 0 regressions | Proposed |
| NFR-002 | `mypy --strict` passes with zero new errors or warnings on all modified and new files | 0 type errors | Proposed |
| NFR-003 | `ruff check` passes with zero new violations on all modified and new files | 0 violations | Proposed |
| NFR-004 | The new delegation in `project_resolver.py` does not increase module import time measurably — the deferred import fires only at call time, not at module load time | No measurable import-time increase vs. baseline (deferred import inside function body fires at call time only, not at module load; absolute import time reflects full package init cost and is not a relevant comparator) | Proposed |
| NFR-005 | New test coverage for the modified and new code paths is ≥ 90% as measured by the project's standard coverage tooling | ≥ 90% line coverage | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The fix MUST use a deferred import (`from specify_cli.core.paths import locate_project_root as _authoritative` inside the function body) — not a module-level import — to preserve the import cycle safety that the WP05 author was guarding against | Proposed |
| C-002 | No caller import-site changes are permitted: all four callers (`cli/helpers.py`, `cli/commands/lint.py`, `compat/planner.py`, `core/__init__.py`) must continue importing from their current import paths without modification | Proposed |
| C-003 | The `resolve_template_path` function below `locate_project_root` in `project_resolver.py` must not be touched — it is unrelated to this mission | Proposed |
| C-004 | No `# noqa`, `# type: ignore`, or blanket suppression comments may be introduced to satisfy static analysis | Proposed |
| C-005 | The change scope is limited to `src/specify_cli/core/project_resolver.py` (production) and the test files enumerated in FR-008 through FR-010 | Proposed |
| C-006 | The architectural decision to use a deferred import as the cycle-break mechanism must be recorded in an inline docstring rationale in `project_resolver.py` so future contributors do not "fix" it back to a module-level import | Proposed |

---

## Assumptions

1. The deferred import pattern (`from X import Y` inside a function body) is safe in the Python 3.11+ runtime targeted by this project — confirmed by the existing use of the same pattern in `paths.py` itself (lines importing `git_ops` and `feature_dir_resolver`).
2. The four callers identified by the Debugger Debbie investigation are the complete set of callers of the reduced implementation. No additional callers were introduced between `8431dd931` and the implementation of this mission.
3. `tests/specify_cli/cli/test_helpers.py` either exists or can be created; if it does not exist, the worktree test for `get_project_root_or_exit` belongs in the closest existing test module for `cli/helpers.py`.
4. The `planner.py` caller uses an injectable `project_root_resolver` parameter — the fix closes the default-argument gap; callers that already inject a custom resolver are unaffected.

---

## Success Criteria

1. Running any `spec-kitty` CLI command from inside a git worktree no longer exits with "project root not found" when the main repo is a valid Spec Kitty project.
2. Setting `SPECIFY_REPO_ROOT` to a valid path causes all `spec-kitty` commands (including `lint`) to use that path as the project root, regardless of the current working directory.
3. The compatibility planner correctly identifies project state (STALE / COMPATIBLE / etc.) when invoked from a worktree or CI environment — migration gates and upgrade nags fire as expected.
4. The `project_resolver.py` source file contains no walk-body logic — only the deferred delegation and its docstring rationale.
5. All three resolution paths (env-var authoritative, worktree pointer, `.kittify` walk) have direct test coverage via `project_resolver.locate_project_root`, making future divergence immediately detectable.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `locate_project_root` | The function that resolves a Spec Kitty project's root directory. Three implementations exist pre-fix; one authoritative implementation exists post-fix. |
| `SPECIFY_REPO_ROOT` | Environment variable that, when set to an existing directory, provides an authoritative override for the project root location. Used by CI/CD pipelines and test harnesses. |
| Git worktree | A secondary working tree linked to a main repository via a `.git` file (not directory). The `.git` file contains a pointer to the main repository's `.git/worktrees/<name>` directory. |
| `.kittify` | The sentinel directory whose presence marks a Spec Kitty project root. The fallback search walks parent directories until it is found. |
| `project_resolver.py` | Module currently housing the reduced implementation. Post-fix, it contains only a deferred-import delegation shim. |
| `paths.py` | Module housing the authoritative implementation. Unchanged by this mission. |
| Deferred import | A Python import statement placed inside a function body rather than at module level, ensuring the import resolves at call time rather than at module load time — the mechanism that breaks the import cycle risk. |
