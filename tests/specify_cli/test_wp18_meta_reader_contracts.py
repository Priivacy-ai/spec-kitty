"""Live consumer tests for the WP18 meta-reader migration (FR-006c).

The canonical reader contract is covered in ``test_mission_metadata.py``.
This module retains only observable ``verify_enhanced`` consumer behavior.

Production-shaped identity
---------------------------
ULID: 01KVRJ6PQ7XB2M9K4D8N3FZ0YT  (26 chars)
mid8: 01KVRJ6P                       (8 chars)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from specify_cli.mission_metadata import META_FILENAME, write_meta

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped identity (testing-principles — never a short placeholder)
_MISSION_ID = "01KVRJ6PQ7XB2M9K4D8N3FZ0YT"
_MID8 = _MISSION_ID[:8]  # "01KVRJ6P"
_MISSION_SLUG = f"single-authority-topology-cleanup-{_MID8}"


def _valid_meta(mission_type: str = "software-dev") -> dict[str, Any]:
    """A complete, production-shaped meta.json mapping."""
    return {
        "mission_id": _MISSION_ID,
        "mission_number": None,
        "slug": _MISSION_SLUG,
        "mission_slug": _MISSION_SLUG,
        "friendly_name": "Single-Authority Topology Cleanup",
        "mission_type": mission_type,
        "target_branch": "feat/single-authority-topology-cleanup",
        "created_at": "2026-06-23T07:37:56+00:00",
    }


def _seed_valid(feature_dir: Path, mission_type: str = "software-dev") -> dict[str, Any]:
    """Write a valid meta.json via the production write seam; return its dict."""
    meta = _valid_meta(mission_type)
    write_meta(feature_dir, meta)
    return meta


def _seed_malformed(feature_dir: Path) -> None:
    """Write a genuinely un-parseable meta.json (truncated JSON, not empty).

    An empty file would only hit the missing-content branch; ``{"a":`` is
    truncated JSON that ``json.loads`` cannot parse — this is the malformed arm.
    """
    (feature_dir / META_FILENAME).write_text('{"a":', encoding="utf-8")


# ===========================================================================
# verify_enhanced._resolve_mission_from_feature: lazy import + broad except
# removed → module-level load_meta_or_empty (FR-006c campsite)
#
# Observable contract: the *function return value* (str | None) given
# different meta.json states.
# ===========================================================================


def test_resolve_mission_from_feature_returns_none_on_missing_meta(
    tmp_path: Path,
) -> None:
    """No meta.json → function returns None (missing arm)."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    result = _resolve_mission_from_feature(tmp_path)
    assert result is None


def test_resolve_mission_from_feature_returns_none_on_malformed_meta(
    tmp_path: Path,
) -> None:
    """Malformed meta.json → function returns None — never raises (malformed arm).

    Previously the broad ``except Exception: pass`` masked this; now
    ``load_meta_or_empty`` guarantees the silent-empty contract, and
    ``if meta:`` treats ``{}`` as falsy → returns None.
    """
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    _seed_malformed(tmp_path)
    result = _resolve_mission_from_feature(tmp_path)
    assert result is None


def test_resolve_mission_from_feature_returns_mission_type(tmp_path: Path) -> None:
    """Valid meta.json with mission_type → function returns the mission_type string."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    _seed_valid(tmp_path, mission_type="research")
    result = _resolve_mission_from_feature(tmp_path)
    assert result == "research"


def test_resolve_mission_from_feature_falls_back_to_legacy_mission_field(
    tmp_path: Path,
) -> None:
    """Legacy meta.json with ``mission`` key (no mission_type) → returns that value."""
    from specify_cli.verify_enhanced import _resolve_mission_from_feature

    meta = _valid_meta()
    del meta["mission_type"]
    meta["mission"] = "documentation"
    write_meta(tmp_path, meta, validate=False)

    result = _resolve_mission_from_feature(tmp_path)
    assert result == "documentation"
