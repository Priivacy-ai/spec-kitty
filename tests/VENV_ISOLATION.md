# Virtual Environment Test Isolation

## Overview

The spec-kitty test suite uses **venv-based interpreter isolation** to ensure tests run against the correct version of the CLI, regardless of what's installed globally on the system.

## Problem

Prior to this implementation, tests were **filesystem-isolated** but not **interpreter-isolated**:

- Tests would spawn subprocesses using `sys.executable` (the Python running pytest)
- Those subprocesses would import spec-kitty from the global installation
- This caused **version mismatches** when:
  - Developer has spec-kitty v0.10.8 installed globally
  - Source code is at v0.11.0
  - Tests fail with version mismatch errors despite correct code

## Solution

### Session-Scoped Test Venv

The `test_venv` fixture (in `tests/conftest.py`) creates a session-scoped virtual environment:

```python
@pytest.fixture(scope="session", autouse=True)
def test_venv() -> Path:
    """Create and cache a test venv for isolated CLI execution."""
    venv_dir = REPO_ROOT / ".pytest_cache" / "spec-kitty-test-venv"

    # Rebuild if version changes
    if source_version_changed(venv_dir):
        rebuild_venv(venv_dir)

    # Install package in editable mode
    pip install -e REPO_ROOT

    return venv_dir
```

### Test Helpers

The `tests/test_isolation_helpers.py` module provides utilities:

- **`get_venv_python()`** - Returns path to venv's Python executable
- **`get_venv_metadata_version()`** - Gets installed version from venv
- **`get_venv_module_version()`** - Gets __version__ from venv's module
- **`run_cli_subprocess()`** - Runs CLI through venv with isolation

### Usage in Tests

All tests that spawn CLI subprocesses must use `get_venv_python()`:

```python
# ❌ WRONG - Uses test runner's Python
subprocess.run([sys.executable, "-m", "specify_cli.__init__", "--version"])

# ✅ CORRECT - Uses venv Python
from tests.test_isolation_helpers import get_venv_python
subprocess.run([str(get_venv_python()), "-m", "specify_cli.__init__", "--version"])
```

## Architecture

```
┌─────────────────────────────────────┐
│ Test Runner (pytest)                │
│ Python: spec-kitty-test/venv/python │
│ Version: 0.10.13 (may differ)       │
└──────────────┬──────────────────────┘
               │
               │ Creates session fixture
               ▼
┌─────────────────────────────────────┐
│ Test Venv                           │
│ Location: .pytest_cache/spec-kitty- │
│           test-venv/                │
│ Python: venv/bin/python             │
│ Version: 0.11.0 (from source)       │
└──────────────┬──────────────────────┘
               │
               │ All CLI tests use this
               ▼
┌─────────────────────────────────────┐
│ Subprocess calls                    │
│ get_venv_python() →                 │
│   .pytest_cache/spec-kitty-test-    │
│   venv/bin/python                   │
└─────────────────────────────────────┘
```

## Key Files

### Core Infrastructure

- `tests/conftest.py`
  - `test_venv` fixture (session-scoped, autouse)
  - Creates and manages test venv

- `tests/test_isolation_helpers.py`
  - `get_venv_python()` - Get venv Python path
  - `get_venv_metadata_version()` - Query venv's installed version
  - `get_venv_module_version()` - Query venv's module version
  - `run_cli_subprocess()` - Helper for running CLI

### Integration Test Fixtures

- `tests/integration/conftest.py`
  - `isolated_env` fixture - Sets up environment variables
  - `run_cli` fixture - Wrapper for running CLI in tests

### Updated Files

These files were updated to use venv Python instead of `sys.executable`:

- `tests/integration/test_version_isolation.py`
- `tests/integration/test_workspace_per_wp_workflow.py`
- `tests/test_version_detection.py`

## Testing Multiple Versions

### Testing Current Version (Default)

```bash
# Runs against source version (from pyproject.toml)
pytest tests/
```

The venv will have the current source version installed in editable mode.

### Testing Specific Version

To test against a specific version, you can:

1. **Clear the venv** to force rebuild:
   ```bash
   rm -rf .pytest_cache/spec-kitty-test-venv
   pytest tests/
   ```

2. **Modify pyproject.toml version** before running tests
   ```bash
   # Edit version in pyproject.toml
   vim pyproject.toml

   # Clear venv and run tests
   rm -rf .pytest_cache/spec-kitty-test-venv
   pytest tests/
   ```

3. **Install specific version in venv** manually:
   ```bash
   .pytest_cache/spec-kitty-test-venv/bin/pip install spec-kitty-cli==0.10.8
   pytest tests/
   ```

### Version-Conditional Tests

Tests can skip based on version using fixtures:

```python
def test_new_feature(requires_v011):
    # Only runs on v0.11.0+
    ...

def test_legacy_behavior(requires_pre_v011):
    # Only runs on < v0.11.0
    ...
```

## Verification

### Check Isolation

```bash
# Test runner's version (may differ)
python -c "from importlib.metadata import version; print(version('spec-kitty-cli'))"

# Test venv's version (should match source)
.pytest_cache/spec-kitty-test-venv/bin/python -c "from importlib.metadata import version; print(version('spec-kitty-cli'))"

# Source version
grep '^version' pyproject.toml
```

### Run Isolation Tests

```bash
# Verify isolation infrastructure works
pytest tests/integration/test_version_isolation.py -v

# Verify version detection works
pytest tests/test_version_detection.py -v
```

## Benefits

1. **True Isolation** - Tests run against controlled version, not global install
2. **Version Independence** - Developers can have any global version installed
3. **Consistent CI** - Same isolation mechanism in CI and local development
4. **Multi-Version Testing** - Can test different versions by rebuilding venv
5. **Fast Iteration** - Venv cached across test runs (session scope)

## Troubleshooting

### "Version mismatch" errors

If you see errors like:
```
Project version: 0.10.8
Installed version: 0.10.8
```

This means the test is still using global installation. Check that:
1. Test uses `get_venv_python()` not `sys.executable`
2. Test venv exists: `.pytest_cache/spec-kitty-test-venv/`
3. Venv has correct version installed

### Rebuild test venv

```bash
rm -rf .pytest_cache/spec-kitty-test-venv
pytest tests/  # Will rebuild on first run
```

### Version detection fails

If `get_installed_version()` returns None:
```bash
# Check venv exists
ls .pytest_cache/spec-kitty-test-venv/

# Check package installed
.pytest_cache/spec-kitty-test-venv/bin/pip list | grep spec-kitty

# Reinstall if needed
.pytest_cache/spec-kitty-test-venv/bin/pip install -e .
```

## Future Enhancements

Potential improvements:

1. **Parallel version testing** - Create multiple venvs for different versions
2. **Version matrix** - Test against range of versions automatically
3. **Faster venv creation** - Use shared pip cache
4. **Docker-based isolation** - Full system isolation for distribution tests
