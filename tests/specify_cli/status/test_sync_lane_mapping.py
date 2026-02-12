"""Tests for the 7-to-4 lane collapse mapping (_SYNC_LANE_MAP).

Covers:
  T025 - Parametrized tests for all 7 canonical lanes -> 4-lane sync outputs
  T026 - Invalid lane handling via TransitionError
  T027 - Centralization verification (_SYNC_LANE_MAP in status/emit.py only)
  T028 - Contract doc (lane-mapping.md) matches implementation
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.status.emit import (
    TransitionError,
    _SYNC_LANE_MAP,
    emit_status_transition,
)
from specify_cli.status.models import Lane
from specify_cli.status.transitions import CANONICAL_LANES, LANE_ALIASES


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Create a minimal feature directory for tests."""
    fd = tmp_path / "kitty-specs" / "039-test-feature"
    fd.mkdir(parents=True)
    return fd


# ── T025: Parametrized tests for all 7 lanes ─────────────────


class TestSyncLaneMapValues:
    """Verify every canonical lane maps to the expected 4-lane sync value."""

    @pytest.mark.parametrize(
        "input_lane,expected_output",
        [
            ("planned", "planned"),
            ("claimed", "planned"),
            ("in_progress", "doing"),
            ("for_review", "for_review"),
            ("done", "done"),
            ("blocked", "doing"),
            ("canceled", "planned"),
        ],
    )
    def test_sync_lane_map_values(
        self, input_lane: str, expected_output: str
    ) -> None:
        """Each canonical lane maps to the correct 4-lane sync value."""
        assert _SYNC_LANE_MAP[input_lane] == expected_output

    def test_map_covers_all_canonical_lanes(self) -> None:
        """_SYNC_LANE_MAP has an entry for every canonical lane."""
        for lane in CANONICAL_LANES:
            assert lane in _SYNC_LANE_MAP, (
                f"Missing _SYNC_LANE_MAP entry for canonical lane '{lane}'"
            )

    def test_map_has_no_extra_keys(self) -> None:
        """_SYNC_LANE_MAP contains only canonical lane keys (no stale entries)."""
        canonical_set = set(CANONICAL_LANES)
        extra = set(_SYNC_LANE_MAP.keys()) - canonical_set
        assert extra == set(), (
            f"_SYNC_LANE_MAP has non-canonical keys: {extra}"
        )

    def test_map_outputs_are_valid_4_lane_values(self) -> None:
        """All mapped values belong to the allowed 4-lane SaaS vocabulary."""
        allowed_saas_lanes = {"planned", "doing", "for_review", "done"}
        for canonical_lane, sync_lane in _SYNC_LANE_MAP.items():
            assert sync_lane in allowed_saas_lanes, (
                f"_SYNC_LANE_MAP['{canonical_lane}'] = '{sync_lane}' "
                f"is not in allowed SaaS lanes {allowed_saas_lanes}"
            )

    def test_map_exactly_seven_entries(self) -> None:
        """_SYNC_LANE_MAP has exactly 7 entries (one per canonical lane)."""
        assert len(_SYNC_LANE_MAP) == 7

    def test_doing_alias_maps_through_in_progress(self) -> None:
        """The 'doing' alias resolves to 'in_progress', which maps to 'doing'."""
        resolved = LANE_ALIASES.get("doing")
        assert resolved == "in_progress"
        assert _SYNC_LANE_MAP[resolved] == "doing"


# ── T026: Invalid lane handling via TransitionError ───────────


class TestInvalidLaneHandling:
    """Ensure invalid lane values are rejected with TransitionError."""

    def test_invalid_to_lane_raises_transition_error(
        self, feature_dir: Path
    ) -> None:
        """Completely unknown lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="NONEXISTENT",
                actor="tester",
            )

    def test_empty_to_lane_raises_transition_error(
        self, feature_dir: Path
    ) -> None:
        """Empty string lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="",
                actor="tester",
            )

    def test_numeric_lane_raises_transition_error(
        self, feature_dir: Path
    ) -> None:
        """Numeric lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="42",
                actor="tester",
            )

    def test_case_sensitive_rejection(self, feature_dir: Path) -> None:
        """Uppercase lane values that are not aliases are rejected."""
        # 'PLANNED' is not in LANE_ALIASES and not a canonical lane value
        # resolve_lane_alias lowercases, so "PLANNED" -> "planned" works.
        # But a totally unknown word like "Doing_stuff" should fail.
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="Doing_stuff",
                actor="tester",
            )

    def test_invalid_lane_does_not_persist(self, feature_dir: Path) -> None:
        """Invalid lane rejection happens before any event persistence."""
        from specify_cli.status.store import EVENTS_FILENAME

        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="bogus",
                actor="tester",
            )

        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()

    def test_invalid_lane_not_in_sync_map(self) -> None:
        """Looking up a non-canonical lane in _SYNC_LANE_MAP returns None."""
        assert _SYNC_LANE_MAP.get("NONEXISTENT") is None
        assert _SYNC_LANE_MAP.get("") is None
        assert _SYNC_LANE_MAP.get("42") is None


# ── T027: Centralization verification ─────────────────────────


class TestMappingCentralization:
    """Verify _SYNC_LANE_MAP is centralized in status/emit.py and not duplicated."""

    @staticmethod
    def _find_src_root() -> Path:
        """Locate the src/specify_cli directory."""
        # Walk up from this test file to find the project root
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "src" / "specify_cli"
            if candidate.is_dir():
                return candidate
        raise FileNotFoundError("Could not locate src/specify_cli")

    def test_sync_lane_map_defined_in_emit_py(self) -> None:
        """_SYNC_LANE_MAP is defined in status/emit.py."""
        src = self._find_src_root()
        emit_path = src / "status" / "emit.py"
        assert emit_path.exists(), f"Expected {emit_path} to exist"
        content = emit_path.read_text(encoding="utf-8")
        assert "_SYNC_LANE_MAP" in content

    def test_no_duplicate_7_to_4_mapping_outside_emit(self) -> None:
        """No other Python file in src/specify_cli/ defines a 7-to-4 lane dict."""
        src = self._find_src_root()
        emit_path = src / "status" / "emit.py"
        duplicate_files: list[str] = []

        for py_file in src.rglob("*.py"):
            if py_file == emit_path:
                continue
            content = py_file.read_text(encoding="utf-8")
            # Check for the specific variable name
            if "_SYNC_LANE_MAP" in content:
                # Imports like "from .emit import _SYNC_LANE_MAP" are OK
                # Definitions like "_SYNC_LANE_MAP = {" are NOT OK
                lines = content.splitlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("_SYNC_LANE_MAP") and "=" in stripped:
                        # Skip import statements
                        if "import" not in stripped:
                            duplicate_files.append(str(py_file.relative_to(src)))

        assert duplicate_files == [], (
            f"_SYNC_LANE_MAP is defined outside emit.py: {duplicate_files}"
        )

    def test_emit_py_map_is_importable(self) -> None:
        """_SYNC_LANE_MAP can be imported from the expected module path."""
        from specify_cli.status.emit import _SYNC_LANE_MAP as imported_map

        assert isinstance(imported_map, dict)
        assert len(imported_map) == 7


# ── T028: Contract doc matches implementation ─────────────────


class TestContractDocMatchesImplementation:
    """Verify contracts/lane-mapping.md matches _SYNC_LANE_MAP implementation."""

    @staticmethod
    def _find_contract_doc() -> Path:
        """Locate lane-mapping.md in kitty-specs contracts."""
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = (
                parent
                / "kitty-specs"
                / "039-cli-2x-readiness"
                / "contracts"
                / "lane-mapping.md"
            )
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            "Could not locate kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md"
        )

    def _parse_mapping_table(self, content: str) -> dict[str, str]:
        """Extract the 7-to-4 mapping table from the contract markdown.

        Expects a markdown table with columns:
        | 7-Lane (Internal) | 4-Lane (Sync Payload) | Rationale |
        """
        mapping: dict[str, str] = {}
        # Match table rows like: | PLANNED | planned | ... |
        # or: | planned | planned | ... |
        table_row_re = re.compile(
            r"^\|\s*(\w+)\s*\|\s*(\w+)\s*\|", re.MULTILINE
        )
        for match in table_row_re.finditer(content):
            canonical_lane = match.group(1).strip().lower()
            sync_lane = match.group(2).strip().lower()
            # Skip header rows
            if canonical_lane in ("7", "lane", "internal", "---"):
                continue
            if sync_lane in ("4", "lane", "sync", "payload", "---"):
                continue
            mapping[canonical_lane] = sync_lane
        return mapping

    def test_contract_doc_exists(self) -> None:
        """lane-mapping.md contract document exists."""
        doc_path = self._find_contract_doc()
        assert doc_path.exists()

    def test_contract_mapping_matches_implementation(self) -> None:
        """Every entry in the contract doc matches _SYNC_LANE_MAP."""
        doc_path = self._find_contract_doc()
        content = doc_path.read_text(encoding="utf-8")
        contract_mapping = self._parse_mapping_table(content)

        # Contract should have all 7 entries
        assert len(contract_mapping) == 7, (
            f"Contract doc has {len(contract_mapping)} entries, expected 7. "
            f"Found: {contract_mapping}"
        )

        # Every contract entry must match the implementation
        for canonical_lane, contract_sync_lane in contract_mapping.items():
            impl_sync_lane = _SYNC_LANE_MAP.get(canonical_lane)
            assert impl_sync_lane is not None, (
                f"Contract references canonical lane '{canonical_lane}' "
                f"which is not in _SYNC_LANE_MAP"
            )
            assert contract_sync_lane == impl_sync_lane, (
                f"Contract drift! For lane '{canonical_lane}': "
                f"contract says '{contract_sync_lane}', "
                f"implementation says '{impl_sync_lane}'"
            )

    def test_implementation_fully_covered_by_contract(self) -> None:
        """Every _SYNC_LANE_MAP entry appears in the contract doc."""
        doc_path = self._find_contract_doc()
        content = doc_path.read_text(encoding="utf-8")
        contract_mapping = self._parse_mapping_table(content)

        for canonical_lane in _SYNC_LANE_MAP:
            assert canonical_lane in contract_mapping, (
                f"Implementation has lane '{canonical_lane}' which is "
                f"missing from the contract document"
            )

    def test_contract_documents_doing_alias(self) -> None:
        """Contract doc mentions the 'doing' -> 'in_progress' alias."""
        doc_path = self._find_contract_doc()
        content = doc_path.read_text(encoding="utf-8")
        # The doc should mention the doing alias somewhere
        assert "doing" in content.lower() and "in_progress" in content.lower(), (
            "Contract doc should document the 'doing' -> 'in_progress' alias"
        )

    def test_contract_documents_4_saas_lanes(self) -> None:
        """Contract doc lists the 4 SaaS lanes."""
        doc_path = self._find_contract_doc()
        content = doc_path.read_text(encoding="utf-8")
        for saas_lane in ("planned", "doing", "for_review", "done"):
            assert saas_lane in content, (
                f"Contract doc should list SaaS lane '{saas_lane}'"
            )
