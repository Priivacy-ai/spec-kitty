"""Unit tests for MissionStatus aggregate (WP04, FR-015–FR-023, T025).

Covers:
- MissionStatus.load() for legacy and coord topologies
- Fail-closed behavior when coord worktree is declared but missing
- MissionStatus.claim() returns correct ActiveWPStatus
- ActiveWPStatus field contract
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mission_dir(root: Path, slug: str) -> Path:
    """Create a minimal legacy mission directory in tmp_path."""
    mission_dir = root / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    return mission_dir


def _write_meta(mission_dir: Path, mission_id: str | None = None, coordination_branch: str | None = None) -> None:
    """Write a meta.json to a mission directory."""
    meta: dict = {}
    if mission_id is not None:
        meta["mission_id"] = mission_id
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_events_file(mission_dir: Path, events: list[dict] | None = None) -> None:
    """Create a status.events.jsonl file with given events (or empty)."""
    lines = ""
    if events:
        lines = "\n".join(json.dumps(e) for e in events)
    (mission_dir / "status.events.jsonl").write_text(lines, encoding="utf-8")


def _make_event(
    mission_slug: str,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    event_id: str = "01HXYZ0123456789ABCDEFGHXX",
) -> dict:
    return {
        "event_id": event_id,
        "mission_slug": mission_slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": "2026-06-01T12:00:00+00:00",
        "actor": "claude",
        "force": False,
        "execution_mode": "worktree",
        "evidence": None,
        "reason": None,
        "review_ref": None,
        "feature_slug": mission_slug,
    }


# ---------------------------------------------------------------------------
# T025.1 — MissionStatus.load() with legacy mission (no coord branch)
# ---------------------------------------------------------------------------


class TestLoadLegacyMission:
    def test_topology_is_legacy_when_no_meta(self, tmp_path: Path) -> None:
        slug = "034-test-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert ms.topology == "legacy"
        assert ms.read_dir == mission_dir
        assert ms.mission_id is None
        assert ms.mid8 == ""

    def test_topology_is_legacy_when_meta_has_no_coord_branch(self, tmp_path: Path) -> None:
        slug = "034-test-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_meta(mission_dir, mission_id="01KT6HVH12345678901234AB")

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert ms.topology == "legacy"
        assert ms.read_dir == mission_dir
        assert ms.mission_id == "01KT6HVH12345678901234AB"
        assert ms.mid8 == "01KT6HVH"

    def test_topology_is_legacy_when_no_coord_worktree_and_no_coord_declared(self, tmp_path: Path) -> None:
        slug = "test-feature"
        _make_mission_dir(tmp_path, slug)

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert ms.topology == "legacy"
        assert ms.mission_slug == slug


# ---------------------------------------------------------------------------
# T025.2 — MissionStatus.load() with coordination topology
# ---------------------------------------------------------------------------


class TestLoadCoordMission:
    def test_topology_is_coordination_when_coord_worktree_exists(self, tmp_path: Path) -> None:
        """When the coord worktree exists on disk, topology should be 'coordination'."""
        slug = "test-feature"
        mission_id = "01TESTKITTY12345678901234"
        mid8 = mission_id[:8]

        # Create primary mission dir with coord-branch declaration
        primary_mission_dir = _make_mission_dir(tmp_path, slug)
        _write_meta(primary_mission_dir, mission_id=mission_id, coordination_branch=f"kitty/mission-{slug}-{mid8}")

        # Create the coord worktree directory (simulates worktree materialisation)
        # The coord worktree path is: .worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/
        coord_dir_name = f"{slug}-{mid8}"
        coord_worktree_root = tmp_path / ".worktrees" / f"{coord_dir_name}-coord"
        coord_mission_dir = coord_worktree_root / "kitty-specs" / coord_dir_name
        coord_mission_dir.mkdir(parents=True)

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert ms.topology == "coordination"
        assert ms.read_dir == coord_mission_dir
        assert ms.mission_id == mission_id
        assert ms.mid8 == mid8


# ---------------------------------------------------------------------------
# T025.3 — Fail-closed: coord declared but worktree missing
# ---------------------------------------------------------------------------


class TestLoadCoordUnavailableFailsClosed:
    def test_raises_coord_authority_unavailable_when_coord_missing(self, tmp_path: Path) -> None:
        """coord-topology declared but coord path not on disk → raises, does NOT fall back."""
        slug = "test-feature"
        mission_id = "01TESTKITTY12345678901234"

        # Primary mission dir with coord declaration, but NO coord worktree
        primary_mission_dir = _make_mission_dir(tmp_path, slug)
        _write_meta(
            primary_mission_dir,
            mission_id=mission_id,
            coordination_branch=f"kitty/mission-{slug}-{mission_id[:8]}",
        )

        from specify_cli.status.aggregate import CoordAuthorityUnavailable, MissionStatus

        with pytest.raises(CoordAuthorityUnavailable) as exc_info:
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        exc = exc_info.value
        assert exc.mission_slug == slug
        assert "coordination worktree unavailable" in str(exc).lower()

    def test_does_not_fall_back_to_primary_checkout(self, tmp_path: Path) -> None:
        """No silent fallback: coord-declared mission without coord worktree raises."""
        slug = "stale-feature"
        mission_id = "01STALEKITTY1234567890AB"

        # Primary has events (potentially stale)
        primary_dir = _make_mission_dir(tmp_path, slug)
        _write_meta(
            primary_dir,
            mission_id=mission_id,
            coordination_branch=f"kitty/mission-{slug}-{mission_id[:8]}",
        )
        _write_events_file(primary_dir, [
            _make_event(slug, "WP01", "planned", "claimed"),
        ])

        from specify_cli.status.aggregate import CoordAuthorityUnavailable, MissionStatus

        # Even though primary has events, we MUST raise — not silently use primary
        with pytest.raises(CoordAuthorityUnavailable):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)


# ---------------------------------------------------------------------------
# T025.4 — MissionStatus.claim() returns correct lane
# ---------------------------------------------------------------------------


class TestClaimReturnsCorrectLane:
    def test_claim_returns_active_wp_status_for_known_wp(self, tmp_path: Path) -> None:
        slug = "034-claim-test"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [
            _make_event(slug, "WP01", "planned", "claimed", event_id="01HXYZ0123456789ABCDEFGH01"),
            _make_event(slug, "WP01", "claimed", "in_progress", event_id="01HXYZ0123456789ABCDEFGH02"),
        ])

        from specify_cli.status import Lane
        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        wp_status = ms.claim("WP01")

        assert wp_status.wp_id == "WP01"
        assert wp_status.current_lane == Lane.IN_PROGRESS
        assert wp_status.last_event is not None
        assert wp_status.last_event.wp_id == "WP01"

    def test_claim_current_lane_matches_last_event_to_lane(self, tmp_path: Path) -> None:
        slug = "034-lane-verify"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [
            _make_event(slug, "WP02", "planned", "claimed", event_id="01HXYZ0123456789ABCDEFGH10"),
        ])

        from specify_cli.status import Lane
        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        wp_status = ms.claim("WP02")

        assert wp_status.current_lane == Lane.CLAIMED

    def test_claim_no_events_returns_uninitialized_string(self, tmp_path: Path) -> None:
        """When a WP has no events, get_wp_lane returns 'uninitialized'."""
        slug = "034-empty-wp"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [])  # empty events

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        wp_status = ms.claim("WP99")

        # 'uninitialized' is the sentinel returned by get_wp_lane for unknown WPs
        assert str(wp_status.current_lane) == "uninitialized"
        assert wp_status.last_event is None


# ---------------------------------------------------------------------------
# T025.5 — ActiveWPStatus field contract
# ---------------------------------------------------------------------------


class TestActiveWPStatusFields:
    def test_active_wp_status_is_frozen(self) -> None:
        from specify_cli.status import Lane
        from specify_cli.status.aggregate import ActiveWPStatus

        aws = ActiveWPStatus(wp_id="WP01", current_lane=Lane.PLANNED, last_event=None)
        with pytest.raises((AttributeError, TypeError)):
            aws.wp_id = "WP02"  # type: ignore[misc]

    def test_active_wp_status_has_required_fields(self) -> None:
        from specify_cli.status import Lane
        from specify_cli.status.aggregate import ActiveWPStatus

        aws = ActiveWPStatus(wp_id="WP01", current_lane=Lane.IN_PROGRESS, last_event=None)
        assert aws.wp_id == "WP01"
        assert aws.current_lane == Lane.IN_PROGRESS
        assert aws.last_event is None

    def test_mission_status_is_frozen(self, tmp_path: Path) -> None:
        slug = "034-frozen-test"
        _make_mission_dir(tmp_path, slug)

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        with pytest.raises((AttributeError, TypeError)):
            ms.mission_slug = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T025.6 — Importability from status façade
# ---------------------------------------------------------------------------


class TestStatusFacadeExports:
    def test_mission_status_importable_from_status(self) -> None:
        from specify_cli.status import MissionStatus  # noqa: F401

    def test_active_wp_status_importable_from_status(self) -> None:
        from specify_cli.status import ActiveWPStatus  # noqa: F401

    def test_coord_authority_unavailable_importable_from_status(self) -> None:
        from specify_cli.status import CoordAuthorityUnavailable  # noqa: F401

    def test_all_three_in_dunder_all(self) -> None:
        import specify_cli.status as status_mod

        assert "MissionStatus" in status_mod.__all__
        assert "ActiveWPStatus" in status_mod.__all__
        assert "CoordAuthorityUnavailable" in status_mod.__all__
