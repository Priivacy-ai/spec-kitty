"""WP04 / C-CTX-4 regression: ``agent context._find_feature_directory``.

Proves the silent fallback to a wrong-but-plausible primary-checkout path has
been replaced by a structured :class:`ActionContextError`, and that a bare
``mid8`` handle resolves to the same directory as the full slug (F-001).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_runtime import ActionContextError
from specify_cli.cli.commands.agent.context import _find_feature_directory

pytestmark = [pytest.mark.fast]


def _seed_mission(tmp_path: Path, *, slug: str, mission_id: str) -> Path:
    mission_dir = tmp_path / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": slug}),
        encoding="utf-8",
    )
    return mission_dir


def test_mid8_resolves_same_as_full_slug(tmp_path: Path) -> None:
    """F-001: ``--mission <mid8>`` and ``--mission <slug>`` find the same dir."""
    mission_id = "01KTPKSTABCDEFGHJKMNPQRSTV"
    mid8 = mission_id[:8]
    slug = f"my-feature-{mid8}"
    expected = _seed_mission(tmp_path, slug=slug, mission_id=mission_id)

    via_slug = _find_feature_directory(tmp_path, tmp_path, explicit_mission=slug)
    via_mid8 = _find_feature_directory(tmp_path, tmp_path, explicit_mission=mid8)

    assert via_slug == expected
    assert via_mid8 == expected


def test_unresolvable_handle_raises_structured_error(tmp_path: Path) -> None:
    """C-CTX-4: an unknown handle raises a structured ActionContextError, not a
    silent fallback to ``kitty-specs/<handle>``."""
    (tmp_path / "kitty-specs").mkdir()
    with pytest.raises(ActionContextError) as excinfo:
        _find_feature_directory(tmp_path, tmp_path, explicit_mission="nope")
    assert excinfo.value.code == "FEATURE_CONTEXT_UNRESOLVED"


def test_ambiguous_handle_raises_structured_error(tmp_path: Path) -> None:
    """C-CTX-4 / C-009: an ambiguous handle raises MISSION_AMBIGUOUS_SELECTOR."""
    _seed_mission(tmp_path, slug="083-alpha", mission_id="01AAAAAAAAAAAAAAAAAAAAAAAA")
    _seed_mission(tmp_path, slug="083-beta", mission_id="01BBBBBBBBBBBBBBBBBBBBBBBB")
    with pytest.raises(ActionContextError) as excinfo:
        _find_feature_directory(tmp_path, tmp_path, explicit_mission="083")
    assert excinfo.value.code == "MISSION_AMBIGUOUS_SELECTOR"


def test_missing_handle_raises_structured_error(tmp_path: Path) -> None:
    """No handle → structured error (not a ValueError leaking to the operator)."""
    with pytest.raises(ActionContextError) as excinfo:
        _find_feature_directory(tmp_path, tmp_path)
    assert excinfo.value.code == "FEATURE_CONTEXT_UNRESOLVED"
