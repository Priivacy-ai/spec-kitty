---
work_package_id: WP03
title: '`doctor restart-daemon` subcommand + hint refresh (#1124)'
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-002
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07
base_commit: 45edd287a01e5a00dedf1d7fb7ba38183ede266e
created_at: '2026-05-19T09:58:35.910003+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "62047"
history:
- at: '2026-05-19T08:46:23Z'
  actor: spec-kitty.tasks
  note: Generated initial WP prompt.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctor.py
execution_mode: code_change
mission_slug: unblock-sync-identity-boundary-canary-01KRZJ07
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/sync/preflight.py
- src/specify_cli/sync/restart.py
- tests/specify_cli/cli/commands/test_doctor_restart_daemon.py
- tests/specify_cli/sync/test_preflight_remediation_hints.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

The profile defines your identity, governance scope, and boundaries for this work. Apply it for the entire duration of this work package.

## Pre-flight (charter compliance)

Before opening any code changes:

1. **Assign the tracker ticket to the Human-in-Charge.** This WP traces to GitHub issue [`Priivacy-ai/spec-kitty#1124`](https://github.com/Priivacy-ai/spec-kitty/issues/1124). Per charter rule "HiC assignment for tracker-backed work", assign that issue to the project's HiC before (or as part of) beginning implementation.
2. **If you encounter pre-existing test failures** while running the doctor or sync suites (or any test), per charter you MUST open a GitHub issue first — record the failing command, the failure summary, and your evidence that the failure is pre-existing — before treating it as accepted baseline.
3. **Respect C-004**: do NOT rename any field on `ForegroundIdentity` / `DaemonOwnerRecord`. Read these structures; do not modify the names. That rename is the responsibility of sibling issue `#43`.

## Objective

Implement the `spec-kitty doctor restart-daemon` subcommand so it stops the registered sync daemon and respawns it at the foreground executable/source recorded in the daemon owner record. Refresh all four `_REMEDIATION_HINTS` occurrences in `src/specify_cli/sync/preflight.py` (lines 99, 103, 107, 119) plus the related comment at line 218 so the wording is uniform and every command mentioned in any hint resolves on the installed CLI.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree allocated per lane by `finalize-tasks`. Enter with `spec-kitty agent action implement WP03 --agent <name>`.

## Context

### What the bug is

`src/specify_cli/sync/preflight.py` emits user-facing remediation hints that tell operators to run `spec-kitty doctor restart-daemon`. That subcommand does not exist; the operator hits a dead end. The fix has two parts:
1. Implement the missing subcommand (composing existing daemon stop + launch primitives).
2. Refresh all four hint strings (and the related explanatory comment) in `sync/preflight.py` so wording stays uniform and every referenced command resolves.

Decision `01KRZJ2FTT89B2QMRN55SXN3N6` (resolved: `subcommand_plus_hints`) chose this combined approach. Decision `01KRZKFX0M43WZ3CB7DT2E7YBV` (resolved: `compose_stop_plus_start`) chose composition over a dedicated restart code path.

### Source contract

See [contracts/doctor-restart-daemon.md](../contracts/doctor-restart-daemon.md) for the CLI shape, exit-code table, composition skeleton, and hint-refresh scope.

### Existing primitives to reuse

- Daemon stop primitive used by `spec-kitty sync stop`. Find it under `src/specify_cli/sync/` (likely named `stop_registered_daemon`, `stop_daemon`, or similar).
- Daemon launch primitive used by `spec-kitty sync now`. Find it under `src/specify_cli/sync/` (likely named `launch_daemon_for_foreground`, `start_daemon`, or similar).
- `DaemonOwnerRecord` reader used by `preflight.py`.

**Important**: do not modify these primitives. Compose them.

## Subtasks

### T011 — Implement `restart_daemon` composition primitive

**Purpose**: A single function that drives stop → launch using existing primitives.

**Steps**:
1. Create `src/specify_cli/sync/restart.py` (new module). Define:
   ```python
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Optional

   @dataclass(frozen=True)
   class RestartResult:
       status: str  # "restarted" | "no_owner" | "stop_failed" | "respawn_failed" | "stale_owner_cleaned"
       exit_code: int
       previous_pid: Optional[int]
       new_pid: Optional[int]
       error: Optional[str]

   def restart_daemon(repo_root: Path) -> RestartResult:
       ...
   ```
2. The function reads the owner record (use the existing reader; do not roll your own). If absent, return `RestartResult(status="no_owner", exit_code=1, ...)` with an actionable error mentioning `spec-kitty sync now`.
3. If the owner record exists, call the existing stop primitive. If stop reports the process is already dead, treat as `stale_owner_cleaned` and continue to the launch step. If stop fails for another reason, return `RestartResult(status="stop_failed", exit_code=3, ...)` and leave the owner record intact.
4. Resolve the foreground identity (use the existing helper in `preflight.py` / sibling modules). Call the existing daemon launcher with the foreground binding. If launch fails, return `RestartResult(status="respawn_failed", exit_code=2, ...)`. Owner record state after a respawn failure: per the contract, leave the system in a stopped state and surface the error.
5. On success, return `RestartResult(status="restarted", exit_code=0, previous_pid=..., new_pid=...)`.
6. Type-annotate strictly. No new public state. All side effects flow through existing primitives.

**Files**:
- `src/specify_cli/sync/restart.py` (new; ~90 lines including dataclass + function + docstring)

**Validation**:
- [ ] `from specify_cli.sync.restart import restart_daemon, RestartResult` works.
- [ ] mypy --strict clean.

### T012 — Register `restart-daemon` typer subcommand

**Purpose**: Wire the CLI surface so `spec-kitty doctor restart-daemon` resolves.

**Steps**:
1. Open `src/specify_cli/cli/commands/doctor.py`. Locate the typer app or `@app.command` decorator pattern used by sibling subcommands (`mission-state`, `orphan-daemons`, etc.).
2. Add a thin wrapper:
   ```python
   @app.command("restart-daemon")
   def restart_daemon_cmd(
       json_output: bool = typer.Option(False, "--json", help="Emit a single JSON object instead of human text."),
   ) -> None:
       """Stop the registered sync daemon and respawn it at the foreground executable/source."""
       repo_root = _resolve_repo_root()  # follow existing helper conventions in doctor.py
       result = restart_daemon(repo_root)
       _render_restart_result(result, json_output=json_output)
       raise typer.Exit(code=result.exit_code)
   ```
3. Implement `_render_restart_result` either in `doctor.py` or in `sync/restart.py`. Human form: short status line + `previous_pid` / `new_pid` if present. JSON form: dump the `RestartResult` fields as one object.
4. Ensure the new command is listed under `spec-kitty doctor --help` alongside the existing subcommands.
5. Sanity-check: the names listed under `spec-kitty doctor --help` should now include `restart-daemon`.

**Files**:
- `src/specify_cli/cli/commands/doctor.py` (modify; ~30 added lines)

**Validation**:
- [ ] `spec-kitty doctor restart-daemon --help` exits 0 and shows the command summary.
- [ ] `spec-kitty doctor --help` lists `restart-daemon`.

### T013 — Refresh `_REMEDIATION_HINTS` + the line-218 comment

**Purpose**: Make the four hint strings + their explanatory comment uniformly reference the (now-working) `doctor restart-daemon` subcommand.

**Steps**:
1. Open `src/specify_cli/sync/preflight.py`. Locate `_REMEDIATION_HINTS` and read all four entries (lines 99, 103, 107, 119) + the related comment at line 218.
2. Choose one canonical phrasing for the primary remedy. Suggested template (adapt to the existing tone):
   > "Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground version/source, then verify with `spec-kitty sync status --check`."
3. Replace each of the four hint values with this phrasing (vary only the diagnostic preamble that names which mismatch fired — keep the remedy phrasing identical across all four).
4. Update the line-218 comment so it accurately describes the unified remedy (one or two sentences).
5. Do not introduce additional remedies in this WP; the goal is to make the existing ones correct, not to expand the surface.
6. Keep the dictionary structure intact — no renames of keys.

**Files**:
- `src/specify_cli/sync/preflight.py` (modify; ~20 changed lines around the four hint entries + the comment)

**Validation**:
- [ ] grep `doctor restart-daemon` in `src/specify_cli/sync/preflight.py` returns exactly the expected number of occurrences (four hint entries plus the comment).
- [ ] All four entries use the same remedy phrasing.

### T014 — Regression tests for the subcommand

**Purpose**: Cover the exit-code matrix.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_doctor_restart_daemon.py`.
2. Use `typer.testing.CliRunner` plus monkeypatching of the stop/launch primitives to simulate each scenario from the contract's exit-code matrix:
   - **Happy path**: stop returns OK, launch returns new pid. Assert exit 0 and `new_pid != previous_pid` in JSON output.
   - **No owner record**: monkeypatch the owner-record reader to return None. Assert exit 1 and the error message mentions `spec-kitty sync now`.
   - **Stop fails**: monkeypatch stop primitive to raise / report failure. Assert exit 3 and owner record left intact (no launch attempted).
   - **Respawn fails**: stop OK, launch raises / reports failure. Assert exit 2.
   - **Foreground binding**: simulate owner record bound to stale version while foreground is newer; after restart, owner record's `package_version` matches foreground. (May require a small fixture or fake state.)
3. Use existing `CliRunner` fixture conventions.

**Files**:
- `tests/specify_cli/cli/commands/test_doctor_restart_daemon.py` (new; ~180 lines)

**Validation**:
- [ ] All five tests pass.
- [ ] No actual daemon is spawned during tests (everything goes through fakes / monkeypatches).

### T015 — Hint-coverage test

**Purpose**: Pin "every command in any `_REMEDIATION_HINTS` entry resolves on the installed CLI" in CI.

**Steps**:
1. Create `tests/specify_cli/sync/test_preflight_remediation_hints.py`.
2. Implement two tests:
   - **Hint coverage**: import `_REMEDIATION_HINTS`. For each entry, extract `spec-kitty …` commands (use a simple regex like `r"spec-kitty[\w\- ]+"`). For each command, invoke `<cmd> --help` via `CliRunner` (or subprocess in test mode) and assert exit code 0. If a hint mentions a non-spec-kitty command (`pkill -f …`), document an allowlist explicitly.
   - **Wording uniformity**: assert that all four hint values reference `doctor restart-daemon` in the canonical phrase chosen in T013.
3. The hint-coverage test should fail on rc13 because `doctor restart-daemon` is missing.

**Files**:
- `tests/specify_cli/sync/test_preflight_remediation_hints.py` (new; ~80 lines)

**Validation**:
- [ ] Both tests pass after T012+T013 land.
- [ ] On rc13, hint-coverage test FAILS with "No such command 'restart-daemon'".

### T016 — Manual smoke

**Purpose**: Operator-facing confirmation before merge.

**Steps**:
1. With the installed dev CLI, run `spec-kitty sync now` to start a daemon in a tmp project. Note the pid.
2. Run `spec-kitty doctor restart-daemon`. Confirm exit code 0; note new pid.
3. Confirm via `spec-kitty sync status --check` that the daemon is healthy and `package_version` / `executable_path` match the foreground.
4. Trigger a boundary mismatch (e.g., briefly run a stale binary). Read the rendered remediation hint; confirm `doctor restart-daemon` is named and the command actually runs.
5. Run with no owner record (clean tmp project where `sync now` was never invoked). Confirm exit code 1 and the error message points at `sync now`.

**Files**: none.

**Validation**:
- [ ] All five manual steps produce the expected outcomes.

## Definition of Done

- [ ] All six subtasks complete; each `[ ]` above checked.
- [ ] Spec-side requirements FR-007, FR-008, FR-009, C-004 satisfied.
- [ ] NFR-002 (≤10 s end-to-end on dev machine) confirmed in manual smoke or logged in the PR.
- [ ] No existing daemon-lifecycle tests fail.
- [ ] Charter pre-flight items completed: HiC assignment recorded; any pre-existing test failures (if hit) opened as GitHub issues before continuing.

## Reviewer Guidance

- Read `sync/restart.py` first; confirm it is purely a composition of existing primitives — no signal-sending, no respawn logic of its own.
- Cross-check the four `_REMEDIATION_HINTS` entries: identical remedy phrasing across the four.
- Run `spec-kitty doctor --help`; confirm `restart-daemon` appears.
- Verify the test file uses fakes/monkeypatches and does not actually spawn daemons.
- Confirm no rename of fields on `ForegroundIdentity` / `DaemonOwnerRecord` (Constraint C-004).

## Activity Log

- 2026-05-19T09:58:37Z – claude:opus:python-pedro:implementer – shell_pid=52859 – Assigned agent via action command
- 2026-05-19T10:12:18Z – claude:opus:python-pedro:implementer – shell_pid=52859 – WP03 ready: doctor restart-daemon subcommand + hint refresh; T011-T016 done; 15/15 tests pass; mypy --strict clean on new code
- 2026-05-19T10:13:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=62047 – Started review via action command
- 2026-05-19T10:15:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=62047 – Review passed: restart-daemon subcommand is pure composition of stop_sync_daemon + ensure_sync_daemon_running; exit codes 0/1/2/3 match contract; all four restart-class hints share canonical _RESTART_DAEMON_REMEDY; auth switch fully purged; daemon_team_or_user hint expansion (logout+login+restart-daemon) is a defensible FR-008 side-find; C-004 respected; 15/15 new tests + 76/76 daemon-lifecycle regression tests green.
