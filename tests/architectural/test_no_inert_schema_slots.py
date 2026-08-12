"""Reject newly declared doctrine slots with no live producer.

The frozen ledger remains migration debt, not a second test surface.  This file
keeps only the live shrink-only gate and a two-sided controlled fault over the
same scanner.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from tests.architectural._inert_slots import (
    find_inert_slots,
    load_baseline,
    ratchet,
)

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _plant(root: Path, *, slot: str, produced: bool) -> None:
    schema_dir = root / "src" / "doctrine" / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "probe.schema.yaml").write_text(
        f"type: object\nproperties:\n  {slot}:\n    type: string\n",
        encoding="utf-8",
    )
    if produced:
        artifact_dir = root / "src" / "doctrine" / "styleguides" / "built-in"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "probe.styleguide.yaml").write_text(
            f"id: probe\n{slot}: live\n",
            encoding="utf-8",
        )


def test_inert_slot_scanner_has_two_sided_fault_bite(tmp_path: Path) -> None:
    _plant(tmp_path, slot="live_slot", produced=True)
    assert find_inert_slots(tmp_path) == []

    _plant(tmp_path, slot="missing_producer", produced=False)
    assert [slot.name for slot in find_inert_slots(tmp_path)] == [
        "missing_producer"
    ]


def test_schema_definitions_are_not_mistaken_for_data_slots(tmp_path: Path) -> None:
    schema_dir = tmp_path / "src" / "doctrine" / "schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "probe.schema.yaml").write_text(
        "type: object\ndefinitions:\n  helper:\n    type: object\nproperties: {}\n",
        encoding="utf-8",
    )
    assert find_inert_slots(tmp_path) == []


def test_live_tree_has_no_new_inert_slots() -> None:
    found = find_inert_slots(_REPO_ROOT)
    assert found, "inert-slot scan collected no live schema/model corpus"
    new, cleared = ratchet(found, load_baseline())
    if cleared:
        warnings.warn(
            "inert-slot baseline shrank; delete cleared ledger rows: "
            + ", ".join(entry.name for entry in cleared),
            stacklevel=1,
        )
    assert new == [], (
        "new schema/model slots have no live producer: "
        + ", ".join(f"{slot.name} ({slot.declared_at})" for slot in new)
    )
