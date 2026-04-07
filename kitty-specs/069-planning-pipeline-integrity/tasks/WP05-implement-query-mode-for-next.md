---
work_package_id: WP05
title: Implement query mode for spec-kitty next
dependencies: []
requirement_refs:
- C-005
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T027, T028, T029, T030, T031, T032, T033, T034]
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/decision.py
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/next/test_query_mode_unit.py
---

# WP05: Implement Query Mode for spec-kitty next

## Objective

Change `spec-kitty next` so that a bare call (no `--result`) returns the current mission step without advancing the state machine. Output begins with `[QUERY — no result provided, state not advanced]` verbatim (SC-003). `--result success/failed/blocked` retains its current advancing behavior exactly.

**Success criterion**: Before calling `spec-kitty next`, record the current step from the run snapshot. After calling `spec-kitty next` without `--result`, the step is unchanged. The first line of stdout is `[QUERY — no result provided, state not advanced]`.

## Context

`src/specify_cli/cli/commands/next_cmd.py` line 25 currently defaults `result = "success"`. Every bare invocation silently advances the state machine. During mission 068, an agent ghost-completed 6 planning steps in seconds.

The fix:
1. Change `result: str = "success"` → `result: str | None = None`
2. Add a query-mode branch: if `result is None`, call a new read-only function and return
3. Add `query_current_state()` to `runtime_bridge.py` that reads run state without calling `next_step()`
4. Fix `_print_human()` to print the SC-003 verbatim label as the first line when `is_query=True`

The change does NOT touch `spec-kitty-runtime` (external package). All query logic is in the CLI layer.

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (Lane A worktree — independent)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP05`

---

## Subtask T027: Add `DecisionKind.query` and `Decision.is_query`

**Purpose**: Extend the Decision contract to support query mode.

**File**: `src/specify_cli/next/decision.py`

**Changes**:

1. Add `query = "query"` to `DecisionKind`:
   ```python
   class DecisionKind:
       step = "step"
       decision_required = "decision_required"
       blocked = "blocked"
       terminal = "terminal"
       query = "query"   # New: bare next call; state not advanced
   ```

2. Add `is_query: bool = False` field to `Decision` dataclass (after `run_id`):
   ```python
   @dataclass
   class Decision:
       ...
       run_id: str | None = None
       step_id: str | None = None
       decision_id: str | None = None
       question: str | None = None
       options: list[str] = field(default_factory=list)
       is_query: bool = False   # New: True when kind == DecisionKind.query
   ```

3. Update `to_dict()` (if it exists) to include `"is_query": self.is_query`.

**Validation**:
- [ ] `Decision(kind=DecisionKind.query, ..., is_query=True).to_dict()` includes `"is_query": True`
- [ ] Existing `DecisionKind.step` usage is unchanged

---

## Subtask T028: Implement `query_current_state()` in `runtime_bridge.py`

**Purpose**: Read the current run state without advancing the DAG. Returns a `Decision` with `kind=DecisionKind.query`.

**File**: `src/specify_cli/next/runtime_bridge.py`

Add function after the existing `decide_next_via_runtime()` definition:

```python
def query_current_state(
    agent: str,
    mission_slug: str,
    repo_root: Path,
) -> Decision:
    """Return current mission state without advancing the DAG.

    Reads the run snapshot idempotently. Does NOT call next_step().
    Returns a Decision with kind=DecisionKind.query and is_query=True.

    Args:
        agent: Agent name (for Decision construction only).
        mission_slug: Mission slug (e.g. '069-planning-pipeline-integrity').
        repo_root: Repository root path.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    now = datetime.now(timezone.utc).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason=None,
        )

    mission_type = get_mission_type(feature_dir)
    progress = _compute_wp_progress(feature_dir)

    try:
        run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    except Exception as exc:
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason=None,
            progress=progress,
        )

    # Read current step WITHOUT calling next_step()
    current_step_id = "unknown"
    try:
        from spec_kitty_runtime.engine import _read_snapshot  # private API — see note
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        current_step_id = snapshot.issued_step_id or "unknown"
    except Exception:
        pass  # Unknown step is safe — query mode still returns useful output

    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=current_step_id,
        timestamp=now,
        is_query=True,
        reason=None,   # label printed by _print_human(); not in reason field
        progress=progress,
        run_id=getattr(run_ref, "run_id", None),
    )
```

**Note on `_read_snapshot`**: This is a private function in `spec_kitty_runtime.engine`. It is already used by `decide_next_via_runtime()` at line ~478. If it is removed or renamed in a future runtime update, `query_current_state()` will degrade gracefully (catches the exception and returns `mission_state="unknown"`) rather than crashing.

---

## Subtask T029: Change `result` default to `None` in `next_cmd.py`

**Purpose**: Make the bare `spec-kitty next` invocation trigger query mode.

**File**: `src/specify_cli/cli/commands/next_cmd.py`

**Changes**:

1. Change the `result` parameter signature (~line 25):
   ```python
   # Before:
   result: Annotated[
       str, typer.Option("--result", help="Result of previous step: success|failed|blocked")
   ] = "success",

   # After:
   result: Annotated[
       str | None,
       typer.Option(
           "--result",
           help=(
               "Result of previous step: success|failed|blocked. "
               "If omitted, returns current state without advancing (query mode)."
           ),
       ),
   ] = None,
   ```

2. Add query mode branch immediately after `mission_slug` resolution (before the `--result` validation block):
   ```python
   # Query mode: bare call without --result
   if result is None:
       from specify_cli.next.runtime_bridge import query_current_state
       decision = query_current_state(agent, mission_slug, repo_root)
       if json_output:
           d = decision.to_dict()
           if answered_id is not None:
               d["answered"] = answered_id
               d["answer"] = answer
           print(json.dumps(d, indent=2))
       else:
           if answered_id is not None:
               print(f"  Answered decision: {answered_id}")
           _print_human(decision)
       return   # No event emitted, no DAG advancement

   # --result validation (only reached when result is not None)
   if result not in _VALID_RESULTS:
       print(f"Error: --result must be one of {_VALID_RESULTS}, got '{result}'", file=sys.stderr)
       raise typer.Exit(1)
   ```

3. The rest of `next_step()` function body is **unchanged** — it only executes when `result` is not None.

**Type annotation**: Update `Optional[str]` imports at the top if needed (`from typing import Annotated` is already there).

---

## Subtask T030: Add `is_query` branch to `_print_human()`

**Purpose**: SC-003 requires the output to **begin with** `[QUERY — no result provided, state not advanced]` verbatim. The existing `_print_human()` would print `[QUERY]` (from `kind.upper()`) followed later by the step info. This does not satisfy SC-003.

**File**: `src/specify_cli/cli/commands/next_cmd.py`

**Change** — add `is_query` check at the very top of `_print_human()`:

```python
def _print_human(decision) -> None:
    """Print a human-readable summary."""

    # SC-003: query mode output must begin with the full verbatim label
    if getattr(decision, "is_query", False):
        print("[QUERY — no result provided, state not advanced]")
        print(f"  Mission: {decision.mission} @ {decision.mission_state}")
        if decision.progress:
            p = decision.progress
            total = p.get("total_wps", 0)
            done = p.get("done_wps", 0)
            if total > 0:
                pct = int(p.get("weighted_percentage", 0))
                print(f"  Progress: {pct}% ({done}/{total} done)")
        if decision.run_id:
            print(f"  Run ID: {decision.run_id}")
        return

    # --- Standard (non-query) output — unchanged below this line ---
    kind = decision.kind.upper()
    print(f"[{kind}] {decision.mission} @ {decision.mission_state}")
    # ... rest of existing _print_human() body unchanged ...
```

**Key requirement**: The very first character of stdout must be `[` and the first line must be exactly `[QUERY — no result provided, state not advanced]` — the em dash (—) is a Unicode character (U+2014), not two hyphens. Copy it verbatim from this document.

---

## Subtask T031: Unit test — bare call does not advance

**File**: `tests/next/test_query_mode_unit.py` (new)

```python
"""Unit tests for spec-kitty next query mode (FR-012, FR-013)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.next_cmd import next_step

pytestmark = pytest.mark.fast
runner = CliRunner()


def _make_mock_decision(is_query: bool = False, mission_state: str = "specify"):
    from specify_cli.next.decision import Decision, DecisionKind
    return Decision(
        kind=DecisionKind.query if is_query else DecisionKind.step,
        agent="claude",
        mission_slug="069-test",
        mission="069-test",
        mission_state=mission_state,
        timestamp="2026-04-07T00:00:00+00:00",
        is_query=is_query,
    )


class TestQueryModeDoesNotAdvance:
    def test_bare_call_invokes_query_not_decide(self, tmp_path: Path) -> None:
        """When --result is omitted, query_current_state() is called, not decide_next()."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.cli.commands.next_cmd.query_current_state",
                   return_value=mock_decision) as mock_query, \
             patch("specify_cli.cli.commands.next_cmd.decide_next") as mock_decide:

            result = runner.invoke(next_step, ["--agent", "claude", "--json"])

        mock_query.assert_called_once()
        mock_decide.assert_not_called()
```

---

## Subtask T032: Unit test — query output begins with verbatim label

**File**: `tests/next/test_query_mode_unit.py`

```python
class TestQueryModeOutput:
    def test_human_output_begins_with_query_label(self, tmp_path: Path) -> None:
        """SC-003: first line of stdout is the verbatim query label."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.cli.commands.next_cmd.query_current_state",
                   return_value=mock_decision):

            result = runner.invoke(next_step, ["--agent", "claude"])

        lines = result.output.strip().split("\n")
        assert lines[0] == "[QUERY \u2014 no result provided, state not advanced]"

    def test_json_output_includes_is_query_true(self, tmp_path: Path) -> None:
        """JSON output includes is_query: true."""
        import json
        mock_decision = _make_mock_decision(is_query=True)

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.cli.commands.next_cmd.query_current_state",
                   return_value=mock_decision):

            result = runner.invoke(next_step, ["--agent", "claude", "--json"])

        data = json.loads(result.output)
        assert data.get("is_query") is True
```

---

## Subtask T033: Unit test — `--result success` still advances

**File**: `tests/next/test_next_command_integration.py` (extend existing) or `tests/next/test_query_mode_unit.py`

```python
class TestResultSuccessStillAdvances:
    def test_result_success_calls_decide_not_query(self, tmp_path: Path) -> None:
        """C-005: --result success retains its advancing behavior."""
        from specify_cli.next.decision import Decision, DecisionKind
        mock_decision = Decision(
            kind=DecisionKind.step, agent="claude", mission_slug="069-test",
            mission="069-test", mission_state="plan", timestamp="2026-04-07T00:00:00+00:00",
        )

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.cli.commands.next_cmd.decide_next",
                   return_value=mock_decision) as mock_decide, \
             patch("specify_cli.cli.commands.next_cmd.query_current_state") as mock_query, \
             patch("specify_cli.mission_v1.events.emit_event"):

            result = runner.invoke(next_step, ["--agent", "claude", "--result", "success", "--json"])

        mock_decide.assert_called_once()
        mock_query.assert_not_called()
```

---

## Subtask T034: Unit test — JSON output `is_query: true`

Covered in T032. Add one additional check in the query mode JSON test verifying the `kind` field is `"query"`:

```python
    def test_json_kind_is_query(self, tmp_path: Path) -> None:
        import json
        mock_decision = _make_mock_decision(is_query=True)
        with patch(...):
            result = runner.invoke(next_step, ["--agent", "claude", "--json"])
        data = json.loads(result.output)
        assert data.get("kind") == "query"
        assert data.get("is_query") is True
```

---

## Definition of Done

- [ ] `DecisionKind.query = "query"` exists in `decision.py`
- [ ] `Decision.is_query: bool = False` field exists and is included in `to_dict()`
- [ ] `query_current_state()` exists in `runtime_bridge.py` and does not call `next_step()`
- [ ] `result` default is `None` in `next_cmd.py`
- [ ] `_print_human()` has an `is_query` branch that prints the verbatim SC-003 label as line 1
- [ ] T031–T034 tests pass
- [ ] `spec-kitty next --result success` behavior is identical to before (T033 passes)
- [ ] `mypy --strict` passes on all three modified files

## Reviewer Guidance

- Confirm the em dash in `[QUERY — no result provided, state not advanced]` is U+2014 (em dash), not two hyphens or en dash. Copy from this document.
- Confirm `query_current_state()` does not emit a `MissionNextInvoked` event (the event emit block in `next_cmd.py` must not be reached in query mode — it is after the `return` statement).
- Confirm `--answer` flows still work (T029's query branch correctly forwards `answered_id`).
