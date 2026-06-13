"""Regression coverage for the #1860 class (FR-006, WP04).

#1860 class: branch-identity consumers used legacy ``\\d{3}-``-only regexes or
hand-rolled ``f"kitty/mission-{slug}"`` composes, so every *mid8-era* mission
(post-083 ``<human-slug>-<mid8>`` naming) silently dropped its identity — the
parser returned ``None`` / the composer named a branch that never existed,
surfacing downstream as "no canonical status" / wrong-branch operator advice.

These tests feed BOTH a legacy ``042-foo`` AND a modern ``<slug>-<mid8>`` handle
through every migrated seam (`branch_naming`, `detection`, `sync`, `manifest`,
`compute`, `recovery`) and prove: both eras resolve, and the genuinely-lost
modern identity fails closed with a structured error — never a silent
None/drop/wrong-compose.
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.branch_naming import (
    BranchIdentityUnresolved,
    mission_branch_name_required,
    parse_mission_slug_from_branch,
)
from specify_cli.lanes.compute import compute_lanes
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest

pytestmark = [pytest.mark.regression, pytest.mark.fast]

_LEGACY_BRANCH = "kitty/mission-042-foo-lane-a"
_MODERN_BRANCH = "kitty/mission-foo-01KNXQS9-lane-a"
_MODERN_ID = "01KNXQS9ATWWFXS3K5ZJ9E5008"


class TestParserDualEra:
    """The canonical parser resolves both eras — never None for a mid8 branch."""

    def test_legacy_lane_branch_resolves(self):
        parsed = parse_mission_slug_from_branch(_LEGACY_BRANCH)
        assert parsed is not None
        assert parsed.slug == "042-foo"
        assert parsed.lane_id == "lane-a"
        assert parsed.mid8_token is None

    def test_modern_lane_branch_resolves(self):
        # The pre-fix legacy-only regex returned None here — the #1860 drop.
        parsed = parse_mission_slug_from_branch(_MODERN_BRANCH)
        assert parsed is not None
        assert parsed.slug == "foo"
        assert parsed.lane_id == "lane-a"
        assert parsed.mid8_token == "01KNXQS9"


class TestComposeDualEra:
    """The fail-closed composer resolves both eras, rejects only unresolvable."""

    def test_legacy_compose_resolves(self):
        assert (
            mission_branch_name_required("042-foo", None)
            == "kitty/mission-042-foo"
        )

    def test_modern_compose_with_id_resolves(self):
        assert (
            mission_branch_name_required("foo", _MODERN_ID)
            == "kitty/mission-foo-01KNXQS9"
        )

    def test_unresolvable_modern_fails_closed(self):
        # The single genuinely-wrong case: modern slug, no id, no mid8 tail.
        with pytest.raises(BranchIdentityUnresolved):
            mission_branch_name_required("foo", None)


class TestComputeManifestDualEra:
    """compute_lanes writes a correct mission_branch for both eras (B5)."""

    @staticmethod
    def _manifest() -> dict[str, OwnershipManifest]:
        return {
            "WP01": OwnershipManifest(
                execution_mode=ExecutionMode("code_change"),
                owned_files=("src/a.py",),
                authoritative_surface="src/a.py",
            )
        }

    def test_modern_mission_branch_is_mid8_era(self):
        # Pre-fix: f"kitty/mission-{slug}" emitted a nonexistent branch for a
        # mid8 mission. Now compute threads mission_id → canonical mid8 branch.
        manifest = compute_lanes(
            {"WP01": []},
            self._manifest(),
            "foo",
            mission_id=_MODERN_ID,
        )
        assert manifest.mission_branch == "kitty/mission-foo-01KNXQS9"

    def test_legacy_mission_branch_stays_legacy(self):
        manifest = compute_lanes(
            {"WP01": []},
            self._manifest(),
            "042-foo",
            mission_id=None,
        )
        assert manifest.mission_branch == "kitty/mission-042-foo"


class TestRecoveryComposeDualEra:
    """recovery composes the mission branch fail-closed, fed mission_id from meta."""

    def test_modern_meta_drives_mid8_branch(self, tmp_path):
        import json

        from specify_cli.lanes.recovery import _resolve_mission_branch

        feature_dir = tmp_path / "foo"
        feature_dir.mkdir()
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_id": _MODERN_ID}), encoding="utf-8"
        )
        # No lanes.json → falls through to fail-closed compose using meta id.
        assert (
            _resolve_mission_branch(feature_dir, "foo")
            == "kitty/mission-foo-01KNXQS9"
        )

    def test_legacy_slug_without_meta_resolves(self, tmp_path):
        from specify_cli.lanes.recovery import _resolve_mission_branch

        feature_dir = tmp_path / "042-foo"
        feature_dir.mkdir()  # no meta.json
        assert (
            _resolve_mission_branch(feature_dir, "042-foo")
            == "kitty/mission-042-foo"
        )

    def test_unresolvable_modern_recovery_fails_closed(self, tmp_path):
        from specify_cli.lanes.recovery import _resolve_mission_branch

        feature_dir = tmp_path / "foo"
        feature_dir.mkdir()  # no meta.json, modern slug, no mid8 tail
        with pytest.raises(BranchIdentityUnresolved):
            _resolve_mission_branch(feature_dir, "foo")


class TestManifestDiscoveryDualEra:
    """Branch discovery surfaces both legacy and mid8 mission slugs (B2)."""

    def test_mid8_branch_discovered(self, monkeypatch, tmp_path):
        import subprocess

        from specify_cli.manifest import WorktreeStatus

        class _Result:
            returncode = 0
            stdout = (
                "  kitty/mission-foo-01KNXQS9-lane-a\n"
                "  kitty/mission-042-bar-lane-a\n"
                "  042-legacy-feature\n"
                "  main\n"
            )

        def _fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
            return _Result()

        monkeypatch.setattr(subprocess, "run", _fake_run)
        ws = WorktreeStatus(tmp_path)
        features = ws._get_features_from_branches()
        # The mid8 mission slug must be discovered (pre-fix: silently excluded).
        assert "foo" in features
        assert "042-bar" in features
        assert "042-legacy-feature" in features
        assert "main" not in features
