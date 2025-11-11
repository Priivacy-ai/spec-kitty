---
work_package_id: WP06
work_package_title: CLI Commands Extraction
subtitle: Extract CLI commands into separate modules
subtasks:
  - T050
  - T051
  - T052
  - T053
  - T054
  - T055
  - T056
  - T057
  - T058
  - T059
phases: story-based
priority: P3
lane: planned
tags:
  - cli
  - commands
  - parallel
  - agent-e
history:
  - date: 2025-11-11
    status: created
    by: spec-kitty.tasks
---

# WP06: CLI Commands Extraction

## Objective

Extract each CLI command (except init) into its own module for better organization, testing, and maintainability.

## Context

All CLI commands are currently in the monolithic `__init__.py` file. This work package moves each to a dedicated module in `cli/commands/`.

**Agent Assignment**: Agent E (Days 4-5)

## Requirements from Specification

- One module per command
- Maintain exact CLI interface
- Preserve all command options and behavior
- Each module under 200 lines

## Implementation Guidance

### T050: Extract check command to cli/commands/check.py

From `__init__.py` lines 2041-2099:
```python
"""Dependency checking command."""

import typer
from rich.console import Console
from ...core.tool_checker import check_tool

console = Console()
app = typer.Typer()

@app.command()
def check(json_output: bool = False) -> None:
    """Check that all required tools are installed."""
    # ... implementation ...
```

### T051: Extract research command to cli/commands/research.py

From lines 1880-2039:
- Complex command with feature detection
- Creates research artifacts
- Uses acceptance module imports

### T052: Extract accept command to cli/commands/accept.py

From lines 2257-2383:
- Feature acceptance workflow
- Uses acceptance module heavily
- JSON output option

### T053: Extract merge command to cli/commands/merge.py

From lines 2387-2626:
- Most complex command (240 lines)
- Git merge operations
- Worktree cleanup
- Branch deletion

### T054: Extract verify_setup to cli/commands/verify.py

From lines 2629-2693:
- Calls verify_enhanced module
- JSON output for AI agents
- ~65 lines

### T055: Extract dashboard command to cli/commands/dashboard.py

From lines 2103-2195:
- Starts/manages dashboard server
- Browser opening logic
- ~95 lines

### T056: Create cli/commands/__init__.py

Register all commands:
```python
"""CLI commands for spec-kitty."""

from .check import check
from .research import research
from .accept import accept
from .merge import merge
from .verify import verify_setup
from .dashboard import dashboard
# init will be added by WP07

__all__ = [
    'check',
    'research',
    'accept',
    'merge',
    'verify_setup',
    'dashboard',
]
```

### T057: Extract helpers to cli/helpers.py

From `__init__.py`:
- `BannerGroup` class (lines 802-817)
- `show_banner()` function (lines 863-887)
- `callback()` function (lines 889-896)

### T058-T059: Testing and integration

**T058**: Write integration tests for each command
- Test with various options
- Verify output format
- Check error handling

**T059**: Verify command registration
- Ensure all commands appear in CLI
- Test help text
- Verify options work

## Testing Strategy

1. **Command tests**: Test each command with all options
2. **Integration tests**: Test command interactions
3. **CLI tests**: Verify commands register correctly
4. **Output tests**: Check console and JSON output

## Definition of Done

- [ ] Each command in separate module
- [ ] All commands work identically
- [ ] Tests written and passing
- [ ] Command registration verified
- [ ] Help text unchanged
- [ ] All options preserved

## Risks and Mitigations

**Risk**: Command registration might break
**Mitigation**: Test CLI thoroughly after extraction

**Risk**: Complex commands like merge have many dependencies
**Mitigation**: Careful import management

## Review Guidance

1. Verify each command works exactly as before
2. Check all command options preserved
3. Ensure help text unchanged
4. Confirm tests cover all paths

## Dependencies

- WP01: Needs cli/ui.py for UI components
- WP04: Needs core services (git_ops, project_resolver)

## Dependents

- WP08: Integration will register all commands