---
work_package_id: "WP03"
subtasks: ["T034", "T035", "T036", "T037", "T038", "T039", "T040", "T041", "T042", "T043", "T044", "T045", "T046", "T047", "T048", "T049", "T050", "T051", "T052", "T053"]
title: "Task Workflow Commands"
phase: "Phase 3 - Task Commands (Stream B)"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "18142"
review_status: ""
reviewed_by: "claude"
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-18T23:07:00Z"
    lane: "done"
    agent: "claude"
    shell_pid: "18142"
    action: "Code review complete - approved (44/44 tests passed)"
---

# Work Package Prompt: WP03 – Task Workflow Commands

## Objectives & Success Criteria

**Goal**: Migrate task management bash scripts to Python agent commands, converting 850 lines of argparse CLI to Typer.

**Success Criteria**:
- All 6 task commands implemented: `move-task`, `mark-status`, `list-tasks`, `add-history`, `rollback-task`, `validate-workflow` (note: `move-task` later evolved to `workflow implement/review` in v0.11.1)
- `spec-kitty agent move-task WP01 --to doing --json` moves task and returns JSON (historical - now `spec-kitty agent workflow implement WP01`)
- Full task workflow works: planned → doing → for_review → done
- All existing `tasks_support.py` functionality preserved
- 90%+ test coverage for `tasks.py`
- Commands work from main repo and worktree

**Why This Matters**: Task commands are the most frequently used by agents during implementation. Reliability is critical for agent productivity.

---

## Context & Constraints

**Prerequisites**:
- **WP01 complete** ✅ (foundation infrastructure)
- Existing code to migrate: `src/specify_cli/tasks_support.py` (850 lines argparse)
- Bash wrappers to replace: Thin scripts calling `tasks_cli.py`

**Stream Assignment**: **Stream B (Agent Beta)** - Can run in parallel with WP02, WP04, WP05

**Files Owned by This Stream**:
- `src/specify_cli/cli/commands/agent/tasks.py` ✅
- `tests/unit/agent/test_tasks.py` ✅

**Key Requirements**:
- Preserve ALL existing functionality from `tasks_support.py`
- YAML frontmatter parsing with ruamel.yaml (handles edge cases)
- Lane transitions with history tracking
- Validation of task metadata structure

---

## Subtasks & Detailed Guidance

### T034 – Analyze existing tasks_support.py

Read `src/specify_cli/tasks_support.py` to understand:
1. Argparse command structure (6 subcommands)
2. YAML frontmatter parsing logic
3. Lane transition rules
4. History entry format
5. Validation rules

Document key functions to preserve in migration notes.

---

### T035 – Convert argparse to Typer in tasks.py

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/tasks.py` (stub from WP01)
2. Convert argparse patterns to Typer decorators:
   ```python
   import typer
   from typing_extensions import Annotated
   from pathlib import Path

   app = typer.Typer(
       name="tasks",
       help="Task workflow commands for AI agents",
       no_args_is_help=True
   )
   ```
3. Preserve core logic from `tasks_support.py` (frontmatter parsing, file operations)
4. Create internal helper functions for shared logic (YAML parsing, history updates)

---

### T036-T041 – Implement 6 task commands

Implement each command following this pattern (historical example - `move-task` later evolved to `workflow` subcommands):

```python
@app.command(name="move-task")  # Historical: later superseded by workflow implement/review
def move_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Move task between lanes (planned → doing → for_review → done)."""
    try:
        repo_root = locate_project_root()
        feature_dir = # detect feature directory
        
        # Read task file frontmatter
        task_file = find_task_file(feature_dir, task_id)
        metadata = parse_frontmatter(task_file)
        
        # Update lane in metadata
        metadata["lane"] = to
        
        # Add history entry
        add_history_entry(metadata, f"Moved to {to}")
        
        # Write updated frontmatter
        write_frontmatter(task_file, metadata)
        
        if json_output:
            print(json.dumps({
                "result": "success",
                "task_id": task_id,
                "old_lane": old_lane,
                "new_lane": to
            }))
        else:
            console.print(f"[green]✓[/green] Moved {task_id} to {to}")
    
    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
            raise typer.Exit(1)
        else:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
```

**Commands to implement**:
- **T036**: `move-task` - Move between lanes (historical - later evolved to `workflow implement/review`)
- **T037**: `mark-status` - Update checkbox status
- **T038**: `list-tasks` - List tasks by lane with filtering
- **T039**: `add-history` - Append history entry
- **T040**: `rollback-task` - Undo lane move (use history)
- **T041**: `validate-workflow` - Validate task metadata structure

---

### T042 – Ensure dual output for task commands

Verify all 6 commands support:
- `--json` flag ✅
- JSON-only output in JSON mode (no console mixing) ✅
- Rich console output in default mode ✅
- Error handling in both modes ✅

---

### T043 – Preserve tasks_support.py functionality

**Checklist**:
- [ ] All argparse subcommands converted to Typer
- [ ] YAML frontmatter parsing works identically (use `ruamel.yaml`)
- [ ] Lane transition validation rules preserved
- [ ] History entry format unchanged
- [ ] File path resolution logic preserved
- [ ] Error messages equivalent or better

---

### T044-T049 – Unit test all 6 commands

Create `tests/unit/agent/test_tasks.py` with tests for:

- **T044**: `test_move_task` - All lane transitions
- **T045**: `test_mark_status` - Checkbox state changes
- **T046**: `test_list_tasks` - Filtering by lane, JSON output
- **T047**: `test_add_history` - Frontmatter history updates
- **T048**: `test_rollback_task` - Undo logic
- **T049**: `test_validate_workflow` - Metadata validation rules

Use pattern:
```python
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.tasks import app

runner = CliRunner()

# Historical test for original move-task command (later evolved to workflow commands)
def test_move_task_json(mock_worktree, tmp_task_file):
    result = runner.invoke(app, ["move-task", "WP01", "--to", "doing", "--json"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["new_lane"] == "doing"
```

---

### T050 – Integration test: Full task workflow

Create end-to-end test of complete workflow (historical test for original move-task command):

```python
def test_full_task_workflow(tmp_repo):
    # Create task in planned
    create_task(tmp_repo, "WP01")

    # Move planned → doing
    result = run_cmd(["move-task", "WP01", "--to", "doing"])
    assert result["new_lane"] == "doing"

    # Move doing → for_review
    result = run_cmd(["move-task", "WP01", "--to", "for_review"])
    assert result["new_lane"] == "for_review"

    # Move for_review → done
    result = run_cmd(["move-task", "WP01", "--to", "done"])
    assert result["new_lane"] == "done"

    # Verify history has 4 entries
    metadata = read_task_metadata(tmp_repo, "WP01")
    assert len(metadata["history"]) == 4

# Note: These tests were later updated to test workflow implement/review commands
```

---

### T051 – Integration test: Commands from both locations

Test task commands work identically from main repo and worktree:

```python
def test_task_commands_main_repo(main_repo):
    result = run_cmd_in_dir(main_repo, ["list-tasks", "--json"])
    assert result.exit_code == 0

def test_task_commands_worktree(worktree):
    result = run_cmd_in_dir(worktree, ["list-tasks", "--json"])
    assert result.exit_code == 0
```

---

### T052 – Verify 90%+ coverage

Run coverage analysis:
```bash
pytest tests/unit/agent/test_tasks.py \
  --cov=src/specify_cli/cli/commands/agent/tasks \
  --cov-report=term-missing
```

Add tests for uncovered branches until 90%+ achieved.

---

### T053 – Deprecate old tasks_support.py

**Timeline Clarification**:
- **WP03 (this work package)**: Add deprecation warning, update references
- **WP06 (cleanup phase)**: Physical deletion of file along with all bash scripts

**Steps for WP03**:
1. Add deprecation warning to `tasks_support.py` module docstring:
   ```python
   """
   DEPRECATED: This module is deprecated as of v0.10.0.
   Use `spec-kitty agent tasks` commands instead.

   This file will be removed in the next release.
   See: src/specify_cli/cli/commands/agent/tasks.py
   """
   ```
2. Update any internal references to use new `agent tasks` commands
3. Document migration in code comments
4. **Do NOT delete file yet** - deletion happens in WP06 T100-T101

**Verification**: Deprecation warning visible, all functionality works via new commands

---

## Test Strategy

**Unit Tests**: All 6 commands with edge cases (90%+ coverage target)
**Integration Tests**: Full workflow + location independence
**Manual Tests**: Run each command with `--json` and verify parseable

---

## Risks & Mitigations

**Risk**: YAML frontmatter parsing edge cases (malformed, missing fields)
**Mitigation**: Use `ruamel.yaml` (handles comments, ordering), comprehensive edge case tests

**Risk**: Breaking existing task files during migration
**Mitigation**: Preserve exact frontmatter format, validate against existing files

---

## Definition of Done Checklist

- [ ] All 6 task commands implemented
- [ ] Full workflow integration test passing
- [ ] 90%+ test coverage achieved
- [ ] All `tasks_support.py` functionality preserved
- [ ] Commands work from main repo and worktree
- [ ] JSON output validated and parseable

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-17T22:17:57Z – claude – shell_pid=71324 – lane=doing – Started implementation
- 2025-12-17T22:21:26Z – claude – shell_pid=71324 – lane=for_review – Core implementation complete (T034-T043,T053). Tests pending in follow-up.
- 2025-12-17T22:27:56Z – claude – shell_pid=71324 – lane=doing – Resuming to complete tests (T044-T052)
- 2025-12-17T22:37:10Z – claude – shell_pid=71324 – lane=for_review – Completed all subtasks T034-T053 with 94% test coverage (44 tests)
