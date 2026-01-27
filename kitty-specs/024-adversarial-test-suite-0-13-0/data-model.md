# Data Model: Adversarial Test Suite for 0.13.0

**Date**: 2026-01-25
**Feature**: 024-adversarial-test-suite-0-13-0

## Overview

This document defines the test entities, fixtures, and data structures for the adversarial test suite.

## Test Entities

### AttackVector

Represents a single malicious or edge-case input being tested.

```python
@dataclass
class AttackVector:
    name: str           # Descriptive name (e.g., "directory_traversal_parent")
    input: str | bytes  # The malicious input
    category: str       # Category (path, csv, git, migration, config)
    expected: str       # Expected behavior (reject, warn, handle)
    description: str    # Human-readable description
```

### TestResult

Outcome of an adversarial test.

```python
@dataclass
class TestResult:
    vector: AttackVector
    passed: bool
    actual_behavior: str
    error_message: str | None
    execution_time_ms: float
```

## Fixture Data Structures

### Path Attack Vectors

```python
PATH_ATTACK_VECTORS = [
    # Directory traversal
    AttackVector("traversal_parent", "../kitty-specs/", "path", "reject", "Parent directory escape"),
    AttackVector("traversal_deep", "../../../etc/passwd", "path", "reject", "Deep traversal"),
    AttackVector("traversal_dot_slash", "./kitty-specs/", "path", "reject", "Dot-slash traversal"),

    # Case sensitivity bypass (macOS)
    AttackVector("case_upper", "KITTY-SPECS/test/", "path", "reject", "Uppercase bypass"),
    AttackVector("case_mixed", "Kitty-Specs/test/", "path", "reject", "Mixed case bypass"),

    # Empty/whitespace
    AttackVector("empty_string", "", "path", "reject", "Empty path"),
    AttackVector("whitespace_only", "   ", "path", "reject", "Whitespace path"),
    AttackVector("slashes_only", "///", "path", "reject", "Slashes normalize to empty"),

    # Special paths
    AttackVector("home_tilde", "~/research/", "path", "reject", "Home directory reference"),
    AttackVector("absolute_path", "/tmp/research/", "path", "reject", "Absolute path"),
    AttackVector("null_byte", "docs/research/\x00/", "path", "reject", "Null byte injection"),

    # Unicode
    AttackVector("unicode_valid", "docs/研究/", "path", "handle", "Valid Unicode path"),
    AttackVector("unicode_rtl", "docs/\u202e/", "path", "reject", "RTL override character"),
]
```

### CSV Attack Vectors

```python
CSV_ATTACK_VECTORS = [
    # Formula injection
    AttackVector("formula_equals", "=cmd|'/c calc'!A1", "csv", "warn", "Excel formula injection"),
    AttackVector("formula_plus", "+1+1", "csv", "warn", "Plus formula"),
    AttackVector("formula_at", "@SUM(A1:A10)", "csv", "warn", "At-sign formula"),

    # Encoding attacks
    AttackVector("invalid_utf8", b"\xff\xfe", "csv", "handle", "Invalid UTF-8 sequence"),
    AttackVector("latin1_encoding", "café".encode("latin-1"), "csv", "handle", "Latin-1 encoded"),
    AttackVector("utf16_bom", b"\xff\xfeh\x00e\x00l\x00l\x00o\x00", "csv", "handle", "UTF-16 BOM"),

    # Schema attacks
    AttackVector("duplicate_columns", "col1,col1,col2", "csv", "reject", "Duplicate column names"),
    AttackVector("empty_file", "", "csv", "handle", "Empty CSV file"),
    AttackVector("headers_only", "col1,col2,col3\n", "csv", "handle", "Headers without data"),
    AttackVector("extra_columns", "a,b,c,d,e,f,g", "csv", "reject", "Extra columns beyond schema"),
    AttackVector("missing_columns", "a,b", "csv", "reject", "Missing required columns"),

    # Malformed
    AttackVector("unquoted_comma", "a,b,c,d with, comma", "csv", "handle", "Unquoted field with comma"),
    AttackVector("mixed_line_endings", "a,b\r\nc,d\ne,f\r", "csv", "handle", "Mixed CRLF/LF/CR"),
]
```

### Git State Scenarios

```python
GIT_STATE_SCENARIOS = [
    # Detached HEAD
    {"name": "detached_head", "setup": "git checkout --detach HEAD"},
    {"name": "detached_with_changes", "setup": "git checkout --detach HEAD && echo x > file"},

    # Merge/rebase state
    {"name": "merge_in_progress", "setup": "create MERGE_HEAD file"},
    {"name": "rebase_in_progress", "setup": "create REBASE_HEAD file"},
    {"name": "cherry_pick_in_progress", "setup": "create CHERRY_PICK_HEAD file"},

    # Commit state
    {"name": "staged_not_committed", "setup": "git add file (no commit)"},
    {"name": "partially_staged", "setup": "git add -p (partial)"},

    # Branch state
    {"name": "main_diverged", "setup": "advance main after WP branch"},
    {"name": "no_commits_on_branch", "setup": "create branch, no new commits"},
]
```

### Config Corruption Scenarios

```python
CONFIG_CORRUPTION_SCENARIOS = [
    {"name": "invalid_yaml", "content": "invalid: yaml: content: ["},
    {"name": "empty_file", "content": ""},
    {"name": "null_content", "content": "null"},
    {"name": "wrong_type", "content": "available: 'not a list'"},
    {"name": "unknown_agent", "content": "available:\n  - unknown_agent_xyz"},
    {"name": "unicode_corruption", "content": "available:\n  - claud\xe9"},
]
```

## Fixture Factories

### CSV File Factory

```python
def create_malformed_csv(tmp_path: Path, vector: AttackVector) -> Path:
    """Create a CSV file with the specified attack vector."""
    csv_path = tmp_path / "test.csv"

    if isinstance(vector.input, bytes):
        csv_path.write_bytes(vector.input)
    else:
        csv_path.write_text(vector.input, encoding="utf-8")

    return csv_path
```

### Git Repo Factory

```python
def create_git_scenario(tmp_path: Path, scenario: dict) -> Path:
    """Create a git repository in the specified state."""
    # Initialize repo
    # Apply scenario setup
    # Return repo path
```

### Symlink Factory

```python
def create_symlink(tmp_path: Path, target: str, link_name: str) -> Path | None:
    """Create symlink, returning None if not supported on platform."""
    try:
        link_path = tmp_path / link_name
        link_path.symlink_to(target)
        return link_path
    except OSError:
        return None  # Windows without elevation
```

## Test Organization

```
tests/adversarial/
├── __init__.py
├── conftest.py          # Shared fixtures, factories, markers
├── vectors/             # Attack vector data files (optional)
│   ├── paths.py
│   ├── csv.py
│   └── git.py
├── test_distribution.py
├── test_path_validation.py
├── test_csv_attacks.py
├── test_git_state.py
├── test_migration_robustness.py
├── test_multi_parent_merge.py
├── test_workspace_context.py
├── test_context_validation.py
└── test_agent_config.py
```

## Relationships

```
AttackVector (1) ──────> (N) TestCase
    │
    ├── category: path     → test_path_validation.py
    ├── category: csv      → test_csv_attacks.py
    ├── category: git      → test_git_state.py
    ├── category: migration → test_migration_robustness.py
    └── category: config   → test_agent_config.py

TestCase (N) ──────> (1) TargetModule
    │
    ├── mission.py
    ├── csv_schema.py
    ├── tasks.py
    ├── runner.py
    └── context_validation.py
```
