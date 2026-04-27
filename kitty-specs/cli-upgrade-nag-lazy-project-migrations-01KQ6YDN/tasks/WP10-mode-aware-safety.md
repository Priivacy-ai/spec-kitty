---
work_package_id: WP10
title: Mode-aware safety predicates for dashboard and doctor
dependencies:
- WP04
- WP06
requirement_refs:
- FR-008
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
agent: "claude:sonnet:python-implementer:implementer"
shell_pid: "18574"
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/safety_modes.py
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/safety_modes.py
- tests/cli_gate/test_dashboard_modes.py
- tests/cli_gate/test_doctor_modes.py
priority: P2
tags: []
---

# WP10 — Mode-aware safety predicates for dashboard and doctor

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP10 --agent <name>` after WP04 and WP06 merge.

## Objective

Register mode-aware safety predicates for `dashboard` and `doctor`. Read-only invocations are SAFE under schema mismatch; write/init/sync/repair invocations are UNSAFE. This closes the user's refinement to the safe/unsafe classification (mode-aware, not command-aware).

## Context

- Spec: §"Safe / Unsafe Command Classification" — explicit user refinement during specify dialog.
- Plan: §"Engineering Alignment" Q3-A refinement.
- Data model: [`data-model.md`](../data-model.md) §1.5 (`Safety`), §5 (`register_safety`).
- Existing: `src/specify_cli/cli/commands/dashboard.py` and `src/specify_cli/cli/commands/doctor.py`. Inspect their flag schemas to determine which flags trigger write/init/sync/repair modes.

## Subtasks

### T039 — Register dashboard predicate

**Steps**:
1. Inspect `src/specify_cli/cli/commands/dashboard.py`. Identify any flags that mutate state (e.g. `--init`, `--sync`, `--repair`, `--refresh-cache`, anything that writes to disk). If `dashboard` today has no mutating flags, the predicate is a no-op (always SAFE) and this WP becomes a forward-looking placeholder.
2. In `src/specify_cli/compat/safety_modes.py`:
   ```python
   from .safety import Safety, register_safety

   _DASHBOARD_UNSAFE_FLAGS = frozenset({"--repair", "--init", "--sync", "--refresh-cache", "--rebuild"})

   def _dashboard_predicate(invocation) -> Safety:
       if any(flag in invocation.raw_args for flag in _DASHBOARD_UNSAFE_FLAGS):
           return Safety.UNSAFE
       return Safety.SAFE

   def register() -> None:
       register_safety(("dashboard",), predicate=_dashboard_predicate)
   ```
3. Call `register()` once at module import time of `compat/__init__.py` — add to WP06's `__init__.py` exports list. Alternatively, call from the typer app initialisation in `cli/main.py`. Document the choice.

**Files**: `src/specify_cli/compat/safety_modes.py` (new).

**Validation**: `dashboard` (no flags) classifies as SAFE; `dashboard --repair` classifies as UNSAFE. If `--repair` is not a real flag today, the predicate's _UNSAFE_FLAGS set should match what *is* real — check via `dashboard --help`.

### T040 — Register doctor predicate

**Steps**:
1. Inspect `src/specify_cli/cli/commands/doctor.py`. Identify mutating flags (typical: `--fix`, `--repair`, `--apply`, `--auto-fix`).
2. Add `_doctor_predicate` and call `register_safety(("doctor",), predicate=_doctor_predicate)`.
3. The two predicates can co-exist in `safety_modes.py`. Keep the file small (≤80 lines).

**Files**: `src/specify_cli/compat/safety_modes.py` (extend).

**Validation**: `doctor` classifies SAFE; `doctor --fix` classifies UNSAFE.

### T041 — Integration tests

**Steps**:
1. `tests/cli_gate/test_dashboard_modes.py`:
   - Use the `fixture_project_too_new` fixture from `tests/cli_gate/conftest.py` (created in WP08).
   - `dashboard` (read-only) → exit 0.
   - `dashboard --repair` (or whichever real mutating flag exists) → exit 5 (CLI too old for this project).
   - If `dashboard` has zero mutating flags today, write a forward-looking test that monkeypatches the predicate's UNSAFE_FLAGS to include a synthetic flag and assert the gate triggers.
2. `tests/cli_gate/test_doctor_modes.py`:
   - Mirror for `doctor` and its `--fix`/`--repair` modes.
3. Use parametrize to keep tests dense.

**Files**: `tests/cli_gate/test_dashboard_modes.py`, `tests/cli_gate/test_doctor_modes.py`.

**Validation**: `pytest tests/cli_gate/test_dashboard_modes.py tests/cli_gate/test_doctor_modes.py -v` green.

## Definition of Done

- [ ] `safety_modes.py` registers predicates for `dashboard` and `doctor`.
- [ ] Read-only invocation → SAFE; mutating invocation → UNSAFE.
- [ ] Integration tests cover both modes for both commands.
- [ ] Predicates registered exactly once (no double registration on re-import).
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.

## Risks

- `dashboard` and `doctor` may have zero mutating flags today. The WP still ships the predicate scaffolding — the predicate just always returns SAFE. Future commits add the real UNSAFE_FLAGS as new modes are introduced. Document this in the module docstring.
- Predicate registration timing: ensure it runs **before** the typer callback consults `safety.classify(...)` for the first time. Importing `compat/__init__.py` should suffice if `__init__.py` imports `safety_modes`.

## Reviewer Guidance

1. **Real flags**: confirm the UNSAFE_FLAGS frozenset matches actual flags from `dashboard --help` and `doctor --help`. Document any mismatch.
2. **Idempotent registration**: importing `safety_modes` twice does not create duplicate predicates (the registry is a dict; later registration replaces earlier).
3. **No breakage**: `dashboard` and `doctor` invocations against a *compatible* project work exactly as before.
4. **Forward-looking docstring**: the module documents that future mutating modes get added by appending to the frozenset.

## Implementation command

```bash
spec-kitty agent action implement WP10 --agent <name>
```

## Activity Log

- 2026-04-27T10:27:53Z – claude:sonnet:python-implementer:implementer – shell_pid=18574 – Started implementation via action command
- 2026-04-27T10:33:13Z – claude:sonnet:python-implementer:implementer – shell_pid=18574 – Ready: predicates registered (Option A wiring), tests cover read-only/mutating split
