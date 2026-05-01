"""Reader tolerance tests.

Covers:
  - Corrupt YAML     → YAMLParseError
  - Missing required field → SchemaError
  - status=pending   → SchemaError
  - Missing file     → FileNotFoundError
  - verify_evidence API surface (no-op for now, WP03 wires it)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.retrospective.reader import SchemaError, YAMLParseError, read_record

# ---------------------------------------------------------------------------
# Minimal valid YAML for a completed record
# ---------------------------------------------------------------------------

MISSION_ID = "01KQ6YEGT4YBZ3GZF7X680KQ3V"

VALID_YAML = f"""\
schema_version: "1"
mission:
  mission_id: {MISSION_ID}
  mid8: 01KQ6YEG
  mission_slug: test-mission
  mission_type: software-dev
  mission_started_at: "2026-04-27T07:46:18.715532+00:00"
  mission_completed_at: "2026-04-27T11:00:00+00:00"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed
started_at: "2026-04-27T10:55:00+00:00"
completed_at: "2026-04-27T11:00:00+00:00"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful: []
gaps: []
proposals: []
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "2026-04-27T11:00:00+00:00"
  schema_version: "1"
"""

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_corrupt_yaml_raises_yaml_parse_error(tmp_path: Path) -> None:
    """Non-YAML content → YAMLParseError."""
    bad = tmp_path / "retrospective.yaml"
    bad.write_text("{ not valid yaml: [unclosed\n", encoding="utf-8")
    with pytest.raises(YAMLParseError):
        read_record(bad)


def test_missing_required_field_raises_schema_error(tmp_path: Path) -> None:
    """Valid YAML but missing required field → SchemaError."""
    # Remove 'status' which is required.
    yaml_no_status = VALID_YAML.replace("status: completed\n", "")
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_no_status, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_missing_required_nested_field_raises_schema_error(tmp_path: Path) -> None:
    """Missing nested required field → SchemaError."""
    # Remove 'schema_version' from provenance.
    yaml_bad = VALID_YAML.replace('  schema_version: "1"\n', "")
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_bad, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_pending_status_raises_schema_error(tmp_path: Path) -> None:
    """status=pending is refused at the read boundary."""
    yaml_pending = VALID_YAML.replace("status: completed", "status: pending").replace('completed_at: "2026-04-27T11:00:00+00:00"\n', "")
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_pending, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    """Absent file → FileNotFoundError (natural propagation from Path.read_text)."""
    absent = tmp_path / "does_not_exist" / "retrospective.yaml"
    with pytest.raises(FileNotFoundError):
        read_record(absent)


def test_valid_yaml_reads_correctly(tmp_path: Path) -> None:
    """A well-formed YAML file deserializes to a RetrospectiveRecord."""
    good = tmp_path / "retrospective.yaml"
    good.write_text(VALID_YAML, encoding="utf-8")
    record = read_record(good)
    assert record.status == "completed"
    assert record.mission.mission_id == MISSION_ID
    assert record.schema_version == "1"


def test_extra_field_raises_schema_error(tmp_path: Path) -> None:
    """Extra unknown top-level field → SchemaError (extra='forbid')."""
    yaml_extra = VALID_YAML + "unknown_field: some_value\n"
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_extra, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_verify_evidence_api_surface(tmp_path: Path) -> None:
    """verify_evidence=True is accepted and returns a valid record (WP03 no-op stub)."""
    good = tmp_path / "retrospective.yaml"
    good.write_text(VALID_YAML, encoding="utf-8")
    # Should not raise; the actual check is deferred to WP03.
    record = read_record(good, verify_evidence=True)
    assert record.status == "completed"


def test_top_level_not_mapping_raises_schema_error(tmp_path: Path) -> None:
    """YAML that parses but is not a mapping → SchemaError."""
    yaml_list = "- item1\n- item2\n"
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_list, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_skipped_record_missing_skip_reason_raises_schema_error(tmp_path: Path) -> None:
    """Skipped record without skip_reason → SchemaError."""
    yaml_skipped = (
        VALID_YAML.replace("status: completed", "status: skipped")
        # skip_reason is absent; completed_at is present (needed for skipped).
    )
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_skipped, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)


def test_failed_record_missing_failure_raises_schema_error(tmp_path: Path) -> None:
    """Failed record without failure → SchemaError."""
    yaml_failed = VALID_YAML.replace("status: completed", "status: failed")
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(yaml_failed, encoding="utf-8")
    with pytest.raises(SchemaError):
        read_record(bad)
