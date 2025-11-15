# Testing Guidelines for Spec Kitty Agents

## Critical: Dashboard Process Cleanup

### Problem
Dashboard processes are long-running HTTP servers that persist beyond test execution. If tests fail or are interrupted, orphaned dashboard processes remain running indefinitely and cause subsequent failures:

1. Orphaned dashboards occupy ports in the default range (9237-9337)
2. New dashboard starts find an available port but fails health check due to project path mismatch
3. Health check times out after 20 seconds → false "Unable to start dashboard" error
4. Orphans accumulate over time, eventually exhausting all available ports

### Required: Proper Cleanup in All Dashboard Tests

**ALWAYS use pytest fixtures with proper teardown for dashboard tests:**

```python
import pytest
from pathlib import Path
from specify_cli.dashboard import stop_dashboard, ensure_dashboard_running

@pytest.fixture
def clean_dashboard(tmp_path):
    """Fixture that ensures dashboard cleanup after test."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Yield the project directory for test use
    yield project_dir

    # CRITICAL: Always cleanup, even if test fails
    try:
        stop_dashboard(project_dir)
    except Exception:
        pass  # Best effort cleanup

def test_dashboard_feature(clean_dashboard):
    """Example test using proper cleanup fixture."""
    # Test uses clean_dashboard fixture
    url, port, started = ensure_dashboard_running(clean_dashboard)
    # ... test logic ...
    # Cleanup happens automatically via fixture teardown
```

### Cleanup Checklist for Dashboard Tests

Before writing or modifying dashboard tests, ensure:

- [ ] **Fixture-based cleanup**: Use pytest fixtures with teardown, not manual cleanup in test body
- [ ] **Try-except wrappers**: Wrap `stop_dashboard()` in try-except to handle edge cases
- [ ] **Temp directories**: Use `tmp_path` fixture for test projects (auto-cleanup by pytest)
- [ ] **Autouse fixtures**: Consider module-level autouse fixtures to cleanup all orphans:
  ```python
  @pytest.fixture(autouse=True, scope="module")
  def cleanup_all_test_dashboards():
      """Kill all test dashboards before and after test module."""
      yield
      # After all tests in module, kill any remaining test dashboards
      import subprocess
      subprocess.run(['pkill', '-f', 'run_dashboard_server'],
                     stderr=subprocess.DEVNULL)
  ```
- [ ] **CI/CD considerations**: Ensure CI test runners kill orphans between test runs
- [ ] **Manual testing**: After manual testing, always run `pkill -f run_dashboard_server`

### Why This Matters

**Impact of orphaned dashboards:**
- Local development: Blocks dashboard startup for real projects
- CI/CD: Flaky tests due to port conflicts and timeouts
- Resource leaks: Python processes accumulate over time
- False negatives: Tests pass locally but fail in CI (or vice versa)

**Prevention is better than detection:**
The codebase now includes orphan cleanup logic, but proper test hygiene prevents the problem entirely and makes tests more reliable.

### Common Anti-Patterns to Avoid

❌ **Bad: Cleanup in test body only**
```python
def test_dashboard():
    ensure_dashboard_running(project_dir)
    # ... test logic ...
    stop_dashboard(project_dir)  # Won't run if test fails!
```

✅ **Good: Cleanup in fixture teardown**
```python
@pytest.fixture
def dashboard(tmp_path):
    yield tmp_path
    stop_dashboard(tmp_path)  # Always runs, even on failure
```

❌ **Bad: Shared project directory across tests**
```python
PROJECT_DIR = Path("/tmp/shared_test")  # Conflicts between tests
```

✅ **Good: Isolated temp directories per test**
```python
def test_dashboard(tmp_path):  # Unique dir per test
    project_dir = tmp_path / "isolated_test"
```

❌ **Bad: No cleanup on exceptions**
```python
def test_dashboard():
    ensure_dashboard_running(project_dir)
    raise ValueError("Test failed")  # Dashboard orphaned!
```

✅ **Good: Cleanup guaranteed via fixture**
```python
@pytest.fixture
def dashboard(tmp_path):
    try:
        yield tmp_path
    finally:
        stop_dashboard(tmp_path)  # Always runs
```

## General Testing Best Practices

### Test Isolation
- Each test should be completely independent
- Use fixtures for shared setup/teardown
- Avoid global state or shared resources

### Resource Management
- Always clean up files, processes, network connections
- Use context managers (`with` statements) when possible
- Ensure cleanup happens even on test failure

### Temp Directories
- Use pytest's `tmp_path` fixture for file system tests
- Never hardcode `/tmp/` paths (conflicts between parallel tests)
- Let pytest handle cleanup of temp directories

### Background Processes
- Always track process IDs for cleanup
- Use fixtures to ensure process termination
- Consider timeout mechanisms for hung processes

---

**Remember: Every orphaned process is a future flaky test. Write defensive cleanup code.**

## Review Attribution

### Critical: Reviewer vs. Implementer Identity

When approving tasks during code review, it's critical to record the **reviewer's** identity, not the implementer's:

**Problem:** Using generic `tasks-move-to-lane.sh` for approvals records the wrong agent:
- Inherits implementer's `agent` and `shell_pid` from frontmatter
- Activity log shows implementer approved their own work
- No audit trail of who actually reviewed the code

**Solution:** Use the dedicated `approve` command:

```bash
# Capture YOUR identity as the reviewer
REVIEWER_AGENT="claude-reviewer"  # Or from $AGENT_ID
REVIEWER_SHELL_PID=$$

# Use dedicated approve command
python3 .kittify/scripts/tasks/tasks_cli.py approve <FEATURE> <TASK_ID> \
  --review-status "approved without changes" \
  --reviewer-agent "$REVIEWER_AGENT" \
  --reviewer-shell-pid "$REVIEWER_SHELL_PID"
```

**What this does:**
- Sets `reviewed_by: "claude-reviewer"` (NEW field)
- Sets `review_status: "approved without changes"` (NEW field)
- Updates `agent: "claude-reviewer"` (was implementer)
- Updates `shell_pid: "$$"` (was implementer's PID)
- Adds activity log entry with REVIEWER's info

**Why this matters:**
- **Accountability**: Know who approved potentially buggy code
- **Process compliance**: Prove reviews actually happened
- **Debugging**: Trace review decisions when bugs appear
- **Multi-agent coordination**: Distinguish implementer vs reviewer actions
