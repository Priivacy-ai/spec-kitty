---
work_package_id: WP05
title: CLI Cost Command
lane: "done"
dependencies:
- WP02
- WP04
base_branch: feature/doctrine-kitty-2x
base_commit: a3505ae86accdeb8991e664f58da7942909cc00f
created_at: '2026-02-15T21:16:25.216035+00:00'
subtasks:
- T024
- T025
- T026
- T027
- T028
phase: Phase 3 - User Interface
assignee: ''
agent: copilot
shell_pid: '516747'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T19:43:21Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – CLI Cost Command

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

Depends on WP02 (query layer) and WP04 (cost aggregation). Use `--base WP04`, then merge WP02:

```bash
spec-kitty implement WP05 --base WP04
cd .worktrees/043-telemetry-foundation-WP05/
git merge 043-telemetry-foundation-WP02
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Add `spec-kitty agent telemetry cost` CLI command
- Support `--feature`, `--since`/`--until`, `--group-by`, `--json` flags
- Rich-formatted table output with per-group rows and project total
- JSON output when `--json` flag is provided
- "No execution events found" message for empty projects
- CLI completes in <2 seconds for typical projects
- 90%+ test coverage

## Context & Constraints

- **Spec**: FR-018 through FR-021, User Story 5
- **Plan**: CLI registered under existing `agent` command group
- **Research**: R5 (CLI command structure)
- **Existing pattern**: `src/specify_cli/cli/commands/agent/__init__.py` — register sub-commands via `app.add_typer()`
- **Dependencies**: `query_execution_events()` and `query_project_events()` from WP02, `cost_summary()` from WP04
- **Rich**: Already a project dependency — use `rich.table.Table` and `rich.console.Console`
- **Typer**: CLI framework — use `typer.Typer()`, `@app.command()`, `typer.Option()`

## Subtasks & Detailed Guidance

### Subtask T024 – Create telemetry CLI command module

- **Purpose**: Establish the `spec-kitty agent telemetry` command group with the `cost` sub-command.
- **Steps**:
  1. Create `src/specify_cli/cli/commands/agent/telemetry.py`
  2. Define the Typer app:

     ```python
     import typer

     app = typer.Typer(
         name="telemetry",
         help="Telemetry and cost tracking commands.",
         no_args_is_help=True,
     )
     ```

  3. Add the `cost` command skeleton:

     ```python
     @app.command("cost")
     def cost_cmd(
         feature: str | None = typer.Option(None, "--feature", "-f", help="Filter by feature slug or glob pattern"),
         since: str | None = typer.Option(None, "--since", help="Start date (ISO 8601)"),
         until: str | None = typer.Option(None, "--until", help="End date (ISO 8601)"),
         group_by: str = typer.Option("agent", "--group-by", "-g", help="Group by: agent, model, feature"),
         json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
     ) -> None:
         """Show cost report for AI agent invocations."""
         ...
     ```

- **Files**: `src/specify_cli/cli/commands/agent/telemetry.py` (new, ~30 lines initially)
- **Notes**: Use `str | None` type hints (Python 3.11+). Typer handles optional arguments natively.

### Subtask T025 – Implement CLI flags and query logic

- **Purpose**: Wire CLI flags to the query and cost layers.
- **Steps**:
  1. In `cost_cmd()`, resolve the repo root:

     ```python
     from specify_cli.cli.utils import get_repo_root  # or however repo root is resolved
     repo_root = get_repo_root()
     ```

  2. Build `EventFilter`:

     ```python
     from specify_cli.telemetry.query import EventFilter, query_execution_events, query_project_events
     from datetime import datetime

     filters = EventFilter(
         event_type="ExecutionEvent",
         since=datetime.fromisoformat(since) if since else None,
         until=datetime.fromisoformat(until) if until else None,
     )
     ```

  3. Query events:
     - If `--feature` provided: find matching feature dir, call `query_execution_events(feature_dir, filters)`
     - If no `--feature`: call `query_project_events(repo_root, filters)`
  4. Feature matching: glob `kitty-specs/{feature}*/` to support partial matches
  5. If no events found: print "No execution events found." and return
  6. Call `cost_summary(events, group_by=group_by)`
- **Files**: `src/specify_cli/cli/commands/agent/telemetry.py` (modify, ~40 lines added)
- **Notes**: Check how other CLI commands resolve repo root — likely `Path.cwd()` or a shared utility. For `--feature` glob matching, use `Path.glob()` on the kitty-specs directory.

### Subtask T026 – Add Rich-formatted table output

- **Purpose**: Display a human-readable cost report with Rich tables.
- **Steps**:
  1. For non-JSON output, build a Rich table:

     ```python
     from rich.console import Console
     from rich.table import Table

     console = Console()
     table = Table(title=f"Cost Report (grouped by {group_by})")
     table.add_column("Group", style="cyan")
     table.add_column("Input Tokens", justify="right")
     table.add_column("Output Tokens", justify="right")
     table.add_column("Cost (USD)", justify="right", style="green")
     table.add_column("Events", justify="right")
     table.add_column("Estimated", justify="center")
     ```

  2. Add a row for each `CostSummary`:

     ```python
     for summary in summaries:
         estimated_flag = "~" if summary.estimated_cost_usd > 0 else ""
         table.add_row(
             summary.group_key,
             f"{summary.total_input_tokens:,}",
             f"{summary.total_output_tokens:,}",
             f"${summary.total_cost_usd:.4f}",
             str(summary.event_count),
             estimated_flag,
         )
     ```

  3. Add a footer row with project totals:

     ```python
     total_cost = sum(s.total_cost_usd for s in summaries)
     total_events = sum(s.event_count for s in summaries)
     total_input = sum(s.total_input_tokens for s in summaries)
     total_output = sum(s.total_output_tokens for s in summaries)
     table.add_section()
     table.add_row(
         "TOTAL", f"{total_input:,}", f"{total_output:,}",
         f"${total_cost:.4f}", str(total_events), "",
         style="bold",
     )
     ```

  4. Print: `console.print(table)`
  5. For `--json` output:

     ```python
     if json_output:
         import json
         output = [s.to_dict() for s in summaries]
         console.print_json(json.dumps(output, indent=2))
         return
     ```

- **Files**: `src/specify_cli/cli/commands/agent/telemetry.py` (modify, ~40 lines added)
- **Notes**: The "Estimated" column uses `~` to flag groups where some costs were estimated from the pricing table (not reported by the agent). This gives operators a visual cue about data quality.

### Subtask T027 – Register telemetry sub-command

- **Purpose**: Wire the telemetry command into the CLI hierarchy.
- **Steps**:
  1. Open `src/specify_cli/cli/commands/agent/__init__.py`
  2. Import the telemetry module:

     ```python
     from specify_cli.cli.commands.agent import telemetry
     ```

  3. Register the sub-command:

     ```python
     app.add_typer(telemetry.app, name="telemetry")
     ```

  4. Verify `spec-kitty agent telemetry --help` shows the `cost` command
  5. Verify `spec-kitty agent telemetry cost --help` shows all flags
- **Files**: `src/specify_cli/cli/commands/agent/__init__.py` (modify, 2 lines added)
- **Notes**: Follow the existing pattern from `config` and `feature` sub-commands in the same file.

### Subtask T028 – Write CLI integration tests

- **Purpose**: Verify the full CLI command works end-to-end.
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/test_telemetry_cli.py`
  2. Test cases:
     - **test_cost_with_events**: Seed execution events in `tmp_path/kitty-specs/test-feature/execution.events.jsonl`, invoke CLI, verify Rich table output contains expected data
     - **test_cost_empty_project**: No events files, verify "No execution events found" message
     - **test_cost_json_output**: Use `--json` flag, verify parseable JSON output with correct structure
     - **test_cost_feature_filter**: Use `--feature` flag, verify only that feature's events are aggregated
     - **test_cost_group_by_model**: Use `--group-by model`, verify grouping changed
     - **test_cost_timeframe_filter**: Use `--since` and `--until`, verify temporal filtering
  3. Use `typer.testing.CliRunner` for invoking commands
  4. Use `tmp_path` with seeded JSONL files
  5. For Rich output testing, use `CliRunner` capture and assert on key strings in output
- **Files**: `tests/specify_cli/cli/commands/test_telemetry_cli.py` (new, ~130 lines)
- **Notes**: `CliRunner` from typer provides `.invoke()` which captures stdout. For Rich table output, assert on column header strings and expected values rather than exact formatting (Rich output may vary by terminal width). For JSON output, parse the captured stdout with `json.loads()`.

## Risks & Mitigations

- **Repo root resolution**: Different CLI commands use different approaches. Check the pattern in nearby commands (e.g., `agent/config.py`). If there's a shared utility, use it. Otherwise, `Path.cwd()` is acceptable for MVP.
- **Rich output in tests**: Rich output includes ANSI codes. Use `Console(file=StringIO(), force_terminal=True)` or CliRunner's `--no-color` to get plain text for assertions.
- **Feature glob matching**: `--feature 043*` should match `043-telemetry-foundation`. Use `Path.glob()` on `kitty-specs/` directory.

## Review Guidance

- Verify `spec-kitty agent telemetry cost` works from the command line
- Verify all flags work: `--feature`, `--since`, `--until`, `--group-by`, `--json`
- Verify Rich table is readable and totals are correct
- Verify JSON output is valid and matches `CostSummary.to_dict()` schema
- Verify "No execution events found" for empty project
- Verify registration: `spec-kitty agent --help` shows `telemetry` sub-command
- Run `mypy --strict` on the new CLI module

## Activity Log

- 2026-02-15T19:43:21Z – system – lane=planned – Prompt created.
- 2026-02-15T21:16:25Z – copilot – shell_pid=516747 – lane=doing – Assigned agent via workflow command
- 2026-02-15T21:32:20Z – copilot – shell_pid=516747 – lane=for_review – Ready for review: CLI cost command with Rich table, JSON output, all 5 flags, 12 tests pass
- 2026-02-15T21:39:07Z – copilot – shell_pid=516747 – lane=done – Review passed: fixed exception handling, date validation, group_by validation. 14 tests pass.
