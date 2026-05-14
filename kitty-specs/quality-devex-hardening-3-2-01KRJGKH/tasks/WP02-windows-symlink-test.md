---
work_package_id: WP02
title: Windows symlink-fallback test for m_0_8_0 migration
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1120293"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: tests/upgrade/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- tests/upgrade/test_m_0_8_0_symlink_windows.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP02.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load python-pedro
```

The profile establishes your identity (Python Pedro), primary focus (writing well-tested Python code), and avoidance boundary (no architectural redesign; locality of change). If the profile load fails, stop and surface the error — do not improvise.

## Objective

Author a behavior-driven test that exercises the `m_0_8_0_worktree_agents_symlink` migration's `OSError → shutil.copy2` fallback path. The fallback exists in code at `src/specify_cli/upgrade/migrations/m_0_8_0_worktree_agents_symlink.py:116-131` but no test asserts it. The risk is silent regression on Windows runners.

The test runs on **every CI pass (POSIX and Windows)** via `monkeypatch.setattr(os, "symlink", _raise)`. Pedro prefers this over a Windows-only `@pytest.mark.windows_ci` because it gives real coverage on every PR.

## Context

### Current code (read carefully before authoring tests)

`src/specify_cli/upgrade/migrations/m_0_8_0_worktree_agents_symlink.py:103-131`:

```python
try:
    os.chdir(wt_kittify)
    os.symlink(relative_path, "AGENTS.md")
finally:
    os.chdir(original_cwd)

changes.append(f"Created .kittify/AGENTS.md symlink in worktree {worktree.name}")
except OSError as e:
    try:
        shutil.copy2(main_agents, wt_agents)
        changes.append(f"Copied .kittify/AGENTS.md to worktree {worktree.name} (symlink failed)")
    except OSError as copy_error:
        errors.append(f"Failed to create AGENTS.md in {worktree.name}: {e}, copy also failed: {copy_error}")
```

### Validation snapshot (Pedro, 2026-05-14)

```
$ grep -rn "m_0_8_0" tests/ 2>/dev/null
(no results)
```

No targeted test exists. `tests/core/test_worktree_symlink_fallback.py` covers `setup_feature_directory` (a different function with the same fallback shape) but does NOT cover this migration.

## Doctrine Citations

This WP applies:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — assertions are on the resulting `AGENTS.md` file content and the migration's `changes` / `errors` lists. No assertions on call counts or internal state.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.
- Execution worktree allocated by `lanes.json`.

## Subtasks

### T008 — Create test file with happy `OSError → shutil.copy2` fallback case

**Purpose**: Verify that when `os.symlink` raises `OSError`, the migration falls back to `shutil.copy2` and produces a valid `AGENTS.md` file in the worktree.

**Steps**:

1. Create `tests/upgrade/test_m_0_8_0_symlink_windows.py`.
2. Build a fixture that:
   - Sets up a `tmp_path / "repo"` with a minimal `.kittify/AGENTS.md` (some test content) and an initial git commit.
   - Creates a `tmp_path / "worktree"` representing a target worktree.
3. Use `monkeypatch.setattr(os, "symlink", lambda *a, **kw: (_ for _ in ()).throw(OSError("not permitted")))` to simulate the Windows symlink-permission failure on POSIX runners.
4. Invoke the migration class's `apply` method against the fixture (do NOT call the migration's CLI surface — call the class directly so the test stays focused).
5. Assert:
   - The worktree's `.kittify/AGENTS.md` exists as a regular file (not a symlink).
   - Its content matches the source `AGENTS.md`.
   - The migration's `MigrationResult.changes` list contains an entry matching `"Copied .kittify/AGENTS.md to worktree {worktree.name} (symlink failed)"` (substring match on `(symlink failed)` is acceptable for stability).
   - `MigrationResult.errors` is empty.
   - `MigrationResult.success` is `True`.

**Files**: `tests/upgrade/test_m_0_8_0_symlink_windows.py` (new, ~80 lines).

**Validation**:

- Test passes locally (`uv run pytest tests/upgrade/test_m_0_8_0_symlink_windows.py -v`).
- Test asserts on observable outcomes — file content and changes-list entries — not on call counts or `mock.call_args`.

### T009 — Parametrize the dual-failure case (`shutil.copy2` also raises `OSError`)

**Purpose**: Cover the inner `except` arm — when both `os.symlink` and `shutil.copy2` fail, the migration records the dual failure in `MigrationResult.errors`.

**Steps**:

1. Add a second test (or a parameterization of T008's test) that additionally monkeypatches `shutil.copy2` to raise `OSError("disk full")`.
2. Assert:
   - `MigrationResult.errors` contains an entry matching the pattern `"Failed to create AGENTS.md in {worktree.name}: {symlink_error}, copy also failed: {copy_error}"` — substring match on `"copy also failed:"` is the stable assertion.
   - `MigrationResult.success` is `False`.
   - No `AGENTS.md` file exists in the worktree.

**Files**: same file (extend with parametrize or add a sibling test function, ~30 additional lines).

**Validation**:

- Both parametrized cases pass.

### T010 — Verify POSIX CI execution + record glossary fragment

**Purpose**: Confirm the test runs on POSIX runners (not Windows-only); record the WP's glossary fragment.

**Steps**:

1. Run the test with the POSIX-only marker filter to confirm it runs:
   ```bash
   uv run pytest tests/upgrade/test_m_0_8_0_symlink_windows.py -m "not windows_ci" -v
   ```
2. Confirm the test executes (does not get skipped by the marker filter).
3. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP02.md`:
   - Add the canonical term `characterization test` per the spec's Domain Language section.
   - Definition: "A test that captures the observable behavior of existing code as fixture-driven assertions, written before any refactor of that code. The refactor must leave the characterization test green. See `tdd-red-green-refactor` tactic."
   - Confidence: 0.95. Status: active.
4. Stage and commit both the test file and the glossary fragment.

**Validation**:

- Test runs on POSIX CI without `windows_ci` marker filtering it out.
- `glossary-fragments/WP02.md` exists and follows the canonical-term schema.

## Test Strategy

This WP **is** a test-authoring WP. The test artifacts are the deliverable. No production code change.

## Definition of Done

- [ ] `tests/upgrade/test_m_0_8_0_symlink_windows.py` exists with both happy + dual-failure cases.
- [ ] Test asserts on observable outcomes per `function-over-form-testing` (file existence, file content, changes-list entries, errors-list entries).
- [ ] Test runs on POSIX CI via `monkeypatch.setattr`; the migration's actual `os.symlink` call site is never reached in test.
- [ ] `glossary-fragments/WP02.md` carries the "characterization test" entry.
- [ ] Both cases pass: `uv run pytest tests/upgrade/test_m_0_8_0_symlink_windows.py -v` exits 0.

## Risks

- **`monkeypatch.setattr(os, "symlink", ...)` has unexpected scope.** The patch is per-test by default in pytest; verify the test does not leak state to the next test in the suite.
- **The migration's git operations require a real git repo.** Use `subprocess.run(["git", "init"], ...)` in the fixture, not a `dulwich` shim — the migration calls `git` directly.
- **AGENTS.md content drift.** Use a unique sentinel string (e.g. `f"agents content for WP02 test {tmp_path.name}"`) so a content mismatch is visible in the assertion failure.

## Reviewer Guidance

When reviewing this WP, check:

1. Tests assert on file content and changes/errors lists, NOT on `mock.call_count` or `os.symlink.assert_called_once_with(...)`. Reject if structural assertions appear.
2. Tests use `tmp_path` real I/O for the worktree state — no `unittest.mock` patches of `Path.read_text` or similar IO mocks.
3. The migration is invoked at the class level, not via subprocess. Test focus stays on the migration's logic, not on the CLI.
4. The glossary fragment for "characterization test" is well-defined and matches the schema used elsewhere in `spec_kitty_core.yaml`.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent claude
```

## Activity Log

- 2026-05-14T09:06:24Z – claude:sonnet:python-pedro:implementer – shell_pid=1117465 – Started implementation via action command
- 2026-05-14T09:11:15Z – claude:sonnet:python-pedro:implementer – shell_pid=1117465 – Ready: 2 cases for happy + dual-failure fallback; runs on every POSIX CI pass via monkeypatch. Planning artifact (glossary fragment) committed to fix/quality-check-updates. Pre-existing WP01 kitty-specs files on lane branch are not owned by WP02.
- 2026-05-14T09:11:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=1120293 – Started review via action command
- 2026-05-14T09:13:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=1120293 – Approved: targeted POSIX test for m_0_8_0 OSError->shutil.copy2 fallback (happy + dual-failure). Cites function-over-form-testing tactic; assertions on file content, is_symlink, and MigrationResult.{success,errors,changes_made} — zero mock-call-count assertions. Glossary fragment 'characterization test' placed on planning branch fix/quality-check-updates (commit c1e012052) per FR-013 — positive precedent over WP01. Tests pass on POSIX without windows_ci marker; 2/2 green. --force used because residual planning artifacts from prior WP01 cleanup remain on the lane branch (WP01.md fragment + doctor research note); operator resolves at merge time per shared-lane workflow nuance.
