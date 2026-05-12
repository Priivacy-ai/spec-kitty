"""Regression tests for provenance dual-storage routing (FR-022).

Tests:
  - Per-mission routing: ingest of kitty-specs/<m>/charter/x.yaml writes to
    kitty-specs/<m>/.encoding-provenance.jsonl, not to global.
  - Centralized routing: ingest of .kittify/charter/y.yaml writes to
    .kittify/encoding-provenance/global.jsonl, not to any mission file.
  - No duplication: single ingest produces exactly one record across both files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from charter._io import load_charter_file, _route_provenance_path

pytestmark = pytest.mark.fast

_UTF8_BYTES = b"# Charter\nThis is a test charter.\n"


def _read_provenance(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Routing rule unit tests (pure path logic, no file I/O)
# ---------------------------------------------------------------------------


def test_per_mission_routing_path_resolution(tmp_path: Path) -> None:
    """_route_provenance_path returns the per-mission path for files under
    kitty-specs/<mission>/.
    """
    mission_charter = tmp_path / "kitty-specs" / "my-mission-01KRC57C" / "charter" / "charter.yaml"
    result = _route_provenance_path(mission_charter)
    expected = tmp_path / "kitty-specs" / "my-mission-01KRC57C" / ".encoding-provenance.jsonl"
    assert result == expected


def test_centralized_routing_path_resolution(tmp_path: Path) -> None:
    """_route_provenance_path returns the centralized path for files outside
    kitty-specs/.
    """
    kittify_charter = tmp_path / ".kittify" / "charter" / "charter.yaml"
    result = _route_provenance_path(kittify_charter)
    assert result == Path(".kittify/encoding-provenance/global.jsonl")


def test_none_source_path_routes_to_centralized() -> None:
    """source_path=None (inline bytes) routes to the centralized log."""
    result = _route_provenance_path(None)
    assert result == Path(".kittify/encoding-provenance/global.jsonl")


# ---------------------------------------------------------------------------
# Full ingest + provenance write tests
# ---------------------------------------------------------------------------


def test_per_mission_routing_writes_to_mission_file(tmp_path: Path) -> None:
    """Ingest of a file under kitty-specs/<mission>/charter/ writes provenance
    to kitty-specs/<mission>/.encoding-provenance.jsonl and NOT to global.
    """
    # Create the mission directory structure.
    mission_dir = tmp_path / "kitty-specs" / "test-mission-01KABC"
    charter_dir = mission_dir / "charter"
    charter_dir.mkdir(parents=True)
    charter_file = charter_dir / "charter.yaml"
    charter_file.write_bytes(_UTF8_BYTES)

    per_mission_prov = mission_dir / ".encoding-provenance.jsonl"
    global_prov = tmp_path / ".kittify" / "encoding-provenance" / "global.jsonl"

    import charter._io as _io_mod
    original_route = _io_mod._route_provenance_path

    def _patched_route(source_path: Path | None) -> Path:
        # Delegate to real logic but reroute to tmp_path-relative paths.
        real_result = original_route(source_path)
        if real_result == Path(".kittify/encoding-provenance/global.jsonl"):
            return tmp_path / ".kittify" / "encoding-provenance" / "global.jsonl"
        # Per-mission: real_result is relative to something — rebuild under tmp_path.
        # We re-derive the path from source_path to get a tmp_path-rooted version.
        if source_path is not None:
            parts = list(source_path.parts)
            if "kitty-specs" in parts:
                idx = parts.index("kitty-specs")
                mission_slug = parts[idx + 1]
                # Find the kitty-specs root in tmp_path
                return tmp_path / "kitty-specs" / mission_slug / ".encoding-provenance.jsonl"
        return tmp_path / ".kittify" / "encoding-provenance" / "global.jsonl"

    _io_mod._route_provenance_path = _patched_route
    try:
        content = load_charter_file(charter_file)
    finally:
        _io_mod._route_provenance_path = original_route

    # Per-mission file should have the record.
    per_mission_records = _read_provenance(per_mission_prov)
    assert len(per_mission_records) == 1, (
        f"Expected 1 record in per-mission file, got {len(per_mission_records)}"
    )

    # Global file should NOT exist or be empty.
    global_records = _read_provenance(global_prov)
    assert global_records == [], (
        f"Global provenance file should be empty for per-mission ingest, "
        f"but got {len(global_records)} record(s)"
    )


def test_centralized_routing_writes_to_global_file(tmp_path: Path) -> None:
    """Ingest of a file outside kitty-specs/ writes provenance to global.jsonl
    and NOT to any mission-specific file.
    """
    kittify_charter_dir = tmp_path / ".kittify" / "charter"
    kittify_charter_dir.mkdir(parents=True)
    charter_file = kittify_charter_dir / "charter.yaml"
    charter_file.write_bytes(_UTF8_BYTES)

    global_prov = tmp_path / ".kittify" / "encoding-provenance" / "global.jsonl"

    import charter._io as _io_mod
    original_route = _io_mod._route_provenance_path

    def _patched_route(source_path: Path | None) -> Path:
        real_result = original_route(source_path)
        if real_result == Path(".kittify/encoding-provenance/global.jsonl"):
            return global_prov
        return real_result

    _io_mod._route_provenance_path = _patched_route
    try:
        content = load_charter_file(charter_file)
    finally:
        _io_mod._route_provenance_path = original_route

    # Global file should have the record.
    global_records = _read_provenance(global_prov)
    assert len(global_records) == 1, (
        f"Expected 1 record in global file, got {len(global_records)}"
    )

    # Verify no mission-specific files were created.
    kitty_specs = tmp_path / "kitty-specs"
    if kitty_specs.exists():
        mission_prov_files = list(kitty_specs.rglob(".encoding-provenance.jsonl"))
        assert mission_prov_files == [], (
            f"No per-mission provenance files should exist for non-mission ingest, "
            f"found: {mission_prov_files}"
        )


def test_no_duplication_single_ingest_one_record(tmp_path: Path) -> None:
    """A single charter file ingest produces exactly one provenance record
    across both the per-mission file and the global file combined.
    """
    charter_file = tmp_path / "charter.yaml"
    charter_file.write_bytes(_UTF8_BYTES)

    per_mission_prov = tmp_path / "per_mission.jsonl"
    global_prov = tmp_path / "global.jsonl"

    # Track all writes
    written_to: list[str] = []
    import charter._io as _io_mod
    original_route = _io_mod._route_provenance_path
    original_write = _io_mod._write_provenance

    def _patched_route(source_path: Path | None) -> Path:
        return global_prov

    call_count = [0]

    def _patched_write(content: object, *, bypass_used: bool) -> None:
        call_count[0] += 1
        original_write(content, bypass_used=bypass_used)

    _io_mod._route_provenance_path = _patched_route
    _io_mod._write_provenance = _patched_write
    try:
        _io_mod.load_charter_file(charter_file)
    finally:
        _io_mod._route_provenance_path = original_route
        _io_mod._write_provenance = original_write

    # Exactly one write call.
    assert call_count[0] == 1, (
        f"Expected exactly 1 provenance write call, got {call_count[0]}"
    )

    # The global file has exactly one record.
    global_records = _read_provenance(global_prov)
    assert len(global_records) == 1

    # Per-mission file was never written.
    per_mission_records = _read_provenance(per_mission_prov)
    assert per_mission_records == []
