"""Unit tests for ``specify_cli.intake.packet.parse_handoff_packet``."""

from __future__ import annotations

import pytest

from specify_cli.intake.packet import HANDOFF_PACKET_VERSION, parse_handoff_packet

pytestmark = [pytest.mark.fast]


VALID_PACKET = """\
---
handoff_packet: 1
source_tool: example-tool
source_tool_version: "1.0.0"
source_mission: widget-booking
source_ref: abc123
generated_at: "2026-08-13T00:00:00.000Z"
requirements:
  - id: FR-001
    statement: "Book a widget against an open slot."
    source_id: TKT-1042
    acceptance_criteria:
      - id: AC-001
        statement: "An open slot accepts a widget booking."
        source_id: AC-001
constraints:
  - id: C-001
    statement: "Bookings must not overlap."
    source_id: EXT-003
---

# widget-booking

## Objective

Book widgets.
"""


def test_valid_v1_packet_is_parsed():
    packet = parse_handoff_packet(VALID_PACKET)
    assert packet is not None
    assert packet.source_tool == "example-tool"
    assert packet.source_mission == "widget-booking"
    assert packet.source_ref == "abc123"
    assert packet.requirement_count == 1
    assert packet.constraint_count == 1
    assert packet.requirement_ids == ("FR-001",)
    sidecar = packet.sidecar_fields()
    assert sidecar["packet_version"] == HANDOFF_PACKET_VERSION
    assert sidecar["source_tool"] == "example-tool"
    assert sidecar["requirement_count"] == 1


def test_absent_frontmatter_is_prose():
    assert parse_handoff_packet("# Just a plan\n\nDo the thing.\n") is None


def test_frontmatter_without_handoff_packet_is_prose():
    raw = "---\ntitle: Plan\n---\n\n# Plan\n"
    assert parse_handoff_packet(raw) is None


def test_future_version_degrades_to_prose():
    raw = "---\nhandoff_packet: 2\nrequirements: []\n---\n\n# Future\n"
    assert parse_handoff_packet(raw) is None


def test_malformed_yaml_degrades_to_prose():
    raw = "---\nhandoff_packet: [\n---\n\n# Broken\n"
    assert parse_handoff_packet(raw) is None


def test_non_list_requirements_degrades_to_prose():
    raw = "---\nhandoff_packet: 1\nrequirements: nope\n---\n\n# Bad\n"
    assert parse_handoff_packet(raw) is None


def test_requirement_missing_statement_degrades_to_prose():
    raw = (
        "---\nhandoff_packet: 1\nrequirements:\n  - id: FR-001\n---\n\n# Bad\n"
    )
    assert parse_handoff_packet(raw) is None


def test_empty_requirements_list_is_valid_packet():
    raw = "---\nhandoff_packet: 1\nrequirements: []\n---\n\n# Empty\n"
    packet = parse_handoff_packet(raw)
    assert packet is not None
    assert packet.requirement_count == 0
    assert packet.requirement_ids == ()


def test_boolean_true_version_degrades_to_prose():
    raw = "---\nhandoff_packet: true\nrequirements: []\n---\n\n# Bad\n"
    assert parse_handoff_packet(raw) is None


def test_float_version_degrades_to_prose():
    raw = "---\nhandoff_packet: 1.0\nrequirements: []\n---\n\n# Bad\n"
    assert parse_handoff_packet(raw) is None


def test_string_version_degrades_to_prose():
    raw = '---\nhandoff_packet: "1"\nrequirements: []\n---\n\n# Bad\n'
    assert parse_handoff_packet(raw) is None


def test_bom_prefixed_packet_still_parses():
    raw = "\ufeff---\nhandoff_packet: 1\nrequirements: []\n---\n\n# BOM\n"
    packet = parse_handoff_packet(raw)
    assert packet is not None
    assert packet.requirement_count == 0


def test_comment_terminator_in_source_tool_is_escaped_in_sidecar():
    raw = (
        "---\nhandoff_packet: 1\nsource_tool: \"evil --> visible\"\n"
        "requirements: []\n---\n\n# X\n"
    )
    packet = parse_handoff_packet(raw)
    assert packet is not None
    assert "-->" not in packet.sidecar_fields()["source_tool"]
