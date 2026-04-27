---
work_package_id: WP06
title: FR-008 + FR-009 diagnostic dedup + atexit success-flag
dependencies: []
requirement_refs:
- FR-008
- FR-009
- NFR-004
- NFR-005
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
agent: claude
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/diagnostics/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- src/specify_cli/diagnostics/**
- src/specify_cli/sync/background.py
- src/specify_cli/sync/runtime.py
- src/specify_cli/auth/**
- src/specify_cli/cli/commands/agent/mission/**
- tests/sync/test_diagnostic_dedup.py
- tests/e2e/test_mission_create_clean_output.py
role: implementer
tags:
- diagnostics
- output-discipline
---

# WP06 — FR-008 + FR-009 diagnostic dedup + atexit success-flag

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, and self-review checklist. The bug-fixing-checklist tactic guides you to write the failing e2e test (T032) before silencing any handler.

## Objective

Two cooperating fixes that together stop the post-success "shutdown noise" and triple-printed token-refresh diagnostics from polluting CLI output:

1. **FR-009 (in-process dedup)**: Each distinct diagnostic cause prints at most once per CLI invocation. Backed by a `contextvars.ContextVar`.
2. **FR-008 (atexit success-flag)**: When a JSON-emitting command (e.g. `agent mission create`) succeeds, the success path sets a process-state flag. The atexit handlers in `sync/background.py` and `sync/runtime.py` consult that flag and downgrade or skip their warnings on success — preserving full diagnostic value on failure paths.

Live evidence (already captured in [spec.md](../spec.md)): one `agent mission create` invocation printed `Not authenticated, skipping sync` four times. After this WP merges, that count must drop to ≤ 1.

## Context

From [research.md R7](../research.md#r7--diagnostic-noise-post-success-errors-and-dedup-fr-008--fr-009--735--717):

- "Not authenticated, skipping sync" originates at `src/specify_cli/sync/background.py:270` (`_perform_full_sync`) and `:325` (`_sync_once`). Both can fire per command via different paths.
- "Token refresh failed" originates somewhere in `src/specify_cli/auth/` (locate during T028).
- Post-success red lines originate from `atexit`-registered handlers: `BackgroundSyncService.stop` (`sync/background.py:456`) and `SyncRuntime.stop` (`sync/runtime.py:381`). They run AFTER the JSON payload is written.

Smallest-blast-radius approach: a new `src/specify_cli/diagnostics/` package owning the dedup ContextVar and the success flag.

See [contracts/mission_create_clean_output.contract.md](../contracts/mission_create_clean_output.contract.md) for the testable invariant.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T026 — Create the `src/specify_cli/diagnostics/` package

**Purpose**: A single home for in-process dedup + success-flag state. New module, no existing callers to disturb.

**Files**:
- `src/specify_cli/diagnostics/__init__.py` (new — public re-exports)
- `src/specify_cli/diagnostics/dedup.py` (new — implementation)

**Steps**:

1. Create `src/specify_cli/diagnostics/dedup.py`:

   ```python
   """In-process diagnostic dedup + atexit success-flag.

   Why this module exists
   ----------------------
   The CLI prints noisy diagnostics from multiple cooperating subsystems
   (sync, auth, atexit shutdown handlers). Without coordination they:

   - Repeat the same warning N times within one CLI invocation (#717).
   - Print red shutdown errors AFTER a successful JSON payload (#735).

   This module is the smallest-blast-radius coordination point.
   """

   from __future__ import annotations

   import contextvars
   import threading
   from typing import Final

   _REPORTED: Final[contextvars.ContextVar[frozenset[str]]] = contextvars.ContextVar(
       "spec_kitty_diagnostics_reported",
       default=frozenset(),
   )

   _SUCCESS_FLAG_LOCK: Final = threading.Lock()
   _SUCCESS_FLAG: list[bool] = [False]


   def report_once(cause_key: str) -> bool:
       """Return True iff `cause_key` has not been reported in this invocation.

       Safe under asyncio (ContextVar). Caller pattern:

           if report_once("sync.unauthenticated"):
               logger.warning("Not authenticated, skipping sync")
       """
       reported = _REPORTED.get()
       if cause_key in reported:
           return False
       _REPORTED.set(reported | {cause_key})
       return True


   def reset_for_invocation() -> None:
       """Reset both dedup state and success flag.

       Production code should NOT call this. Tests call it from a fixture so
       state does not leak between test runs.
       """
       _REPORTED.set(frozenset())
       with _SUCCESS_FLAG_LOCK:
           _SUCCESS_FLAG[0] = False


   def mark_invocation_succeeded() -> None:
       """Called by JSON-payload-emitting commands AFTER their final write.

       Atexit handlers consult `invocation_succeeded()` to decide whether to
       log shutdown warnings (when False) or skip them (when True).
       """
       with _SUCCESS_FLAG_LOCK:
           _SUCCESS_FLAG[0] = True


   def invocation_succeeded() -> bool:
       """Read by atexit handlers to gate their warning output."""
       with _SUCCESS_FLAG_LOCK:
           return _SUCCESS_FLAG[0]
   ```

2. Create `src/specify_cli/diagnostics/__init__.py`:

   ```python
   """Public diagnostics surface."""

   from specify_cli.diagnostics.dedup import (
       invocation_succeeded,
       mark_invocation_succeeded,
       report_once,
       reset_for_invocation,
   )

   __all__ = [
       "invocation_succeeded",
       "mark_invocation_succeeded",
       "report_once",
       "reset_for_invocation",
   ]
   ```

3. Run `mypy --strict src/specify_cli/diagnostics/` — expect zero errors.

**Validation**:
- [ ] Both files exist; `from specify_cli.diagnostics import report_once, mark_invocation_succeeded` works at the Python REPL.
- [ ] `mypy --strict src/specify_cli/diagnostics/` exits 0.

### T027 — Wrap "Not authenticated, skipping sync" callsites

**Purpose**: Stop the literal repetition.

**Files**:
- `src/specify_cli/sync/background.py`

**Steps**:

1. Open `src/specify_cli/sync/background.py`. Locate the warning at line 270 (inside `_perform_full_sync`) and at line 325 (inside `_sync_once`).
2. Wrap each with `report_once`:

   ```python
   from specify_cli.diagnostics import report_once

   ...

   if report_once("sync.unauthenticated"):
       logger.warning("Not authenticated, skipping sync")
   ```

3. Do NOT remove the warning entirely — the FIRST call per invocation still emits it.

**Validation**:
- [ ] `grep -n "Not authenticated, skipping sync" src/specify_cli/sync/background.py` shows two occurrences, both inside `if report_once(...)` blocks.

### T028 — Locate and gate the token-refresh failure logger

**Purpose**: Same dedup treatment for the token-refresh diagnostic.

**Files**:
- `src/specify_cli/auth/<file>.py` (locate during the WP)

**Steps**:

1. `grep -rn -i "token refresh" src/specify_cli/auth/` to find the warning callsite. Likely candidates: `src/specify_cli/auth/tokens.py`, `src/specify_cli/auth/refresh.py`, or similar.
2. Wrap with `report_once("auth.token_refresh_failed")`:

   ```python
   from specify_cli.diagnostics import report_once

   ...

   if report_once("auth.token_refresh_failed"):
       logger.warning("Token refresh failed: %s", cause)
   ```

3. If multiple distinct token-refresh warnings exist (e.g. one for "expired token", one for "missing refresh token"), mint a distinct cause_key for each.

**Validation**:
- [ ] All token-refresh warnings in `src/specify_cli/auth/` are wrapped in `report_once(...)` with stable cause keys.

### T029 — Call `mark_invocation_succeeded()` from `agent mission create` success path ONLY

**Purpose**: Tell the atexit layer "this invocation succeeded" for the one command the contract names. No other command paths are widened in this WP.

**Files**:
- `src/specify_cli/cli/commands/agent/mission/create.py` (or wherever the `agent mission create` JSON write lives — locate during the WP)

**Steps**:

1. Locate the final `print(json.dumps(payload))` (or `console.print_json(...)`) inside the `agent mission create` success path.
2. Add immediately AFTER it:

   ```python
   from specify_cli.diagnostics import mark_invocation_succeeded

   ...

   print(json.dumps(payload))  # existing line
   mark_invocation_succeeded()  # new line — see FR-008 / [contracts/mission_create_clean_output.contract.md]
   ```

3. **Do NOT** widen the success-flag pattern to other JSON-emitting agent commands in this WP. The contract
   ([`contracts/mission_create_clean_output.contract.md`](../contracts/mission_create_clean_output.contract.md))
   only requires clean output for `agent mission create`. Auditing other
   JSON-emitting commands (`branch-context`, `setup-plan`,
   `check-prerequisites`, etc.) for the same pattern is **out of scope** —
   if their atexit noise becomes a problem, file a new issue and address
   in a follow-on tranche with proper failure-path tests for each new
   call site.

**Validation**:
- [ ] Exactly one call to `mark_invocation_succeeded()` exists, inside the `agent mission create` success path.
- [ ] The call appears AFTER the JSON write, never on a failure path (not inside a `raise` handler, not after `sys.exit(1)`).
- [ ] `grep -rn "mark_invocation_succeeded" src/specify_cli/cli/commands/` returns exactly one line.

### T030 — Update atexit handlers to consult `invocation_succeeded()`

**Purpose**: Stop the post-success red shutdown noise.

**Files**:
- `src/specify_cli/sync/background.py` (around line 456, `BackgroundSyncService.stop`)
- `src/specify_cli/sync/runtime.py` (around line 381, `SyncRuntime.stop`)

**Steps**:

1. In `BackgroundSyncService.stop`:

   ```python
   from specify_cli.diagnostics import invocation_succeeded

   def stop(self) -> None:
       ...
       if not invocation_succeeded():
           # Failure-path shutdown: keep warnings as-is (debug operators want them).
           logger.warning("Could not acquire sync lock during shutdown")
           ...
       else:
           # Success-path shutdown: downgrade to debug to keep stdout clean.
           logger.debug("Skipped shutdown lock acquire after successful invocation")
   ```

2. Same pattern in `SyncRuntime.stop`. Downgrade or skip any `logger.warning` that runs after a successful invocation.
3. Do NOT remove the warnings entirely. On failure (e.g. user hit Ctrl-C, command raised), the warnings remain useful.

**Validation**:
- [ ] Manual smoke: run `spec-kitty agent mission create demo --json ...` against a tmp project; confirm zero red lines after the JSON payload.
- [ ] Manual smoke: artificially fail the command (e.g. invalid arg); confirm warnings still appear.

### T031 — Add `tests/sync/test_diagnostic_dedup.py`

**Purpose**: Cover the ContextVar gate and reset behavior in isolation.

**Files**:
- `tests/sync/test_diagnostic_dedup.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import logging

   import pytest

   from specify_cli.diagnostics import (
       invocation_succeeded,
       mark_invocation_succeeded,
       report_once,
       reset_for_invocation,
   )


   @pytest.fixture(autouse=True)
   def _isolate_diagnostic_state() -> None:
       reset_for_invocation()
       yield
       reset_for_invocation()


   def test_report_once_returns_true_first_time_then_false() -> None:
       assert report_once("test.cause") is True
       assert report_once("test.cause") is False
       assert report_once("test.cause") is False


   def test_report_once_distinct_keys_independent() -> None:
       assert report_once("test.cause.a") is True
       assert report_once("test.cause.b") is True
       assert report_once("test.cause.a") is False
       assert report_once("test.cause.b") is False


   def test_reset_for_invocation_clears_dedup_state() -> None:
       assert report_once("test.cause") is True
       reset_for_invocation()
       assert report_once("test.cause") is True


   def test_invocation_success_flag_lifecycle() -> None:
       assert invocation_succeeded() is False
       mark_invocation_succeeded()
       assert invocation_succeeded() is True
       reset_for_invocation()
       assert invocation_succeeded() is False
   ```

2. Verify both pass.

**Validation**:
- [ ] `pytest tests/sync/test_diagnostic_dedup.py -q` exits 0.

### T032 — Add `tests/e2e/test_mission_create_clean_output.py`

**Purpose**: End-to-end contract enforcement for FR-008 + FR-009.

**Files**:
- `tests/e2e/test_mission_create_clean_output.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import json
   import re
   import subprocess
   from pathlib import Path

   import pytest


   ANSI_RED_RE = re.compile(r"\x1b\[(?:1;)?31m|\[red\]|\[bold red\]", re.IGNORECASE)
   NOT_AUTH_RE = re.compile(r"Not authenticated, skipping sync")


   def test_mission_create_json_ends_cleanly_no_repeats(tmp_path: Path) -> None:
       project = tmp_path / "demo"

       # Init
       subprocess.run(
           ["spec-kitty", "init", "demo", "--no-confirm"],
           cwd=tmp_path, check=True, capture_output=True, text=True,
       )

       # Create mission
       create_result = subprocess.run(
           [
               "spec-kitty", "agent", "mission", "create",
               "demo-feature",
               "--friendly-name", "Demo Feature",
               "--purpose-tldr", "Smoke test for FR-008 / FR-009",
               "--purpose-context", "Verifies clean JSON output and dedup invariant.",
               "--json",
           ],
           cwd=project, check=True, capture_output=True, text=True,
       )

       stdout = create_result.stdout
       stderr = create_result.stderr

       # Stdout closes cleanly with the JSON payload's }
       last_line = stdout.rstrip().splitlines()[-1]
       assert last_line == "}", (
           f"Expected stdout to end with closing JSON brace, got {last_line!r}"
       )

       # JSON parses
       # find the JSON object in stdout (it may be preceded by other lines from other paths)
       payload_start = stdout.index("{")
       payload = json.loads(stdout[payload_start:])
       assert payload["result"] == "success"

       # FR-009: at most one "Not authenticated" per invocation
       not_auth_count = len(NOT_AUTH_RE.findall(stdout)) + len(NOT_AUTH_RE.findall(stderr))
       assert not_auth_count <= 1, (
           f"Expected ≤1 'Not authenticated' diagnostic; got {not_auth_count}.\n"
           f"stdout:\n{stdout}\nstderr:\n{stderr}"
       )

       # FR-008: no red styling in stderr (success path)
       assert not ANSI_RED_RE.search(stderr), (
           f"Found red styling on stderr after successful JSON payload:\n{stderr}"
       )
   ```

2. Run; expect green after T026–T030 land.

**Validation**:
- [ ] `pytest tests/e2e/test_mission_create_clean_output.py -q` exits 0.

**Edge Cases / Risks**:
- The "Not authenticated" warning may appear in stdout OR stderr depending on logger configuration. Test asserts the SUM is ≤ 1.
- If `spec-kitty init` requires arguments other than `--no-confirm`, adapt the subprocess call.

## Test Strategy

- **Unit** (T031): exercises the dedup gate and success flag in isolation. No CLI involvement.
- **E2E** (T032): drives the actual CLI through subprocess. Asserts the operator-visible contract.

Both tests fail without T026–T030; both pass after.

## Definition of Done

- [ ] T026–T032 complete.
- [ ] `pytest tests/sync/test_diagnostic_dedup.py tests/e2e/test_mission_create_clean_output.py -q` exits 0.
- [ ] `mypy --strict src/specify_cli/diagnostics/` exits 0.
- [ ] Manual smoke: `spec-kitty agent mission create ...` produces ONE JSON payload, ZERO red lines after, ≤ 1 "Not authenticated" message.
- [ ] PR description includes:
  - One-line CHANGELOG entries for **WP02** to consolidate. Suggested:
    - `Suppress misleading "shutdown / final-sync" red error lines after a successful \`spec-kitty agent mission create --json\` payload (#735).`
    - `Deduplicate "Not authenticated, skipping sync" / "token refresh failed" diagnostics to at most once per CLI invocation (#717).`

## Risks

- **R1**: `mark_invocation_succeeded()` accidentally fires on a failure path. T032 covers the success path; add a complementary failure-path test if the implementer wants belt+suspenders.
- **R2**: A future `agent ...` command not audited in T029 will still print red atexit noise. Mitigation: doc-comment the contract in `dedup.py` so future authors know to call `mark_invocation_succeeded()` from new JSON-emitting commands.
- **R3**: The dedup ContextVar persists across asyncio tasks within one CLI invocation, which is intentional. If a future async refactor splits one user-facing invocation into multiple ContextVar contexts, dedup may regress. Out of scope for this WP.

## Reviewer Guidance

- Verify `report_once` callers all use stable cause keys (snake-case dot-separated, e.g. `sync.unauthenticated`).
- Verify `mark_invocation_succeeded()` calls are placed AFTER the JSON write and only on success paths.
- Verify atexit handlers DO NOT swallow warnings on failure paths.
- Verify the diagnostics module has zero dependencies outside the stdlib.
- Verify the new module has a clear "Why this module exists" docstring.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent claude
```
