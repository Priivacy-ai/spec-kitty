---
work_package_id: WP05
title: Task-Workflow DX Fixes
dependencies: []
requirement_refs:
- FR-011
- FR-012
tracker_refs:
- '#1981'
- '#1982'
planning_base_branch: fix/cli-bug-sweep-tool-surface-self-registration
merge_target_branch: fix/cli-bug-sweep-tool-surface-self-registration
branch_strategy: Planning artifacts for this mission were generated on fix/cli-bug-sweep-tool-surface-self-registration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cli-bug-sweep-tool-surface-self-registration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-bug-sweep-tool-surface-self-registration-01KV5AWE
base_commit: dfe6a1bfe0e93046ced2fdcd723e9de471a8fbd9
created_at: '2026-06-15T11:25:57.959051+00:00'
subtasks:
- T020
- T021
agent: claude
shell_pid: '18836'
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/agent/test_map_requirements_coord.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/ownership/validation.py
- tests/specify_cli/cli/commands/agent/test_map_requirements_coord.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

> **Note on plan.md in coord worktree**: If you are reading this from a coord worktree environment, the `plan.md` visible there predates the IC-05 mission expansion and shows only four ICs. The planning-branch `plan.md` (on `fix/cli-bug-sweep-tool-surface-self-registration`) contains IC-05 context. This WP file is self-contained — all required implementation detail is here.

## Objective

Fix two workflow bugs discovered during this mission's own planning phase. Both are small, independent code changes that unblock the documented `map-requirements` → `finalize-tasks` task-authoring workflow and improve the error signal when ownership metadata is wrong.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP05 --agent claude`
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Worktree**: allocated per lane from `lanes.json`; do not create worktrees manually

## Context

### Bug A — `map-requirements` spec.md path resolution (T020)

**Root cause**: `map_requirements` calls `resolve_feature_dir_for_mission(main_repo_root, mission_slug)`, which delegates to `mission_runtime.resolve_action_context`. The runtime's coord-worktree routing in `runtime_bridge.py` fires **only when `meta.json` carries `coordination_branch`**. For PR-bound missions created without explicit coord-branch setup, `coordination_branch` is absent from `meta.json`. The runtime falls through to the primary checkout (`main`). If the mission's target branch is not checked out in the primary checkout (e.g. it is checked out in a coord worktree), `kitty-specs/<mission>/` does not exist in the primary checkout's working tree, and `spec.md` is reported not found.

**Key code path** (read before editing):
1. `src/specify_cli/cli/commands/agent/tasks.py` → `def map_requirements` (search with `grep -n "def map_requirements" src/specify_cli/cli/commands/agent/tasks.py`)
2. `resolve_feature_dir_for_mission(main_repo_root, mission_slug)` — delegates to `mission_runtime.resolve_action_context`
3. `src/runtime/next/runtime_bridge.py` → `_mission_declares_coordination_branch()` gate — check whether this is the actual failure branch for this scenario
4. `src/specify_cli/missions/_read_path_resolver.py` → `resolve_mission_read_path()` — the coord-aware primitive already used by `resolve_feature_dir_for_slug` (note: NOT the same as `resolve_feature_dir_for_mission`)

**Investigation step required**: Before writing any code, trace the actual execution for a PR-bound mission with no `coordination_branch` in `meta.json` and the primary checkout on `main`. Specifically: does `resolve_feature_dir_for_mission` ever reach `_read_path_resolver.resolve_mission_read_path()`, which IS coord-topology-aware? If not, the fix is to route `map_requirements` through `resolve_feature_dir_for_slug` (which calls `resolve_mission_read_path` directly) instead of `resolve_feature_dir_for_mission` (which goes through `resolve_action_context` with the `coordination_branch` gate).

**Likely fix path** (confirm against source before implementing):
```python
# In map_requirements, replace:
feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)

# With the coord-aware slug resolver (which calls resolve_mission_read_path directly):
from specify_cli.missions.feature_dir_resolver import resolve_feature_dir_for_slug
feature_dir = resolve_feature_dir_for_slug(main_repo_root, mission_slug)
```
`resolve_feature_dir_for_slug` calls `_read_path_resolver.resolve_mission_read_path(repo_root, mission_slug, mid8_from_slug(mission_slug))`, which checks the coord worktree first regardless of `coordination_branch` in `meta.json`. Confirm this is safe for the action context that `map_requirements` needs (read-only spec path resolution, no write commit targeting required).

### Bug B — `validate_glob_matches` omits `create_intent` hint when suggestion present (T021)

**Root cause**: `src/specify_cli/ownership/validation.py` → `validate_glob_matches` — the section that builds the error message for a zero-match literal `owned_files` path uses a mutually exclusive branch:

```python
if suggestion:
    msg += f" {suggestion}"
else:
    msg += (
        " If this file will be created by this WP, add it to "
        "'create_intent' in the WP frontmatter."
    )
```

When `_nearest_match_suggestion` returns a "did you mean?" string, the `create_intent` guidance is silently omitted. Authors see "did you mean X?" but no hint that `create_intent` would resolve the error for a planned-new-file.

**Key code location**: `src/specify_cli/ownership/validation.py`, search for `_nearest_match_suggestion` (~line 374). The fix is a one-line change: include both the suggestion AND the `create_intent` hint.

---

## Subtask T020 — Fix `map-requirements` Spec Path Resolution

**Purpose**: Make `map-requirements` find `spec.md` when the mission's target branch is checked out in a coord worktree rather than the primary checkout.

**Steps**:

1. Read `src/specify_cli/cli/commands/agent/tasks.py` — locate the `map_requirements` function. Focus on the section after `_ensure_target_branch_checked_out`:
   ```python
   feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
   if not feature_dir.exists():
       _output_error(json_output, f"Mission directory not found: {feature_dir}")
       raise typer.Exit(1)
   spec_md = feature_dir / SPEC_MD_FILENAME
   if not spec_md.exists():
       _output_error(json_output, f"spec.md not found: {spec_md}")
       raise typer.Exit(1)
   ```

2. Find the coord worktree path convention. Grep for the pattern used by `setup-plan`:
   ```bash
   grep -rn "coord" src/specify_cli/coordination/ src/specify_cli/cli/ --include="*.py" | grep -i "worktree\|\.worktrees" | head -20
   ```

3. After the `feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)` call, add a fallback: if `feature_dir` does not exist in `main_repo_root`, try resolving it from the coord worktree:
   ```python
   feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
   if not feature_dir.exists():
       # Primary checkout may be on a different branch (e.g. main) while the
       # mission's target branch is checked out in the coord worktree.
       coord_root = main_repo_root / ".worktrees" / f"{mission_slug}-coord"
       if coord_root.exists():
           coord_feature_dir = resolve_feature_dir_for_mission(coord_root, mission_slug)
           if coord_feature_dir.exists():
               feature_dir = coord_feature_dir
   if not feature_dir.exists():
       _output_error(json_output, f"Mission directory not found: {feature_dir}")
       raise typer.Exit(1)
   ```
   Adjust the coord worktree path pattern to match whatever `setup-plan` actually uses — confirm by reading the relevant source or running `find .worktrees -maxdepth 1 -type d` in a repo where `setup-plan` has run.

4. Confirm that `spec_md = feature_dir / SPEC_MD_FILENAME` and the subsequent read work correctly with the coord-worktree-resolved `feature_dir`.

5. Write a unit test in `tests/specify_cli/cli/commands/agent/test_map_requirements_coord.py`:
   - Read the existing test patterns in `tests/specify_cli/cli/commands/agent/` to understand fixtures and mocking conventions.
   - **Test A**: primary checkout has the kitty-specs dir → spec.md found (baseline, no regression).
   - **Test B**: primary checkout lacks the kitty-specs dir, but a coord worktree mock at the expected path has it → spec.md found via fallback.
   - **Test C**: neither primary nor coord worktree has the dir → "Mission directory not found" error emitted.
   - Mock filesystem and coord worktree resolution at the appropriate boundary (do not hit real git). Use `tmp_path` fixtures.

6. Run `mypy src/specify_cli/cli/commands/agent/tasks.py --strict` — zero errors.

**Validation**:
- With a coord worktree present and primary checkout on `main`: `spec-kitty agent tasks map-requirements --wp WP01 --refs FR-001 --mission <slug> --json` succeeds and returns a coverage summary.
- Without a coord worktree (primary checkout on the target branch): same command still succeeds — no regression.
- With neither (invalid mission): still returns "Mission directory not found" as before.

---

## Subtask T021 — Fix `create_intent` Hint in `validate_glob_matches`

**Purpose**: Ensure authors always see the `create_intent` guidance when a literal `owned_files` path matches zero files on disk, regardless of whether a "did you mean?" suggestion is also present.

**Steps**:

1. Read `src/specify_cli/ownership/validation.py` — find `validate_glob_matches`. Locate the block that builds the error message for zero-match literal paths (search for `_nearest_match_suggestion`). It looks like:
   ```python
   suggestion = _nearest_match_suggestion(pattern, repo_root)
   msg = (
       f"{wp_id}: owned_files path '{pattern}' is a literal "
       f"file path that matches zero files in the repository."
   )
   if suggestion:
       msg += f" {suggestion}"
   else:
       msg += (
           " If this file will be created by this WP, add it to "
           "'create_intent' in the WP frontmatter."
       )
   result.errors.append(msg)
   ```

2. Change to include BOTH the suggestion AND the `create_intent` hint when a suggestion exists:
   ```python
   suggestion = _nearest_match_suggestion(pattern, repo_root)
   msg = (
       f"{wp_id}: owned_files path '{pattern}' is a literal "
       f"file path that matches zero files in the repository."
   )
   if suggestion:
       msg += f" {suggestion}"
   msg += (
       " If this file will be created by this WP, add it to "
       "'create_intent' in the WP frontmatter."
   )
   result.errors.append(msg)
   ```

3. Search for tests that assert the exact old error message text:
   ```bash
   grep -rn "create_intent\|did you mean\|matches zero files" tests/ --include="*.py" | grep -v "# "
   ```
   Update any assertion that matches the old "matches zero files" error message format to expect the new combined form.

4. Run `mypy src/specify_cli/ownership/validation.py --strict` — zero errors.
5. Run `ruff check src/specify_cli/ownership/validation.py` — zero issues.
6. Run `pytest tests/specify_cli/ownership/ -v` — all pass including updated assertions.

**Validation**:
- A WP with a zero-match literal `owned_files` entry AND a nearest-match suggestion available: `finalize-tasks --validate-only` error includes both "did you mean?" and the `create_intent` guidance.
- A WP with a zero-match literal entry and NO nearest-match (truly novel path): error includes just the `create_intent` guidance (unchanged behavior).
- A WP with the path in `create_intent`: error is suppressed and appears as INFO (unchanged behavior).

---

## Integration Check

After both subtasks:

```bash
# T020: coord worktree resolution unit tests (must pass — not optional)
pytest tests/specify_cli/cli/commands/agent/test_map_requirements_coord.py -v

# T021: ownership validation tests
pytest tests/specify_cli/ownership/ -v

# Type check
.venv/bin/mypy src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/ownership/validation.py --strict

# Lint
.venv/bin/ruff check src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/ownership/validation.py

# Broader regression check
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
```

## Definition of Done

- [ ] `map-requirements` resolves `spec.md` correctly when the coord worktree is present and the primary checkout is on a different branch.
- [ ] `map-requirements` has no regression for the no-coord-worktree case.
- [ ] Unit tests in `tests/specify_cli/cli/commands/agent/test_map_requirements_coord.py` cover the three T020 scenarios (baseline, fallback, neither).
- [ ] `validate_glob_matches` zero-match literal error always includes the `create_intent` hint, whether or not a nearest-match suggestion is also present.
- [ ] Any test assertions affected by the error message change are updated.
- [ ] `mypy src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/ownership/validation.py --strict` → zero errors.
- [ ] `ruff check` on both files → zero issues.
- [ ] No other tests broken.

## Risks for Reviewer

- The coord worktree name pattern in T020 must be read from source, not assumed. If `setup-plan` uses a different naming convention than `<mission_slug>-coord`, the fallback won't match.
- T021's message change is cosmetic but may break exact-string test assertions. Audit all `assert "matches zero files"` or `assert "create_intent"` patterns in the test suite before marking done.
- Both fixes are defensive additions (fallback, additional hint) — they do not remove any existing behavior.
