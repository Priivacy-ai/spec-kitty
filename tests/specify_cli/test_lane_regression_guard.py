"""Regression guards preventing reintroduction of frontmatter lane in active code.

Two categories of guard:

1. **Template guard** -- scans ``.md`` files under ``src/specify_cli/missions/``
   and ``src/doctrine/`` for ``lane:`` in YAML frontmatter position and
   ``lane=`` in activity log format strings.

2. **Runtime guard** -- scans ``.py`` files under ``src/specify_cli/`` for
   patterns that read or write frontmatter lane, EXCLUDING known
   migration-only modules:
   - ``upgrade/migrations/``
   - ``migration/``
   - ``status/history_parser.py``
   - ``task_metadata_validation.py``
   - ``scripts/tasks/task_helpers.py`` (event-log-first with legacy fallback)

   Legitimate canonical reads from materialized state (``wp["lane"]``,
   ``state.get("lane")``, ``snapshot.lane``) are NOT flagged.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Template guard helpers
# ---------------------------------------------------------------------------

TEMPLATE_DIRS = [
    REPO_ROOT / "src" / "specify_cli" / "missions",
    REPO_ROOT / "src" / "specify_cli" / "templates",  # shared packaged templates
    REPO_ROOT / "src" / "doctrine" / "templates",
    REPO_ROOT / "src" / "doctrine" / "missions",
]


def _collect_template_files() -> list[Path]:
    files: list[Path] = []
    for d in TEMPLATE_DIRS:
        if d.exists():
            files.extend(d.rglob("*.md"))
    return sorted(files)


def _extract_frontmatter(text: str) -> str | None:
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[1]
    return None


def _has_lane_in_frontmatter(text: str) -> list[str]:
    """Return offending lines containing ``lane:`` inside YAML frontmatter."""
    violations: list[str] = []
    frontmatter = _extract_frontmatter(text)
    if frontmatter is None:
        return violations
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if re.match(r"^lane\s*:", stripped):
            violations.append(f"frontmatter lane: {stripped}")
        elif re.match(r"lane\s*:", stripped):
            if f"frontmatter lane: {stripped}" not in violations:
                violations.append(f"history lane field: {stripped}")
    return violations


def _has_lane_in_activity_log(text: str) -> list[str]:
    """Return offending lines containing ``lane=`` in activity log strings."""
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"lane=", line):
            violations.append(f"line {i}: {line.strip()}")
    return violations


# ---------------------------------------------------------------------------
# Runtime guard helpers
# ---------------------------------------------------------------------------

SRC_ROOT = REPO_ROOT / "src" / "specify_cli"

# Modules that are ALLOWED to read/write frontmatter lane (migration-only)
EXCLUDED_PATHS: set[str] = set()
_EXCLUDED_PREFIXES = [
    "upgrade/migrations/",
    "migration/",
]
_EXCLUDED_FILES = [
    "status/history_parser.py",
    "task_metadata_validation.py",
    "cli/commands/validate_tasks.py",      # legacy command (migration-only)
]


def _is_excluded(rel_path: str) -> bool:
    """Check if a relative path (from src/specify_cli/) is in the exclusion list."""
    for prefix in _EXCLUDED_PREFIXES:
        if rel_path.startswith(prefix):
            return True
    for exc in _EXCLUDED_FILES:
        if rel_path == exc:
            return True
    return False


SCRIPTS_ROOT = REPO_ROOT / "scripts"


def _collect_runtime_py_files() -> list[Path]:
    """Collect all .py files under src/specify_cli/ and scripts/ not in exclusion list."""
    files: list[Path] = []
    for py_file in sorted(SRC_ROOT.rglob("*.py")):
        rel = str(py_file.relative_to(SRC_ROOT))
        if not _is_excluded(rel):
            files.append(py_file)
    # Also scan scripts/ (packaged task tooling)
    if SCRIPTS_ROOT.exists():
        for py_file in sorted(SCRIPTS_ROOT.rglob("*.py")):
            # Use repo-relative path for exclusion check
            rel = str(py_file.relative_to(REPO_ROOT))
            if not _is_excluded(rel):
                files.append(py_file)
    return files


# Patterns that indicate frontmatter lane reads/writes:
#   frontmatter.get("lane"  or  frontmatter["lane"]
#   frontmatter.get('lane'  or  frontmatter['lane']
#   extract_scalar(..., "lane")  or  extract_scalar(..., 'lane')
#   frontmatter["lane"] =  or  frontmatter.get("lane")
_FRONTMATTER_LANE_PATTERNS = [
    # frontmatter.get("lane" or frontmatter.get('lane'
    re.compile(r"""frontmatter\s*\.\s*get\s*\(\s*["']lane["']"""),
    # frontmatter["lane"] or frontmatter['lane']
    re.compile(r"""frontmatter\s*\[\s*["']lane["']\s*\]"""),
    # extract_scalar with "lane" argument
    re.compile(r"""extract_scalar\s*\([^)]*["']lane["']"""),
]

# Patterns that are LEGITIMATE canonical reads and must NOT match:
#   wp["lane"], state.get("lane"), snapshot.lane, etc.
# These are already excluded by the patterns above because they don't
# start with "frontmatter" or use "extract_scalar".


def _find_frontmatter_lane_violations(py_file: Path) -> list[str]:
    """Scan a .py file for frontmatter lane read/write patterns."""
    violations: list[str] = []
    try:
        text = py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations

    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("#"):
            continue
        # Skip docstrings (rough heuristic: lines inside triple-quotes)
        # We check each pattern against the line
        for pattern in _FRONTMATTER_LANE_PATTERNS:
            if pattern.search(line):
                violations.append(f"line {i}: {stripped}")
                break  # One violation per line is enough
    return violations


# ---------------------------------------------------------------------------
# Parametrized template guard tests
# ---------------------------------------------------------------------------

_template_files = _collect_template_files()


@pytest.mark.parametrize(
    "template_path",
    _template_files,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _template_files],
)
def test_template_no_lane_in_frontmatter(template_path: Path) -> None:
    """No mission/doctrine template should contain ``lane:`` in YAML frontmatter."""
    text = template_path.read_text(encoding="utf-8")
    violations = _has_lane_in_frontmatter(text)
    assert not violations, (
        f"{template_path.relative_to(REPO_ROOT)} has lane in frontmatter:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


@pytest.mark.parametrize(
    "template_path",
    _template_files,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _template_files],
)
def test_template_no_lane_in_activity_log(template_path: Path) -> None:
    """No mission/doctrine template should contain ``lane=`` in activity log strings."""
    text = template_path.read_text(encoding="utf-8")
    violations = _has_lane_in_activity_log(text)
    assert not violations, (
        f"{template_path.relative_to(REPO_ROOT)} has lane= in activity log:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Parametrized runtime guard tests
# ---------------------------------------------------------------------------

_runtime_files = _collect_runtime_py_files()
_standalone_task_scripts = [
    REPO_ROOT / "scripts" / "tasks" / "tasks_cli.py",
    REPO_ROOT / "src" / "specify_cli" / "scripts" / "tasks" / "tasks_cli.py",
]


@pytest.mark.parametrize(
    "py_file",
    _runtime_files,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _runtime_files],
)
def test_runtime_no_frontmatter_lane_access(py_file: Path) -> None:
    """No active runtime .py file should access frontmatter lane directly.

    Frontmatter lane is migration-only. Active code must read lane from
    the canonical event log via ``status.lane_reader.get_wp_lane()`` or
    from materialized ``status.json`` snapshots.
    """
    violations = _find_frontmatter_lane_violations(py_file)
    assert not violations, (
        f"{py_file.relative_to(REPO_ROOT)} accesses frontmatter lane directly:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse status.lane_reader.get_wp_lane() or snapshot.work_packages instead."
    )


@pytest.mark.parametrize(
    "script_path",
    _standalone_task_scripts,
    ids=[str(p.relative_to(REPO_ROOT)) for p in _standalone_task_scripts],
)
def test_standalone_task_scripts_do_not_write_lane_activity_entries(script_path: Path) -> None:
    """Standalone task scripts must not write ``lane=`` into body activity logs."""
    text = script_path.read_text(encoding="utf-8")
    violations = [
        f"line {idx}: {line.strip()}"
        for idx, line in enumerate(text.splitlines(), 1)
        if re.search(r"""["'].*lane=.*["']""", line)
    ]
    assert not violations, (
        f"{script_path.relative_to(REPO_ROOT)} still writes lane= activity entries:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Self-tests: verify guards actually catch violations
# ---------------------------------------------------------------------------


def test_template_guard_catches_lane_in_frontmatter() -> None:
    """Verify the template guard catches ``lane:`` if reintroduced."""
    fake = "---\nlane: planned\ntitle: test\n---\n# Test\n"
    assert _has_lane_in_frontmatter(fake), "Guard should catch lane: in frontmatter"


def test_template_guard_catches_lane_in_activity_log() -> None:
    """Verify the template guard catches ``lane=`` if reintroduced."""
    fake = "- 2026-01-12T10:00:00Z -- system -- lane=planned -- Prompt created\n"
    assert _has_lane_in_activity_log(fake), "Guard should catch lane= in activity log"


def test_template_guard_passes_clean_content() -> None:
    """Clean content without lane should pass both guards."""
    clean_fm = "---\ntitle: test\nwork_package_id: WP01\n---\n# Test\n"
    assert not _has_lane_in_frontmatter(clean_fm)

    clean_log = "- 2026-01-12T10:00:00Z -- system -- Prompt created\n"
    assert not _has_lane_in_activity_log(clean_log)


def test_runtime_guard_catches_frontmatter_get_lane() -> None:
    """Verify the runtime guard catches frontmatter.get('lane')."""
    fake_code = '    lane = frontmatter.get("lane", "planned")\n'
    # Write to a temp file and scan
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(fake_code)
        f.flush()
        violations = _find_frontmatter_lane_violations(Path(f.name))
    assert violations, "Guard should catch frontmatter.get('lane')"


def test_runtime_guard_catches_frontmatter_bracket_lane() -> None:
    """Verify the runtime guard catches frontmatter['lane']."""
    fake_code = '    value = frontmatter["lane"]\n'
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(fake_code)
        f.flush()
        violations = _find_frontmatter_lane_violations(Path(f.name))
    assert violations, "Guard should catch frontmatter['lane']"


def test_runtime_guard_catches_extract_scalar_lane() -> None:
    """Verify the runtime guard catches extract_scalar(..., 'lane')."""
    fake_code = '    lane = extract_scalar(frontmatter, "lane")\n'
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(fake_code)
        f.flush()
        violations = _find_frontmatter_lane_violations(Path(f.name))
    assert violations, "Guard should catch extract_scalar with 'lane'"


def test_runtime_guard_ignores_canonical_reads() -> None:
    """Verify the runtime guard does NOT flag legitimate canonical state reads."""
    canonical_code = """
    lane = wp["lane"]
    current = state.get("lane")
    value = snapshot.lane
    from_lane = event.from_lane
"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(canonical_code)
        f.flush()
        violations = _find_frontmatter_lane_violations(Path(f.name))
    assert not violations, f"Guard should NOT flag canonical reads, but found: {violations}"


def test_runtime_guard_ignores_comments() -> None:
    """Verify the runtime guard does NOT flag commented-out code."""
    commented = '    # old code: frontmatter.get("lane")\n'
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(commented)
        f.flush()
        violations = _find_frontmatter_lane_violations(Path(f.name))
    assert not violations, "Guard should skip comments"


def test_template_files_found() -> None:
    """Ensure we found template files to scan (guard against empty glob)."""
    assert len(_template_files) >= 10, (
        f"Expected at least 10 template files but found {len(_template_files)}"
    )


def test_runtime_files_found() -> None:
    """Ensure we found runtime .py files to scan (guard against empty glob)."""
    assert len(_runtime_files) >= 20, (
        f"Expected at least 20 runtime .py files but found {len(_runtime_files)}"
    )


def test_excluded_files_exist() -> None:
    """Verify that the files we exclude actually exist (guard against stale exclusions)."""
    for exc_file in _EXCLUDED_FILES:
        path = SRC_ROOT / exc_file
        assert path.exists(), (
            f"Excluded file {exc_file} does not exist at {path}. "
            "Remove it from the exclusion list if the file was deleted."
        )
