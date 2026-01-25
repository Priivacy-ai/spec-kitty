# Quickstart: Adversarial Test Suite for 0.13.0

**Date**: 2026-01-25
**Feature**: 024-adversarial-test-suite-0-13-0

## Prerequisites

- Python 3.11+
- pytest installed (`pip install pytest`)
- spec-kitty repository cloned
- Git configured

## Directory Setup

```bash
# From repository root
mkdir -p tests/adversarial
touch tests/adversarial/__init__.py
```

## Creating the First Test File

### 1. Create conftest.py with shared fixtures

```python
# tests/adversarial/conftest.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def adversarial_env() -> dict[str, str]:
    """Environment WITHOUT SPEC_KITTY_TEMPLATE_ROOT bypass."""
    env = os.environ.copy()
    env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)  # Critical: no bypass
    env.pop("PYTHONPATH", None)
    return env


@pytest.fixture
def temp_project(tmp_path: Path) -> Iterator[Path]:
    """Create minimal spec-kitty project structure."""
    project = tmp_path / "project"
    project.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True)

    # Create .kittify structure
    kittify = project / ".kittify"
    kittify.mkdir()

    yield project
```

### 2. Create your first test file

```python
# tests/adversarial/test_path_validation.py
from __future__ import annotations

import pytest
from pathlib import Path

from specify_cli.mission import validate_deliverables_path


class TestDirectoryTraversal:
    """Test directory traversal attack prevention."""

    @pytest.mark.parametrize("malicious_path", [
        "../kitty-specs/",
        "../../../etc/passwd",
        "./kitty-specs/",
        "docs/../../kitty-specs/",
    ])
    def test_traversal_rejected(self, malicious_path: str):
        """Directory traversal paths must be rejected."""
        is_valid, error = validate_deliverables_path(malicious_path)

        assert not is_valid, f"Path '{malicious_path}' should be rejected"
        assert error, "Should provide error message"


class TestEmptyPaths:
    """Test empty and whitespace path handling."""

    @pytest.mark.parametrize("empty_path", [
        "",
        "   ",
        "///",
    ])
    def test_empty_rejected(self, empty_path: str):
        """Empty/whitespace paths must be rejected."""
        is_valid, error = validate_deliverables_path(empty_path)

        assert not is_valid, f"Path '{empty_path!r}' should be rejected"
```

## Running Tests

```bash
# Run all adversarial tests
pytest tests/adversarial/ -v

# Run specific category
pytest tests/adversarial/test_path_validation.py -v

# Run with markers
pytest tests/adversarial/ -v -m "not slow"

# Run distribution tests only (requires wheel build)
pytest tests/adversarial/test_distribution.py -v -m distribution
```

## Test Markers

Register markers in `pyproject.toml` or `pytest.ini`:

```toml
[tool.pytest.ini_options]
markers = [
    "adversarial: Adversarial/security tests",
    "distribution: Tests requiring wheel install (slow)",
    "slow: Tests taking >10 seconds",
    "platform_darwin: macOS-specific tests",
    "platform_linux: Linux-specific tests",
]
```

## Key Patterns

### Testing for Rejection

```python
def test_attack_rejected(attack_input):
    is_valid, error = validate_function(attack_input)
    assert not is_valid
    assert error  # Ensure error message provided
```

### Testing Error Messages

```python
def test_clear_error_message(attack_input):
    is_valid, error = validate_function(attack_input)
    assert "directory traversal" in error.lower()  # Specific guidance
```

### Platform-Conditional Tests

```python
import sys

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_case_insensitive_bypass():
    # Test case-sensitivity on HFS+/APFS
    pass
```

### Distribution Test Pattern

```python
import subprocess
import sys

@pytest.mark.distribution
@pytest.mark.slow
def test_wheel_install(tmp_path):
    # Build wheel
    subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True)

    # Create fresh venv
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)

    # Install WITHOUT setting SPEC_KITTY_TEMPLATE_ROOT
    pip = venv / "bin" / "pip"
    wheel = list(Path("dist").glob("*.whl"))[0]
    subprocess.run([str(pip), "install", str(wheel)], check=True)

    # Test template resolution
    spec_kitty = venv / "bin" / "spec-kitty"
    result = subprocess.run(
        [str(spec_kitty), "init", "test-project"],
        capture_output=True,
        text=True,
        env={},  # Clean environment
    )
    assert result.returncode == 0
```

## Common Issues

### Symlink Tests Fail on Windows

```python
@pytest.fixture
def symlink_supported():
    """Skip test if symlinks not supported."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        try:
            Path(tmp, "link").symlink_to(tmp)
            return True
        except OSError:
            pytest.skip("Symlinks not supported")
```

### Concurrent Tests Flaky

Use file-based locking:

```python
import filelock

def test_concurrent_migration(tmp_path):
    lock = filelock.FileLock(tmp_path / ".migration.lock")
    with lock:
        # Run migration
        pass
```

## Next Steps

1. Create remaining test files per category
2. Add to CI pipeline with appropriate markers
3. Document any bugs found
