"""Per-reader regression pins for the rc3 M5 runtime READ converters (WP02).

Each converted reader resolves the mission type through the one shared
``read_mission_type`` seam: the canonical ``mission_type`` field only (no legacy
``mission`` fallback, FR-002) and no silent ``software-dev`` default (FR-003).
The dashboard pin is the FR-005 visible change (AC-1).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

pytestmark = [pytest.mark.unit]


def _write_meta(feature_dir: Path, meta: dict[str, object]) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir


class TestFeatureDirReaders:
    """diagnostics + verify_enhanced ``_resolve_mission_from_feature``."""

    @pytest.mark.parametrize(
        "module",
        ["specify_cli.dashboard.diagnostics", "specify_cli.verify_enhanced"],
    )
    def test_canonical_resolves_legacy_and_typeless_do_not(self, module: str, tmp_path: Path) -> None:
        import importlib

        resolve = importlib.import_module(module)._resolve_mission_from_feature

        assert resolve(_write_meta(tmp_path / "canonical", {"mission_type": "research"})) == "research"
        # legacy `mission`-only no longer resolves (FR-002)
        assert resolve(_write_meta(tmp_path / "legacy", {"mission": "software-dev"})) is None
        # typeless yields neutral None, never software-dev (FR-003)
        assert resolve(_write_meta(tmp_path / "typeless", {})) is None


class TestMissionMetadataReadPath:
    """``resolve_mission_identity`` read path drops legacy + default."""

    def test_typeless_meta_resolves_empty_not_software_dev(self, tmp_path: Path) -> None:
        from specify_cli.mission_metadata import resolve_mission_identity

        identity = resolve_mission_identity(_write_meta(tmp_path / "m", {"mission_slug": "m"}))
        assert identity.mission_type == ""

    def test_legacy_only_does_not_resolve(self, tmp_path: Path) -> None:
        from specify_cli.mission_metadata import resolve_mission_identity

        identity = resolve_mission_identity(
            _write_meta(tmp_path / "m", {"mission_slug": "m", "mission": "software-dev"})
        )
        assert identity.mission_type == ""

    def test_canonical_resolves(self, tmp_path: Path) -> None:
        from specify_cli.mission_metadata import resolve_mission_identity

        identity = resolve_mission_identity(
            _write_meta(tmp_path / "m", {"mission_slug": "m", "mission_type": "research"})
        )
        assert identity.mission_type == "research"


class TestDashboardFeaturesVisibleChange:
    """FR-005 / AC-1: the dashboard reads the canonical field, not legacy."""

    def _resolve(self, meta: dict[str, object]) -> str:
        from specify_cli.dashboard.handlers import features

        captured: dict[str, str] = {}

        def _fake_get_mission_by_name(name: str, _kittify: Path):  # noqa: ANN202
            captured["name"] = name
            raise features.MissionError("stub")  # force the Unknown branch deterministically

        with (
            mock.patch.object(features, "resolve_active_feature", return_value={"name": "f", "meta": meta}),
            mock.patch.object(features, "get_mission_by_name", _fake_get_mission_by_name),
        ):
            features._resolve_active_mission_context(Path("/tmp/proj"))
        return captured["name"]

    def test_canonical_field_is_read(self) -> None:
        assert self._resolve({"mission_type": "research"}) == "research"

    def test_legacy_only_is_typeless_not_software_dev(self) -> None:
        # Previously read meta.get("mission", "software-dev") → "software-dev".
        assert self._resolve({"mission": "software-dev"}) == ""

    def test_absent_is_typeless(self) -> None:
        assert self._resolve({}) == ""
