"""
ATDD: batch-A fail-closed routing for meta.json corruption (FR-007 / WP08).

Exercises REAL batch-A entry points -- not ``load_meta``/``load_meta_fail_closed``
directly -- so this test is genuinely red if a routed call site regresses back to
the unwrapped ``mission_metadata.load_meta`` call (raw ``ValueError`` escaping to
the caller). Covers two of WP08's owned subsystems:

- ``coordination/surface_resolver.py`` (``resolve_status_surface_with_anchor``)
- ``status/aggregate.py`` (``MissionStatus.load``)

Both are corrupt-meta / non-dict-meta cases -- the two shapes that
``mission_metadata._parse_meta_text`` treats as "malformed" (json.JSONDecodeError
and non-object top level).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import resolve_status_surface_with_anchor
from specify_cli.core.paths import MissionMetaReadError
from specify_cli.status.aggregate import MissionMetadataUnavailable, MissionStatus

pytestmark = [pytest.mark.integration]


def _make_mission_dir(root: Path, slug: str, meta_text: str) -> Path:
    """Create a minimal legacy mission directory with a raw meta.json body."""
    mission_dir = root / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    return mission_dir


class TestSurfaceResolverBatchARouting:
    """``coordination/surface_resolver.resolve_status_surface_with_anchor``."""

    def test_corrupt_json_raises_typed_error_not_raw_valueerror(
        self, tmp_path: Path
    ) -> None:
        slug = "batch-a-surface-corrupt"
        _make_mission_dir(tmp_path, slug, "{ bad json")

        # A raw ValueError would ALSO satisfy `pytest.raises(Exception)`, so
        # assert the concrete typed contract -- MissionMetaReadError is a
        # RuntimeError subclass, not a ValueError, so this genuinely fails if
        # the call site reverts to the unwrapped `load_meta(...)`.
        with pytest.raises(MissionMetaReadError, match="Malformed JSON"):
            resolve_status_surface_with_anchor(tmp_path, slug)

    def test_non_dict_json_raises_typed_error_not_raw_valueerror(
        self, tmp_path: Path
    ) -> None:
        slug = "batch-a-surface-non-dict"
        _make_mission_dir(tmp_path, slug, json.dumps([1, 2, 3]))

        with pytest.raises(MissionMetaReadError, match="Expected JSON object"):
            resolve_status_surface_with_anchor(tmp_path, slug)


class TestMissionStatusBatchARouting:
    """``status/aggregate.MissionStatus.load`` (via ``_read_meta``)."""

    def test_corrupt_json_raises_typed_error_not_raw_valueerror(
        self, tmp_path: Path
    ) -> None:
        slug = "batch-a-status-corrupt"
        _make_mission_dir(tmp_path, slug, "{ bad json")

        with pytest.raises(MissionMetadataUnavailable):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)

    def test_non_dict_json_raises_typed_error_not_raw_valueerror(
        self, tmp_path: Path
    ) -> None:
        slug = "batch-a-status-non-dict"
        _make_mission_dir(tmp_path, slug, json.dumps([1, 2, 3]))

        with pytest.raises(MissionMetadataUnavailable):
            MissionStatus.load(repo_root=tmp_path, mission_slug=slug)
