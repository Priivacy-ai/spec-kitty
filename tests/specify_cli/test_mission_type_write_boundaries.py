"""rc3 M5 WP03 pins: write/echo/audit boundaries + reader-allowlist integrity.

The runtime READ readers converged onto read_mission_type (WP02). This module
pins the NON-read boundaries:
  * the audit tool stays field-aware (legacy-only is still its own bucket);
  * the reader-gate allow-list carries a rationale + issue for every exemption.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit]

_ALLOWLIST = Path(__file__).resolve().parents[1] / "architectural" / "mission_type_reader_allowlist.yaml"


class TestAuditToolStaysFieldAware:
    """The census/audit tool reads legacy `mission` BY DESIGN (not converged)."""

    def test_legacy_only_classifies_as_legacy_key_only(self) -> None:
        from specify_cli.cli.commands._mission_type_audit import _classify_absent_key

        resolved_key, state = _classify_absent_key("research")
        assert resolved_key == "research"
        assert state == "legacy-key-only"

    def test_absent_and_blank_are_typeless(self) -> None:
        from specify_cli.cli.commands._mission_type_audit import _classify_absent_key

        assert _classify_absent_key(None) == (None, "typeless")
        assert _classify_absent_key("") == (None, "typeless")


class TestReaderAllowlistIntegrity:
    """Every encoded exemption carries a rationale + issue (no silent excludes)."""

    def test_exemptions_are_well_formed(self) -> None:
        data = yaml.safe_load(_ALLOWLIST.read_text(encoding="utf-8"))
        exemptions = data.get("exemptions", [])
        assert exemptions, "reader allow-list must not be empty"
        for entry in exemptions:
            assert entry.get("path"), f"exemption missing path: {entry}"
            assert entry.get("issue"), f"exemption for {entry['path']} missing issue"
            assert entry.get("rationale"), f"exemption for {entry['path']} missing rationale"
            assert entry.get("kinds"), f"exemption for {entry['path']} missing kinds"
            for kind in entry["kinds"]:
                assert kind in {"legacy", "default"}, f"unknown kind {kind!r} in {entry['path']}"

    def test_domain_exempt_notes_carry_rationale(self) -> None:
        data = yaml.safe_load(_ALLOWLIST.read_text(encoding="utf-8"))
        for entry in data.get("domain_exempt_notes", []):
            assert entry.get("issue") and entry.get("rationale"), entry
