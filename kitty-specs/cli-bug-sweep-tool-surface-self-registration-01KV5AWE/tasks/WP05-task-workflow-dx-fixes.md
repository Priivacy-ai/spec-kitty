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
subtasks:
- T020
- T021
agent: claude
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/ownership/validation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix two workflow bugs discovered during this mission's own planning phase. Both are small, independent code changes that unblock the documented `map-requirements` → `finalize-tasks` task-authoring workflow and improve the error signal when ownership metadata is wrong.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP05 --agent claude`
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Worktree**: allocated per lane from `lanes.json`; do not create worktrees manually

## Context

### Bug A — `map-requirements` spec.md path resolution (T020)

**Root cause**: `map_requirements` in `src/specify_cli/cli/commands/agent/tasks.py` resolves `spec.md` by calling `resolve_feature_dir_for_mission(main_repo_root, mission_slug)`. Here `main_repo_root` is the primary checkout (typically on `main`). After `spec-kitty agent mission setup-plan` runs, a coord worktree (`.worktrees/<mission_slug>-coord/`) is created with the mission's target branch checked out. The primary checkout remains on `main`. Because `kitty-specs/<mission>/` is on the target branch, it exists in the coord worktree's working tree, not in the primary checkout's working tree. `feature_dir` therefore doesn't exist at `main_repo_root / "kitty-specs" / <mission_slug>`, and `spec.md` is reported as not found.

**Key code path** (read before editing):
1. `src/specify_cli/cli/commands/agent/tasks.py` → `map_requirements` function (~line 3444)
2. The `feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)` call (~line 3547)
3. The `if not feature_dir.exists()` guard and `spec_md = feature_dir / SPEC_MD_FILENAME` (~lines 3549–3556)

**Coord worktree naming convention**: `.worktrees/<mission_slug>-coord` — read `src/specify_cli/coordination/` or grep for `coord` to confirm the exact path pattern used by `setup-plan`.

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

5. Run `mypy src/specify_cli/cli/commands/agent/tasks.py --strict` — zero errors.

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
# T020: test with a coord worktree scenario (or mock/test the fallback logic)
pytest tests/specify_cli/ -v -k "map_requirements or map-requirements" 2>/dev/null || echo "no targeted test yet — run manual validation"

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
- [ ] `validate_glob_matches` zero-match literal error always includes the `create_intent` hint, whether or not a nearest-match suggestion is also present.
- [ ] Any test assertions affected by the error message change are updated.
- [ ] `mypy src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/ownership/validation.py --strict` → zero errors.
- [ ] `ruff check` on both files → zero issues.
- [ ] No other tests broken.

## Risks for Reviewer

- The coord worktree name pattern in T020 must be read from source, not assumed. If `setup-plan` uses a different naming convention than `<mission_slug>-coord`, the fallback won't match.
- T021's message change is cosmetic but may break exact-string test assertions. Audit all `assert "matches zero files"` or `assert "create_intent"` patterns in the test suite before marking done.
- Both fixes are defensive additions (fallback, additional hint) — they do not remove any existing behavior.
