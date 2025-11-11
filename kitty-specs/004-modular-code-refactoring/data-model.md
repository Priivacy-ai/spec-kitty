# Data Model: Modular Code Refactoring
*Path: kitty-specs/004-modular-code-refactoring/data-model.md*

**Feature**: 004-modular-code-refactoring
**Date**: 2025-11-11
**Status**: Complete

## Overview

This document defines the module interfaces and data structures for the refactored spec-kitty codebase. Each module exposes a clear API contract to enable parallel development and testing.

## Module Interfaces

### Core Package (`specify_cli.core`)

#### config.py
```python
# Constants (no functions, just data)
AI_CHOICES: dict[str, str]  # Agent key ’ Display name
MISSION_CHOICES: dict[str, str]  # Mission key ’ Display name
AGENT_TOOL_REQUIREMENTS: dict[str, str]  # Agent ’ Required tool
SCRIPT_TYPE_CHOICES: list[str]  # ['sh', 'ps']
AGENT_COMMAND_CONFIG: dict[str, dict]  # Agent ’ Command patterns
DEFAULT_TEMPLATE_REPO: str
DEFAULT_MISSION_KEY: str
BANNER: str  # ASCII art
```

#### utils.py
```python
def format_path(path: Path, relative_to: Path = None) -> str:
    """Format path for display."""

def ensure_directory(path: Path) -> Path:
    """Create directory if it doesn't exist."""

def safe_remove(path: Path) -> bool:
    """Safely remove file or directory."""

def get_platform() -> str:
    """Get current platform (linux/darwin/win32)."""
```

#### git_ops.py
```python
def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""

def init_git_repo(path: Path, quiet: bool = False) -> bool:
    """Initialize new git repository with initial commit."""

def get_current_branch(path: Path) -> str | None:
    """Get current git branch name."""

def run_command(cmd: list[str], cwd: Path = None,
                capture: bool = True, quiet: bool = False) -> tuple[int, str, str]:
    """Run shell command and return (returncode, stdout, stderr)."""
```

#### tool_checker.py
```python
def check_tool(command: str) -> tuple[bool, str]:
    """Check if command-line tool is installed."""

def check_all_tools() -> dict[str, tuple[bool, str]]:
    """Check all required tools."""

def get_tool_version(command: str) -> str | None:
    """Get version string for tool."""
```

#### project_resolver.py
```python
def locate_project_root(start_path: Path = None) -> Path | None:
    """Find .kittify directory walking up from start_path."""

def resolve_template_path(template_name: str,
                         project_root: Path,
                         mission_key: str = None) -> Path | None:
    """Resolve template file path."""

def resolve_worktree_aware_feature_dir(project_root: Path,
                                      feature_name: str = None) -> Path:
    """Get feature directory handling worktrees."""

def get_active_mission_key(project_root: Path) -> str:
    """Get currently active mission."""
```

### CLI Package (`specify_cli.cli`)

#### ui.py
```python
class StepTracker:
    """Hierarchical progress tracker with live updates."""

    def __init__(self, title: str):
        pass

    def add(self, key: str, label: str) -> None:
        """Add a step to track."""

    def start(self, key: str) -> None:
        """Mark step as in progress."""

    def complete(self, key: str, detail: str = None) -> None:
        """Mark step as completed."""

    def error(self, key: str, detail: str) -> None:
        """Mark step as failed."""

    def render(self) -> Tree:
        """Render current state as Rich Tree."""

def get_key() -> str:
    """Get single keypress cross-platform."""

def select_with_arrows(prompt: str,
                       options: list[tuple[str, str]],
                       multi: bool = False) -> str | list[str]:
    """Interactive selection menu."""

def multi_select_with_arrows(prompt: str,
                            options: list[tuple[str, str]],
                            required: bool = True) -> list[str]:
    """Multi-selection menu with checkboxes."""
```

#### helpers.py
```python
class BannerGroup(TyperGroup):
    """Custom Typer group that shows banner."""

def show_banner() -> None:
    """Display ASCII art banner."""

def callback(version: bool = False) -> None:
    """Global CLI callback."""
```

### Template Package (`specify_cli.template`)

#### manager.py
```python
def get_local_repo_root() -> Path | None:
    """Find local spec-kitty repository."""

def copy_specify_base_from_local(repo_root: Path,
                                project_path: Path,
                                script_type: str) -> Path:
    """Copy .kittify structure from local repo."""

def copy_specify_base_from_package(project_path: Path,
                                  script_type: str) -> Path:
    """Copy .kittify from package resources."""
```

#### renderer.py
```python
def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from content."""

def render_template(template_path: Path,
                   variables: dict[str, str]) -> str:
    """Render template with variable substitution."""

def rewrite_paths(content: str,
                 replacements: dict[str, str]) -> str:
    """Rewrite paths in content."""
```

#### github_client.py
```python
def download_release(owner: str,
                    repo: str,
                    asset_pattern: str,
                    output_dir: Path,
                    token: str = None,
                    progress: bool = True) -> Path:
    """Download release asset from GitHub."""

def get_latest_release(owner: str,
                      repo: str,
                      token: str = None) -> dict:
    """Get latest release metadata."""

def parse_repo_slug(slug: str) -> tuple[str, str]:
    """Parse owner/repo from slug."""
```

#### asset_generator.py
```python
def generate_agent_assets(commands_dir: Path,
                         project_path: Path,
                         agent_key: str,
                         script_type: str) -> None:
    """Generate agent-specific command files."""

def render_command_template(template_path: Path,
                           agent_key: str,
                           command_name: str,
                           script_type: str) -> str:
    """Render command template for agent."""
```

### Dashboard Package (`specify_cli.dashboard`)

#### Public API (__init__.py)
```python
def ensure_dashboard_running(project_dir: Path,
                            verbose: bool = False,
                            open_browser: bool = False) -> tuple[str, int, str]:
    """Start dashboard if not running, return (url, port, token)."""

def stop_dashboard(project_dir: Path,
                  timeout: int = 10,
                  verbose: bool = False) -> bool:
    """Stop running dashboard."""

def get_dashboard_status(project_dir: Path) -> dict | None:
    """Get dashboard status if running."""
```

#### server.py
```python
def start_dashboard(project_dir: Path,
                   port: int = None,
                   background: bool = True) -> tuple[str, int, str]:
    """Start dashboard HTTP server."""

def find_free_port(start: int = 9240,
                  end: int = 9340) -> int:
    """Find available port for server."""
```

#### scanner.py
```python
def scan_all_features(project_root: Path) -> list[dict]:
    """Scan all features in project."""

def scan_feature_kanban(feature_dir: Path) -> dict:
    """Scan kanban board for feature."""

def get_feature_artifacts(feature_dir: Path) -> dict:
    """Check which artifacts exist."""

def get_workflow_status(artifacts: dict) -> str:
    """Determine workflow phase from artifacts."""
```

#### diagnostics.py
```python
def run_diagnostics(project_dir: Path) -> dict:
    """Run comprehensive diagnostics."""

def check_worktree_status(project_dir: Path) -> dict:
    """Check git worktree status."""

def verify_file_integrity(project_dir: Path) -> dict:
    """Verify expected files exist."""
```

#### lifecycle.py
```python
def check_dashboard_health(url: str,
                          token: str,
                          timeout: int = 5) -> bool:
    """Check if dashboard is healthy."""

def wait_for_shutdown(url: str,
                     token: str,
                     timeout: int = 10) -> bool:
    """Wait for dashboard to shut down."""

def parse_dashboard_file(project_dir: Path) -> dict | None:
    """Parse .dashboard metadata file."""

def write_dashboard_file(project_dir: Path,
                        url: str,
                        port: int,
                        token: str) -> None:
    """Write .dashboard metadata file."""
```

## Data Structures

### StepInfo
```python
@dataclass
class StepInfo:
    label: str
    status: Literal["pending", "running", "complete", "error", "skipped"]
    detail: str | None = None
    substeps: dict[str, StepInfo] = field(default_factory=dict)
```

### DashboardMetadata
```python
@dataclass
class DashboardMetadata:
    url: str
    port: int
    token: str
    pid: int | None = None
```

### FeatureInfo
```python
@dataclass
class FeatureInfo:
    id: str
    name: str
    branch: str
    status: str
    artifacts: dict[str, bool]
    kanban_stats: dict[str, int]
    worktree_exists: bool
```

### DiagnosticResult
```python
@dataclass
class DiagnosticResult:
    category: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict | None = None
```

## Command Registration

### CLI Commands
Each command module exports a function decorated with `@app.command()`:

```python
# cli/commands/init.py
def init(project_name: str,
        ai_assistant: str = None,
        script_type: str = None,
        mission_key: str = None,
        **kwargs) -> None:
    """Initialize new spec-kitty project."""

# cli/commands/check.py
def check(json_output: bool = False) -> None:
    """Check dependencies."""

# cli/commands/research.py
def research(force: bool = False) -> None:
    """Generate research artifacts."""

# cli/commands/accept.py
def accept(comprehensive: bool = False,
          json_output: bool = False) -> None:
    """Run acceptance checks."""

# cli/commands/merge.py
def merge(skip_tests: bool = False,
         cleanup_branches: bool = True) -> None:
    """Merge feature to main."""

# cli/commands/verify.py
def verify_setup(json_output: bool = False) -> None:
    """Verify environment setup."""
```

## Inter-Module Communication

### Event Flow
1. User invokes CLI command
2. Command validates input and resolves paths
3. Command calls appropriate service functions
4. Services may spawn subprocesses or start servers
5. Results returned through console output or JSON

### Error Handling
- All modules raise specific exceptions
- CLI catches and formats for user display
- Dashboard returns JSON errors with status codes
- Subprocesses log to stderr

### Import Resolution
Each module handles three contexts:
1. **Package import**: Standard relative imports
2. **Absolute import**: Fallback for subprocesses
3. **Development import**: sys.path manipulation if needed

## Testing Interfaces

Each module provides test fixtures:

```python
# In tests/conftest.py
@pytest.fixture
def mock_project_root(tmp_path):
    """Create mock project structure."""

@pytest.fixture
def mock_dashboard_server():
    """Create mock dashboard server."""

@pytest.fixture
def captured_output():
    """Capture console output."""
```

## Migration Notes

### Backward Compatibility
- All CLI commands maintain exact same interface
- Configuration files remain compatible
- Dashboard URLs unchanged
- Git operations identical

### Breaking Changes
- Direct imports of internal functions will break
- Must use public API from package __init__.py
- Some internal constants renamed/reorganized

### Deprecations
None - this is internal refactoring only.

## Performance Considerations

### Module Loading
- Lazy imports for heavy dependencies (httpx, rich)
- Conditional imports for platform-specific code
- Precompiled regex patterns in config

### Caching
- Template paths cached after first resolution
- Git status cached for command duration
- Dashboard metadata cached in .dashboard file

### Subprocess Optimization
- Reuse subprocess.run() wrapper
- Batch git operations where possible
- Connection pooling for HTTP requests