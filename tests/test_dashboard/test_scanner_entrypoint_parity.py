"""Baseline parity test for the scanner's two mission-listing entry points.

Establishes the safety net for the registry refactor in WP02-WP07. If
this test starts failing after a registry change, the registry refactor
diverged scan_all_features and build_mission_registry; revert the change
and investigate.

Owned by WP01 of mission mission-registry-and-api-boundary-doctrine-01KQPDBB.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """Build a minimal fixture project with 2 missions."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    for mid8, slug, ulid in [
        ("01ABCDEF", "mission-alpha-01ABCDEF", "01ABCDEFGHJKMNPQRSTVWXYZ00"),
        ("01GHIJKL", "mission-beta-01GHIJKL", "01GHIJKLMNPQRSTVWXYZ00ABCD"),
    ]:
        feature_dir = tmp_path / "kitty-specs" / slug
        (feature_dir / "tasks").mkdir(parents=True)
        (feature_dir / "spec.md").write_text(f"# {slug}\n", encoding="utf-8")
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {
                    "mission_id": ulid,
                    "mission_slug": slug,
                    "friendly_name": slug.replace("-", " ").title(),
                    "mission_number": None,
                    "mission_type": "software-dev",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return tmp_path


def test_scan_and_registry_agree_on_mission_id_set(fixture_project: Path) -> None:
    """Both readers must surface the same set of mission_ids for the same fixture."""
    from specify_cli.dashboard.scanner import build_mission_registry, scan_all_features

    features = scan_all_features(fixture_project)
    registry = build_mission_registry(fixture_project)

    feature_ids = {
        f["meta"].get("mission_id")
        for f in features
        if f.get("meta", {}).get("mission_id")
    }
    registry_ids = set(registry.keys())

    assert feature_ids == registry_ids, (
        f"scan_all_features and build_mission_registry disagree on mission_id set:\n"
        f"  scan_all_features only: {feature_ids - registry_ids}\n"
        f"  build_mission_registry only: {registry_ids - feature_ids}\n"
        "If this fails on a fresh project: scanner divergence is a pre-existing bug."
    )


def test_scan_and_registry_agree_on_mission_slug_set(fixture_project: Path) -> None:
    """Same assertion at the slug level."""
    from specify_cli.dashboard.scanner import build_mission_registry, scan_all_features

    features = scan_all_features(fixture_project)
    registry = build_mission_registry(fixture_project)

    feature_slugs = {f["id"] for f in features}
    registry_slugs = {
        entry["mission_slug"]
        for entry in registry.values()
        if entry.get("mission_slug")
    }

    assert feature_slugs == registry_slugs, (
        f"slug-set divergence: scan-only={feature_slugs - registry_slugs}, "
        f"registry-only={registry_slugs - feature_slugs}"
    )
