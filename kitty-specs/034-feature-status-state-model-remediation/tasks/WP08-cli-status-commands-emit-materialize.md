---
work_package_id: "WP08"
title: "CLI Status Commands (emit & materialize)"
phase: "Phase 1 - Canonical Log"
lane: "planned"
dependencies: ["WP07"]
subtasks:
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-08T14:07:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 -- CLI Status Commands (emit & materialize)

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Create the `spec-kitty agent status` CLI command group with `emit` and `materialize` subcommands, providing direct CLI access to the canonical status pipeline.

**Success Criteria**:
1. `spec-kitty agent status emit WP01 --to claimed --actor claude` works end-to-end from CLI.
2. `spec-kitty agent status materialize` rebuilds `status.json` and views from the event log.
3. `--json` flag on both commands produces machine-readable output suitable for scripting.
4. Feature auto-detection works via `detect_feature_slug()` when `--feature` is not provided.
5. The status command group is registered in the agent CLI parent app alongside tasks, feature, workflow.
6. CLI error handling produces user-friendly Rich-formatted output for validation failures.

## Context & Constraints

**Architecture References**:
- `plan.md` AD-6 shows the fan-out pipeline that `status emit` triggers.
- Existing CLI pattern: `src/specify_cli/cli/commands/agent/tasks.py` defines the `tasks` typer app.
- Agent CLI registration: `src/specify_cli/cli/commands/agent/__init__.py` registers sub-apps.
- Feature detection: `src/specify_cli/core/feature_detection.py` provides `detect_feature_slug()`.

**Dependency Artifacts Available** (from completed WPs):
- WP07 provides `emit_status_transition()` from `status/emit.py`.
- WP03 provides `reducer.materialize()` from `status/reducer.py`.

**Constraints**:
- Follow the exact same typer patterns used in `tasks.py` -- same Console usage, same error handling style.
- Use `typer.Option()` for optional flags and `typer.Argument()` for positional arguments.
- Evidence must be passed as a JSON string via `--evidence-json` (CLI cannot accept nested objects directly).
- No interactive prompts. All inputs via flags/arguments.

**Implementation Command**: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### T038: Create CLI Status Module

**Purpose**: Create the typer app for the `status` command group.

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/status.py`.
2. Define the module structure following the `tasks.py` pattern:
   ```python
   """Canonical status management commands for AI agents."""

   from __future__ import annotations

   import json
   import logging
   from pathlib import Path
   from typing import Optional

   import typer
   from rich.console import Console
   from typing_extensions import Annotated

   from specify_cli.core.feature_detection import (
       detect_feature_slug,
       FeatureDetectionError,
   )
   from specify_cli.core.paths import locate_project_root, get_main_repo_root

   logger = logging.getLogger(__name__)

   app = typer.Typer(
       name="status",
       help="Canonical status management commands",
       no_args_is_help=True,
   )

   console = Console()
   ```
3. Keep imports minimal at module level. Import status engine modules inside command functions to avoid circular imports.

**Files**: `src/specify_cli/cli/commands/agent/status.py`

**Validation**: Module imports without error. `app` is a valid typer.Typer instance.

**Edge Cases**:
- Module must not import `status.emit` at module level (could cause circular import with sync).

### T039: `status emit` Command

**Purpose**: Expose the `emit_status_transition()` pipeline as a CLI command.

**Steps**:
1. Define the command in `status.py`:
   ```python
   @app.command()
   def emit(
       wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
       to: Annotated[str, typer.Option("--to", help="Target lane")] = ...,
       actor: Annotated[str, typer.Option("--actor", help="Who is making this transition")] = ...,
       feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
       force: Annotated[bool, typer.Option("--force", help="Force transition bypassing guards")] = False,
       reason: Annotated[Optional[str], typer.Option("--reason", help="Reason for forced transition")] = None,
       evidence_json: Annotated[Optional[str], typer.Option("--evidence-json", help="JSON string with done evidence")] = None,
       review_ref: Annotated[Optional[str], typer.Option("--review-ref", help="Review feedback reference")] = None,
       execution_mode: Annotated[str, typer.Option("--execution-mode", help="Execution mode")] = "worktree",
       json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
   ) -> None:
   ```
2. Implementation body:
   - Resolve `repo_root` via `get_main_repo_root()`.
   - If `feature` is None, call `detect_feature_slug()` to auto-detect.
   - Construct `feature_dir` as `repo_root / "kitty-specs" / feature_slug`.
   - If `evidence_json` is provided, parse it: `evidence = json.loads(evidence_json)`. Handle `json.JSONDecodeError` with a user-friendly error.
   - Import and call `emit_status_transition()` from `specify_cli.status.emit`.
   - On success: print event summary (event_id, from_lane, to_lane, actor) using Rich or JSON.
   - On `TransitionError`: print error with Rich formatting and `raise typer.Exit(1)`.
3. Output format (non-JSON):
   ```
   [green]OK[/green] WP01: planned -> claimed (event: 01HXYZ...)
   ```
4. Output format (JSON):
   ```json
   {"event_id": "01HXYZ...", "wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed", "actor": "claude"}
   ```

**Files**: `src/specify_cli/cli/commands/agent/status.py`

**Validation**:
- Test with valid args: prints success message and exits 0.
- Test with invalid transition: prints error and exits 1.
- Test `--json` output: is valid JSON parseable by `json.loads()`.

**Edge Cases**:
- `--evidence-json` with invalid JSON: clear error message before calling emit.
- Feature auto-detection fails: clear error suggesting `--feature` flag.
- `wp_id` format validation: should match `WP\d{2}` pattern.

### T040: `status materialize` Command

**Purpose**: Rebuild `status.json` and all derived views from the canonical event log.

**Steps**:
1. Define the command:
   ```python
   @app.command()
   def materialize(
       feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
       json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
   ) -> None:
   ```
2. Implementation body:
   - Resolve `repo_root` and `feature_slug` (same pattern as emit).
   - Construct `feature_dir`.
   - Import `reducer.materialize` from `specify_cli.status.reducer`.
   - Call `snapshot = materialize(feature_dir, feature_slug)`.
   - Import `legacy_bridge.update_all_views` from `specify_cli.status.legacy_bridge`.
   - Call `update_all_views(feature_dir, snapshot)`.
   - On success: print snapshot summary (total events, WP count, lane distribution).
3. Output format (non-JSON):
   ```
   [green]Materialized[/green] 034-test-feature: 15 events -> 5 WPs
     planned: 1  in_progress: 2  for_review: 1  done: 1
   ```
4. Output format (JSON): serialize the full snapshot dict.

**Files**: `src/specify_cli/cli/commands/agent/status.py`

**Validation**:
- Test with valid event log: snapshot written and summary printed.
- Test with empty/missing event log: clear error message.
- Test `--json`: full snapshot as JSON.

**Edge Cases**:
- No `status.events.jsonl` exists: error message guiding user to emit first or run migration.
- Corrupted JSONL: error from store propagates with line number.

### T041: Register Status App in Agent CLI

**Purpose**: Wire the status command group into the existing agent CLI hierarchy.

**Steps**:
1. Edit `src/specify_cli/cli/commands/agent/__init__.py`.
2. Add import: `from . import status` (alongside existing imports of config, feature, tasks, etc.).
3. Add registration: `app.add_typer(status.app, name="status")`.
4. The final file should look like:
   ```python
   from . import config, feature, tasks, context, release, workflow, status

   # ... existing registrations ...
   app.add_typer(status.app, name="status")
   ```
5. Verify the command appears in help output: `spec-kitty agent --help` should list `status`.

**Files**: `src/specify_cli/cli/commands/agent/__init__.py`

**Validation**:
- `spec-kitty agent status --help` shows emit and materialize subcommands.
- `spec-kitty agent status emit --help` shows all options.
- Existing commands (tasks, feature, etc.) still work.

**Edge Cases**:
- Name collision: verify no existing subcommand named "status" in agent app.
- Import order: status module imports must not trigger circular dependencies at registration time.

### T042: Integration Tests for CLI Commands

**Purpose**: Verify CLI commands work end-to-end using typer's CliRunner.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_status_cli.py`.
2. Import and configure the test runner:
   ```python
   from typer.testing import CliRunner
   from specify_cli.cli.commands.agent.status import app

   runner = CliRunner()
   ```
3. Test cases:

   **test_emit_valid_transition**:
   - Set up feature directory with a WP file in tmp_path.
   - Invoke: `runner.invoke(app, ["emit", "WP01", "--to", "claimed", "--actor", "test-agent", "--feature", "034-test"])`.
   - Assert exit code 0.
   - Assert output contains "WP01" and "claimed".
   - Verify `status.events.jsonl` exists on disk.

   **test_emit_invalid_transition_exits_1**:
   - Invoke: move planned directly to done without force.
   - Assert exit code 1.
   - Assert output contains error message about illegal transition.

   **test_emit_json_output**:
   - Invoke with `--json` flag.
   - Assert exit code 0.
   - Parse stdout as JSON and verify required fields.

   **test_emit_evidence_json_parsing**:
   - Invoke with `--evidence-json '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}'`.
   - Assert success.

   **test_emit_invalid_evidence_json**:
   - Invoke with `--evidence-json 'not json'`.
   - Assert exit code 1.
   - Assert error about JSON parsing.

   **test_materialize_command**:
   - Pre-populate a `status.events.jsonl` file with valid events.
   - Invoke: `runner.invoke(app, ["materialize", "--feature", "034-test"])`.
   - Assert exit code 0.
   - Verify `status.json` exists.

   **test_materialize_json_output**:
   - Invoke with `--json`.
   - Parse stdout as JSON snapshot.

   **test_materialize_no_events**:
   - Feature dir exists but no JSONL file.
   - Assert appropriate error message.

4. Use monkeypatch or environment setup to make feature detection work with tmp_path.

**Files**: `tests/specify_cli/cli/commands/test_status_cli.py`

**Validation**: All tests pass. CLI command coverage reaches 85%+.

**Edge Cases**:
- Runner captures both stdout and stderr. Verify error messages go to stderr (via Rich console).
- Feature auto-detection in test context: may need to mock `detect_feature_slug()`.

## Test Strategy

**Unit Tests** (in `tests/specify_cli/cli/commands/test_status_cli.py`):
- Use `typer.testing.CliRunner` to invoke commands programmatically.
- Mock the status engine for pure CLI layer tests (argument parsing, output formatting).

**Integration Tests** (also in `test_status_cli.py` or separate `tests/integration/test_status_cli_integration.py`):
- Use real filesystem with tmp_path.
- Verify end-to-end from CLI invocation through to file artifacts.

**Smoke Test**:
- After implementation, manually run:
  ```bash
  spec-kitty agent status --help
  spec-kitty agent status emit --help
  spec-kitty agent status materialize --help
  ```

**Running Tests**:
```bash
python -m pytest tests/specify_cli/cli/commands/test_status_cli.py -x -q
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import at agent/__init__.py registration | CLI fails to start | Use lazy imports inside command functions, not at module level |
| Feature auto-detection fails in worktree context | User must always pass --feature | Reuse existing `detect_feature_slug()` which handles worktrees |
| JSON evidence parsing errors are opaque | User cannot debug evidence format | Catch JSONDecodeError explicitly and print the parsing error with guidance |
| typer CliRunner does not capture Rich output correctly | Test assertions fail on output format | Use `rich_markup=False` in test runner or assert on plain text content |
| Status commands conflict with existing "status" in show_kanban_status | User confusion | Commands are under `agent status`, not top-level; `show_kanban_status` is in agent_utils |

## Review Guidance

When reviewing this WP, verify:
1. **CLI registration**: `spec-kitty agent status --help` works and lists both subcommands.
2. **Argument handling**: All required arguments are validated before calling emit_status_transition.
3. **Error output**: TransitionErrors produce user-friendly messages with exit code 1, not tracebacks.
4. **JSON output**: `--json` flag produces valid JSON that includes all event fields.
5. **Evidence parsing**: `--evidence-json` handles valid JSON, invalid JSON, and missing evidence correctly.
6. **Feature detection**: Both `--feature` explicit and auto-detection paths are tested.
7. **No fallback behavior**: If something fails, it fails loudly with a clear error message.
8. **Pattern consistency**: Compare with `tasks.py` to ensure CLI patterns (Console usage, error handling, option naming) are consistent.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
