"""Forbid process-name-wide dashboard cleanup in test infrastructure.

The dashboard entrypoint name is legitimate in direct dashboard tests, so this
gate flags it only when a line also names a process-wide enumeration or kill
tool.  The scanner's own literals are safe because its file is excluded.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SELF_PATH = Path(__file__).resolve()
_DASHBOARD_PROCESS_NAME = "run_dashboard_server"
_PROCESS_NAME_KILL_TOOLS = ("pgrep", "killall")
_PROCESS_ENUMERATION_TOKENS = (
    "psutil.process_iter",
    "ps aux",
    "ps -ef",
    "ps -e",
    "ps -a",
)
_SCAN_DIRECTORIES = ("tests", "scripts", "bin", ".github/workflows")
_ROOT_FILES = ("Makefile", "run_tests.sh")


def _line_violation(line: str) -> str | None:
    normalized = " ".join(line.lower().split())
    if _DASHBOARD_PROCESS_NAME not in normalized:
        return None
    for tool in _PROCESS_NAME_KILL_TOOLS:
        if tool in normalized:
            return f"process-name kill tool {tool}"
    for token in _PROCESS_ENUMERATION_TOKENS:
        if token in normalized:
            return f"process-wide enumeration {token}"
    return None


def _scanned_files(repo_root: Path = _REPO_ROOT) -> list[Path]:
    paths: list[Path] = []
    for directory in _SCAN_DIRECTORIES:
        paths.extend((repo_root / directory).rglob("*"))
    paths.extend(repo_root / filename for filename in _ROOT_FILES)
    return sorted(path for path in paths if path.is_file() and path.resolve() != _SELF_PATH and "__pycache__" not in path.parts)


def _collect_violations(
    *,
    repo_root: Path = _REPO_ROOT,
    files: Iterable[Path] | None = None,
) -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    for path in _scanned_files(repo_root) if files is None else files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(lines, start=1):
            violation = _line_violation(line)
            if violation is not None:
                relative_path = path.relative_to(repo_root).as_posix()
                violations.append((relative_path, lineno, violation))
    return violations


def test_no_process_name_wide_dashboard_kill() -> None:
    """Keep dashboard cleanup scoped to resources this test run owns."""
    files = _scanned_files()
    assert files, "dashboard process-sweep scan collected zero files"
    assert _collect_violations() == []


def test_scan_covers_nested_test_infrastructure_and_makefile(tmp_path: Path) -> None:
    tests = tmp_path / "tests" / "dashboard"
    tests.mkdir(parents=True)
    (tests / "conftest.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("value = 1\n", encoding="utf-8")

    relative_paths = {path.relative_to(tmp_path).as_posix() for path in _scanned_files(tmp_path)}
    assert relative_paths == {"Makefile", "tests/dashboard/conftest.py"}


@pytest.mark.parametrize(
    ("source", "expected_violation"),
    [
        (
            'subprocess.run(["pgrep", "-f", "run_dashboard_server"])',
            "process-name kill tool pgrep",
        ),
        (
            "pgrep -f 'run_dashboard_server'",
            "process-name kill tool pgrep",
        ),
        (
            "killall -f run_dashboard_server",
            "process-name kill tool killall",
        ),
        (
            "ps aux | grep run_dashboard_server",
            "process-wide enumeration ps aux",
        ),
        (
            "ps -ef | grep run_dashboard_server",
            "process-wide enumeration ps -ef",
        ),
        (
            "psutil.process_iter() if 'run_dashboard_server' in process.cmdline()",
            "process-wide enumeration psutil.process_iter",
        ),
    ],
)
def test_process_sweep_scanner_catches_known_shapes(
    source: str,
    expected_violation: str,
) -> None:
    assert _line_violation(source) == expected_violation


def test_process_sweep_scanner_allows_legitimate_dashboard_references() -> None:
    assert _line_violation("server.run_dashboard_server(project, port, token)") is None
    assert _line_violation("# Historical dashboard sweeps used pgrep") is None
