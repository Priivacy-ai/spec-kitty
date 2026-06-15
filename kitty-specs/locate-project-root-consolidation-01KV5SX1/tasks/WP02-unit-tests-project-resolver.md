---
work_package_id: WP02
title: 'Unit Tests: project_resolver.locate_project_root'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-008
- NFR-001
- NFR-005
tracker_refs: []
planning_base_branch: feat/locate-project-root-consolidation
merge_target_branch: feat/locate-project-root-consolidation
branch_strategy: Planning artifacts for this mission were generated on feat/locate-project-root-consolidation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/locate-project-root-consolidation unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: claude
shell_pid: '16033'
history:
- date: '2026-06-15'
  event: Created during /spec-kitty.tasks by Architect Alphonso
agent_profile: implementer-ivan
authoritative_surface: tests/runtime/
create_intent: []
execution_mode: code_change
owned_files:
- tests/runtime/test_project_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Add three tests to `tests/runtime/test_project_resolver.py` covering all three resolution paths of `project_resolver.locate_project_root`:

1. `test_env_root_authoritative` — `SPECIFY_REPO_ROOT` takes precedence (Tier 1)
2. `test_worktree_pointer_resolution` — git worktree `.git` file is followed to main repo (Tier 2)
3. Verify existing `test_locate_project_root_and_template_resolution` still passes; add `start`-parameter variant (Tier 3)

These tests make any future reversion to a walk body immediately detectable.

**Prerequisite:** WP01 must be merged. All three tests call `locate_project_root` imported from `specify_cli.core.project_resolver` (not from `paths`) — they exercise the shim, not the authoritative implementation directly.

---

## Context

**Current coverage gap (Stenographer, 2026-06-15):**
- `tests/runtime/test_project_resolver.py` has exactly one test: `test_locate_project_root_and_template_resolution` (line 12). It performs a plain `.kittify` walk; no `SPECIFY_REPO_ROOT`, no worktree setup.
- Zero env-var tests exist for `project_resolver.locate_project_root`.
- Zero worktree tests exist for `project_resolver.locate_project_root`.

**Import to use in all three tests:**
```python
from specify_cli.core.project_resolver import locate_project_root
```
Not `from specify_cli.core.paths import locate_project_root` — the tests must exercise the shim's delegation chain.

---

## Branch Strategy

**Planning base branch:** `feat/locate-project-root-consolidation`  
**Final merge target:** `feat/locate-project-root-consolidation`  
**Execution workspace:** allocated per `lanes.json` — resolve via `spec-kitty agent action implement WP02 --agent claude`.

---

## Subtask T004 — Add test_env_root_authoritative

**Purpose:** Verify that when `SPECIFY_REPO_ROOT` is set to an existing directory (without `.kittify` there, CWD also outside any `.kittify` tree), `locate_project_root` returns the env-var value. This is Tier 1 resolution — the env var wins outright.

**File:** `tests/runtime/test_project_resolver.py`

**Test to add:**
```python
def test_env_root_authoritative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPECIFY_REPO_ROOT wins even when there is no .kittify at that path."""
    # tmp_path is an existing directory with no .kittify inside it
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))
    # start from a completely unrelated directory (also tmp_path, but no .kittify)
    result = locate_project_root(start=tmp_path)
    assert result == tmp_path
```

**Steps:**
1. Read `tests/runtime/test_project_resolver.py` in full to understand existing imports and fixtures.
2. Add the test after the existing `test_locate_project_root_and_template_resolution`.
3. Ensure `pytest` and `pathlib.Path` are imported at the top of the file (they should be already).
4. Run: `pytest tests/runtime/test_project_resolver.py::test_env_root_authoritative -v`

**Why this catches regressions:** If WP01 is ever reverted to the walk body, this test will fail because the walk body ignores `SPECIFY_REPO_ROOT` — `tmp_path` has no `.kittify`, so the walk returns `None`, not `tmp_path`.

**Edge case to understand:** `paths.locate_project_root` (the authoritative implementation) checks `SPECIFY_REPO_ROOT` before walking. As of commit `8431dd931`, it returns the env-var value on `exists()` alone — no `.kittify` precondition. If the env-var path does NOT exist as a directory, it falls through to the walk. The test uses `tmp_path` (which always exists) so Tier 1 fires.

**Validation:**
- [ ] Test passes with WP01's shim in place
- [ ] `monkeypatch.setenv` is used (not `os.environ` mutation)
- [ ] `result == tmp_path` (not just truthy)

---

## Subtask T005 — Add test_worktree_pointer_resolution

**Purpose:** Verify that when the caller's CWD is inside a git worktree (`.git` is a file, not a directory), `locate_project_root` follows the `.git` file pointer and returns the main worktree root (which has `.kittify`).

**File:** `tests/runtime/test_project_resolver.py`

**Fake worktree filesystem structure to build:**
```
tmp_path/
├── main_repo/
│   ├── .kittify/               ← sentinel directory
│   └── .git/
│       └── worktrees/
│           └── test_lane/      ← worktree pointer dir
└── worktree/
    └── .git                    ← FILE (not dir), contains: "gitdir: /tmp/main_repo/.git/worktrees/test_lane"
```

**Test to add:**
```python
def test_worktree_pointer_resolution(tmp_path: Path) -> None:
    """locate_project_root follows .git file pointers to the main worktree."""
    # Build fake main repo
    main_repo = tmp_path / "main_repo"
    (main_repo / ".kittify").mkdir(parents=True)
    worktrees_dir = main_repo / ".git" / "worktrees" / "test_lane"
    worktrees_dir.mkdir(parents=True)

    # Build fake worktree — .git is a FILE pointing at the worktrees dir
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

    result = locate_project_root(start=worktree)
    assert result == main_repo
```

**Steps:**
1. Add the test to `tests/runtime/test_project_resolver.py`.
2. Run: `pytest tests/runtime/test_project_resolver.py::test_worktree_pointer_resolution -v`

**How `paths.locate_project_root` detects worktrees:** It reads the `.git` file content, extracts the `gitdir:` path, checks whether the resolved path is inside a `.git/worktrees/` directory structure, and if so navigates up to the main repo root. The fake filesystem must match this exact structure for the test to pass.

**Why this test matters (Matrix-Maker row 3):** Without this test, a reversion to the walk body goes undetected until a developer tries to run `spec-kitty status` from inside a worktree and gets a hard exit 1 with "project root not found".

**Validation:**
- [ ] Test passes with WP01's shim in place
- [ ] `result == main_repo` (the directory with `.kittify`, not the worktree)
- [ ] Test uses only `tmp_path` — no real repo paths

---

## Subtask T006 — Verify existing test passes; add start-parameter variant

**Purpose:** Confirm the WP01 shim doesn't break the existing test. Add a `start`-parameter variant that exercises the `start` parameter explicitly (currently the existing test may call with `start=None`).

**File:** `tests/runtime/test_project_resolver.py`

**Steps:**
1. Run: `pytest tests/runtime/test_project_resolver.py::test_locate_project_root_and_template_resolution -v`
   - Expected: passes. If it fails, diagnose — WP01 shim should preserve this behavior via the delegation chain.
2. Read the existing test to understand how it sets up its `.kittify` directory.
3. Add a new test `test_locate_project_root_with_explicit_start` that calls `locate_project_root(start=some_subdir_of_project)` and asserts it returns the project root:

```python
def test_locate_project_root_with_explicit_start(tmp_path: Path) -> None:
    """locate_project_root resolves correctly when start is a subdirectory."""
    project_root = tmp_path / "project"
    (project_root / ".kittify").mkdir(parents=True)
    deep_subdir = project_root / "src" / "foo" / "bar"
    deep_subdir.mkdir(parents=True)

    result = locate_project_root(start=deep_subdir)
    assert result == project_root
```

4. Run the full test file: `pytest tests/runtime/test_project_resolver.py -v`

**Validation:**
- [ ] Existing `test_locate_project_root_and_template_resolution` still passes
- [ ] New `test_locate_project_root_with_explicit_start` passes
- [ ] All tests in the file pass

---

## Definition of Done

- [ ] Three new tests added to `tests/runtime/test_project_resolver.py`
- [ ] All new tests import from `specify_cli.core.project_resolver` (not from `paths`)
- [ ] `pytest tests/runtime/test_project_resolver.py -v` — all tests pass
- [ ] No `monkeypatch` state escapes between tests (env vars cleaned up by `monkeypatch` fixture)
- [ ] `mypy --strict tests/runtime/test_project_resolver.py` passes

## Risks

- **Worktree filesystem construction:** The `.git` file content format (`gitdir: <path>`) must exactly match what `paths.locate_project_root` parses. If the test fails unexpectedly, inspect `src/specify_cli/core/paths.py` worktree detection logic around the `.git` file read.
- **Env-var pollution between tests:** Use `monkeypatch.setenv` (not `os.environ`) so the fixture cleans up automatically. A leaked `SPECIFY_REPO_ROOT` will cause subsequent tests to fail.

## Reviewer Guidance

- Confirm all three tests import from `specify_cli.core.project_resolver`, not `paths`
- Confirm `test_env_root_authoritative` uses `monkeypatch.setenv` 
- Confirm `test_worktree_pointer_resolution` uses only `tmp_path` paths (no real filesystem paths)
- Confirm existing test still passes (it appears in test output)
