# Tasks: locate_project_root Split-Brain Consolidation

**Mission**: locate-project-root-consolidation-01KV5SX1  
**Branch**: `feat/locate-project-root-consolidation`  
**Merge target**: `feat/locate-project-root-consolidation`  
**Generated**: 2026-06-15T14:15:28Z  

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Replace `locate_project_root` walk body in `project_resolver.py` with deferred delegation shim | WP01 | No |
| T002 | Write rationale docstring in shim (C-006: deferred import pattern, #1971 reference) | WP01 | No |
| T003 | Verify `mypy --strict` and `ruff check` pass on modified `project_resolver.py` with zero violations | WP01 | No |
| T004 | Add `test_env_root_authoritative` to `test_project_resolver.py` | WP02 | [P] |
| T005 | Add `test_worktree_pointer_resolution` to `test_project_resolver.py` | WP02 | [P] |
| T006 | Verify existing `test_locate_project_root_and_template_resolution` still passes; add `start`-parameter variant | WP02 | [P] |
| T007 | Add `test_get_project_root_or_exit_succeeds_in_worktree` to `tests/specify_cli/cli/test_helpers.py` | WP03 | [P] |
| T008 | Add `test_lint_uses_spec_repo_root_as_cwd` to `tests/specify_cli/cli/commands/test_lint.py` | WP03 | [P] |
| T009 | Run full test suite, confirm zero regressions, ≥90% coverage for changed files | WP03 | No |
| T010 | Add `test_planner_default_resolver_in_worktree` to `tests/specify_cli/compat/test_planner.py` — exercises FR-007 | WP03 | [P] |

---

## Work Packages

### WP01 — Production Delegation Shim

**Goal**: Replace the 7-line `.kittify` walk body in `project_resolver.locate_project_root` with a deferred-import delegation shim into `paths.locate_project_root`, plus the rationale docstring required by C-006. Verify static analysis passes.  
**Priority**: P0 — must land before WP02 and WP03  
**Success criteria**: `project_resolver.locate_project_root` contains no walk logic; calling it with `SPECIFY_REPO_ROOT` set returns the env-var path; calling it from a worktree returns the main repo root; `mypy --strict` and `ruff check` report zero new violations  
**Estimated prompt size**: ~250 lines  
**Dependencies**: none

Subtasks:
- [x] T001 Replace `locate_project_root` walk body with deferred delegation shim (WP01)
- [x] T002 Write rationale docstring referencing #1971 and explaining deferred import pattern (WP01)
- [x] T003 Verify `mypy --strict` and `ruff check` pass with zero violations on modified file (WP01)

**Implementation sketch**: Read `src/specify_cli/core/project_resolver.py` lines 8–40. Replace `locate_project_root` body with a single deferred import + call. Preserve `resolve_template_path` below it verbatim. Update the function docstring to explain the shim contract and import-cycle rationale. Run `mypy --strict src/specify_cli/core/project_resolver.py` and `ruff check src/specify_cli/core/project_resolver.py`.  
**Risks**: Deferred import must be inside the function body, not at module level — a module-level import would reintroduce the cycle risk that blocked consolidation.  
**Prompt file**: `tasks/WP01-production-delegation-shim.md`

---

### WP02 — Unit Tests: project_resolver.locate_project_root

**Goal**: Add three tests to `tests/runtime/test_project_resolver.py` covering all three resolution paths of `project_resolver.locate_project_root`: env-var authoritative, worktree pointer, and normal `.kittify` walk. These tests make any future reversion to a walk body immediately detectable.  
**Priority**: P1  
**Success criteria**: Three new tests pass; existing tests pass; coverage for `project_resolver.py` reaches 100% for the `locate_project_root` function  
**Estimated prompt size**: ~300 lines  
**Dependencies**: WP01

Subtasks:
- [ ] T004 Add `test_env_root_authoritative` — `SPECIFY_REPO_ROOT` set to `tmp_path`, no `.kittify`, CWD elsewhere; assert result = `tmp_path` (WP02)
- [ ] T005 Add `test_worktree_pointer_resolution` — fake worktree with `.git` file pointing at main repo that has `.kittify`; assert result = main repo root (WP02)
- [ ] T006 Verify existing `test_locate_project_root_and_template_resolution` still passes; add `start`-parameter variant that passes CWD explicitly (WP02)

**Implementation sketch**: Use `tmp_path` fixtures throughout. For T004, `monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))`. For T005, create `worktree/.git` as a file containing `gitdir: /main_repo/.git/worktrees/test_lane`; create `/main_repo/.git/worktrees/test_lane/` and `/main_repo/.kittify/`. Call `from specify_cli.core.project_resolver import locate_project_root` in each test — not from `paths` — to exercise the shim.  
**Risks**: Worktree filesystem construction is non-trivial; consult `src/specify_cli/core/paths.py` worktree detection logic to understand the exact `.git` file format expected.  
**Prompt file**: `tasks/WP02-unit-tests-project-resolver.md`

---

### WP03 — Caller Integration Tests and Suite Validation

**Goal**: Add targeted tests for `get_project_root_or_exit` in a worktree context and for `lint_command` with `SPECIFY_REPO_ROOT` set, then run the full suite to confirm zero regressions and ≥90% coverage for all changed files.  
**Priority**: P2  
**Success criteria**: Two new tests pass; full suite has zero new failures; coverage gate met  
**Estimated prompt size**: ~300 lines  
**Dependencies**: WP01, WP02

Subtasks:
- [ ] T007 Add `test_get_project_root_or_exit_succeeds_in_worktree` — fake worktree CWD, main repo has `.kittify`; assert function returns main repo path, does not call `typer.Exit` (WP03)
- [ ] T008 Add `test_lint_uses_spec_repo_root_as_cwd` — `SPECIFY_REPO_ROOT` set, mock `subprocess.run`, invoke `lint_command`; assert subprocess called with correct `cwd` (WP03)
- [ ] T009 Run `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider`; confirm zero regressions; check coverage for `project_resolver.py`, `test_project_resolver.py`, `test_helpers.py`, `test_lint.py` (WP03)
- [ ] T010 Add `test_planner_default_resolver_in_worktree` to `tests/specify_cli/compat/test_planner.py`; `monkeypatch.chdir(worktree)`, call `plan(invocation)` with no `project_root_resolver`, assert `result.project_status.state != ProjectState.NO_PROJECT` (WP03)

**Implementation sketch**: For T007, import `get_project_root_or_exit` from `specify_cli.cli.helpers` (not mocked); construct fake worktree in `tmp_path`; call with `start=worktree_path`; assert result. For T008, use `monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path / "project"))` and `monkeypatch.setattr(subprocess, "run", mock_fn)`.  
**Risks**: `get_project_root_or_exit` calls `typer.Exit(1)` on failure — test must call it in a way that catches `SystemExit` if the path is wrong. T009 is the integration gate; don't skip it.  
**Prompt file**: `tasks/WP03-caller-integration-tests.md`
