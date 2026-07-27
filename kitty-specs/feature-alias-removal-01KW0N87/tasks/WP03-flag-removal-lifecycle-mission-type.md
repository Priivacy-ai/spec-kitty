---
work_package_id: WP03
title: Flag removal in lifecycle.py and mission_type.py
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/feature-alias-removal
merge_target_branch: feat/feature-alias-removal
branch_strategy: Planning artifacts for this mission were generated on feat/feature-alias-removal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/feature-alias-removal unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
agent: claude
shell_pid: '1566092'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/lifecycle.py
- src/specify_cli/cli/commands/mission_type.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 – Flag removal in lifecycle.py and mission_type.py

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Remove the hidden `--feature` Typer option from `lifecycle.plan()`, `lifecycle.tasks()`, and
`mission_type.current_cmd()`. Rename the positional `feature` → `mission` in
`lifecycle.specify()` per the orchestrator ruling. Confirm `_legacy_aliases.py` is absent.

**Files in scope (ONLY these two):**
- `src/specify_cli/cli/commands/lifecycle.py`
- `src/specify_cli/cli/commands/mission_type.py`

**CRITICAL constraint**: The `resolve_selector` call at line :136 in `lifecycle.specify()` uses
`alias_flag="--mission"` (aliasing `--mission-type` → `--mission`). This call is OUT OF SCOPE
and MUST NOT be touched. The `resolve_selector` import in `lifecycle.py` must be KEPT.

---

## Context

**Research findings (lifecycle.py):**
- `--feature` option at :169 in `plan()` and :258 in `tasks()`.
- `resolve_selector` called in `plan()` at :176 with `alias_flag="--feature"` — remove and inline guard.
- `resolve_selector` called in `tasks()` at :266 with `alias_flag="--feature"` — remove and inline guard.
- `resolve_selector` called in `specify()` at :136 with `alias_flag="--mission"` — OUT OF SCOPE, DO NOT TOUCH.
- Positional `feature: str = typer.Argument(...)` in `specify()` at :126 — rename to `mission`
  (orchestrator ruling); metavar changes from `FEATURE` to `MISSION` (Typer auto-derives from param name).
- `_slugify_feature_input()` function is NOT renamed (its signature takes `value: str`, not `feature`).

**Research findings (mission_type.py):**
- `--feature` option at :207–210 in `current_cmd()`.
- `resolve_selector` called at :246, inside `if mission is None and feature is None: else:` block.
- After removal: the `if mission is None:` path uses the inline guard instead.
- `resolve_selector` import must be removed from mission_type.py (no other caller in that file).

**Inline guard pattern:**
```python
mission_norm = mission.strip() if isinstance(mission, str) else None
if not mission_norm:
    raise typer.BadParameter("--mission <slug> is required")
mission_slug = mission_norm
```

---

## Subtask T013 — Remove `--feature` from `lifecycle.plan()` and inline guard

**Purpose**: Delete the hidden `--feature` option from `plan()` and replace the `resolve_selector`
call (which used `alias_flag="--feature"`) with the inline whitespace-normalization guard.

**Steps:**
1. Open `src/specify_cli/cli/commands/lifecycle.py`.
2. In `plan()` signature (~line :169), delete:
   ```python
   feature: str | None = typer.Option(None, "--feature", hidden=True, ...)
   ```
3. In `plan()` body, find the `resolve_selector` block (~line :176). It currently looks like:
   ```python
   if mission is not None or feature is not None:
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
   The `if mission is not None or feature is not None:` outer conditional becomes unnecessary —
   the inline guard handles the None/empty case directly.

**Critical**: Do NOT remove the `resolve_selector` import yet — it's still used in `specify()`.

**Validation:**
- `grep "\"--feature\"" lifecycle.py` for `plan` section → 0 matches.

---

## Subtask T014 — Remove `--feature` from `lifecycle.tasks()` and inline guard

**Purpose**: Same as T013 but for the `tasks()` sub-command in lifecycle.py.

**Steps:**
1. In `tasks()` signature (~line :258), delete the `feature` parameter declaration.
2. In `tasks()` body, find the `resolve_selector` block (~line :266). Replace with the same
   inline guard pattern:
   ```python
   mission_norm = mission.strip() if isinstance(mission, str) else None
   if not mission_norm:
       raise typer.BadParameter("--mission <slug> is required")
   mission_slug = mission_norm
   ```
3. Confirm the `resolve_selector` import is still present in the file (needed for `specify()` at :136).

**Validation:**
- `grep "\"--feature\"" lifecycle.py` → 0 matches (both `plan()` and `tasks()` cleaned).
- `grep "resolve_selector" lifecycle.py` → at least one match remains (the `specify()` call site).

---

## Subtask T015 — Rename positional `feature` → `mission` in `lifecycle.specify()`

**Purpose**: Rename the positional argument from `feature` to `mission` in `lifecycle.specify()`.
This satisfies the orchestrator ruling and the terminology canon (FR-002). The CLI invocation
`spec-kitty lifecycle specify my-mission-slug` is UNCHANGED because Typer derives the CLI
argument name from the metavar/position, not the Python param name for positional args.

**Steps:**
1. In `specify()` signature (~line :126), find:
   ```python
   feature: str = typer.Argument(...)
   ```
   Rename the Python parameter to `mission`:
   ```python
   mission: str = typer.Argument(...)
   ```
2. If the `typer.Argument(...)` call specifies `metavar="FEATURE"`, change it to `metavar="MISSION"`.
   If no explicit metavar is set, Typer auto-derives it from the param name, so it will become
   `MISSION` automatically.
3. In the `specify()` body, find all uses of the old `feature` variable and rename to `mission`.
4. Find the call `_slugify_feature_input(feature)` and update to `_slugify_feature_input(mission)`.
   The `_slugify_feature_input` function itself is NOT renamed.
5. Confirm `resolve_selector` call at :136 is NOT touched (it uses `alias_flag="--mission"`
   for aliasing `--mission-type` → `--mission` — completely unrelated to this change).

**Validation:**
- `spec-kitty lifecycle specify test-slug --dry-run` (or a quick import test) works without error.
- No `feature` variable reference remains in `specify()` body.

---

## Subtask T016 — Remove `--feature` from `mission_type.current_cmd()` and inline guard

**Purpose**: Remove `--feature` from `current_cmd()` in mission_type.py and replace the
`resolve_selector` call with the inline guard. Remove the `resolve_selector` import.

**Steps:**
1. Open `src/specify_cli/cli/commands/mission_type.py`.
2. In `current_cmd()` signature (~line :207), delete the `feature` parameter:
   ```python
   feature: Annotated[str | None, typer.Option("--feature", hidden=True, ...)] = None
   ```
3. In `current_cmd()` body, find the `if mission is None and feature is None: else:` block (~line :217):
   ```python
   if mission is None and feature is None:
       # auto-detect path
   else:
       result = resolve_selector(mission=mission, alias_value=feature, alias_flag="--feature", ...)
       ...
   ```
   After removal, the `else:` branch's alias resolution collapses. Replace with:
   ```python
   if mission is None:
       # auto-detect path (unchanged)
   else:
       mission_norm = mission.strip() if isinstance(mission, str) else None
       if not mission_norm:
           raise typer.BadParameter("--mission <slug> is required")
       mission_slug = mission_norm
   ```
   Ensure the auto-detect code path is preserved exactly. The auto-detect path runs from
   `tmp_path` (no project) and emits its own error when no project is found — leave it alone.
4. Remove the `from specify_cli.cli.selector_resolution import resolve_selector` import.
5. Verify no other `resolve_selector` usage remains in mission_type.py.

**Validation:**
- `grep "\"--feature\"\|resolve_selector" mission_type.py` → 0 matches.
- `ruff check src/specify_cli/cli/commands/mission_type.py` → 0 errors.

---

## Subtask T017 — Confirm `_legacy_aliases.py` is absent (FR-005)

**Purpose**: FR-005 requires verification that `src/specify_cli/missions/_legacy_aliases.py`
does not exist. This WP is the implementation phase where the verification must be re-confirmed.

**Steps:**
1. Run:
   ```bash
   find src/ -name "_legacy_aliases.py"
   grep -rn "_legacy_aliases" src/
   ```
2. If BOTH return zero results: record the verification output in a comment in `lifecycle.py`
   or a brief note in the WP review. No further action needed.
3. If `_legacy_aliases.py` EXISTS: DO NOT delete it immediately. Run `grep -rn "_legacy_aliases" src/`
   to find all importers. Report the finding to the reviewer before taking any action.
   (Per spec, if live importers exist, de-export first; deletion is blocked.)

**Validation:** Verification output captured; result is "absent" (expected).

---

## Branch Strategy

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
depends on:      WP02 (next_cmd.py, research.py, context.py, accept.py changes merged first)
```

---

## Definition of Done

- [ ] `grep "\"--feature\"" src/specify_cli/cli/commands/lifecycle.py src/specify_cli/cli/commands/mission_type.py` → 0 matches.
- [ ] `grep "resolve_selector" src/specify_cli/cli/commands/lifecycle.py` → exactly 1 match (the `specify()` call at line :136 with `alias_flag="--mission"`).
- [ ] `grep "resolve_selector" src/specify_cli/cli/commands/mission_type.py` → 0 matches.
- [ ] `lifecycle.specify()` Python param is `mission` (not `feature`); `_slugify_feature_input(mission)` call updated.
- [ ] `_legacy_aliases.py` confirmed absent; grep result recorded.
- [ ] `ruff check` + `mypy` pass on both files.
- [ ] Existing tests for lifecycle and mission_type continue to pass.

## Risks

- `lifecycle.specify()` positional rename: if any test invokes `specify(feature="...")` as a
  keyword argument, it will break. The helper function `_slugify_feature_input` takes `value: str`
  not `feature` — no collision. Grep for `specify(feature=` in tests before renaming.
- `mission_type.current_cmd()` auto-detect path must be preserved unchanged. Only the `else:`
  branch (explicit mission selector) is modified.

## Reviewer Guidance

1. Confirm the `resolve_selector` call in `lifecycle.specify()` at :136 is UNTOUCHED.
2. Confirm `resolve_selector` import is retained in `lifecycle.py` and removed from `mission_type.py`.
3. Confirm `lifecycle.specify()` still accepts a positional argument (not `--mission`).
4. Confirm `_legacy_aliases.py` verification result is recorded.
