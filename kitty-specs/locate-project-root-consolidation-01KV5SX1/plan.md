# Implementation Plan: locate_project_root Split-Brain Consolidation

**Branch**: `feat/locate-project-root-consolidation` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)  
**Mission ID**: 01KV5SX17ERG3B9YEVJ1NF6FX9  
**Input**: Feature specification from `kitty-specs/locate-project-root-consolidation-01KV5SX1/spec.md`

---

## Summary

Replace the 7-line `.kittify` walk body in `src/specify_cli/core/project_resolver.py::locate_project_root` with a deferred-import delegation shim into the authoritative `src/specify_cli/core/paths.py::locate_project_root`. No caller import-site changes are needed. Add tests that cover all three resolution paths (env-var authoritative, worktree pointer, normal walk) for `project_resolver.locate_project_root` and targeted tests for `get_project_root_or_exit` in a worktree filesystem and `spec-kitty lint` under `SPECIFY_REPO_ROOT`. This closes a behavioral divergence active since commit `2e071e8ad` (2026-05-31, #1534) and documented as issue #1971.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pytest, mypy (strict mode), ruff, typer, pathlib (stdlib)  
**Storage**: N/A  
**Testing**: pytest with ≥90% coverage for modified and new code; `mypy --strict` zero-error; `ruff check` zero-violation; existing test suite must remain green  
**Target Platform**: Linux, macOS, Windows 10+ (CLI tool)  
**Project Type**: Single Python package (`src/specify_cli/`)  
**Performance Goals**: Deferred import must not measurably increase module load time (fires only at call time, not at import time)  
**Constraints**: No caller import-site changes; no `# noqa` / `# type: ignore` suppression; deferred import is mandatory (not module-level) per C-001; `resolve_template_path` in `project_resolver.py` is out of scope per C-003  
**Scale/Scope**: 1 production file changed (~7 LOC replaced), 3 test files added/modified, ~40–60 lines of new test code  

---

## Charter Check

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | This mission targets the project's minimum supported runtime |
| mypy --strict | REQUIRED | All new and modified files must pass with zero errors |
| ruff check | REQUIRED | All new and modified files must pass with zero violations |
| ≥90% coverage for new code | REQUIRED | Three test concerns (IC-02, IC-03, IC-04) cover all new paths |
| No import cycles | PASS | Falsifier paradigm confirmed: deferred import inside function body breaks the cycle; `paths.py` does not import `project_resolver.py`; chain is a straight DAG |
| No blanket suppression | REQUIRED | No `# noqa`, `# type: ignore` additions permitted |
| Caller API preserved | REQUIRED | Public contract of `project_resolver.locate_project_root` unchanged: signature `(start: Path | None = None) -> Path | None` |

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/locate-project-root-consolidation-01KV5SX1/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── tasks.md             # Phase 2 output (spec-kitty.tasks — not created here)
└── tasks/               # Work packages (spec-kitty.tasks — not created here)
```

### Source Code (changed files)

```
src/specify_cli/core/
└── project_resolver.py          # CHANGED: replace walk body with deferred delegation

tests/runtime/
└── test_project_resolver.py     # CHANGED: add env-var, worktree, normal-walk tests

tests/specify_cli/cli/
└── test_helpers.py              # CHANGED OR CREATED: add worktree test for get_project_root_or_exit

tests/specify_cli/cli/commands/
└── test_lint.py                 # CHANGED OR CREATED: add SPECIFY_REPO_ROOT test for lint_command
```

**Unchanged** (confirmed by Falsifier + C-002 + C-003):
- `src/specify_cli/core/paths.py` — authoritative implementation, no change
- `src/specify_cli/cli/helpers.py` — caller, no import-site change
- `src/specify_cli/cli/commands/lint.py` — caller, no import-site change
- `src/specify_cli/compat/planner.py` — caller, no import-site change
- `src/specify_cli/core/__init__.py` — re-export shim, no change

---

## Implementation Concern Map

### IC-01 — Production Delegation Shim

- **Purpose**: Replace the 7-line `.kittify` walk body in `project_resolver.locate_project_root` with a single deferred-import call to `paths.locate_project_root`, making the function a transparent authority-preserving shim with no behavioral logic of its own.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, C-001, C-002, C-003, C-006
- **Affected surfaces**: `src/specify_cli/core/project_resolver.py` (lines 8–40 approximately; `locate_project_root` function only — `resolve_template_path` is untouched)
- **Sequencing/depends-on**: none (can be implemented first; tests in IC-02 through IC-04 depend on this)
- **Risks**: The deferred import pattern must be verified to not regress the module-level import chain. The existing docstring (explaining why the walk was separate) must be replaced with a new docstring explaining the shim rationale and referencing issue #1971 per C-006.

**Canonical implementation shape:**
```python
def locate_project_root(start: Path | None = None) -> Path | None:
    """Delegates to the authoritative implementation in :mod:`specify_cli.core.paths`.

    All resolution authority — ``SPECIFY_REPO_ROOT`` env-var check, git worktree
    ``.git`` pointer following, and ``.kittify`` directory walk — lives in
    :func:`specify_cli.core.paths.locate_project_root`.

    The import is deferred to the function body (not module-level) to preserve
    the import-cycle safety established in WP05 (#1965): ``core/__init__.py``
    imports from this module, and a module-level import of ``paths`` here could
    re-trigger ``specify_cli`` package initialisation before it finishes loading.
    The deferred pattern fires only at call time and is already used by
    ``paths.py`` itself for its own internal deferred imports. (#1971)
    """
    from specify_cli.core.paths import locate_project_root as _authoritative
    return _authoritative(start)
```

---

### IC-02 — Unit Tests: project_resolver.locate_project_root

- **Purpose**: Add three tests covering the three resolution paths that the current `test_project_resolver.py` does not cover for `project_resolver.locate_project_root` — env-var authoritative, worktree pointer, and normal `.kittify` walk — ensuring any future reversion to a walk-body is immediately caught.
- **Relevant requirements**: FR-008, NFR-001, NFR-005
- **Affected surfaces**: `tests/runtime/test_project_resolver.py`
- **Sequencing/depends-on**: IC-01 (tests must pass against the delegation shim, not the walk body)
- **Risks**: Worktree test requires constructing a fake git worktree filesystem (a `.git` file pointing at a `.git/worktrees/<name>` directory structure). Use `tmp_path` fixtures; do not modify the real repo. Env-var test must restore env after each test (use `monkeypatch.setenv`).

**Tests to add:**
1. `test_env_root_authoritative` — set `SPECIFY_REPO_ROOT` to `tmp_path` (no `.kittify` there, CWD elsewhere); assert result equals `tmp_path`
2. `test_worktree_pointer_resolution` — construct fake worktree with `.git` file pointing at main repo that has `.kittify`; assert result equals main repo root
3. `test_normal_kittify_walk` — existing test already covers this; verify it still passes; add a CWD-variation to confirm `start` parameter is respected

---

### IC-03 — Integration Test: get_project_root_or_exit in Worktree

- **Purpose**: Add one test that exercises `get_project_root_or_exit` in a real fake-worktree filesystem context (not mocked), confirming it no longer exits 1 when the main repo has `.kittify` and the caller is in a worktree directory.
- **Relevant requirements**: FR-005, NFR-001, NFR-005
- **Affected surfaces**: `tests/specify_cli/cli/test_helpers.py` (create if absent)
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Must use `typer.testing.CliRunner` or equivalent to capture exit codes without actually terminating the test process. The fake worktree filesystem setup is the same pattern as IC-02 — consider a shared `pytest.fixture` if both test files are adjacent.

**Test to add:**
- `test_get_project_root_or_exit_succeeds_in_worktree` — fake worktree CWD, main repo has `.kittify`; call `get_project_root_or_exit(start=worktree_cwd)`; assert returns main repo path (not None, no exit)

---

### IC-04 — Integration Test: lint_command with SPECIFY_REPO_ROOT

- **Purpose**: Add one test that exercises `lint_command` with `SPECIFY_REPO_ROOT` set and CWD outside the project directory, confirming `ruff`/`mypy` receive the correct working directory (not `Path.cwd()`).
- **Relevant requirements**: FR-006, NFR-001, NFR-005
- **Affected surfaces**: `tests/specify_cli/cli/commands/test_lint.py` (create if absent, or add to existing)
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: `lint_command` spawns real `ruff`/`mypy` subprocesses. The test should mock the subprocess call (e.g., `subprocess.run`) and assert it was called with `cwd=` matching the `SPECIFY_REPO_ROOT` value, rather than executing real linters. Use `monkeypatch.setenv` for `SPECIFY_REPO_ROOT`.

**Test to add:**
- `test_lint_uses_spec_repo_root_as_cwd` — set `SPECIFY_REPO_ROOT=/fake/project`, mock `subprocess.run`, invoke `lint_command`; assert subprocess called with `cwd=Path("/fake/project")`

---

## Sequencing Summary

```
IC-01 (shim)
  └── IC-02 (unit tests for project_resolver)
        ├── IC-03 (get_project_root_or_exit worktree test)
        └── IC-04 (lint SPECIFY_REPO_ROOT test)
```

IC-01 is a prerequisite. IC-02 must pass before IC-03 and IC-04 are meaningful. IC-03 and IC-04 are independent of each other and can be developed in parallel.
