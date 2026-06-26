---
work_package_id: WP02
title: Flag removal in next_cmd.py, research.py, context.py, accept.py
dependencies:
- WP01
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
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: claude
shell_pid: '1371948'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/research.py
- src/specify_cli/cli/commands/context.py
- src/specify_cli/cli/commands/accept.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Flag removal in next_cmd.py, research.py, context.py, accept.py

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Hard-remove the hidden `--feature` Typer option from four in-scope commands. Replace every
`resolve_selector(alias_value=feature, alias_flag="--feature", ...)` call with an inline
two-line whitespace-normalization guard. Remove now-unused `resolve_selector` imports from
three files. Rename `feature_slug` parameter names in accept.py's two helper functions.
Standardize accept.py's no-handle exit to code 2.

**Files in scope (ONLY these four):**
- `src/specify_cli/cli/commands/next_cmd.py`
- `src/specify_cli/cli/commands/research.py`
- `src/specify_cli/cli/commands/context.py`
- `src/specify_cli/cli/commands/accept.py`

Do NOT touch any file outside this list. Do NOT delete `resolve_selector` from
`selector_resolution.py` (C-005). Do NOT rename `feature_slug` JSON key strings in stored
artifacts (C-003).

---

## Context

**Inline guard pattern (D-01, plan.md):**
```python
mission_norm = mission.strip() if isinstance(mission, str) else None
if not mission_norm:
    raise typer.BadParameter("--mission <slug> is required")
mission_slug = mission_norm
```
`typer.BadParameter` → exit code 2 natively. The `isinstance(str)` check prevents TypeError
when Typer passes an `OptionInfo` sentinel for missing optional params.

**Research findings per file:**
- **next_cmd.py**: `--feature` option at :71–74 in `next()`. `resolve_selector` called at :333
  inside private `_resolve_mission_slug(mission, feature, repo_root)`.
- **research.py**: `--feature` option at :33–38 in `research()`. `resolve_selector` called at :67,
  result unwrapped with `.canonical_value`.
- **context.py**: `--feature` option at :244 in `mission_resolve_command()`. `resolve_selector`
  called at :269, result unwrapped with `.canonical_value`.
- **accept.py**: `--feature` option at :231–236 in `accept()`. Uses `raw_handle = mission or feature`
  then `resolve_mission_handle`. `feature_slug` Python variable name in two helper functions at :43
  and :73 — these are Python variable names (not JSON key strings), so rename is in scope (FR-002).
  Current no-handle path: `typer.Exit(1)` — update to `typer.Exit(2)` (D-02).

---

## Subtask T007 — Flag removal + inline guard in next_cmd.py

**Purpose**: Remove `--feature` from `next()` and eliminate the `feature` parameter from
`_resolve_mission_slug()`, replacing the `resolve_selector` call with an inline guard.

**Steps:**
1. Open `src/specify_cli/cli/commands/next_cmd.py`.
2. In `next()` signature (~line :71), delete the `feature` parameter:
   ```python
   feature: Annotated[str | None, typer.Option("--feature", hidden=True, ...)] = None
   ```
3. In `_resolve_mission_slug(mission, feature, repo_root)` (~line :331):
   - Remove `feature` from the function signature.
   - Remove the `resolve_selector` call at :333 (which used `alias_flag="--feature"`).
   - Replace with the inline guard:
     ```python
     mission_norm = mission.strip() if isinstance(mission, str) else None
     if not mission_norm:
         raise typer.BadParameter("--mission <slug> is required")
     mission_slug = mission_norm
     ```
   - Continue with `mission_slug` for downstream logic (previously the `.canonical_value`
     of `resolve_selector`'s result).
4. Update the call site in `next()` that passes `feature` to `_resolve_mission_slug(...)` —
   remove the `feature` argument.
5. Remove the `from specify_cli.cli.selector_resolution import resolve_selector` import if
   no other usage of `resolve_selector` remains in this file.

**Validation:**
- `grep "\"--feature\"\|resolve_selector\|feature_flag" next_cmd.py` → 0 matches.
- `ruff check src/specify_cli/cli/commands/next_cmd.py` → 0 errors.

---

## Subtask T008 — Flag removal + inline guard in research.py

**Purpose**: Remove `--feature` from `research()` and replace the `resolve_selector` call with
the inline guard.

**Steps:**
1. Open `src/specify_cli/cli/commands/research.py`.
2. In `research()` signature (~line :33), delete the `feature` parameter:
   ```python
   feature: str | None = typer.Option(None, "--feature", hidden=True, ...)
   ```
3. In `research()` body, find the `resolve_selector` call at :67:
   ```python
   result = resolve_selector(mission=mission, alias_value=feature, alias_flag="--feature", ...)
   mission_slug = result.canonical_value
   ```
   Replace with:
   ```python
   mission_norm = mission.strip() if isinstance(mission, str) else None
   if not mission_norm:
       raise typer.BadParameter("--mission <slug> is required")
   mission_slug = mission_norm
   ```
4. Remove the `from specify_cli.cli.selector_resolution import resolve_selector` import.
5. Verify no other reference to `resolve_selector` or `feature` (as a param/var) remains.

**Validation:**
- `grep "\"--feature\"\|resolve_selector" research.py` → 0 matches.
- `ruff check src/specify_cli/cli/commands/research.py` → 0 errors.

---

## Subtask T009 — Flag removal + inline guard in context.py

**Purpose**: Remove `--feature` from `mission_resolve_command()` and replace the `resolve_selector`
call with the inline guard.

**Steps:**
1. Open `src/specify_cli/cli/commands/context.py`.
2. In `mission_resolve_command()` signature (~line :244), delete the `feature` parameter:
   ```python
   feature: Annotated[str | None, typer.Option("--feature", hidden=True, ...)] = None
   ```
3. In `mission_resolve_command()` body, find the `resolve_selector` call at :269:
   ```python
   result = resolve_selector(mission=mission, alias_value=feature, alias_flag="--feature", ...)
   canonical = result.canonical_value
   ```
   Replace with:
   ```python
   mission_norm = mission.strip() if isinstance(mission, str) else None
   if not mission_norm:
       raise typer.BadParameter("--mission <slug> is required")
   canonical = mission_norm
   ```
4. Remove the `from specify_cli.cli.selector_resolution import resolve_selector` import.
5. Verify no other `resolve_selector` usage remains in this file.

**Validation:**
- `grep "\"--feature\"\|resolve_selector" context.py` → 0 matches.
- `ruff check src/specify_cli/cli/commands/context.py` → 0 errors.

---

## Subtask T010 — Flag removal + exit-code standardization in accept.py

**Purpose**: Remove `--feature` from `accept()`, collapse the `raw_handle` expression, and
standardize the no-handle exit to code 2.

**Steps:**
1. Open `src/specify_cli/cli/commands/accept.py`.
2. In `accept()` signature (~line :231), delete the `feature` parameter:
   ```python
   feature: str | None = typer.Option(None, "--feature", hidden=True, ...)
   ```
3. In `accept()` body, find:
   ```python
   raw_handle = mission or feature
   ```
   Collapse to:
   ```python
   raw_handle = mission
   ```
   The existing `if raw_handle is None:` check must remain — it guards against no-mission input.
4. Find the no-handle exit: currently `typer.Exit(1)`. Change to `typer.Exit(2)`.
5. Verify no other `feature` variable reference remains in `accept()` body.

**Validation:**
- `grep "\"--feature\"" accept.py` → 0 matches.
- `grep "Exit(1)" accept.py` → 0 matches (all no-selector exits are now Exit(2)).

---

## Subtask T011 — Rename `feature_slug` params in accept.py helper functions

**Purpose**: Rename the Python parameter name `feature_slug` → `mission_slug` in two helper
functions inside accept.py. These are Python variable names, NOT JSON key strings (C-003 does
not apply).

**Steps:**
1. In `_spec_artifact_dirty_paths(feature_slug, ...)` (~line :43):
   - Rename parameter `feature_slug` → `mission_slug`.
   - Update all uses of `feature_slug` inside the function body to `mission_slug`.
2. In `_commit_residual_acceptance_artifacts(feature_slug, ...)` (~line :73):
   - Rename parameter `feature_slug` → `mission_slug`.
   - Update all uses of `feature_slug` inside the function body to `mission_slug`.
3. Update the call sites inside `accept()` that pass these helpers — rename the keyword arg
   if used as `feature_slug=...` → `mission_slug=...`.

**Important constraint**: Do NOT rename `feature_slug` string literals used as dict keys
(e.g., `data.get("feature_slug")` or `meta["feature_slug"]`). Those are JSON field names
and are immutable per C-003. Only Python parameter and local variable names change.

**Validation:**
- `grep "feature_slug" accept.py` → only remaining matches should be JSON-key string literals
  (e.g., inside `get("feature_slug")` calls). No function parameter or local variable named
  `feature_slug` should remain.

---

## Subtask T012 — Verification grepping

**Purpose**: Confirm no external callers were broken and all cleanup is complete.

**Steps:**
1. Confirm no external file imports `_spec_artifact_dirty_paths` or
   `_commit_residual_acceptance_artifacts` and passes `feature_slug=` as a keyword argument:
   ```bash
   grep -rn "_spec_artifact_dirty_paths\|_commit_residual_acceptance_artifacts" src/ --include="*.py"
   ```
   If no matches outside `accept.py`, the rename is safe.

2. Confirm `resolve_selector` imports are gone from all three files:
   ```bash
   grep -n "resolve_selector" \
     src/specify_cli/cli/commands/next_cmd.py \
     src/specify_cli/cli/commands/research.py \
     src/specify_cli/cli/commands/context.py
   ```
   Expected: 0 matches.

3. Run a quick import smoke-test for all four files:
   ```bash
   python -c "
   from specify_cli.cli.commands.next_cmd import next_cmd
   from specify_cli.cli.commands.research import research
   from specify_cli.cli.commands.context import mission_resolve_command
   from specify_cli.cli.commands.accept import accept
   print('OK')
   "
   ```

**Validation:** All grepping returns expected results; import smoke-test prints "OK".

---

## Branch Strategy

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
depends on:      WP01 (implement.py + merge.py changes merged first)
```

---

## Definition of Done

- [ ] `grep "\"--feature\"" src/specify_cli/cli/commands/next_cmd.py src/specify_cli/cli/commands/research.py src/specify_cli/cli/commands/context.py src/specify_cli/cli/commands/accept.py` → 0 matches.
- [ ] `grep "resolve_selector" src/specify_cli/cli/commands/next_cmd.py src/specify_cli/cli/commands/research.py src/specify_cli/cli/commands/context.py` → 0 matches.
- [ ] `grep "feature_slug" src/specify_cli/cli/commands/accept.py` → only JSON dict-key string literals (no function params/locals).
- [ ] `grep "Exit(1)" src/specify_cli/cli/commands/accept.py` → 0 matches.
- [ ] `ruff check` + `mypy` pass on all four files.
- [ ] Existing tests for these commands continue to pass (no tests deleted).

## Risks

- `accept.py`'s `feature_slug` rename: if external code calls these private helpers with keyword
  `feature_slug=...`, it will break. T012 verification grep guards against this.
- Removing `resolve_selector` import: if the file has another call to `resolve_selector` not
  documented in research.md, the import removal causes `NameError`. Always grep before removing.

## Reviewer Guidance

1. Confirm `isinstance(mission, str)` guard pattern is consistent across all four inline guards.
2. Confirm `accept.py` no-handle path uses `typer.Exit(2)`.
3. Confirm no `feature` variable or `feature_slug` Python param remains in accept.py's helpers.
4. Confirm `resolve_selector` import gone from next_cmd.py, research.py, context.py.
