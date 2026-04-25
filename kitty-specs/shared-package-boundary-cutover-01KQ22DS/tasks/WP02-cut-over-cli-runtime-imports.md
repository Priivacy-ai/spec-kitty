---
work_package_id: WP02
title: Cut Over CLI Runtime Imports
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-016
- FR-017
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:opus-4.7:python-reviewer:reviewer"
shell_pid: "38679"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/next/test_runtime_bridge_unit.py
- tests/next/test_decision_unit.py
- tests/next/test_next_command_integration.py
tags: []
---

# WP02 — Cut Over CLI Runtime Imports

## Objective

Replace every production `from spec_kitty_runtime ...` / `import spec_kitty_runtime`
in the CLI source tree with imports from
`specify_cli.next._internal_runtime`. After this WP, no production code path in
the CLI imports the standalone runtime PyPI package. Tests are rewritten in
lockstep so the suite stays green throughout.

## Context

This is the cutover step itself — the change PR #779 was rejected for trying to
defer. WP01 has shipped the internalized runtime; this WP redirects every CLI
caller to it.

The complete pre-cutover import inventory (verified by grep):

| File | Line | Statement |
|------|------|-----------|
| `src/specify_cli/next/runtime_bridge.py` | 28..37 | `from spec_kitty_runtime import (DiscoveryContext, MissionPolicySnapshot, MissionRunRef, NextDecision, NullEmitter, next_step as runtime_next_step, provide_decision_answer as runtime_provide_decision_answer, start_mission_run)` |
| `src/specify_cli/next/runtime_bridge.py` | 38 | `from spec_kitty_runtime.schema import ActorIdentity, load_mission_template_file` |
| `src/specify_cli/next/runtime_bridge.py` | 560 | `from spec_kitty_runtime.engine import _read_snapshot` (lazy) |
| `src/specify_cli/next/runtime_bridge.py` | 736 | `from spec_kitty_runtime import engine` (lazy) |
| `src/specify_cli/next/runtime_bridge.py` | 737 | `from spec_kitty_runtime.planner import plan_next` (lazy) |
| `src/specify_cli/next/runtime_bridge.py` | 858 | `from spec_kitty_runtime.engine import _read_snapshot` (lazy) |
| `src/specify_cli/cli/commands/next_cmd.py` | 227 | `from spec_kitty_runtime.engine import _read_snapshot` (lazy) |

Test files importing the same:
- `tests/next/test_runtime_bridge_unit.py` (lines 14, 305, 306, 343, 344, 426, 583)
- `tests/next/test_decision_unit.py` (lines 120, 121, 163)
- `tests/next/test_next_command_integration.py` (lines 164, 165, 202, 593)

After WP02, the production grep set MUST be empty:
```bash
grep -rn "from spec_kitty_runtime\|import spec_kitty_runtime" src/
# expected: zero matches
```

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: lane A (depends on WP01).

## Implementation

### Subtask T010 — Cut over `runtime_bridge.py`

**Purpose**: The single largest production importer of `spec_kitty_runtime` is
this file. Six import sites must be rewritten in one atomic change.

**Steps**:

1. Replace the top-level imports (lines 28..37):
   ```python
   # Before:
   from spec_kitty_runtime import (
       DiscoveryContext,
       MissionPolicySnapshot,
       MissionRunRef,
       NextDecision,
       NullEmitter,
       next_step as runtime_next_step,
       provide_decision_answer as runtime_provide_decision_answer,
       start_mission_run,
   )

   # After:
   from specify_cli.next._internal_runtime import (
       DiscoveryContext,
       MissionPolicySnapshot,
       MissionRunRef,
       NextDecision,
       NullEmitter,
       next_step as runtime_next_step,
       provide_decision_answer as runtime_provide_decision_answer,
       start_mission_run,
   )
   ```

2. Replace the schema import (line 38):
   ```python
   # Before:
   from spec_kitty_runtime.schema import ActorIdentity, load_mission_template_file
   # After:
   from specify_cli.next._internal_runtime.schema import ActorIdentity, load_mission_template_file
   ```

3. Replace the four lazy imports (lines 560, 736, 737, 858) with their
   `_internal_runtime` equivalents:
   - `from spec_kitty_runtime.engine import _read_snapshot` →
     `from specify_cli.next._internal_runtime.engine import _read_snapshot`
   - `from spec_kitty_runtime import engine` →
     `from specify_cli.next._internal_runtime import engine`
   - `from spec_kitty_runtime.planner import plan_next` →
     `from specify_cli.next._internal_runtime.planner import plan_next`

4. The aliases `runtime_next_step` and `runtime_provide_decision_answer` are
   preserved verbatim — they are referenced throughout the file. Do not
   refactor them in this WP.

5. The module docstring at the top of `runtime_bridge.py` references
   `spec-kitty-runtime` engine. Update the docstring to read "CLI-internal
   `_internal_runtime` engine" and add a one-line note that the runtime is now
   internalized as part of mission `shared-package-boundary-cutover-01KQ22DS`.

**Files**: `src/specify_cli/next/runtime_bridge.py`.

**Validation**:
- `grep -n "spec_kitty_runtime" src/specify_cli/next/runtime_bridge.py` returns zero matches.
- `mypy --strict src/specify_cli/next/runtime_bridge.py` passes.
- `python -c "from specify_cli.next.runtime_bridge import *"` succeeds.

### Subtask T011 — Cut over `next_cmd.py` [P]

**Purpose**: One lazy import remains in `next_cmd.py`. Rewrite it.

**Steps**:

1. Replace the lazy import at line 227:
   ```python
   # Before:
   from spec_kitty_runtime.engine import _read_snapshot
   # After:
   from specify_cli.next._internal_runtime.engine import _read_snapshot
   ```

2. The function context that performs this import is unchanged.

**Files**: `src/specify_cli/cli/commands/next_cmd.py`.

**Validation**:
- `grep -n "spec_kitty_runtime" src/specify_cli/cli/commands/next_cmd.py` returns zero matches.
- `mypy --strict` passes.

### Subtask T012 — Rewrite `tests/next/` test imports

**Purpose**: Three test files import `spec_kitty_runtime` directly. Rewrite them
to use `_internal_runtime`. Test intent is preserved; only import paths change.

**Steps**:

1. `tests/next/test_runtime_bridge_unit.py` — replace imports at lines 14, 305,
   306, 343, 344, 426, 583. Most are of the form
   `from spec_kitty_runtime import ...` or
   `from spec_kitty_runtime.engine import _read_snapshot` /
   `import spec_kitty_runtime.engine as runtime_engine` /
   `from spec_kitty_runtime.schema import MissionRuntimeError`. Each becomes the
   `_internal_runtime` equivalent.

2. `tests/next/test_decision_unit.py` — replace imports at lines 120, 121, 163.

3. `tests/next/test_next_command_integration.py` — replace imports at lines 164,
   165, 202, 593.

4. Per FR-016, if any test fixture in these files **must** continue to reference
   `spec_kitty_runtime` for migration / removal-assertion purposes, that
   reference is gated by:
   - A clear marker (`@pytest.mark.runtime_migration_quarantine` — define in
     `conftest.py` if it doesn't already exist).
   - A comment containing the literal mission slug
     `shared-package-boundary-cutover-01KQ22DS` and the cutover removal
     milestone (e.g. "remove when mission lands on 2026-04-25").

   This WP does NOT need any such fixture — the test rewrites are pure import
   substitutions. Document the absence in a comment at the top of each file.

**Files**: 3 test files in `tests/next/`.

**Validation**:
- `grep -rn "spec_kitty_runtime" tests/next/` returns zero matches outside
  fixture-quarantine markers (this WP shouldn't introduce any).
- `pytest tests/next/ -v` passes.

### Subtask T013 — Run full unit + integration suite

**Purpose**: Confirm zero behavior regression from the cutover. Any delta caught
here means WP01's parity tests missed something — fix it (in this WP, against
`_internal_runtime`'s implementation) before the WP closes.

**Steps**:

1. Run the unit test gate:
   ```bash
   pytest -m "fast or integration" -x
   ```

2. Run the next-command integration tests specifically:
   ```bash
   pytest tests/next/ -v
   ```

3. If any test fails for behavioral reasons (not import-path reasons): the
   failure is a parity gap. Fix it inside `_internal_runtime` (yes, even though
   it's WP01's authoritative surface — WP02 owns this validation gate, and
   WP01's authoritative surface allows direct fixes when they surface during
   WP02 validation). File a one-line note at the top of the affected
   `_internal_runtime` sub-module: "Delta caught in WP02 validation: <symbol>
   needed <fix>."

4. Run the full architectural test suite to confirm no layer-rule regressions:
   ```bash
   pytest tests/architectural/ -v
   ```

**Files**: None modified directly in this subtask; any fixes flow into files
covered by other subtasks (T010..T012 or, if a parity gap, into WP01's
authoritative files in a coordinated update).

**Validation**:
- All test suites green.
- `grep -rn "from spec_kitty_runtime\|import spec_kitty_runtime" src/` returns zero matches.

## Definition of Done

- [ ] All 4 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] Zero production imports of `spec_kitty_runtime` in `src/`.
- [ ] Three rewritten test files pass.
- [ ] Full unit + integration suite green.
- [ ] `mypy --strict` green on changed files.

## Risks

- **A behavioral delta surfaces only after the cutover is wired up.** Mitigation:
  WP01's parity tests catch most; T013's full-suite run is the second gate.
  Any delta caught here is fixed in WP01's authoritative surface immediately
  (T013 explicitly authorizes this cross-WP fix path because the alternative —
  reverting WP02 — is worse for cutover atomicity).
- **Aliased imports (`runtime_next_step`) are renamed inadvertently.**
  Mitigation: T010 explicitly preserves the aliases.

## Reviewer guidance

- Verify the production grep set is empty.
- Verify rewritten tests preserve assertion intent (compare diffs side-by-side).
- Verify the integration suite is green.
- If any delta-fix touched WP01's surface, verify the fix is documented in the
  affected `_internal_runtime/` module.

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T11:02:39Z – claude:opus-4.7:python-implementer:implementer – shell_pid=32856 – Started implementation via action command
- 2026-04-25T11:11:38Z – claude:opus-4.7:python-implementer:implementer – shell_pid=32856 – Ready for review: cutover complete; zero spec_kitty_runtime imports in src/, all 245 next+architectural tests pass
- 2026-04-25T11:12:00Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=38679 – Started review via action command
