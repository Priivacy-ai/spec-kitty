# Data Model: 3.2.0 Release Blocker Cleanup

**Mission**: `stable-320-release-blocker-cleanup-01KQW4DF`
**Phase**: 1 — Design
**Date**: 2026-05-05

---

## Overview

This mission introduces three new data structures and refines one existing CLI
output shape. No database or persistent storage changes are made. All new types
are purely in-memory within a single command invocation or written to stderr.

---

## 1. SyncDiagnosticCode (Blocker 1)

**Module**: `src/specify_cli/sync/diagnostics.py` (new)

```python
import enum

class SyncDiagnosticCode(str, enum.Enum):
    """Stable string codes for final-sync failure classification.

    These codes appear in stderr diagnostics and in test assertions.
    Do not rename existing members without a deprecation cycle.
    """
    LOCK_UNAVAILABLE       = "sync.final_sync_lock_unavailable"
    AUTH_REFRESH_IN_PROGRESS = "sync.auth_refresh_in_progress"
    WEBSOCKET_OFFLINE      = "sync.websocket_offline"
    EVENT_LOOP_UNAVAILABLE = "sync.event_loop_unavailable"
    SERVER_AUTH_FAILURE    = "sync.server_auth_failure"
```

**SyncDiagnostic message format** (stderr, one line per invocation):

```
sync_diagnostic severity=warning diagnostic_code=<code> fatal=false \
  sync_phase=final_sync message=<human message>
```

This mirrors the format already observed in smoke evidence for
`sync.final_sync_lock_unavailable`. All five codes use the same format.

**Deduplication state**:

```python
_emitted_codes: set[SyncDiagnosticCode] = set()  # module-level, per-process

def emit_sync_diagnostic(code: SyncDiagnosticCode, message: str) -> None:
    """Emit at most one diagnostic per code per process invocation to stderr."""
    if code in _emitted_codes:
        return
    _emitted_codes.add(code)
    sys.stderr.write(
        f"sync_diagnostic severity=warning diagnostic_code={code.value} "
        f"fatal=false sync_phase=final_sync message={message}\n"
    )
```

**Invariant**: `emit_sync_diagnostic()` is the only function in the codebase
that writes final-sync failure diagnostics to stderr. All call sites in
`daemon.py` and `batch.py` that currently emit such text must be replaced
with calls to this function.

---

## 2. TaskIdResult / TaskIdResolutionOutcome (Blocker 2)

**Module**: `src/specify_cli/cli/commands/agent/tasks.py` (extended)

```python
import enum
from dataclasses import dataclass

class TaskIdResolutionOutcome(str, enum.Enum):
    """Per-ID result for mark-status resolution strategies."""
    UPDATED           = "updated"            # checkbox/event log mutated
    ALREADY_SATISFIED = "already_satisfied"  # target state already held
    NOT_FOUND         = "not_found"          # ID absent from all formats

class TaskIdResolutionFormat(str, enum.Enum):
    """Which resolution strategy matched the task ID."""
    CHECKBOX       = "checkbox"        # - [ ] T001 row
    PIPE_TABLE     = "pipe_table"      # | T001 | ... | row
    INLINE_SUBTASKS = "inline_subtasks" # Subtasks: T001, T002
    WP_ID          = "wp_id"           # bare WP02 → event log

@dataclass
class TaskIdResult:
    id: str
    outcome: TaskIdResolutionOutcome
    format: TaskIdResolutionFormat | None  # None when not_found
    message: str                           # human-readable explanation
```

**Resolution strategy stack** (first match wins):

```
1. Checkbox row       → TaskIdResolutionFormat.CHECKBOX
2. Pipe-table row     → TaskIdResolutionFormat.PIPE_TABLE
3. Inline Subtasks:   → TaskIdResolutionFormat.INLINE_SUBTASKS
4. WP ID (event log)  → TaskIdResolutionFormat.WP_ID
5. No match           → outcome=NOT_FOUND, format=None
```

**Invariant**: Strategies 1–3 may mutate task artifact files. Strategy 4
(WP ID) delegates to `emit_status_transition()` and never mutates artifact
files. The stack order preserves backwards compatibility: existing checkbox
and pipe-table tests are unaffected because those strategies execute first.

---

## 3. NestedEnvResult (Blocker 3)

**Module**: `spec-kitty-end-to-end-testing/support/nested_env.py` (new)

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class NestedEnvResult:
    venv_dir: Path
    python: Path    # absolute path to the venv interpreter
    pip: Path       # absolute path to the venv pip
    method: str     # "uv_venv" | "stdlib_venv"
```

**Invariant**: `create_nested_env()` either returns a fully-initialized
`NestedEnvResult` or raises `pytest.skip.Exception` with a structured reason.
It never raises an unhandled `EnsurepipDisabled`, `OSError`, or
`subprocess.CalledProcessError` to the test body.

---

## 4. MergeDryRunBlockerPayload (Blocker 4)

This is a JSON output shape, not a Python dataclass. It is emitted to stdout
when `merge --dry-run --json` detects a missing mission branch.

**Schema** (see `contracts/merge-dry-run-blocker.schema.json` for the full JSON
Schema):

```json
{
  "ready": false,
  "blocker": "missing_mission_branch",
  "expected_branch": "kitty/mission-<mission-slug>",
  "remediation": "git branch kitty/mission-<mission-slug> <base-commit-sha>"
}
```

**Field invariants**:

| Field | Type | Invariant |
|-------|------|-----------|
| `ready` | `boolean` | Always `false` when any blocker is present |
| `blocker` | `string` | Stable identifier; `missing_mission_branch` for this blocker |
| `expected_branch` | `string` | Full local branch name (`kitty/mission-<slug>`) |
| `remediation` | `string` | Complete shell command the user can copy-paste; includes base commit SHA from `merge_target_branch` HEAD |

**Composition with other blockers**: If `_check_mission_branch()` returns a
blocker and other preflight checks also fail, the JSON output must include all
blockers in an array form (or the missing-branch blocker must not mask other
blockers). Implementation note: the existing preflight pattern raises on first
failure; the team should decide during implementation whether to accumulate
blockers or halt on first. The requirement (FR — missing-branch does not mask
others) is captured in test case 5 (`test_missing_branch_does_not_mask_other_blockers`).

---

## Existing Types (unchanged)

These types are used by the new code but are not modified:

| Type | Module | Role |
|------|--------|------|
| `StatusEvent` | `src/specify_cli/status/models.py` | Event model consumed by WP ID strategy |
| `Lane` | `src/specify_cli/status/models.py` | Lane enum used in WP ID transition |
| `MergeState` | `src/specify_cli/merge/state.py` | Existing merge state; not changed |
| `PreflightResult` | `src/specify_cli/merge/preflight.py` | Existing preflight result; `_check_mission_branch()` may extend it |
