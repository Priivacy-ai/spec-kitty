---
work_package_id: WP07
title: Test Marker Cataloguing
dependencies:
- WP06
requirement_refs:
- FR-016
planning_base_branch: feat/079-ci-hardening-and-lint-cleanup
merge_target_branch: feat/079-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/079-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/079-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
- T035
- T036
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: tests/lanes/
execution_mode: code_change
owned_files:
- tests/lanes/**
- tests/review/**
- tests/merge/**
- tests/cli/**
tags: []
---

# WP07 — Test Marker Cataloguing

## Objective

Add at least one pytest marker (`fast`, `git_repo`, `slow`, `integration`, or `e2e`) to
every test function in `tests/lanes/`, `tests/review/`, `tests/merge/`, and `tests/cli/`
that currently has zero markers.

After this WP, every test function in these four directories is visible to marker-scoped
pytest runs. This is a prerequisite for WP09 (CI split) to produce accurate coverage
accounting.

## Context

**Why this WP exists (FR-016):** Research finding R-03 showed that `tests/lanes/` (12 files)
and `tests/review/` (6 files) have zero marked tests. A marker-scoped CI run using
`-m 'fast or git_repo'` would collect zero tests from these directories, producing 0%
coverage and falsely appearing to pass coverage floors. WP09 cannot be valid until every
test is marked.

**Classification criteria:**
- `fast`: no subprocess, no git, no network, no disk writes outside `tmp_path` — pure logic
  or filesystem reads from `tmp_path`
- `git_repo`: requires `subprocess.run('git ...')` or `git init` — needs a real git repository
- `slow`: takes > 30 seconds (rare; use sparingly)
- `integration`: multiple real components interacting (e.g., actual SQLite + event writer)
- `e2e`: full CLI invoked as a subprocess end-to-end

**Doctrine:** `testing-select-appropriate-level` tactic, `test-pyramid-progression` tactic.

**This WP is part of Batch 2 (sequential).** Depends on WP06; WP08 depends on this WP.

## Subtask Guidance

### T032 — Classify and add markers to all 12 `tests/lanes/` test files

**Directory:** `tests/lanes/`

**Process:**
1. List all test files: `ls tests/lanes/test_*.py`
2. For each file, read the test functions and identify:
   - Does the test call `subprocess.run` or use a `git_repo` fixture? → `git_repo`
   - Does the test use `tmp_path` but no git? → likely `fast`
   - Does the test use multiple real spec-kitty services? → `integration`
3. Apply the marker at the function level (preferred) or class level:
   ```python
   import pytest

   @pytest.mark.fast
   def test_some_logic():
       ...

   @pytest.mark.git_repo
   def test_lane_transition_in_repo():
       ...
   ```
4. If a test file already imports `pytest`, just add the decorator. If not, add `import pytest`.

**Note:** `lanes/` contains the WP lifecycle state machine logic. Tests that assert on lane
state transitions without actual git operations should be `fast`. Tests that create a
spec-kitty project in a real git repo should be `git_repo`.

**Validation (partial):**
```bash
pytest tests/lanes/ -m fast --collect-only -q 2>&1 | head -20
pytest tests/lanes/ -m git_repo --collect-only -q 2>&1 | head -20
```
Verify that tests are collected under each marker.

---

### T033 — Classify and add markers to all 6 `tests/review/` test files

**Directory:** `tests/review/`

**Process:** Same as T032 but for `tests/review/`.

The `review` module handles the code review workflow in spec-kitty (claiming WPs for review,
approving, returning to in-progress). Tests that assert on data structures or transition
logic without git → `fast`. Tests that create a real repo to simulate review workflows → `git_repo`.

**Validation (partial):**
```bash
pytest tests/review/ -m fast --collect-only -q 2>&1 | head -20
pytest tests/review/ -m git_repo --collect-only -q 2>&1 | head -20
```

---

### T034 — Classify and add markers to all 7 `tests/merge/` test files

**Directory:** `tests/merge/`

Research R-03 shows `tests/merge/` already has 2 `fast` + 1 `git_repo` marked test, but
most tests are unmarked. Apply markers to the unmarked test functions.

**Process:**
1. Identify already-marked tests (skip those).
2. For unmarked tests:
   - Merge tests often exercise conflict detection, resolution strategies, or state
     persistence — check whether these require real git worktrees or just data structures.
   - If the test uses `MergeState` or `PreflightResult` objects without a git repo: `fast`
   - If the test calls `git merge` or inspects branch state: `git_repo`

**Validation:**
```bash
pytest tests/merge/ --collect-only -q 2>&1 | grep "no tests ran"
# Should NOT print "no tests ran" — all tests should be collected
pytest tests/merge/ -m fast --collect-only -q 2>&1 | head -20
```

---

### T035 — Classify and add markers to all 3 `tests/cli/` test files

**Directory:** `tests/cli/`

The `cli` module is the typer CLI layer. Tests of CLI commands often:
- Test command invocation using `typer.testing.CliRunner` → likely `fast`
- Test commands that trigger actual git operations → `git_repo`
- Test full workflows end-to-end → `e2e` or `integration`

**Process:** Read each test, determine the fixture setup, apply the appropriate marker.

**Validation:**
```bash
pytest tests/cli/ --collect-only -q 2>&1 | grep "no tests ran"
pytest tests/cli/ -m fast --collect-only -q 2>&1 | head -20
```

---

### T036 — Verify all newly-marked tests pass; confirm `pytest -m fast` runs cleanly

**Full verification gate:**

```bash
# 1. All tests in the 4 directories pass (markers are additive, not behavioral)
pytest tests/lanes/ tests/review/ tests/merge/ tests/cli/ -v -q 2>&1 | tail -10

# 2. Marker-scoped fast run collects and passes
pytest tests/lanes/ tests/review/ tests/merge/ tests/cli/ -m fast -q 2>&1 | tail -5

# 3. No unmarked tests remain
# This counts test functions without any marker:
python3 - <<'EOF'
import ast, pathlib

directories = ['tests/lanes', 'tests/review', 'tests/merge', 'tests/cli']
unmarked = []

for d in directories:
    for path in pathlib.Path(d).rglob('test_*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                has_marker = any(
                    (isinstance(d, ast.Call) and
                     isinstance(d.func, ast.Attribute) and
                     d.func.attr in ('fast', 'git_repo', 'slow', 'integration', 'e2e'))
                    or
                    (isinstance(d, ast.Attribute) and
                     d.attr in ('fast', 'git_repo', 'slow', 'integration', 'e2e'))
                    for d in getattr(node, 'decorator_list', [])
                )
                if not has_marker:
                    unmarked.append(f"{path}:{node.lineno} {node.name}")

if unmarked:
    print("UNMARKED TESTS:")
    for u in unmarked:
        print(f"  {u}")
else:
    print("All test functions are marked.")
EOF
```

If unmarked tests are reported: add the missing markers. If tests fail after marker addition:
verify the marker decorator syntax is correct (common mistake: missing `@pytest.mark.` prefix).

**Commit** the changes once all gates pass.

## Definition of Done

- [ ] All test functions in `tests/lanes/`, `tests/review/`, `tests/merge/`, `tests/cli/` have at least one pytest marker
- [ ] `pytest -m fast tests/lanes/ tests/review/ tests/merge/ tests/cli/` collects and passes tests from all four directories
- [ ] All existing tests still pass (no regressions from marker addition)
- [ ] `coverage-baseline.md` coverage measurements can now be reproduced with the marker filter (for modules that had zero markers)
- [ ] Changes committed to `feat/079-ci-hardening-and-lint-cleanup`

## Risks

- **Misclassifying a `git_repo` test as `fast`:** If a test uses a `git_repo` fixture or
  calls git subprocesses and is marked `fast`, it will fail when run without a repo. Read
  the fixture list and the test body carefully before assigning `fast`.
- **Class-level vs function-level markers:** If a test class has 5 methods and 4 are `fast`
  and 1 is `git_repo`, apply markers at the function level (not the class level), because
  a class-level `fast` marker would incorrectly mark the `git_repo` test.
- **pytest marker registration:** If the project's `pytest.ini` / `pyproject.toml` requires
  markers to be registered, new markers will produce warnings. Check `pyproject.toml`
  `[tool.pytest.ini_options]` for a `markers = [...]` list and add any new markers there.

## Reviewer Guidance

Every changed file should show only `@pytest.mark.X` decorator additions and `import pytest`
additions where missing. No test assertion logic should change. A diff that modifies any
`assert` statement or test setup logic is out of scope for this WP.
