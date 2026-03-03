"""Shared fixtures for adversarial tests."""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AttackVector:
    """Represents a single malicious or edge-case input being tested."""

    name: str  # Descriptive name
    input: str | bytes  # The malicious input
    category: str  # Category (path, csv, git, migration, config)
    expected: str  # Expected behavior (reject, warn, handle)
    description: str  # Human-readable description


# =============================================================================
# PATH ATTACK VECTORS (T003)
# =============================================================================

PATH_ATTACK_VECTORS = [
    # Directory traversal
    AttackVector(
        "traversal_parent", "../kitty-specs/", "path", "reject", "Parent directory escape"
    ),
    AttackVector(
        "traversal_deep", "../../../etc/passwd", "path", "reject", "Deep traversal"
    ),
    AttackVector(
        "traversal_dot_slash", "./kitty-specs/", "path", "reject", "Dot-slash to kitty-specs"
    ),
    AttackVector(
        "traversal_nested", "docs/../../kitty-specs/", "path", "reject", "Nested traversal"
    ),
    # Case sensitivity bypass (macOS HFS+/APFS)
    AttackVector("case_upper", "KITTY-SPECS/test/", "path", "reject", "Uppercase bypass"),
    AttackVector("case_mixed", "Kitty-Specs/test/", "path", "reject", "Mixed case bypass"),
    AttackVector(
        "case_alternating", "KiTtY-SpEcS/test/", "path", "reject", "Alternating case"
    ),
    # Empty/whitespace
    AttackVector("empty_string", "", "path", "reject", "Empty path"),
    AttackVector("whitespace_only", "   ", "path", "reject", "Whitespace-only path"),
    AttackVector("slashes_only", "///", "path", "reject", "Slashes normalize to empty"),
    AttackVector("tab_whitespace", "\t\t", "path", "reject", "Tab characters"),
    # Special paths
    AttackVector("home_tilde", "~/research/", "path", "reject", "Home directory reference"),
    AttackVector("absolute_path", "/tmp/research/", "path", "reject", "Absolute path"),
    AttackVector(
        "null_byte", "docs/research/\x00evil/", "path", "reject", "Null byte injection"
    ),
    # Unicode edge cases
    AttackVector("unicode_valid", "docs/研究/", "path", "handle", "Valid Unicode path"),
    AttackVector(
        "unicode_rtl", "docs/\u202e/test/", "path", "reject", "RTL override character"
    ),
    AttackVector("unicode_bidi", "docs/a\u202eb\u202c/", "path", "reject", "BiDi override"),
]


@pytest.fixture(params=[v for v in PATH_ATTACK_VECTORS if v.expected == "reject"])
def malicious_path(request) -> AttackVector:
    """Parametrized fixture providing path attack vectors expected to be rejected."""
    return request.param


@pytest.fixture(params=[v for v in PATH_ATTACK_VECTORS if v.expected == "handle"])
def valid_unicode_path(request) -> AttackVector:
    """Parametrized fixture providing valid Unicode paths that should be handled."""
    return request.param


# =============================================================================
# CSV ATTACK VECTORS (T004)
# =============================================================================

CSV_ATTACK_VECTORS = [
    # Formula injection
    AttackVector(
        "formula_equals", "=cmd|'/c calc'!A1", "csv", "warn", "Excel formula injection"
    ),
    AttackVector("formula_plus", "+1+1", "csv", "warn", "Plus formula"),
    AttackVector("formula_minus", "-1+1", "csv", "warn", "Minus formula"),
    AttackVector("formula_at", "@SUM(A1:A10)", "csv", "warn", "At-sign formula"),
    # Encoding attacks
    AttackVector(
        "invalid_utf8", b"\xff\xfe\x00\x01", "csv", "handle", "Invalid UTF-8 sequence"
    ),
    AttackVector(
        "latin1_encoding",
        "café,naïve,résumé".encode("latin-1"),
        "csv",
        "handle",
        "Latin-1 encoded",
    ),
    AttackVector(
        "utf16_bom",
        b"\xff\xfeh\x00e\x00l\x00l\x00o\x00",
        "csv",
        "handle",
        "UTF-16 with BOM",
    ),
    AttackVector("null_bytes", b"col1,col2\x00,col3", "csv", "handle", "Null bytes in content"),
    # Schema violations
    AttackVector(
        "duplicate_columns", "col1,col1,col2", "csv", "reject", "Duplicate column names"
    ),
    AttackVector(
        "extra_columns", "a,b,c,d,e,f,g,h,i,j", "csv", "reject", "Extra columns beyond schema"
    ),
    AttackVector("missing_columns", "a,b", "csv", "reject", "Missing required columns"),
    AttackVector(
        "whitespace_columns", " col1 , col2 ", "csv", "handle", "Whitespace in column names"
    ),
    # Empty/malformed
    AttackVector("empty_file", "", "csv", "handle", "Empty CSV file"),
    AttackVector("headers_only", "col1,col2,col3\n", "csv", "handle", "Headers without data rows"),
    AttackVector(
        "mixed_line_endings", "a,b\r\nc,d\ne,f\r", "csv", "handle", "Mixed CRLF/LF/CR"
    ),
    AttackVector(
        "unquoted_comma", "a,b,c with, comma,d", "csv", "handle", "Unquoted field with comma"
    ),
]


@pytest.fixture
def malformed_csv_factory(tmp_path: Path) -> Callable[[AttackVector, str], Path]:
    """Factory fixture for creating malformed CSV files."""

    def _create(vector: AttackVector, filename: str = "test.csv") -> Path:
        csv_path = tmp_path / filename
        if isinstance(vector.input, bytes):
            csv_path.write_bytes(vector.input)
        else:
            csv_path.write_text(vector.input, encoding="utf-8")
        return csv_path

    return _create


# =============================================================================
# PLATFORM DETECTION FIXTURES (T005)
# =============================================================================


def _symlinks_supported() -> bool:
    """Check if symlinks are supported on this platform."""
    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp)
        target = test_dir / "target"
        link = test_dir / "link"
        target.mkdir()
        try:
            link.symlink_to(target)
            return True
        except OSError:
            return False  # Windows without elevation or restricted


def _is_case_sensitive_filesystem() -> bool:
    """Check if the filesystem is case-sensitive."""
    with tempfile.TemporaryDirectory() as tmp:
        test_path = Path(tmp)
        lower = test_path / "test"
        upper = test_path / "TEST"
        lower.touch()
        return not upper.exists()


@pytest.fixture(scope="session")
def symlinks_supported() -> bool:
    """Session fixture indicating whether symlinks work on this platform."""
    return _symlinks_supported()


@pytest.fixture
def symlink_factory(
    tmp_path: Path, symlinks_supported: bool
) -> Callable[[str | Path, str], Path | None]:
    """Factory fixture for creating symlinks with platform awareness.

    Returns None if symlinks not supported, allowing tests to skip gracefully.
    """

    def _create(target: str | Path, link_name: str) -> Path | None:
        if not symlinks_supported:
            return None
        link_path = tmp_path / link_name
        # Ensure parent directory exists
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target)
        return link_path

    return _create


@pytest.fixture(scope="session")
def case_insensitive_fs() -> bool:
    """Session fixture indicating case-insensitive filesystem (macOS, Windows)."""
    return not _is_case_sensitive_filesystem()


# =============================================================================
# ENVIRONMENT AND PROJECT FIXTURES (T006)
# =============================================================================


@pytest.fixture
def adversarial_env() -> dict[str, str]:
    """Environment WITHOUT SPEC_KITTY_TEMPLATE_ROOT bypass.

    This is critical for distribution testing - ensures tests run against
    packaged templates, not local repo templates.
    """
    env = os.environ.copy()

    # Remove all spec-kitty bypasses
    env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)
    env.pop("PYTHONPATH", None)

    # Keep PATH for git, python, etc.
    return env


@pytest.fixture
def temp_git_project(tmp_path: Path) -> Iterator[Path]:
    """Create a minimal git project for testing."""
    project = tmp_path / "project"
    project.mkdir()

    # Initialize git
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=project, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@adversarial.local"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Adversarial Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Initial commit
    readme = project / "README.md"
    readme.write_text("# Test Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    yield project


@pytest.fixture
def kittify_project(temp_git_project: Path) -> Path:
    """Create a project with .kittify structure."""
    kittify = temp_git_project / ".kittify"
    kittify.mkdir()

    # Minimal config
    config = kittify / "config.yaml"
    config.write_text("available:\n  - claude\n", encoding="utf-8")

    return temp_git_project
