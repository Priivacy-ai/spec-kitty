# Quickstart: Unified Python CLI for Agents

*Path: kitty-specs/008-unified-python-cli/quickstart.md*

## Overview

This guide helps developers work on migrating spec-kitty's bash scripts to a unified Python CLI. The migration eliminates ~2,600 lines of bash code and provides AI agents with a reliable, location-aware `spec-kitty agent` command interface.

## Prerequisites

- Python 3.11+
- Git with worktree support
- spec-kitty development environment set up
- Access to the `008-unified-python-cli` branch
- Familiarity with Typer CLI framework

## Getting Started

### 1. Set Up Your Worktree

```bash
# From main spec-kitty repo
git worktree add .worktrees/008-unified-python-cli 008-unified-python-cli
cd .worktrees/008-unified-python-cli
```

### 2. Understand Parallel Work Streams

This feature is implemented in 7 phases with maximum parallelization:

- **Phase 1** (Days 1-2): Foundation - **SEQUENTIAL** (one person)
- **Phases 2-5** (Days 3-8): Command Implementation - **PARALLEL** (4 agents)
  - **Stream A** (Agent Alpha): Feature commands
  - **Stream B** (Agent Beta): Task commands
  - **Stream C** (Agent Gamma): Context commands
  - **Stream D** (Agent Delta): Release commands
- **Phase 6** (Days 9-10): Cleanup & Migration - **SEQUENTIAL** (one person)
- **Phase 7** (Day 11): Validation - **SEQUENTIAL** (one person)

### 3. Review Your Assignment

Check `plan.md` for your work stream assignment. Each stream owns specific files with **no conflicts**:

**Stream A (Agent Alpha)**: Feature Commands

- Files: `src/specify_cli/cli/commands/agent/feature.py`, `src/specify_cli/core/worktree.py`
- Dependencies: Phase 1 complete
- Duration: 2 days

**Stream B (Agent Beta)**: Task Commands

- Files: `src/specify_cli/cli/commands/agent/tasks.py`
- Dependencies: Phase 1 complete
- Duration: 2 days

**Stream C (Agent Gamma)**: Context Commands

- Files: `src/specify_cli/cli/commands/agent/context.py`, `src/specify_cli/core/agent_context.py`
- Dependencies: Phase 1 complete
- Duration: 1 day

**Stream D (Agent Delta)**: Release Commands

- Files: `src/specify_cli/cli/commands/agent/release.py`, `src/specify_cli/core/release.py`
- Dependencies: Phase 1 complete
- Duration: 1 day

## Development Workflow

### Phase 1: Foundation Setup (Required Before Parallel Work)

If you're working on Phase 1, complete ALL foundation items before parallel streams begin:

```bash
# 1. Create agent namespace structure
mkdir -p src/specify_cli/cli/commands/agent
touch src/specify_cli/cli/commands/agent/__init__.py
touch src/specify_cli/cli/commands/agent/feature.py
touch src/specify_cli/cli/commands/agent/context.py
touch src/specify_cli/cli/commands/agent/tasks.py
touch src/specify_cli/cli/commands/agent/release.py

# 2. Create test infrastructure
mkdir -p tests/unit/agent
mkdir -p tests/integration

# 3. Test foundation
spec-kitty agent --help  # Should display help text
```

**Checkpoint**: Foundation complete when `spec-kitty agent --help` works.

### Parallel Streams: Implementation Pattern

Each stream follows this pattern:

#### Step 1: Read Bash Script Being Replaced

```bash
# Example for Stream A
cat .kittify/scripts/bash/create-new-feature.sh | head -100
```

Understand the bash logic before migrating to Python.

#### Step 2: Implement Python Equivalent

**Pattern for all agent commands**:

```python
# src/specify_cli/cli/commands/agent/<module>.py
import json
import typer
from typing_extensions import Annotated
from specify_cli.core.paths import locate_project_root
from specify_cli.cli import console

app = typer.Typer(
    name="<module>",
    help="<Module> commands for AI agents",
    no_args_is_help=True
)

@app.command(name="<command-name>")
def command_name(
    arg: Annotated[str, typer.Argument(help="Description")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """
    Command description.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent <command-name> "value" --json
    """
    try:
        repo_root = locate_project_root()
        # ... implementation ...

        if json_output:
            print(json.dumps({"result": "success", "data": {}}))
        else:
            console.print("[green]✓[/green] Success message")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
            raise typer.Exit(1)
        else:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
```

#### Step 3: Write Tests

**Unit test pattern**:

```python
# tests/unit/agent/test_<module>.py
import pytest
from pathlib import Path
from specify_cli.cli.commands.agent.<module> import command_name

def test_command_name_basic():
    """Test command succeeds with valid input."""
    # Arrange
    test_input = "test-value"

    # Act
    result = command_name(test_input, json_output=True)

    # Assert
    assert result["result"] == "success"

def test_command_name_from_worktree(tmp_path):
    """Test command works when executed from worktree."""
    # Arrange: Create mock worktree structure
    worktree = tmp_path / ".worktrees" / "test-feature"
    worktree.mkdir(parents=True)

    # Act
    result = command_name_from_worktree(worktree)

    # Assert
    assert result is not None
```

**Integration test pattern**:

```python
# tests/integration/test_agent_workflows.py
def test_feature_creation_workflow(tmp_repo):
    """Test full feature creation from main repo and worktree."""
    # Arrange
    repo_root = setup_test_repo(tmp_repo)

    # Act: Create feature from main repo
    result = run_command(["spec-kitty", "agent", "create-feature", "test", "--json"])

    # Assert
    assert result["feature"] == "001-test"
    assert Path(result["feature_dir"]).exists()
```

#### Step 4: Verify No Conflicts

Before committing, verify you haven't modified files owned by other streams:

```bash
git status
# Should only show files in your assigned modules
```

### Coordination Points

**Daily Sync (Required)**:

1. Push your changes to feature branch
2. Run integration tests: `pytest tests/integration/`
3. Report status: "Stream X complete" or "Stream X blocked on Y"
4. Pull changes from other streams

**Sync Checkpoints**:

- **Sync 1 (Day 2)**: Foundation complete, parallel streams begin
- **Sync 2 (Day 6)**: Streams A+B complete
- **Sync 3 (Day 8)**: All streams complete, begin cleanup
- **Sync 4 (Day 10)**: Cleanup complete, begin validation

## Testing Your Work

### Unit Tests (Run Frequently)

```bash
# Test only your module
pytest tests/unit/agent/test_<your_module>.py -v

# Test with coverage
pytest tests/unit/agent/test_<your_module>.py --cov=src/specify_cli/cli/commands/agent/<your_module> --cov-report=term-missing
```

**Target**: 90%+ coverage for your module

### Integration Tests (Run Before Sync)

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific workflow test
pytest tests/integration/test_agent_workflows.py::test_<your_workflow> -v
```

### Manual Testing

```bash
# Test from main repo
cd /Users/robert/Code/spec-kitty
spec-kitty agent <your-command> <args> --json

# Test from worktree
cd .worktrees/008-unified-python-cli
spec-kitty agent <your-command> <args> --json
```

**Verify**: Command works identically from both locations

## Common Patterns

### Path Resolution

Always use the path resolution utilities:

```python
from specify_cli.core.paths import locate_project_root, resolve_feature_dir

# Get repo root (works from anywhere)
repo_root = locate_project_root()

# Resolve feature directory (worktree-aware)
feature_dir = resolve_feature_dir(repo_root, feature_slug)
```

### JSON Output Mode

Always support both JSON and rich output:

```python
if json_output:
    print(json.dumps({"key": "value"}))
else:
    console.print("[green]✓[/green] Human-readable message")
```

### Error Handling

Always handle errors gracefully with appropriate output:

```python
try:
    # ... operation ...
except FileNotFoundError as e:
    if json_output:
        print(json.dumps({"error": f"File not found: {e}"}))
        raise typer.Exit(1)
    else:
        console.print(f"[red]Error:[/red] File not found: {e}")
        raise typer.Exit(1)
```

## Debugging

### Check Agent Command Registration

```bash
spec-kitty agent --help
# Should show all subcommands
```

### Verify Path Resolution

```python
# Quick test script
from specify_cli.core.paths import locate_project_root
print(locate_project_root())
# Should work from main repo or worktree
```

### Test JSON Parsing

```bash
result=$(spec-kitty agent <command> --json)
echo "$result" | python -m json.tool  # Pretty-print JSON
```

## Migration Reference

When migrating bash scripts, refer to these equivalents:

| Bash Pattern | Python Equivalent |
|--------------|-------------------|
| `$(get_repo_root)` | `locate_project_root()` |
| `eval $(get_feature_paths)` | `resolve_feature_dir(repo_root, feature_slug)` |
| `git rev-parse --show-toplevel` | `subprocess.run(["git", "rev-parse", "--show-toplevel"])` |
| `if [ -f "$file" ]` | `if Path(file).exists()` |
| `if [ -L "$file" ]` | `if Path(file).is_symlink()` |
| `mkdir -p "$dir"` | `Path(dir).mkdir(parents=True, exist_ok=True)` |
| `basename "$path"` | `Path(path).name` |
| `dirname "$path"` | `Path(path).parent` |

## Troubleshooting

### "Module not found" errors

```bash
# Verify you're in correct location
pwd  # Should be in worktree

# Install in development mode
pip install -e .
```

### Path resolution failures

```bash
# Check .kittify marker exists
ls .kittify/

# Verify git worktree
git worktree list
```

### Test failures

```bash
# Run with verbose output
pytest -vv -s tests/unit/agent/test_<module>.py

# Run specific test
pytest tests/unit/agent/test_<module>.py::test_name -vv
```

## Resources

- **Spec**: `kitty-specs/008-unified-python-cli/spec.md`
- **Plan**: `kitty-specs/008-unified-python-cli/plan.md`
- **Research**: `kitty-specs/008-unified-python-cli/research.md`
- **Data Model**: `kitty-specs/008-unified-python-cli/data-model.md`
- **Typer Docs**: <https://typer.tiangolo.com/>
- **pathlib Docs**: <https://docs.python.org/3/library/pathlib.html>

## Need Help?

- Check plan.md for phase details and dependencies
- Review research.md for validation findings
- Check data-model.md for entity relationships
- Ask in coordination sync if blocked by another stream
