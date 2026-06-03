"""Ratchets for issue #1681 raw mission-spec path remediation."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


pytestmark = [pytest.mark.architectural]

_SRC_ROOT = Path("src")
_RAW_PATTERN = re.compile(r'"kitty-specs"|"kitty\.specs"|kitty_specs')
_SEMANTIC_PATTERN = re.compile(r"/ KITTY_SPECS_DIR /")

_RAW_EXEMPT_PARTS = (
    "status/",
    "core/execution_context.py",
    "upgrade/migrations/",
    "core/constants.py",
    "core/paths.py",
    "missions/_read_path_resolver.py",
    "migration/",
)

_SEMANTIC_CONSTRUCTOR_FILES = {
    Path("src/specify_cli/core/git_ops.py"),
    Path("src/specify_cli/core/mission_creation.py"),
    Path("src/specify_cli/core/project_resolver.py"),
    Path("src/specify_cli/core/worktree.py"),
    Path("src/specify_cli/core/worktree_topology.py"),
    Path("src/specify_cli/coordination/status_transition.py"),
    Path("src/specify_cli/coordination/transaction.py"),
    Path("src/specify_cli/events/decision_log.py"),
    Path("src/specify_cli/mission_read_path.py"),
    Path("src/specify_cli/missions/feature_dir_resolver.py"),
    Path("src/specify_cli/workspace/root_resolver.py"),
}


def _active_source_files() -> list[Path]:
    return sorted(_SRC_ROOT.rglob("*.py"))


def _is_raw_exempt(path: Path) -> bool:
    normalized = path.as_posix()
    return any(part in normalized for part in _RAW_EXEMPT_PARTS)


def test_no_raw_mission_spec_path_strings_outside_exempt_owners() -> None:
    offenders: list[str] = []
    for path in _active_source_files():
        if _is_raw_exempt(path):
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _RAW_PATTERN.search(line):
                offenders.append(f"{path}:{line_no}: {line.strip()}")

    assert offenders == []


def test_constant_based_mission_spec_path_construction_stays_in_constructor_files() -> None:
    offenders: list[str] = []
    for path in _active_source_files():
        if path in _SEMANTIC_CONSTRUCTOR_FILES or _is_raw_exempt(path):
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _SEMANTIC_PATTERN.search(line):
                offenders.append(f"{path}:{line_no}: {line.strip()}")

    assert offenders == []
