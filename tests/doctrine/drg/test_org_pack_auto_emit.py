"""Tests for FR-014 DRG auto-emit on org pack load (WP06 T036).

When a pack artifact declares ``enhances: <id>`` or ``overrides: <id>``,
:func:`doctrine.drg.org_pack_loader.load_org_pack` MUST auto-emit a matching
edge into the pack's DRG fragment. Hand-authored duplicates of the same edge
are deduplicated by ``(source, target, relation)``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.models import Relation
from doctrine.drg.org_pack_loader import load_org_pack

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_tactic_yaml(
    pack_root: Path,
    *,
    artifact_id: str,
    overrides: str | None = None,
    enhances: str | None = None,
) -> Path:
    """Write a minimal, schema-valid pack tactic with optional augmentation fields."""
    tactics_dir = pack_root / "tactics"
    tactics_dir.mkdir(parents=True, exist_ok=True)
    body_lines = [
        'schema_version: "1.0"',
        f"id: {artifact_id}",
        f"name: {artifact_id.title()}",
    ]
    if overrides is not None:
        body_lines.append(f"overrides: {overrides}")
    if enhances is not None:
        body_lines.append(f"enhances: {enhances}")
    body_lines.extend(
        [
            "steps:",
            "  - title: Single step",
        ]
    )
    yaml_path = tactics_dir / f"{artifact_id}.tactic.yaml"
    yaml_path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    return yaml_path


def _write_fragment_yaml(pack_root: Path, body: str) -> Path:
    drg_dir = pack_root / "drg"
    drg_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = drg_dir / "fragment.yaml"
    fragment_path.write_text(body, encoding="utf-8")
    return fragment_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_enhances_auto_emits_drg_edge(tmp_path: Path) -> None:
    """FR-014: `enhances` field surfaces as an ENHANCES edge in the fragment."""
    pack_root = tmp_path / "pack"
    _write_tactic_yaml(
        pack_root,
        artifact_id="pack-tactic",
        enhances="builtin-tactic-id",
    )
    _write_fragment_yaml(
        pack_root,
        body=(
            'pack_name: testpack\n'
            'source_kind: local_path\n'
            'source_ref: "/tmp/pack"\n'
            "layer_index: 1\n"
            "nodes: []\n"
            "edges: []\n"
        ),
    )

    fragment = load_org_pack("testpack", pack_root, layer_index=1)

    matching = [
        e
        for e in fragment.edges
        if e.source == "tactic:pack-tactic"
        and e.target == "tactic:builtin-tactic-id"
        and e.relation == Relation.ENHANCES.value
    ]
    assert matching, f"Auto-emitted ENHANCES edge missing. edges={fragment.edges}"
    assert matching[0].reason == "declared via tactic.enhances field"


def test_overrides_auto_emits_drg_edge(tmp_path: Path) -> None:
    """FR-014: `overrides` field surfaces as an OVERRIDES edge in the fragment."""
    pack_root = tmp_path / "pack"
    _write_tactic_yaml(
        pack_root,
        artifact_id="pack-tactic",
        overrides="builtin-tactic-id",
    )
    _write_fragment_yaml(
        pack_root,
        body=(
            'pack_name: testpack\n'
            'source_kind: local_path\n'
            'source_ref: "/tmp/pack"\n'
            "layer_index: 1\n"
            "nodes: []\n"
            "edges: []\n"
        ),
    )

    fragment = load_org_pack("testpack", pack_root, layer_index=1)

    matching = [
        e
        for e in fragment.edges
        if e.source == "tactic:pack-tactic"
        and e.target == "tactic:builtin-tactic-id"
        and e.relation == Relation.OVERRIDES.value
    ]
    assert matching, f"Auto-emitted OVERRIDES edge missing. edges={fragment.edges}"
    assert matching[0].reason == "declared via tactic.overrides field"


def test_auto_emit_deduplicates_hand_authored_edge(tmp_path: Path) -> None:
    """FR-014 dedupe: hand-authored copy of the auto-emitted edge survives only once."""
    pack_root = tmp_path / "pack"
    _write_tactic_yaml(
        pack_root,
        artifact_id="pack-tactic",
        enhances="builtin-tactic-id",
    )
    _write_fragment_yaml(
        pack_root,
        body=(
            'pack_name: testpack\n'
            'source_kind: local_path\n'
            'source_ref: "/tmp/pack"\n'
            "layer_index: 1\n"
            "nodes: []\n"
            "edges:\n"
            "  - source: tactic:pack-tactic\n"
            "    target: tactic:builtin-tactic-id\n"
            "    relation: enhances\n"
        ),
    )

    fragment = load_org_pack("testpack", pack_root, layer_index=1)

    matching = [
        e
        for e in fragment.edges
        if e.source == "tactic:pack-tactic"
        and e.target == "tactic:builtin-tactic-id"
        and e.relation == Relation.ENHANCES.value
    ]
    assert len(matching) == 1, (
        f"Hand-authored + auto-emitted edge should collapse to one. "
        f"Found {len(matching)}: {matching}"
    )


def test_no_augmentation_fields_emits_no_extra_edges(tmp_path: Path) -> None:
    """Baseline: pack without `enhances`/`overrides` does not gain auto edges."""
    pack_root = tmp_path / "pack"
    _write_tactic_yaml(pack_root, artifact_id="pack-tactic")
    _write_fragment_yaml(
        pack_root,
        body=(
            'pack_name: testpack\n'
            'source_kind: local_path\n'
            'source_ref: "/tmp/pack"\n'
            "layer_index: 1\n"
            "nodes: []\n"
            "edges: []\n"
        ),
    )

    fragment = load_org_pack("testpack", pack_root, layer_index=1)

    assert fragment.edges == []


def test_relation_enum_includes_enhances_and_overrides() -> None:
    """T035: `Relation` enum exposes the new augmentation values; REPLACES remains."""
    assert Relation.ENHANCES.value == "enhances"
    assert Relation.OVERRIDES.value == "overrides"
    # Backward compatibility: REPLACES must NOT be removed.
    assert Relation.REPLACES.value == "replaces"
