---
work_package_id: WP01
title: Flag removal in implement.py and merge.py
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
tracker_refs: []
planning_base_branch: feat/feature-alias-removal
merge_target_branch: feat/feature-alias-removal
branch_strategy: Planning artifacts for this mission were generated on feat/feature-alias-removal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/feature-alias-removal unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-feature-alias-removal-01KW0N87
base_commit: f184aa9111313cf3892280691f0cc6c252bfb0c6
created_at: '2026-06-26T01:06:24.157307+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: claude
shell_pid: '819231'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/merge.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Flag removal in implement.py and merge.py

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This loads the Python implementer profile with the coding conventions and doctrine relevant to this WP.

---

## Objective

Hard-remove the hidden `--feature` Typer option from `implement()` and `merge()`. Rename all
internal `feature`-prefixed identifiers to their `mission`-prefixed canonical equivalents. Standardize
the `merge` no-selector exit to code 2. After this WP, passing `--feature` to either command yields
Typer's built-in "No such option: --feature" error (exit 2).

**Files in scope (ONLY these two):**
- `src/specify_cli/cli/commands/implement.py`
- `src/specify_cli/cli/commands/merge.py`

Do NOT touch any file outside this list. `resolve_selector` in `selector_resolution.py` is
retained — do not delete it (C-005).

---

## Context

**Research findings (implement.py):**
- `--feature` Typer option is at line :934 in `implement()`.
- `detect_feature_context()` at line :144 takes `mission_flag` and `feature_flag`; uses
  `raw_handle = mission_flag or feature_flag` at :155.
- `detect_feature_context()` is called from two sites inside `implement.py`.
- `_run_recover_mode()` at :836 receives `feature` and contains `_feature_number` locals at :851 and :999.
- `implement()` does NOT call `resolve_selector` — no import to remove from this file.
- `implement()` function already has `# noqa: C901` for complexity; the removal of one parameter
  keeps complexity the same or lower — do NOT introduce new branching.

**Research findings (merge.py):**
- `--feature` Typer option is at line :412 in `merge()`.
- `feature` param threads through: `merge()` :412, `_resolve_slug_or_exit()` :231,
  `_dispatch_abort()` :277, `_dispatch_resume()` :328.
- `resolved_feature` local variable appears in `merge()` :453+, `_run_real_merge()` :350,
  and `_dispatch_resume()`.
- `merge()` uses `(mission or feature or "").strip()` — after removal this collapses to
  `(mission or "").strip()`.
- `_resolve_slug_or_exit()` currently exits `typer.Exit(1)` on no-selector — update to `typer.Exit(2)`.
- merge.py does NOT call `resolve_selector` — no import to clean up.

**Inline guard pattern (D-01 from plan.md):**
```python
mission_norm = mission.strip() if isinstance(mission, str) else None
if not mission_norm:
    raise typer.BadParameter("--mission <slug> is required")
mission_slug = mission_norm
```
`typer.BadParameter` exits with code 2 and formats a clean user-facing message.
The `isinstance(str)` guard replicates `_normalize_selector`'s sentinel protection (prevents TypeError
when Typer passes `OptionInfo` instead of a string in edge cases).

**Stored JSON field names (`feature_slug` in meta.json / event JSONL) MUST NOT be renamed — C-003.**
Only Python variable names and Typer parameter names change.

---

## Subtask T001 — Remove `--feature` Typer option from `implement()` signature

**Purpose**: Delete the hidden `--feature` Typer option so passing it triggers Typer's native
"No such option" error.

**Steps:**
1. Open `src/specify_cli/cli/commands/implement.py`.
2. Locate `implement()` function signature around line :934. Find the `feature` parameter:
   ```python
   feature: Annotated[str | None, typer.Option("--feature", hidden=True, ...)] = None
   ```
3. Delete the entire `feature` parameter declaration (the `Annotated[...]` line).
4. If `feature` appears in the function body, it will be addressed in T002/T003.

**Validation:**
- `grep "\"--feature\"" src/specify_cli/cli/commands/implement.py` → zero matches.

---

## Subtask T002 — Rename `feature`/`feature_flag` identifiers in implement.py

**Purpose**: Eliminate all internal `feature`-prefixed variable names in implement.py, satisfying FR-002.

**Steps:**
1. In `implement()` body (post-T001): rename `feature` local usages to `mission` where they
   referred to the old `--feature` parameter.
2. In `_run_recover_mode()` (~line :836):
   - Rename parameter `feature` → `mission`.
   - Rename local variables `_feature_number` → `_mission_number` (appears at :851 and :999).
3. In `detect_feature_context()` (~line :144):
   - Rename parameter `feature_flag` → `mission_flag`.
   - Update `raw_handle = mission_flag or feature_flag` → `raw_handle = mission_flag` (the
     feature_flag branch is being eliminated; mission_flag is the only source now).

**Validation:**
- `grep "_feature_number\|feature_flag\|feature: str" src/specify_cli/cli/commands/implement.py`
  → zero matches (excluding comments documenting the removal).

---

## Subtask T003 — Update `detect_feature_context()` signature and call sites

**Purpose**: Remove the now-deleted `feature_flag` parameter from `detect_feature_context()` and
update both call sites so no dead argument is passed.

**Steps:**
1. In `detect_feature_context()` signature, remove the `feature_flag` parameter entirely.
2. Find both call sites inside `implement.py` (they pass `feature_flag=...`). Remove the
   `feature_flag=` keyword argument from each call.
3. Confirm `detect_feature_context` is NOT imported by anything outside `implement.py`.
   Run: `grep -rn "detect_feature_context" src/ --include="*.py"` — if external callers exist,
   record them in a comment but do NOT change them in this WP.
4. Verify the simplified `raw_handle = mission_flag` path still resolves correctly for the
   mission-found and mission-not-found code paths.

**Validation:**
- `grep "feature_flag" src/specify_cli/cli/commands/implement.py` → zero matches.
- `python -c "from specify_cli.cli.commands.implement import implement"` exits without ImportError.

---

## Subtask T004 — Remove `--feature` Typer option from `merge()` signature

**Purpose**: Delete the hidden `--feature` Typer option from `merge()`.

**Steps:**
1. Open `src/specify_cli/cli/commands/merge.py`.
2. Locate `merge()` function signature around line :412. Find:
   ```python
   feature: str = typer.Option(None, "--feature", hidden=True, ...)
   ```
3. Delete the entire `feature` parameter declaration.
4. In the `merge()` body, find `resolved_feature = (mission or feature or "").strip()` and
   collapse it to `resolved_mission = (mission or "").strip()`. This collapses cleanly.

**Validation:**
- `grep "\"--feature\"" src/specify_cli/cli/commands/merge.py` → zero matches.

---

## Subtask T005 — Rename `feature`/`resolved_feature` identifiers in merge.py

**Purpose**: Rename all `feature`-prefixed local variables and parameters in merge.py so the
canonical `mission`-prefixed term is used throughout.

**Steps:**
1. In `merge()` (~line :412): rename parameter `feature` → `mission` (already removed as Typer
   option in T004; rename in any remaining usage in function body).
2. Rename all occurrences of `resolved_feature` → `resolved_mission` in:
   - `merge()` body (line :453 onward)
   - `_run_real_merge()` (~line :350) — function parameter and usages
   - `_dispatch_resume()` (~line :328) — parameter and usages
3. In `_resolve_slug_or_exit()` (~line :231): rename parameter `feature` → `mission`; update
   the `(mission or feature or "").strip()` to `(mission or "").strip()`.
4. In `_dispatch_abort()` (~line :277): rename parameter `feature` → `mission`.
5. Verify no remaining `feature` or `resolved_feature` references in merge.py (outside comments).

**Risk**: ~10 occurrences of `resolved_feature` across multiple helpers. A missed rename causes
a `NameError` at runtime. Do a final grep before declaring done.

**Validation:**
- `grep "resolved_feature\b\|: feature\b\|feature," src/specify_cli/cli/commands/merge.py`
  → zero matches (excluding comments).

---

## Subtask T006 — Standardize merge no-selector exit to code 2

**Purpose**: `merge` currently exits with code 1 when no mission selector is found. Standardize
to code 2 per D-02 in plan.md and the no-selector-error-contract.md.

**Steps:**
1. In `_resolve_slug_or_exit()` (~line :231), find the `typer.Exit(1)` call on the no-selector
   path.
2. Change `typer.Exit(1)` → `typer.Exit(2)`.
3. Verify the error message emitted on this path is a readable string (not a traceback).

**Validation:**
- `grep "Exit(1)" src/specify_cli/cli/commands/merge.py` → zero matches (all no-selector exits
  should now be `Exit(2)` or `BadParameter`).

---

## Branch Strategy

This WP executes on a lane branch off `feat/feature-alias-removal`. The execution worktree is
allocated by `lanes.json` after `finalize-tasks` runs. Do NOT create the worktree manually.

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
```

---

## Definition of Done

- [ ] `grep "\"--feature\"" src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/merge.py` → 0 matches.
- [ ] `grep "_feature_number\|feature_flag\|resolved_feature" src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/merge.py` → 0 matches.
- [ ] `grep "Exit(1)" src/specify_cli/cli/commands/merge.py` → 0 matches.
- [ ] `python -c "from specify_cli.cli.commands.implement import implement; from specify_cli.cli.commands.merge import merge"` exits cleanly.
- [ ] `ruff check src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/merge.py` → 0 errors.
- [ ] `mypy src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/merge.py` → 0 errors.
- [ ] Existing tests for implement and merge continue to pass (no tests deleted).

## Risks

- `detect_feature_context` may be exported in `__all__` or imported elsewhere; verify before
  changing its signature.
- `_run_real_merge` receives `resolved_feature` (now `resolved_mission`) as a keyword argument
  from at least two call sites; inconsistent rename causes NameError.
- Do not touch `_run_real_merge`'s callers outside `merge.py` if any exist — check with grep first.

## Reviewer Guidance

Verify:
1. `--feature` is absent from the Typer option lists of both functions.
2. `resolved_mission` flows through all four merge helper functions consistently.
3. No `typer.Exit(1)` remains in merge.py on the no-selector path.
4. `implement.py`'s complexity annotation (`# noqa: C901`) is preserved and no new branches added.
