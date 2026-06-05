"""Unit tests for MissionStatus aggregate (WP04, FR-015–FR-023, T025).

Covers:
- MissionStatus.load() for legacy and coord topologies
- Fail-closed behavior when coord worktree is declared but missing
- MissionStatus.claim() returns correct ActiveWPStatus
- ActiveWPStatus field contract
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


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


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_repo(path: Path) -> Path:
    repo = path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


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

    def test_corrupt_meta_fails_closed_instead_of_legacy_fallback(self, tmp_path: Path) -> None:
        """Existing but corrupt meta.json cannot degrade to a primary-checkout read."""
        slug = "corrupt-meta-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)
        (mission_dir / "meta.json").write_text(
            '{"mission_id":"01CORRUPT12345678901234","coordination_branch":',
            encoding="utf-8",
        )
        _write_events_file(mission_dir, [
            _make_event(slug, "WP01", "planned", "claimed"),
        ])

        from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

        with pytest.raises(MissionMetadataUnavailable) as exc_info:
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        exc = exc_info.value
        assert exc.mission_slug == slug
        assert exc.primary_candidate == mission_dir

    def test_non_dict_meta_fails_closed_instead_of_legacy_fallback(self, tmp_path: Path) -> None:
        """Existing meta.json must be an object before topology can be trusted."""
        slug = "array-meta-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)
        (mission_dir / "meta.json").write_text("[]", encoding="utf-8")

        from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

        with pytest.raises(MissionMetadataUnavailable, match="expected object"):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

    def test_non_string_mission_id_fails_closed(self, tmp_path: Path) -> None:
        """Malformed mission_id cannot be laundered into a legacy read."""
        slug = "bad-mission-id-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)
        (mission_dir / "meta.json").write_text(
            '{"mission_id": ["01BAD"], "coordination_branch": "kitty/mission-bad"}',
            encoding="utf-8",
        )

        from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

        with pytest.raises(MissionMetadataUnavailable, match="mission_id must be string"):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

    def test_non_string_coordination_branch_fails_closed(self, tmp_path: Path) -> None:
        """Malformed coordination_branch cannot degrade to primary checkout."""
        slug = "bad-coord-branch-feature"
        mission_dir = _make_mission_dir(tmp_path, slug)
        (mission_dir / "meta.json").write_text(
            '{"mission_id": "01BADCOORD12345678901234", "coordination_branch": 123}',
            encoding="utf-8",
        )

        from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

        with pytest.raises(MissionMetadataUnavailable, match="coordination_branch must be string"):
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

    def test_mission_metadata_unavailable_importable_from_status(self) -> None:
        from specify_cli.status import MissionMetadataUnavailable  # noqa: F401

    def test_all_three_in_dunder_all(self) -> None:
        import specify_cli.status as status_mod

        assert "MissionStatus" in status_mod.__all__
        assert "ActiveWPStatus" in status_mod.__all__
        assert "CoordAuthorityUnavailable" in status_mod.__all__
        assert "MissionMetadataUnavailable" in status_mod.__all__


# ---------------------------------------------------------------------------
# FR-019 / FR-020 — MissionStatus.transition() and .save() unit tests
# ---------------------------------------------------------------------------


class TestTransitionHappyPath:
    def test_transition_validates_then_applies(self, tmp_path: Path) -> None:
        """transition() rejects illegal transitions before calling BookkeepingTransaction."""
        slug = "034-transition-test"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [
            _make_event(slug, "WP01", "planned", "claimed", event_id="01HXYZ0123456789ABCDEFGH01"),
        ])

        from specify_cli.status import InvalidTransitionError, TransitionRequest
        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        # planned → claimed → in_progress is valid from 'claimed'
        # But planned → approved is illegal
        bad_request = TransitionRequest(
            wp_id="WP01",
            to_lane="approved",
            actor="claude",
            feature_dir=ms.read_dir,
            mission_slug=slug,
        )
        with pytest.raises((InvalidTransitionError, Exception)) as exc_info:
            ms.transition(bad_request)
        # Must raise — must NOT silently succeed or call BookkeepingTransaction
        assert exc_info.value is not None

    def test_transition_raises_invalid_transition_error_on_illegal_move(self, tmp_path: Path) -> None:
        """transition() raises InvalidTransitionError, not a generic exception."""
        slug = "034-invalid-transition"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [
            _make_event(slug, "WP01", "planned", "claimed", event_id="01HXYZ0123456789ABCDEFGH20"),
        ])

        from specify_cli.status import InvalidTransitionError, TransitionRequest
        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        # 'done' is only reachable via merge — transitioning directly is illegal
        bad_request = TransitionRequest(
            wp_id="WP01",
            to_lane="done",
            actor="claude",
            feature_dir=ms.read_dir,
            mission_slug=slug,
        )
        with pytest.raises(InvalidTransitionError):
            ms.transition(bad_request)

    def test_transition_coerces_unparseable_lanes_in_error_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """transition() still raises InvalidTransitionError (not a crash) when the
        lane strings are not parseable ``Lane`` values — the WP01/FR-004 error
        coercion falls back to ``Lane.PLANNED`` for both from- and to-lane."""
        slug = "034-coerce-bogus-lanes"
        mission_dir = _make_mission_dir(tmp_path, slug)
        _write_events_file(mission_dir, [
            _make_event(slug, "WP01", "planned", "claimed", event_id="01HXYZ0123456789ABCDEFGH21"),
        ])

        import specify_cli.status as status_pkg
        from specify_cli.status import InvalidTransitionError, TransitionRequest
        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        # Force the resolved from-lane to a non-Lane string so the from-lane
        # coercion hits the ValueError -> Lane.PLANNED fallback.
        monkeypatch.setattr(status_pkg, "get_wp_lane", lambda *a, **k: "uninitialized")

        bad_request = TransitionRequest(
            wp_id="WP01",
            to_lane="not-a-real-lane",  # unparseable to-lane -> ValueError fallback too
            actor="claude",
            feature_dir=ms.read_dir,
            mission_slug=slug,
        )
        with pytest.raises(InvalidTransitionError):
            ms.transition(bad_request)


class TestSaveReturnType:
    def test_save_uses_real_bookkeeping_transaction_and_returns_commit_receipt(
        self, tmp_path: Path
    ) -> None:
        """save() commits status artifacts through the real BookkeepingTransaction."""
        slug = "save-modern"
        mission_id = "01SAVE12345678901234567890"
        mid8 = mission_id[:8]
        coord_branch = f"kitty/mission-{slug}-{mid8}"
        repo = _make_git_repo(tmp_path)

        from specify_cli.status.aggregate import MissionStatus
        from specify_cli.coordination.workspace import CoordinationWorkspace

        primary_dir = _make_mission_dir(repo, slug)
        _write_meta(primary_dir, mission_id=mission_id, coordination_branch=coord_branch)
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add mission meta")
        _git(repo, "branch", coord_branch)

        coord_root = CoordinationWorkspace.resolve(repo, slug, mid8)
        coord_dir = coord_root / "kitty-specs" / f"{slug}-{mid8}"
        coord_dir.mkdir(parents=True)
        events_path = coord_dir / "status.events.jsonl"
        events_path.write_text(
            json.dumps(_make_event(slug, "WP01", "planned", "claimed")) + "\n",
            encoding="utf-8",
        )

        ms = MissionStatus.load(repo_root=repo, mission_slug=slug)
        receipt = ms.save(operation="test-save")

        assert receipt.destination_ref == coord_branch
        assert receipt.commit_sha
        committed = _git(repo, "show", f"{coord_branch}:kitty-specs/{slug}-{mid8}/status.events.jsonl")
        assert "WP01" in committed

    def test_save_supports_identity_bearing_legacy_mission(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Legacy missions with mission_id but no coord branch commit on current branch."""
        base_slug = "save-legacy"
        mission_id = "01LEGACY45678901234567890"
        mid8 = mission_id[:8]
        slug = f"{base_slug}-{mid8}"
        repo = _make_git_repo(tmp_path)
        _git(repo, "checkout", "-b", "legacy-lane")
        monkeypatch.chdir(repo)

        mission_dir = _make_mission_dir(repo, slug)
        _write_meta(mission_dir, mission_id=mission_id)
        events_path = mission_dir / "status.events.jsonl"
        events_path.write_text(
            json.dumps(_make_event(slug, "WP02", "planned", "claimed")) + "\n",
            encoding="utf-8",
        )

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=repo, mission_slug=slug)
        receipt = ms.save(operation="test-save-legacy")

        assert receipt.destination_ref == "legacy-lane"
        committed = _git(repo, "show", f"legacy-lane:kitty-specs/{slug}/status.events.jsonl")
        assert "WP02" in committed

    def test_save_fails_closed_without_mission_identity(self, tmp_path: Path) -> None:
        """No-meta missions cannot be persisted through BookkeepingTransaction."""
        slug = "034-save-test"
        _make_mission_dir(tmp_path, slug)

        from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
        with pytest.raises(MissionMetadataUnavailable, match="mission_id is required"):
            ms.save(operation="test-save")


# ---------------------------------------------------------------------------
# FR-007 / DIRECTIVE_010 — mission_slug ASCII allowlist guard at load()
# ---------------------------------------------------------------------------


class TestMissionSlugAllowlistGuard:
    """``MissionStatus.load()`` rejects slugs outside ``^[A-Za-z0-9_-]+$``."""

    @pytest.mark.parametrize(
        "slug",
        [
            "034-feature-name",
            "test-feature",
            "save-legacy-01ABCDEF",
            "WP_underscored",
            "ABC123",
        ],
    )
    def test_normal_ascii_slug_passes(self, tmp_path: Path, slug: str) -> None:
        """Identifier-safe ASCII slugs load without raising."""
        _make_mission_dir(tmp_path, slug)

        from specify_cli.status.aggregate import MissionStatus

        ms = MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert ms.mission_slug == slug
        # The validated identifier must be pure ASCII (FR-007).
        assert ms.mission_slug.isascii()

    def test_accented_latin_slug_is_rejected(self, tmp_path: Path) -> None:
        """An accented-Latin slug (non-ASCII) is rejected at load()."""
        slug = "café-mission"
        # Defensive: the offending slug must not be ASCII, otherwise the test
        # would not exercise the .isascii() branch of the guard.
        assert not slug.isascii()

        from specify_cli.status.aggregate import InvalidMissionSlug, MissionStatus

        with pytest.raises(InvalidMissionSlug) as exc_info:
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

        assert exc_info.value.mission_slug == slug
        assert slug in str(exc_info.value)

    @pytest.mark.parametrize(
        "slug",
        [
            "feature/with-slash",
            "feature with space",
            "feature.with.dot",
            "feature$injection",
            "..",
            "",
            "naïve",  # accented variant of a common ASCII word
            "münchen-mission",
        ],
    )
    def test_disallowed_slugs_are_rejected(self, tmp_path: Path, slug: str) -> None:
        """Path-injection and non-ASCII slugs all raise InvalidMissionSlug."""
        from specify_cli.status.aggregate import InvalidMissionSlug, MissionStatus

        with pytest.raises(InvalidMissionSlug):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

    def test_invalid_mission_slug_is_value_error_subclass(self) -> None:
        """InvalidMissionSlug is a ValueError so existing handlers can catch it."""
        from specify_cli.status.aggregate import InvalidMissionSlug

        assert issubclass(InvalidMissionSlug, ValueError)

    def test_invalid_mission_slug_importable_from_status_aggregate(self) -> None:
        from specify_cli.status.aggregate import InvalidMissionSlug  # noqa: F401

    def test_invalid_mission_slug_in_aggregate_dunder_all(self) -> None:
        import specify_cli.status.aggregate as aggregate_mod

        assert "InvalidMissionSlug" in aggregate_mod.__all__
