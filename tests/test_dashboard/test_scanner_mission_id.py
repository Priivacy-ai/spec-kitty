"""Tests for dashboard scanner rekeyed by mission_id (WP09, T050).

Covers:
- Three `080-*` missions with distinct mission_ids produce three distinct records.
- Legacy mission (no mission_id) shows up with `legacy:<slug>` pseudo-key.
- API-types shape: mission_id, display_number, mid8, mission_slug all present.
- Display sort order: numeric prefix ASC, None LAST, secondary by slug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.dashboard.scanner import (
    _read_mission_identity,
    build_mission_registry,
    sort_missions_for_display,
)

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str | None = None,
    mission_number: int | None = None,
    friendly_name: str = "",
) -> None:
    """Write a minimal meta.json to feature_dir."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {}
    if mission_id is not None:
        meta["mission_id"] = mission_id
    if mission_number is not None:
        meta["mission_number"] = mission_number
    if friendly_name:
        meta["friendly_name"] = friendly_name
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _create_mission_dir(
    specs_dir: Path,
    slug: str,
    *,
    mission_id: str | None = None,
    mission_number: int | None = None,
    friendly_name: str = "",
) -> Path:
    """Create a minimal mission directory in specs_dir."""
    feature_dir = specs_dir / slug
    _write_meta(
        feature_dir,
        mission_id=mission_id,
        mission_number=mission_number,
        friendly_name=friendly_name,
    )
    return feature_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Three distinct ULIDs representing three `080-*` missions
ULID_FOO = "01JQABC1234567890ABCFOO111"
ULID_BAR = "01JQABC1234567890ABCBAR222"
ULID_BAZ = "01JQABC1234567890ABCBAZ333"


@pytest.fixture()
def triple_080_repo(tmp_path: Path) -> Path:
    """Repo with three 080-* missions having distinct mission_ids."""
    specs = tmp_path / "kitty-specs"
    _create_mission_dir(specs, "080-foo", mission_id=ULID_FOO, mission_number=80, friendly_name="Foo Feature")
    _create_mission_dir(specs, "080-bar", mission_id=ULID_BAR, mission_number=80, friendly_name="Bar Feature")
    _create_mission_dir(specs, "080-baz", mission_id=ULID_BAZ, mission_number=80, friendly_name="Baz Feature")
    return tmp_path


@pytest.fixture()
def mixed_repo(tmp_path: Path) -> Path:
    """Repo with assigned, legacy, and orphan missions."""
    specs = tmp_path / "kitty-specs"
    # Assigned (has mission_id + mission_number)
    _create_mission_dir(specs, "001-alpha", mission_id="01JQABC1234567890ABCALPHA1", mission_number=1)
    # Legacy (mission_number but no mission_id)
    _create_mission_dir(specs, "002-beta", mission_number=2)
    # Orphan (no meta.json fields at all — just an empty dir)
    orphan_dir = specs / "003-orphan"
    orphan_dir.mkdir(parents=True)
    # (no meta.json — but we need to create the dir to be discovered)
    return tmp_path


# ---------------------------------------------------------------------------
# T046 — Scanner keyed by mission_id
# ---------------------------------------------------------------------------


class TestBuildMissionRegistry:
    def test_three_080_missions_produce_three_distinct_keys(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        assert len(registry) == 3, f"Expected 3 distinct keys, got {len(registry)}: {list(registry)}"

    def test_keys_are_mission_ids_not_slugs(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        assert ULID_FOO in registry
        assert ULID_BAR in registry
        assert ULID_BAZ in registry
        # Directory names must NOT be keys
        assert "080-foo" not in registry
        assert "080-bar" not in registry
        assert "080-baz" not in registry

    def test_legacy_mission_uses_pseudo_key(self, mixed_repo: Path) -> None:
        registry = build_mission_registry(mixed_repo)
        legacy_keys = [k for k in registry if k.startswith("legacy:")]
        assert len(legacy_keys) == 1
        assert "legacy:002-beta" in registry

    def test_orphan_mission_uses_pseudo_key(self, mixed_repo: Path) -> None:
        registry = build_mission_registry(mixed_repo)
        orphan_keys = [k for k in registry if k.startswith("orphan:")]
        assert len(orphan_keys) == 1
        assert "orphan:003-orphan" in registry

    def test_assigned_mission_uses_ulid_key(self, mixed_repo: Path) -> None:
        registry = build_mission_registry(mixed_repo)
        assert "01JQABC1234567890ABCALPHA1" in registry

    def test_read_mission_identity_coerces_digit_string(self, tmp_path: Path) -> None:
        """Digit strings in mission_number are coerced to integers."""
        feature_dir = tmp_path / "kitty-specs" / "042-string-number"
        _write_meta(feature_dir, mission_id="01JQABC1234567890ABCALPHA1", mission_number="042")

        mission_id, mission_number = _read_mission_identity(feature_dir)

        assert mission_id == "01JQABC1234567890ABCALPHA1"
        assert mission_number == 42

    def test_read_mission_identity_returns_none_for_non_object_json(self, tmp_path: Path) -> None:
        """Non-object meta.json degrades to (None, None)."""
        feature_dir = tmp_path / "kitty-specs" / "043-list-meta"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text('["not", "an", "object"]', encoding="utf-8")

        assert _read_mission_identity(feature_dir) == (None, None)

    def test_read_mission_identity_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        """Malformed meta.json degrades to (None, None)."""
        feature_dir = tmp_path / "kitty-specs" / "044-invalid-json"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("{bad json", encoding="utf-8")

        assert _read_mission_identity(feature_dir) == (None, None)


# ---------------------------------------------------------------------------
# T047 — Display ordering
# ---------------------------------------------------------------------------


class TestSortMissionsForDisplay:
    def test_three_080_missions_sorted_by_slug(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        order = sort_missions_for_display(registry)
        # All three present
        assert set(order) == {ULID_FOO, ULID_BAR, ULID_BAZ}
        # Secondary sort by slug: 080-bar < 080-baz < 080-foo
        slugs = [registry[mid]["mission_slug"] for mid in order]
        assert slugs == ["080-bar", "080-baz", "080-foo"]

    def test_none_mission_number_sorts_last(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        # One assigned (mission_number=5), one legacy, one pending (no number)
        ULID_PEND = "01JQPENDING1234567890PEND11"
        _create_mission_dir(specs, "005-assigned", mission_id="01JQASSIGNED1234567890ASS1", mission_number=5)
        _create_mission_dir(specs, "pending-thing", mission_id=ULID_PEND)  # no mission_number

        registry = build_mission_registry(tmp_path)
        order = sort_missions_for_display(registry)

        # Assigned (number=5) must come before pending (number=None)
        assigned_key = "01JQASSIGNED1234567890ASS1"
        assert order.index(assigned_key) < order.index(ULID_PEND)

    def test_legacy_and_orphan_appear_in_output(self, mixed_repo: Path) -> None:
        registry = build_mission_registry(mixed_repo)
        order = sort_missions_for_display(registry)
        assert "01JQABC1234567890ABCALPHA1" in order
        assert any(k.startswith("legacy:") for k in order)
        assert any(k.startswith("orphan:") for k in order)

    def test_order_is_deterministic(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        order1 = sort_missions_for_display(registry)
        order2 = sort_missions_for_display(registry)
        assert order1 == order2


# ---------------------------------------------------------------------------
# T048 — API types shape
# ---------------------------------------------------------------------------


class TestApiTypesShape:
    def test_mission_record_has_required_fields(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        record = registry[ULID_FOO]
        # Required fields
        assert "mission_id" in record
        assert "display_number" in record
        assert "mid8" in record
        assert "mission_slug" in record

    def test_mission_id_matches_key(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        for key, record in registry.items():
            if not key.startswith(("legacy:", "orphan:")):
                assert record["mission_id"] == key

    def test_display_number_correct(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        record = registry[ULID_FOO]
        assert record["display_number"] == 80

    def test_mid8_is_first_8_chars_of_mission_id(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        for key, record in registry.items():
            if not key.startswith(("legacy:", "orphan:")):
                assert record["mid8"] == record["mission_id"][:8]

    def test_mid8_is_none_for_pseudo_keys(self, mixed_repo: Path) -> None:
        registry = build_mission_registry(mixed_repo)
        for key, record in registry.items():
            if key.startswith(("legacy:", "orphan:")):
                # mid8 must be None for pseudo-key missions
                assert record["mid8"] is None, f"Expected None mid8 for {key}, got {record['mid8']}"

    def test_mission_slug_matches_directory_name(self, triple_080_repo: Path) -> None:
        registry = build_mission_registry(triple_080_repo)
        assert registry[ULID_FOO]["mission_slug"] == "080-foo"
        assert registry[ULID_BAR]["mission_slug"] == "080-bar"
        assert registry[ULID_BAZ]["mission_slug"] == "080-baz"
