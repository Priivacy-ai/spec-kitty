---
work_package_id: WP08
title: Shift-Left Test Migration
dependencies:
- WP07
requirement_refs:
- FR-017
planning_base_branch: feat/079-ci-hardening-and-lint-cleanup
merge_target_branch: feat/079-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/079-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/079-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: tests/next/
execution_mode: code_change
owned_files:
- tests/next/**
- tests/missions/**
tags: []
---

# WP08 — Shift-Left Test Migration

## Objective

Identify `git_repo`-marked tests in `tests/next/` and `tests/missions/` that do not actually
require a real git repository, and convert them from `@pytest.mark.git_repo` to
`@pytest.mark.fast`. For any tests that cannot be converted, add a comment explaining why.

The goal is to reduce CI time and improve test feedback speed by running more tests in the
`fast` tier (no subprocess overhead, no `git init`).

## Context

**Why this WP exists (FR-017):** Research R-03 identified that `tests/next/` has a 5:4
git_repo-to-fast ratio and `tests/missions/` has a 7:6 ratio. The test pyramid principle
states tests should run bottom-up: fast feedback first. Tests that only need filesystem
state or in-memory data should not pay the 30–90 second overhead of `git subprocess`.

**Eligibility criteria for shift-left:**
A `git_repo` test can be shifted to `fast` if:
1. It does NOT call `subprocess.run`, `subprocess.check_call`, or `subprocess.check_output`
   with any `git` command
2. It does NOT use `git init`, `git worktree`, `git commit`, `git checkout`, or any git
   operation that requires a real repo state
3. Its assertions are on data structures, rendered output, or file contents that can be
   reproduced with `tmp_path` + fixture files
4. Any git-repo fixture it uses can be replaced with a plain `tmp_path` fixture + YAML/
   markdown files placed there

**Conversion approach:**
When a test is eligible:
1. Replace the `git_repo` fixture with `tmp_path`
2. Create any necessary directory structure using `tmp_path / "subdir"` etc.
3. Write any needed YAML/JSON/markdown files using `tmp_path.joinpath("file.md").write_text(...)`
4. Change `@pytest.mark.git_repo` to `@pytest.mark.fast`
5. Verify the test still passes

**Doctrine:** DIRECTIVE_034 (test-first — shift must not reduce coverage), `testing-select-appropriate-level`, `test-pyramid-progression`.

**This WP is part of Batch 2 (sequential).** Depends on WP07 (stable marker state).

## Subtask Guidance

### T037 — Inspect `tests/next/` git_repo tests; identify shift-left candidates

**Directory:** `tests/next/`

Current status (from research R-03): 5 `git_repo` tests, 4 `fast` tests, 7 test files.

**Process:**
1. List all `git_repo`-marked test functions:
   ```bash
   grep -rn "@pytest.mark.git_repo" tests/next/
   ```
2. For each hit, read the test function body. Apply the eligibility criteria:
   - Look for `subprocess.run`, `git`, worktree calls → NOT eligible
   - Look for what data the test creates and asserts on:
     - If the test creates a `status.events.jsonl` file and reads it back → eligible
       (can use `tmp_path` instead of a git repo)
     - If the test triggers `git commit` as part of the operation under test → NOT eligible
   - Check what fixtures the test uses — look for `git_repo_path`, `repo_root`, or similar;
     read those fixtures to see what they set up

3. Produce a classification table (keep in your working notes; summarize in the commit message):
   ```
   tests/next/test_X.py::test_some_function  → eligible (only uses tmp_path structure)
   tests/next/test_Y.py::test_other_function → NOT eligible (git commit in fixture)
   ```

---

### T038 — Convert eligible `tests/next/` git_repo tests to fast

For each eligible test identified in T037:

**Conversion template:**
```python
# BEFORE:
@pytest.mark.git_repo
def test_next_decision_logic(git_repo_path):
    # git_repo_path is a Path to an initialized git repo
    events_file = git_repo_path / ".kittify" / "kitty-specs" / "my-feature" / "status.events.jsonl"
    events_file.parent.mkdir(parents=True)
    events_file.write_text('{"event_id": "01HXY...","wp_id":"WP01","to_lane":"planned"}\n')
    result = run_next_command(git_repo_path)
    assert result.wp_id == "WP01"

# AFTER:
@pytest.mark.fast
def test_next_decision_logic(tmp_path):
    # Use tmp_path instead; no git init needed
    events_file = tmp_path / ".kittify" / "kitty-specs" / "my-feature" / "status.events.jsonl"
    events_file.parent.mkdir(parents=True)
    events_file.write_text('{"event_id": "01HXY...","wp_id":"WP01","to_lane":"planned"}\n')
    result = run_next_command(tmp_path)
    assert result.wp_id == "WP01"
```

For tests that are NOT eligible, add a comment explaining why:
```python
@pytest.mark.git_repo
# shift-left: NOT eligible — this test calls `git commit` as part of the operation under test
def test_next_with_actual_commit(git_repo_path):
    ...
```

**Validation after each conversion:**
```bash
pytest tests/next/ -m fast -v -q 2>&1 | tail -10
```
The converted test must appear in the `fast` collection and pass.

---

### T039 — Inspect `tests/missions/` git_repo tests; identify shift-left candidates

**Directory:** `tests/missions/`

Current status (from research R-03): 7 `git_repo` tests, 6 `fast` tests, 20 test files.

**Process:** Same as T037 but for `tests/missions/`.

The `missions` module handles mission template loading and rendering. The most likely
shift-left opportunities are:
- Tests that render a template from a file in a temporary directory (no git state needed)
- Tests that assert on the YAML/markdown content of a rendered template
- Tests that test template variable substitution

Tests that are NOT eligible:
- Tests that check `git show`, `git log`, or `git blame` output
- Tests that verify commit-based mission history

```bash
grep -rn "@pytest.mark.git_repo" tests/missions/
```

---

### T040 — Convert eligible `tests/missions/` git_repo tests to fast

For each eligible test identified in T039, apply the same conversion pattern as T038.

For `tests/missions/`, template-focused tests typically need:
- A `tmp_path` with a `kitty-specs/<mission>/` directory structure
- A few YAML/markdown files in the right paths
- No git repository

**After converting:**
```bash
pytest tests/missions/ -m fast -v -q 2>&1 | tail -10
```
Converted tests must pass.

---

### T041 — Verify full test suite passes; confirm coverage does not decrease post-shift

**Full verification gate (DIRECTIVE_034 — test-first coverage check):**

```bash
# 1. Run full test suite
pytest tests/next/ tests/missions/ -v -q 2>&1 | tail -10

# 2. Compare coverage before and after (use coverage-baseline.md as the before)
pytest tests/next/ \
  --cov=src/specify_cli/next \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term -q 2>&1 | tail -5

pytest tests/missions/ \
  --cov=src/specify_cli/missions \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term -q 2>&1 | tail -5
```

Compare the output percentages against the values in `coverage-baseline.md`.

**If coverage decreases:**
- A decrease means a converted test is no longer exercising the code path it used to.
- Read the converted test and the uncovered lines.
- If the `tmp_path` replacement skipped a code path that the `git_repo` fixture triggered:
  add the missing fixture setup to the converted test.
- If the decrease cannot be fixed without re-adding git operations: revert the conversion
  and mark the test as `NOT eligible` with a comment.

**Commit** once all tests pass and coverage is not decreased.

## Definition of Done

- [ ] At least 3 tests shifted from `git_repo` to `fast` across `tests/next/` and `tests/missions/` combined
- [ ] All converted tests pass when run with `-m fast`
- [ ] Coverage for `next` and `missions` modules is NOT lower than the values in `coverage-baseline.md`
- [ ] Every test that could NOT be shifted has a comment explaining why
- [ ] All tests in `tests/next/` and `tests/missions/` still pass (no regressions)
- [ ] Changes committed to `feat/079-ci-hardening-and-lint-cleanup`

## Risks

- **Fixture dependency chains:** Some `git_repo` tests may use a fixture that depends on a
  deeper git-repo fixture. Check all fixtures transitively. A test that uses `project_dir`
  which internally uses `git_repo_path` cannot be shifted without also replacing the fixture.
- **Coverage decrease after conversion:** A test that used a git repo fixture may have been
  triggering code paths (e.g., git-detection logic) that are not triggered by `tmp_path`.
  This is a legitimate "not eligible" case — document it.
- **Fewer than 3 candidates:** If fewer than 3 eligible tests are found, that is acceptable —
  document the findings in the commit message. The 3-test threshold is a minimum, not a hard
  requirement; the goal is to shift what is safely shiftable, not to force conversions.

## Reviewer Guidance

The diff should show: `@pytest.mark.git_repo` → `@pytest.mark.fast` changes, fixture
parameter renames (`git_repo_path` → `tmp_path`), and any directory/file setup that replaces
git repo setup. Any new `subprocess.run` or `os.system` call in a converted test is a red
flag — the conversion is invalid if the test still invokes external processes.
