# Spec Kitty Test Suite Documentation

## Overview

The Spec Kitty test suite ensures code quality and prevents regressions through comprehensive testing. Tests are designed to run against **source code** (not installed packages) to guarantee consistency between development and CI environments.

## Test Architecture

### Source-First Testing Philosophy

Tests always run against the current source code in `src/`, never against a pip-installed version of spec-kitty-cli. This prevents version mismatches that can cause spurious failures.

**Key Design Principles:**
1. **Isolation**: Tests create isolated environments that block host package interference
2. **Consistency**: Same test behavior locally and in CI
3. **Fail-Fast**: Configuration errors are caught immediately with clear messages
4. **Performance**: Fast execution (< 30s for full suite)

## Test Categories

### Unit Tests (`tests/unit/`)

Pure Python tests with no subprocess calls or CLI invocation.

```bash
pytest tests/unit/ -v
```

**Characteristics:**
- Test individual functions and classes
- Fast execution (< 1s total)
- No external dependencies
- Mock file system operations where needed

### Integration Tests (`tests/integration/`)

Test complete CLI workflows using subprocess execution.

```bash
pytest tests/integration/ -v
```

**Characteristics:**
- Test CLI commands end-to-end
- Use git operations and file system
- Test version checking, migrations, and workflows
- Require git to be installed

### Functional Tests (`tests/test_*.py`)

End-to-end feature tests for specific functionality.

```bash
pytest tests/test_encoding.py -v
pytest tests/test_version_detection.py -v
```

**Characteristics:**
- Test complete features (encoding, version detection, dashboard)
- Mix of unit and integration approaches
- Feature-focused organization

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -e .[test]

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/integration/test_mission_cli.py

# Run specific test function
pytest tests/integration/test_mission_cli.py::test_mission_list_shows_available_missions

# Run tests matching pattern
pytest -k "mission"

# Run with coverage report
pytest --cov=specify_cli --cov-report=html
```

### Test Execution Options

```bash
# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Disable output capture (see print statements)
pytest -s

# Run in parallel (requires pytest-xdist)
pytest -n 4

# Run only tests that failed last time
pytest --lf

# Run only modified tests
pytest --testmon
```

## Test Isolation System

### How Isolation Works

The test infrastructure uses multiple layers to ensure tests use source code:

#### 1. `isolated_env` Fixture (`tests/integration/conftest.py`)

Creates an environment dictionary with isolation settings:

```python
@pytest.fixture()
def isolated_env() -> dict[str, str]:
    """Create isolated environment blocking host spec-kitty installation."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")  # Source only
    env["SPEC_KITTY_CLI_VERSION"] = source_version  # Override version
    env["SPEC_KITTY_TEST_MODE"] = "1"  # Enforce test behavior
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)  # Find templates
    return env
```

#### 2. Test Mode Enforcement (`src/specify_cli/core/version_checker.py`)

Forces CLI to use environment override in test mode:

```python
def get_cli_version() -> str:
    if os.environ.get("SPEC_KITTY_TEST_MODE") == "1":
        override = os.environ.get("SPEC_KITTY_CLI_VERSION")
        if not override:
            raise RuntimeError("Test mode requires SPEC_KITTY_CLI_VERSION")
        return override
    # ... production fallback logic
```

#### 3. CI Verification (`.github/workflows/*.yml`)

Both CI workflows verify version consistency before running tests:

```yaml
- name: Verify test isolation
  run: python verify_isolation.py  # Checks source vs installed version
```

### Fixtures

#### Core Fixtures

**`isolated_env`** - Environment dictionary with isolation settings
- Used by: All integration tests (via `run_cli`)
- Sets: PYTHONPATH, version overrides, test mode, template root

**`run_cli`** - Execute CLI commands in isolated environment
- Used by: All integration tests that invoke CLI
- Returns: subprocess.CompletedProcess with stdout/stderr

**`test_project`** - Create temporary Spec Kitty project with git
- Used by: Integration tests needing a project
- Creates: .kittify/, git repo, missions, metadata

**`clean_project`** - Alias for test_project (no worktrees)

**`dirty_project`** - Test project with uncommitted changes

**`project_with_worktree`** - Test project with .worktrees/ directory

#### Helper Functions (`tests/test_isolation_helpers.py`)

```python
get_source_version()      # Read version from pyproject.toml
get_installed_version()   # Get pip-installed version if present
assert_test_isolation()   # Fail test if version mismatch detected
run_cli_subprocess()      # Low-level CLI execution with isolation
```

## Troubleshooting

### Common Issues

#### "Version Mismatch Detected"

**Symptom**: Tests fail with version comparison errors

**Cause**: Installed spec-kitty-cli version doesn't match source

**Solution**:
```bash
pip uninstall spec-kitty-cli -y
pytest
```

#### "SPEC_KITTY_TEST_MODE=1 requires SPEC_KITTY_CLI_VERSION"

**Symptom**: RuntimeError when running CLI

**Cause**: Test is not using `isolated_env` or `run_cli` fixture

**Solution**: Use the proper fixtures for integration tests:
```python
def test_my_command(run_cli, test_project):
    result = run_cli(test_project, "my-command")
    assert result.returncode == 0
```

#### "Template not found"

**Symptom**: CLI can't find templates during tests

**Cause**: `SPEC_KITTY_TEMPLATE_ROOT` not set

**Solution**: Ensure you're using `run_cli` fixture (sets this automatically)

#### Tests pass locally but fail in CI

**Symptom**: CI shows failures that don't reproduce locally

**Cause**: Local environment has cached files or different state

**Solution**: Test in clean virtualenv:
```bash
python -m venv test-venv
source test-venv/bin/activate  # On Windows: test-venv\Scripts\activate
pip install -e .[test]
pytest
```

#### Parallel test execution fails

**Symptom**: Tests fail when run with `-n` flag

**Cause**: Shared state or resource conflicts

**Solution**: Ensure tests are independent and use temp directories

### Debugging Tips

**View full test output**:
```bash
pytest -vv --tb=long
```

**Run with print statements visible**:
```bash
pytest -s
```

**Debug specific test with pdb**:
```bash
pytest --pdb tests/integration/test_mission_cli.py::test_mission_list
```

**Check which fixtures are used**:
```bash
pytest --fixtures
```

**See test setup/teardown**:
```bash
pytest --setup-show
```

## Writing New Tests

### Integration Test Template

```python
def test_my_feature(run_cli, test_project):
    """Test description explaining what this verifies."""
    # Arrange: Set up test data
    (test_project / "input.txt").write_text("test data")

    # Act: Run CLI command
    result = run_cli(test_project, "my-command", "--flag")

    # Assert: Verify results
    assert result.returncode == 0
    assert "expected output" in result.stdout
    assert (test_project / "output.txt").exists()
```

### Unit Test Template

```python
def test_my_function():
    """Test description explaining what this verifies."""
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_output
```

### Best Practices

1. **Use fixtures**: Always use `run_cli` and `test_project` for integration tests
2. **Test one thing**: Each test should verify a single behavior
3. **Clear names**: Test names should describe what they verify
4. **Arrange-Act-Assert**: Structure tests in three clear sections
5. **Fail messages**: Add clear assert messages for debugging
6. **Isolation**: Tests should not depend on execution order
7. **Cleanup**: Use fixtures and temp directories (pytest handles cleanup)

### Example: Testing Version Isolation

```python
def test_cli_uses_source_version(run_cli, test_project):
    """Verify CLI reports source version in tests."""
    result = run_cli(test_project, "--version")
    source_version = get_source_version()

    assert result.returncode == 0
    assert source_version in result.stdout, (
        f"CLI reported '{result.stdout}' but source is {source_version}"
    )
```

## CI Behavior

### GitHub Actions Workflows

#### Release Readiness (`.github/workflows/release-readiness.yml`)

Runs on PRs to `main`:
1. Install dependencies (`pip install -e .[test]`)
2. **Verify test isolation** (new step!)
3. Run pytest
4. Validate release metadata
5. Test packaging

#### Release (`.github/workflows/release.yml`)

Runs on git tags (`v*.*.*`):
1. Install dependencies
2. **Verify test isolation** (new step!)
3. Run pytest
4. Validate release
5. Build distributions
6. Verify wheel contents
7. Publish to PyPI
8. Create GitHub Release

### Isolation Verification

Both workflows now include:

```yaml
- name: Verify test isolation
  run: python verify_isolation.py
```

This script checks that installed version matches source, catching version drift before tests run.

## Test Coverage

### Current Coverage

Run coverage report:
```bash
pytest --cov=specify_cli --cov-report=html
open htmlcov/index.html  # View in browser
```

### Coverage Goals

- **Core modules**: > 80% coverage
- **CLI commands**: > 70% coverage
- **Migrations**: 100% coverage (critical for data safety)
- **Utilities**: > 60% coverage

## Regression Tests

### Version Isolation (`tests/integration/test_version_isolation.py`)

Comprehensive tests ensuring isolation system works:
- Source version is readable
- Installed version matches or is absent
- CLI uses source version in tests
- Test mode enforcement works
- Subprocesses inherit isolation
- Parallel execution is isolated

Run isolation tests:
```bash
pytest tests/integration/test_version_isolation.py -v
```

## Performance

### Current Performance

Full suite: ~20-30 seconds

Breakdown:
- Unit tests: < 1s
- Integration tests: ~15-20s
- Functional tests: ~5-10s

### Optimization Tips

1. **Run relevant tests**: Use `-k` to filter
2. **Parallel execution**: Use `-n auto` with pytest-xdist
3. **Rerun failures**: Use `--lf` to run only failures
4. **Skip slow tests**: Mark with `@pytest.mark.slow` and skip with `-m "not slow"`

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Contributing Guide](../CONTRIBUTING.md)
- [Spec-Driven Development](../spec-driven.md)

## Questions?

If you encounter issues not covered here:

1. Check existing test files for examples
2. Review fixture implementations in `tests/integration/conftest.py`
3. Check test helper utilities in `tests/test_isolation_helpers.py`
4. Ask in GitHub Discussions or open an issue
