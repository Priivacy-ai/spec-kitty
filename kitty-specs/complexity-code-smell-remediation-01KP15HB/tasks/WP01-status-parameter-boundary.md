---
work_package_id: WP01
title: 'Status: Parameter Boundary Reduction'
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-018
planning_base_branch: feat/complexity-debt-remediation
merge_target_branch: feat/complexity-debt-remediation
branch_strategy: Planning artifacts for this feature were generated on feat/complexity-debt-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/complexity-debt-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-complexity-code-smell-remediation-01KP15HB
base_commit: fa2a575e9528889b4102800aaeef929c4e371325
created_at: '2026-04-13T06:24:20.673983+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T031
shell_pid: "53183"
agent: "codex:gpt-5.4:python-reviewer:reviewer"
history:
- date: '2026-04-12'
  action: created
  author: spec-kitty.tasks
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/transitions.py
- src/specify_cli/status/__init__.py
- src/specify_cli/status/bootstrap.py
- src/specify_cli/status/validate.py
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/orchestrator_api/commands.py
- tests/agent/test_orchestrator_commands_integration.py
- tests/agent/test_review_feedback_pointer_2x_unit.py
- tests/agent/test_workflow_review_lane_gate.py
- tests/git_ops/test_atomic_status_commits_unit.py
- tests/lanes/test_implementation_recovery.py
- tests/merge/test_merge_done_recording.py
- tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py
- tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py
- tests/specify_cli/cli/commands/test_merge.py
- tests/status/test_emit.py
- tests/status/test_event_mission_id.py
- tests/status/test_parity.py
- tests/status/test_status_e2e_integration.py
- tests/status/test_sync_lane_mapping.py
- tests/status/test_views.py
- tests/sync/test_dual_write_integration.py
- tests/upgrade/test_read_cutover_integration.py
- tests/specify_cli/lanes/test_recovery.py
- tests/status/test_transitions.py
- tests/status/test_validate.py
tags: []
---

# WP01 — Status: Parameter Boundary Reduction

## Objective

Reduce `emit_status_transition` from 19 parameters to 1 (`TransitionRequest`) and
`validate_transition`/`_run_guard` from 12 parameters to 3 (`from_lane`, `to_lane`, `GuardContext`).
Update all call sites. Zero behaviour change.

**FRs**: FR-001, FR-003
**Governing tactics**: `refactoring-encapsulate-record`, `refactoring-change-function-declaration`
**Procedure**: `src/doctrine/procedures/shipped/refactoring.procedure.yaml`
**Directives**: DIRECTIVE_034 (characterize before restructuring), DIRECTIVE_030 (quality gates)

## Branch Strategy

- **Lane**: A (first)
- **Planning base / merge target**: `feat/complexity-debt-remediation`
- **Worktree**: Allocated by `finalize-tasks` — check `lanes.json` for the exact path.
- **Implementation command**: `spec-kitty agent action implement WP01 --agent <name>`

Do not start this WP from `main`. Use the lane worktree.

## Context

`emit_status_transition` is the single entry point for all status state changes. It currently
takes 19 parameters (5 positional, 14 keyword-only). Call sites must construct these separately,
making misuse invisible to mypy when fields are passed in the wrong order.

`validate_transition` and `_run_guard` share 10 keyword parameters that carry guard condition
context. Consolidating them into `GuardContext` makes guard logic testable in isolation.

Both changes follow the **Encapsulate Record** + **Change Function Declaration** refactoring
pattern: define the new dataclass, update the function body, migrate callers one-by-one.

**Baseline CC** (ruff): `emit_status_transition` CC ≈ 21, `validate_transition` CC ≈ 8.
Neither CC changes with this refactor — the goal is parameter reduction, not branch reduction.

## Pre-work: Confirm call sites

Before writing any code:
```bash
grep -rl "emit_status_transition" src/ tests/ --include="*.py" | sort
grep -rl "validate_transition" src/ tests/ --include="*.py" | sort
```

Confirm the lists match the `owned_files` in this WP's frontmatter. If new files appear, add
them to `owned_files` before proceeding.

---

## Subtask T001 — Add `TransitionRequest` dataclass

**Purpose**: Define the consolidation record for `emit_status_transition` inputs.

**File**: `src/specify_cli/status/models.py` (add after `StatusSnapshot`, before module end)

**Implementation**:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class TransitionRequest:
    """All inputs for a single status transition.

    Pass an instance of this as the sole positional argument to
    emit_status_transition(). All fields default to None / False so callers
    only populate what they need — same ergonomics as the old keyword API.
    """
    # Mission identity
    feature_dir: Path | None = None
    mission_dir: Path | None = None
    mission_slug: str | None = None
    _legacy_mission_slug: str | None = None
    repo_root: Path | None = None

    # Transition
    wp_id: str | None = None
    to_lane: str | None = None
    force: bool = False
    reason: str | None = None

    # Actor
    actor: str | None = None
    execution_mode: str = "worktree"

    # Evidence
    evidence: dict[str, Any] | None = None
    review_ref: str | None = None
    review_result: Any = None

    # Guard hints
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    policy_metadata: dict[str, Any] | None = None
```

Also export `TransitionRequest` from `src/specify_cli/status/__init__.py`.

**Validation**:
- `from specify_cli.status import TransitionRequest` works
- `mypy src/specify_cli/status/models.py` — no errors

---

## Subtask T002 — Update `emit_status_transition` signature

**Purpose**: Replace the 19-parameter signature with `(request: TransitionRequest) -> StatusEvent`.

**File**: `src/specify_cli/status/emit.py`

**Implementation**:

Replace the function signature (lines 255–275) with:

```python
def emit_status_transition(request: TransitionRequest) -> StatusEvent:
    """Central orchestration function for all status state changes.
    ...existing docstring...
    """
    # Unpack from request — preserves all existing logic below
    feature_dir = request.feature_dir
    _legacy_mission_slug = request._legacy_mission_slug
    wp_id = request.wp_id
    to_lane = request.to_lane
    actor = request.actor
    mission_dir = request.mission_dir
    mission_slug = request.mission_slug
    force = request.force
    reason = request.reason
    evidence = request.evidence
    review_ref = request.review_ref
    workspace_context = request.workspace_context
    subtasks_complete = request.subtasks_complete
    implementation_evidence_present = request.implementation_evidence_present
    execution_mode = request.execution_mode
    repo_root = request.repo_root
    policy_metadata = request.policy_metadata
    review_result = request.review_result
    # ... rest of function body unchanged ...
```

Add `from specify_cli.status.models import TransitionRequest` to imports.

**Important**: Do NOT change any logic inside the function body. Only change the signature and
add the unpacking block at the top. The internal pipeline (validate → persist → materialize →
views → SaaS) must be byte-for-byte equivalent.

**Validation**:
- `mypy src/specify_cli/status/emit.py` — no errors
- `pytest tests/status/test_emit.py` — may fail until call sites are updated (T003)

---

## Subtask T003 — Migrate all 27 `emit_status_transition` call sites

**Purpose**: Replace every direct keyword-argument call with a `TransitionRequest(...)` constructor.

**Files**: All 27 files listed in `owned_files` that call `emit_status_transition`.

**Migration pattern**:

```python
# Before
event = emit_status_transition(
    feature_dir=feature_dir,
    wp_id=wp_id,
    to_lane="claimed",
    actor="claude",
)

# After
event = emit_status_transition(TransitionRequest(
    feature_dir=feature_dir,
    wp_id=wp_id,
    to_lane="claimed",
    actor="claude",
))
```

**Procedure**:
1. Process files in this order: internal status files first, then CLI, then tests.
   Recommended order:
   ```
   src/specify_cli/status/bootstrap.py
   src/specify_cli/status/__init__.py
   src/specify_cli/lanes/recovery.py
   src/specify_cli/orchestrator_api/commands.py
   src/specify_cli/cli/commands/implement.py
   src/specify_cli/cli/commands/merge.py
   src/specify_cli/cli/commands/agent/status.py
   src/specify_cli/cli/commands/agent/tasks.py
   src/specify_cli/cli/commands/agent/workflow.py
   [then all test files]
   ```
2. After each file: `mypy src/ --no-error-summary 2>&1 | grep -v "^Found"` — fix any new errors before moving on.
3. Ensure `TransitionRequest` is imported at the top of each migrated file:
   `from specify_cli.status import TransitionRequest` or
   `from specify_cli.status.models import TransitionRequest`

**Edge cases**:
- Some test files may call `emit_status_transition` via a helper function or fixture. Find all
  usages within the file with `grep -n "emit_status_transition" <file>` before migrating.
- If a file passes `emit_status_transition` as a callable (e.g. `func = emit_status_transition;
  func(...)`), update the call site where the function is invoked, not the alias.

**Validation after all files**:
- `mypy src/ tests/ 2>&1 | tail -5` — zero errors
- `pytest tests/status/test_emit.py -x` — passes

---

## Subtask T004 — Add `GuardContext` dataclass

**Purpose**: Define the consolidation record for `validate_transition` / `_run_guard` inputs.

**File**: `src/specify_cli/status/transitions.py` (add near top, before `_run_guard`)

**Implementation**:

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class GuardContext:
    """Guard condition inputs for a lane transition.

    All keyword parameters of validate_transition / _run_guard become fields
    of GuardContext. from_lane and to_lane remain positional (routing keys).
    """
    force: bool = False
    actor: str | None = None
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    reason: str | None = None
    review_ref: str | None = None
    evidence: Any = None
    review_result: Any = None
    current_actor: str | None = None
```

Export `GuardContext` from `src/specify_cli/status/__init__.py`.

---

## Subtask T005 — Update `validate_transition` and `_run_guard`

**Purpose**: Replace keyword-only parameters with `ctx: GuardContext`.

**File**: `src/specify_cli/status/transitions.py`

**Updated `_run_guard` signature**:
```python
def _run_guard(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext,
) -> tuple[bool, str | None]:
```

Replace all `parameter` references inside `_run_guard` with `ctx.parameter`. For example:
- `actor` → `ctx.actor`
- `workspace_context` → `ctx.workspace_context`
- etc.

**Updated `validate_transition` signature**:
```python
def validate_transition(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext,
) -> tuple[bool, str | None]:
```

Inside `validate_transition`, `_run_guard` is called — update that call to:
```python
return _run_guard(resolved_from, resolved_to, ctx)
```

All other logic inside `validate_transition` that uses the guard parameters must be updated
to access them via `ctx` (e.g. `force` → `ctx.force`).

**Validation**:
- `mypy src/specify_cli/status/transitions.py` — zero errors
- `pytest tests/status/test_transitions.py -x` — may fail until call sites updated (T006)

---

## Subtask T006 — Migrate all 10 `validate_transition` call sites

**Purpose**: Replace keyword-argument calls with `GuardContext(...)` constructor.

**Files**: All files listed in `owned_files` that call `validate_transition`.

Files to migrate:
```
src/specify_cli/cli/commands/agent/status.py  (already in owned_files from T003)
src/specify_cli/lanes/recovery.py             (already owned)
src/specify_cli/status/emit.py                (already owned — note: emit calls validate_transition internally)
src/specify_cli/status/__init__.py            (already owned)
src/specify_cli/status/validate.py            (already owned)
tests/specify_cli/lanes/test_recovery.py
tests/status/test_status_e2e_integration.py
tests/status/test_transitions.py
tests/status/test_validate.py
```

**Migration pattern**:

```python
# Before
ok, err = validate_transition(
    "planned", "claimed",
    actor="claude",
    force=False,
)

# After
ok, err = validate_transition(
    "planned", "claimed",
    GuardContext(actor="claude", force=False),
)
```

Note: `emit_status_transition` (in `emit.py`) internally calls `validate_transition`. After
T002, it unpacks from `TransitionRequest`. You must construct `GuardContext` from those
unpacked locals when calling `validate_transition`.

**Validation**:
- `mypy src/ tests/ 2>&1 | tail -5` — zero errors
- `pytest tests/status/ -x` — passes

---

## Subtask T031 — Guard `workflow.py` call to `top_level_implement()` against OptionInfo leakage

**Purpose**: Prevent recurrence of the typer OptionInfo default leakage bug (#571, partially
fixed by f18e3a28). Ensure the programmatic call path is robust and tested (FR-018).

**File**: `src/specify_cli/cli/commands/agent/workflow.py`
**Also update**: The `from specify_cli.charter.context import build_charter_context` import in
this file should be redirected to `from charter.context import build_charter_context` as part of
this task (charter import clean-up coordinated with WP05 T026).

**Background**: When `agent action implement` calls `top_level_implement()` as a Python
function (not via CLI entry point), any optional parameter that retains its `typer.models.OptionInfo`
default is truthy and triggers unexpected branches. The fix in f18e3a28 passed `recover=False`
explicitly; this task extends that guard to cover all optional parameters.

**Step 1 — Redirect charter import**:

```python
# Before
from specify_cli.charter.context import build_charter_context

# After
from charter.context import build_charter_context
```

**Step 2 — Audit all `top_level_implement()` call sites in `workflow.py`**:

```bash
grep -n "top_level_implement" src/specify_cli/cli/commands/agent/workflow.py
```

For each call, check every keyword argument against the function signature in `implement.py`
and verify it is passed as an explicit Python value (not left to the typer default).

**Step 3 — Add defensive coercion helper if multiple parameters are at risk**:

```python
from typer.models import OptionInfo as _OptionInfo

def _coerce_typer_defaults(**kwargs: object) -> dict[str, object]:
    """Strip OptionInfo objects from keyword args; replace with their Python default or None."""
    return {
        k: (None if isinstance(v, _OptionInfo) else v)
        for k, v in kwargs.items()
    }
```

Apply the helper (or inline explicit defaults) at each `top_level_implement()` call site.

**Step 4 — Add regression test**:

File: `tests/agent/test_implement_programmatic_call.py` (new file, add to `owned_files`):

```python
def test_top_level_implement_called_programmatically_returns_workspace(tmp_path, ...):
    """Ensure top_level_implement() works when called as Python, not via CLI.

    Regression test for #571: typer OptionInfo leakage caused recover=OptionInfo,
    which is truthy, triggering crash-recovery mode on every call.
    """
    # Set up a minimal lane worktree fixture
    # Call top_level_implement(..., recover=False, ...) directly (not via subprocess)
    # Assert workspace path is returned (not an error)
```

**Validation**:
```bash
pytest tests/agent/ -x -k "implement_programmatic" -q
mypy src/specify_cli/cli/commands/agent/workflow.py
```

---

## Subtask T007 — Quality gate

**Purpose**: Verify the full quality suite passes with no regressions.

**Commands** (run all three; all must be green):
```bash
ruff check src/
mypy src/
pytest tests/ -x --timeout=120
```

**Expected outcomes**:
- ruff: zero violations on all modified files
- mypy: zero new errors (baseline: zero errors on unchanged files)
- pytest: same pass/fail counts as before WP01 (no new failures)

**If tests fail**: Do NOT add suppressions. Diagnose the failure — it will be a call site that
was missed during T003 or T006. Fix the missed migration; do not patch the test.

---

## Definition of Done

- [ ] `TransitionRequest` dataclass exists in `status/models.py` and is exported from `status/__init__.py`
- [ ] `emit_status_transition` accepts exactly one positional parameter of type `TransitionRequest`
- [ ] All 27 call-site files construct `TransitionRequest(...)` explicitly
- [ ] `GuardContext` dataclass exists in `status/transitions.py` and is exported from `status/__init__.py`
- [ ] `validate_transition` and `_run_guard` accept `(from_lane, to_lane, ctx: GuardContext)`
- [ ] All 10 `validate_transition` call-site files construct `GuardContext(...)` explicitly
- [ ] `workflow.py` imports `build_charter_context` from `charter.context` (not `specify_cli.charter.context`)
- [ ] All `top_level_implement()` call sites in `workflow.py` pass optional params as explicit Python values (not OptionInfo defaults)
- [ ] Regression test for programmatic `top_level_implement()` call exists and passes
- [ ] `ruff check src/` — zero violations
- [ ] `mypy src/` — zero errors
- [ ] `pytest tests/` — no new failures
- [ ] No new `# noqa` or `# type: ignore` comments added

## Reviewer Guidance

Focus on:
1. Did any call site get missed? Run `grep -r "emit_status_transition\|validate_transition" src/ tests/ --include="*.py" -l` and confirm every file uses the new API.
2. Is the internal logic of `emit_status_transition` byte-for-byte unchanged? The only difference should be the signature and the unpacking block at the top.
3. Does mypy type-check the `TransitionRequest` and `GuardContext` usages correctly?
4. Any circular imports introduced?

## Activity Log

- 2026-04-13T06:24:20Z – claude – shell_pid=12263 – Assigned agent via action command
- 2026-04-13T11:57:44Z – codex – shell_pid=53183 – Started review via action command
- 2026-04-13T11:59:00Z – codex – shell_pid=53183 – Moved to planned
- 2026-04-13T12:01:50Z – codex – shell_pid=53183 – Started implementation via action command
- 2026-04-13T12:07:17Z – codex – shell_pid=53183 – Moved to for_review
- 2026-04-13T13:11:52Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Started review via action command
- 2026-04-13T13:12:49Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Moved to planned
- 2026-04-13T13:16:24Z – codex:gpt-5.4:python-implementer:implementer – shell_pid=53183 – Started implementation via action command
- 2026-04-13T13:21:59Z – codex:gpt-5.4:python-implementer:implementer – shell_pid=53183 – Ready for review: lane branch cleaned to WP01-owned scope
- 2026-04-13T13:36:15Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Started review via action command
- 2026-04-13T13:36:31Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Review passed: isolated lane diff and focused status transition checks green
