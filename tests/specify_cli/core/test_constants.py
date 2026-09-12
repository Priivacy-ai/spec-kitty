"""Unit tests for shared path constants and the occurrence-map exception SSOT.

``is_occurrence_map_path`` is the single authority both ``kitty-specs/`` lane
guards consult for the DIRECTIVE_035 bulk-edit exception (#2980), so it is pinned
directly here rather than only through its two consumers.
"""

from __future__ import annotations

import pytest

from specify_cli.core.constants import (
    OCCURRENCE_MAP_FILENAME,
    is_occurrence_map_path,
)

pytestmark = [pytest.mark.fast]


@pytest.mark.parametrize(
    "path",
    [
        f"kitty-specs/057-feat/{OCCURRENCE_MAP_FILENAME}",
        "kitty-specs/my-mission-01ABCDEF/occurrence_map.yaml",
    ],
)
def test_permits_mission_occurrence_map(path: str) -> None:
    assert is_occurrence_map_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "kitty-specs/057-feat/spec.md",
        "kitty-specs/057-feat/plan.md",
        "kitty-specs/occurrence_map.yaml",  # not under a mission dir (2 segments)
        "kitty-specs/057-feat/nested/occurrence_map.yaml",  # too deep (4 segments)
        "src/occurrence_map.yaml",  # outside kitty-specs/
        "docs/kitty-specs/057/occurrence_map.yaml",  # kitty-specs not at root
        "occurrence_map.yaml",
        "",
    ],
)
def test_rejects_non_exception_paths(path: str) -> None:
    assert is_occurrence_map_path(path) is False
