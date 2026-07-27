# Quickstart: Modular Code Refactoring
*Path: kitty-specs/004-modular-code-refactoring/quickstart.md*

## Overview

This guide helps developers work on the modular refactoring of spec-kitty's monolithic files. The refactoring splits 5,730 lines across two files into ~21 modules, enabling parallel development by multiple agents.

## Prerequisites

- Python 3.11+
- Git with worktree support
- spec-kitty development environment set up
- Access to the `004-modular-code-refactoring` branch

## Getting Started

### 1. Set Up Your Worktree

```bash
# From main spec-kitty repo
git worktree add .worktrees/004-modular-code-refactoring 004-modular-code-refactoring
cd .worktrees/004-modular-code-refactoring
```

### 2. Understand Your Agent Assignment

Check which agent role you've been assigned:

- **Foundation Agent**: Creates core modules (Day 1)
- **Agent A**: Dashboard Infrastructure (Days 2-3)
- **Agent B**: Template System (Days 2-3)
- **Agent C**: Core Services (Days 2-3)
- **Agent D**: Dashboard Handlers (Days 4-5)
- **Agent E**: CLI Commands (Days 4-5)
- **Agent F**: GitHub & Init (Days 4-5)

### 3. Review Your Files

Each agent owns specific files exclusively:

```bash
# Example for Agent A
dashboard/static/dashboard.css
dashboard/static/dashboard.js
dashboard/templates/index.html
dashboard/scanner.py
dashboard/diagnostics.py
```

## Development Workflow

### Step 1: Create Your Module Structure

```bash
# Example for Agent A
mkdir -p src/specify_cli/dashboard/static
mkdir -p src/specify_cli/dashboard/templates
touch src/specify_cli/dashboard/__init__.py
touch src/specify_cli/dashboard/scanner.py
touch src/specify_cli/dashboard/diagnostics.py
```

### Step 2: Extract Code from Monolith

1. Open the source file (`__init__.py` or `dashboard.py`)
2. Locate your assigned functions/classes
3. Copy to your new module
4. Add necessary imports

Example extraction:
```python
# From dashboard.py lines 381-441 → scanner.py
def scan_all_features(project_root: Path) -> list[dict]:
    """Scan all features in project."""
    # ... extracted code ...
```

### Step 3: Create Import Stubs

For modules not yet created by other agents:

```python
# In your module
try:
    from ..core.config import AI_CHOICES  # Will exist after Foundation Agent
except ImportError:
    # Stub for development
    AI_CHOICES = {}
```

### Step 4: Define Your Interface

Document your module's public API:

```python
# In dashboard/scanner.py
__all__ = ['scan_all_features', 'scan_feature_kanban', 'get_feature_artifacts']

def scan_all_features(project_root: Path) -> list[dict]:
    """
    Scan all features in project.

    Args:
        project_root: Path to project root containing .kittify

    Returns:
        List of feature dictionaries with id, name, status, etc.
    """
    pass  # Implementation here
```

### Step 5: Write Tests

Create corresponding test file:

```python
# tests/test_dashboard/test_scanner.py
import pytest
from pathlib import Path
from specify_cli.dashboard.scanner import scan_all_features

def test_scan_all_features(mock_project_root):
    features = scan_all_features(mock_project_root)
    assert isinstance(features, list)
    # ... more assertions ...
```

## Coordination Rules

### 1. No Concurrent Edits

- Each file is owned by ONE agent only
- Check file ownership before editing
- Never edit another agent's files

### 2. Daily Sync

At end of each day:
```bash
git add .
git commit -m "Agent A: Extracted dashboard infrastructure modules"
git push
```

### 3. Import Dependencies

When depending on another agent's module:

```python
# Option 1: Stub for development
try:
    from ..template.manager import copy_base
except ImportError:
    def copy_base(*args, **kwargs):
        raise NotImplementedError("Waiting for Agent B")

# Option 2: Wait for dependency
# Only work on modules after dependencies are complete
```

### 4. Testing Strategy

Run tests for your modules:
```bash
# Test just your modules
pytest tests/test_dashboard/test_scanner.py -v

# Integration test after merge
pytest tests/ -v
```

## Module Guidelines

### Size Constraints

- Maximum 200 lines per module (excluding comments/docstrings)
- If approaching limit, split into sub-modules

### Import Compatibility

Handle three contexts:
```python
# At top of module
try:
    # Standard package import
    from .scanner import scan_all_features
except ImportError:
    try:
        # Subprocess/detached context
        from specify_cli.dashboard.scanner import scan_all_features
    except ImportError:
        # Development context
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from dashboard.scanner import scan_all_features
```

### Documentation

Every module needs:
- Module docstring explaining purpose
- Function docstrings with args/returns
- Type hints for public functions
- `__all__` list of public exports

## Common Patterns

### Pattern 1: Extracting Classes

```python
# Original in __init__.py
class StepTracker:
    def __init__(self): ...
    def add(self): ...
    # ... 100+ lines ...

# Extract to cli/ui.py
from dataclasses import dataclass, field
from typing import Literal
from rich.tree import Tree

@dataclass
class StepInfo:
    label: str
    status: Literal["pending", "running", "complete", "error", "skipped"]
    # ...

class StepTracker:
    # ... implementation ...
```

### Pattern 2: Extracting Constants

```python
# Original scattered throughout __init__.py
AI_CHOICES = {...}
MISSION_CHOICES = {...}

# Consolidate in core/config.py
"""Configuration constants for spec-kitty."""

AI_CHOICES = {
    "codex": "Codex CLI",
    "claude": "Claude Code",
    # ...
}

MISSION_CHOICES = {
    "software-dev": "Software Dev Kitty",
    # ...
}
```

### Pattern 3: Extracting HTML/CSS/JS

```python
# Original in dashboard.py
def get_dashboard_html():
    return '''<!DOCTYPE html>
    <html>
    <!-- 1000+ lines of HTML/CSS/JS -->
    </html>'''

# Extract to dashboard/templates/index.html
<!DOCTYPE html>
<html>
<!-- Actual HTML -->
</html>

# And dashboard/handlers/base.py
def get_dashboard_html():
    template_path = Path(__file__).parent.parent / "templates" / "index.html"
    return template_path.read_text()
```

## Troubleshooting

### Issue: Import Not Found

```python
# If seeing: ImportError: cannot import name 'X' from 'Y'
# Add fallback import:
try:
    from ..core.config import X
except ImportError:
    X = None  # or appropriate default
```

### Issue: Circular Import

```python
# Avoid by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..other.module import SomeClass

def my_function(obj: 'SomeClass'):
    # Use string annotation to avoid runtime import
    pass
```

### Issue: Test Failures

```bash
# Run with verbose output
pytest tests/test_my_module.py -vvs

# Check import paths
python -c "from specify_cli.my_package.my_module import my_function"
```

## Checklist

Before marking your modules complete:

- [ ] All modules under 200 lines
- [ ] All public functions have docstrings
- [ ] Type hints added for public API
- [ ] Tests written and passing
- [ ] Import compatibility handled
- [ ] No references to old monolithic imports
- [ ] Code formatted with black/ruff
- [ ] Integration tested with other agents' modules

## Resources

- [Full Specification](spec.md)
- [Implementation Plan](plan.md)
- [Data Model](data-model.md)
- [Module Interfaces](contracts/module-interfaces.yaml)
- [Research Findings](research.md)

## Support

If blocked or need clarification:
1. Check the module ownership matrix in plan.md
2. Coordinate with other agents via git commits
3. Use stub implementations to continue development
4. Document blockers in your commit messages