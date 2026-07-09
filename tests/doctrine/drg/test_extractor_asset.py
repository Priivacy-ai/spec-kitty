"""Tests for ASSET registration in the migration extractor + doctrine CLI (WP05).

Covers:
- T019: ``_discover_built_in_artifact_nodes`` scans ``assets/built-in`` and
  registers discovered ``*.asset.yaml`` files as ``NodeKind.ASSET`` nodes.
- T019: ``_KIND_MAP`` stays ``.get``-based (never a raising subscript), so an
  unknown/new reference type is skipped cleanly instead of raising ``KeyError``.
- T020: ``doctrine.py::_SUFFIX_TO_KIND`` resolves ``*.asset.yaml`` to the
  ``("assets", "asset")`` kind pair.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.migration.extractor import (
    _KIND_MAP,
    _discover_built_in_artifact_nodes,
    _kind_for_type,
)
from doctrine.drg.models import DRGNode, NodeKind
from specify_cli.cli.commands.doctrine import _detect_artifact_kind

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]


def test_discover_built_in_artifact_nodes_registers_assets(tmp_path: Path) -> None:
    """A ``*.asset.yaml`` file under ``assets/built-in`` becomes an ASSET node."""
    assets_dir = tmp_path / "assets" / "built-in"
    assets_dir.mkdir(parents=True)
    (assets_dir / "brand-logo.asset.yaml").write_text(
        "id: brand-logo\nname: Brand Logo\n", encoding="utf-8"
    )

    nodes_by_urn: dict[str, DRGNode] = {}
    _discover_built_in_artifact_nodes(tmp_path, nodes_by_urn)

    node = nodes_by_urn.get("asset:brand-logo")
    assert node is not None
    assert node.kind == NodeKind.ASSET
    assert node.label == "Brand Logo"


def test_discover_built_in_artifact_nodes_skips_missing_assets_dir(
    tmp_path: Path,
) -> None:
    """No ``assets/built-in`` directory is a no-op, not an error."""
    nodes_by_urn: dict[str, DRGNode] = {}
    _discover_built_in_artifact_nodes(tmp_path, nodes_by_urn)

    assert nodes_by_urn == {}


def test_kind_map_get_is_none_safe_for_unknown_type() -> None:
    """``_KIND_MAP`` is read via ``.get`` -- an unrecognised type returns ``None``.

    This is the regression guard: a raising subscript (``_KIND_MAP[ref_type]``)
    would crash on any type not yet registered (e.g. a future kind). ``asset``
    is deliberately absent from ``_KIND_MAP`` -- built-in reference fields don't
    target assets by type (org packs declare assets via ``org_pack_loader``,
    not this extractor path) -- so it doubles as the "unknown/new type" probe.
    """
    assert "asset" not in _KIND_MAP
    assert _KIND_MAP.get("asset") is None
    assert _kind_for_type("asset") is None
    assert _kind_for_type("some-future-kind-not-yet-registered") is None


def test_suffix_to_kind_resolves_asset_yaml() -> None:
    """``doctrine.py::_SUFFIX_TO_KIND`` maps ``*.asset.yaml`` to ``("assets", "asset")``."""
    result = _detect_artifact_kind(Path("brand-logo.asset.yaml"))
    assert result == ("assets", "asset")
