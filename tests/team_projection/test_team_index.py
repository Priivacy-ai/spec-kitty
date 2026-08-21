"""Tests for specify_cli.team_projection.team_index (D1-T1).

Covers §4 N2 (stable ordering under filesystem-order shuffle) and N3
(stable cardinality: zero-WP missions and legacy/orphan pseudo-keys appear
exactly once, never omitted or duplicated).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.utils import write_wp

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str,
    mission_slug: str,
    mission_number: int | None,
    mission_type: str = "software-dev",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": mission_slug,
                "mission_number": mission_number,
                "mission_type": mission_type,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_build_team_index_shape(temp_repo: Path) -> None:
    from specify_cli.team_projection.team_index import build_team_index

    write_wp(temp_repo, "001-alpha", "planned", "WP01")
    _write_meta(
        temp_repo / "kitty-specs" / "001-alpha",
        mission_id="01ALPHA0000000000000000AA",
        mission_slug="001-alpha",
        mission_number=1,
    )
    _commit_all(temp_repo)

    index = build_team_index(temp_repo, require_clean=True)

    assert index.schema_ == "team_index/v1"
    assert len(index.missions) == 1
    entry = index.missions[0]
    assert entry.mission_slug == "001-alpha"
    assert entry.content_sha256.startswith("sha256:")


# --- N2: stable ordering under filesystem-order shuffle ----------------------


def test_build_team_index_order_independent_of_registry_insertion_order(
    temp_repo: Path, monkeypatch
) -> None:
    """``build_team_index`` must route through
    ``sort_missions_for_display``, never raw dict/insertion order — simulated
    here by handing it a mission registry inserted in the WRONG (reverse)
    order and confirming the output is still correctly sorted (§4 N2)."""
    from specify_cli.team_projection import team_index as team_index_mod

    for slug, number in (("001-alpha", 1), ("002-bravo", 2), ("003-charlie", 3)):
        write_wp(temp_repo, slug, "planned", "WP01")
        _write_meta(
            temp_repo / "kitty-specs" / slug,
            mission_id=f"01{slug[4:].upper():0<24}"[:26],
            mission_slug=slug,
            mission_number=number,
        )
    _commit_all(temp_repo)

    from specify_cli.dashboard.scanner import build_mission_registry

    real_registry = build_mission_registry(temp_repo)
    # Insert in the REVERSE key order (simulates a non-deterministic iterdir
    # walk that happened to enumerate directory entries backwards).
    reversed_registry = dict(reversed(list(real_registry.items())))
    assert list(reversed_registry.keys()) != list(real_registry.keys())

    monkeypatch.setattr(
        team_index_mod.scanner, "build_mission_registry", lambda _project_dir: reversed_registry
    )

    index = team_index_mod.build_team_index(temp_repo, require_clean=True)

    slugs_in_order = [entry.mission_slug for entry in index.missions]
    assert slugs_in_order == ["001-alpha", "002-bravo", "003-charlie"]


# --- N3: stable cardinality ---------------------------------------------------


def test_zero_wp_mission_appears_exactly_once_all_zero_summary(temp_repo: Path) -> None:
    from specify_cli.team_projection.team_index import build_team_index

    feature_dir = temp_repo / "kitty-specs" / "004-empty"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    _write_meta(feature_dir, mission_id="01EMPTY0000000000000000AA", mission_slug="004-empty", mission_number=4)
    _commit_all(temp_repo)

    index = build_team_index(temp_repo, require_clean=True)

    matches = [e for e in index.missions if e.mission_slug == "004-empty"]
    assert len(matches) == 1
    assert matches[0].summary == {} or all(v == 0 for v in matches[0].summary.values())


def test_legacy_pseudo_key_mission_appears_exactly_once(temp_repo: Path) -> None:
    """A mission dir with a numeric-prefix slug but no meta.json (legacy,
    pre-mission-id) resolves to a ``legacy:<slug>`` pseudo-key and appears
    exactly once."""
    from specify_cli.team_projection.team_index import build_team_index

    write_wp(temp_repo, "005-legacy-mission", "planned", "WP01")
    _commit_all(temp_repo)

    index = build_team_index(temp_repo, require_clean=True)

    matches = [e for e in index.missions if e.mission_slug == "005-legacy-mission"]
    assert len(matches) == 1


# --- Renata review (D1-T1 APPROVE w/ findings), MEDIUM: mission_slug path-
# segment guard. D1.md §3.1 declares specify_cli.core.paths
# (assert_safe_path_segment) as part of D1's allowed import surface, but
# nothing in team_projection/ called it before this fix -- resolve_feature_dir_
# for_mission_slug joined an unvalidated mission_slug straight into a
# filesystem path. mission_slug is always feature_dir.name today (structurally
# "/"-free), but a real mission directory COULD be named with non-ASCII or a
# leading dot; nothing caught that before this guard. ------------------------


def test_resolve_feature_dir_for_mission_slug_rejects_leading_dot(temp_repo: Path) -> None:
    from specify_cli.team_projection.team_index import resolve_feature_dir_for_mission_slug

    with pytest.raises(ValueError, match="safe path segment"):
        resolve_feature_dir_for_mission_slug(temp_repo, ".hidden-mission")


def test_resolve_feature_dir_for_mission_slug_rejects_non_ascii(temp_repo: Path) -> None:
    from specify_cli.team_projection.team_index import resolve_feature_dir_for_mission_slug

    with pytest.raises(ValueError, match="safe path segment"):
        resolve_feature_dir_for_mission_slug(temp_repo, "café-mission")


def test_resolve_feature_dir_for_mission_slug_accepts_normal_slug(temp_repo: Path) -> None:
    """The guard must not reject the ordinary, already-registered case --
    only the hostile-format one (regression guard alongside the two above)."""
    from specify_cli.team_projection.team_index import resolve_feature_dir_for_mission_slug

    write_wp(temp_repo, "001-alpha", "planned", "WP01")
    _commit_all(temp_repo)

    resolved = resolve_feature_dir_for_mission_slug(temp_repo, "001-alpha")
    assert resolved == temp_repo / "kitty-specs" / "001-alpha"
