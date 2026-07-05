"""Unit tests for `_warrants_legacy_warning` (#2351).

The topology-aware warning-only classifier is deliberately SEPARATE from the
shared `_is_legacy_mission()` routing predicate (C-005): it reads the stored
`MissionTopology` (via the non-deriving `stored_topology_from_meta`, C-001)
plus the `flattened` provenance flag to decide *only* whether the
once-per-mission legacy-topology warning fires.

Spec source: FR-001, FR-002, FR-003, FR-004, FR-005; C-001, C-005.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.coordination.transaction import _warrants_legacy_warning

pytestmark = pytest.mark.fast


def _write_meta(feature_dir: Path, meta: dict[str, object]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


def _feature_dir(repo_root: Path, mission_slug: str, mid8: str) -> Path:
    return repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"


@pytest.mark.parametrize(
    ("meta_extra", "expected"),
    [
        pytest.param({}, True, id="genuine-legacy-no-topology-no-coord"),
        pytest.param({"topology": "single_branch"}, False, id="single_branch"),
        pytest.param({"topology": "lanes"}, False, id="lanes"),
        pytest.param({"flattened": True}, False, id="flattened"),
        pytest.param(
            {
                "topology": "coord",
                "coordination_branch": "kitty/mission-classifier-mission-coord",
            },
            False,
            id="coord",
        ),
        pytest.param(
            {
                "topology": "lanes_with_coord",
                "coordination_branch": "kitty/mission-classifier-mission-coord",
            },
            False,
            id="lanes_with_coord",
        ),
        pytest.param(
            {"topology": "not-a-real-shape"}, True, id="malformed-topology-warns"
        ),
    ],
)
def test_warrants_legacy_warning_matrix(
    repo_root: Path,
    meta_extra: dict[str, object],
    expected: bool,
) -> None:
    mission_slug = "classifier-mission"
    mid8 = "01KCLASS"
    meta: dict[str, object] = {
        "mission_id": "01KCLASSZZZZZZZZZZZZZZZZZZ",
        "mission_slug": mission_slug,
        "mid8": mid8,
        **meta_extra,
    }
    _write_meta(_feature_dir(repo_root, mission_slug, mid8), meta)

    assert _warrants_legacy_warning(repo_root, mission_slug, mid8) is expected


def test_warrants_legacy_warning_missing_meta_returns_false(repo_root: Path) -> None:
    """No `meta.json` at all is treated as new-topology (never warn) — the
    same missing-meta contract `_is_legacy_mission()` already has."""
    assert _warrants_legacy_warning(repo_root, "ghost-mission", "01KGHOST1") is False


def test_warrants_legacy_warning_malformed_json_returns_false(repo_root: Path) -> None:
    """A corrupt `meta.json` degrades to "do not warn" — the classifier is
    not the seam responsible for surfacing meta corruption."""
    mission_slug = "corrupt-mission"
    mid8 = "01KCORRUP"
    feature_dir = _feature_dir(repo_root, mission_slug, mid8)
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text("{not valid json", encoding="utf-8")

    assert _warrants_legacy_warning(repo_root, mission_slug, mid8) is False
