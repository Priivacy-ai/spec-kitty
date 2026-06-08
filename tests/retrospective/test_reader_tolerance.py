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

pytestmark = [pytest.mark.unit]

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
    yaml_pending = VALID_YAML.replace("status: completed", "status: pending").replace(
        "completed_at: \"2026-04-27T11:00:00+00:00\"\n", ""
    )
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


def test_legacy_integer_schema_version_reads_correctly(tmp_path: Path) -> None:
    """Older Pydantic-shape records with schema_version: 1 remain readable."""
    legacy_yaml = VALID_YAML.replace('schema_version: "1"', "schema_version: 1")
    good = tmp_path / "retrospective.yaml"
    good.write_text(legacy_yaml, encoding="utf-8")

    record = read_record(good)

    assert record.status == "completed"
    assert record.schema_version == "1"
    assert record.provenance.schema_version == "1"


@pytest.mark.parametrize(
    "mutated_yaml",
    [
        VALID_YAML.replace('schema_version: "1"', "schema_version: true", 1),
        VALID_YAML.replace('schema_version: "1"', "schema_version: 2", 1),
        VALID_YAML.replace('  schema_version: "1"', "  schema_version: 2"),
    ],
)
def test_legacy_schema_version_coercion_stays_narrow(tmp_path: Path, mutated_yaml: str) -> None:
    """Only legacy integer 1 scalars are tolerated."""
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(mutated_yaml, encoding="utf-8")

    with pytest.raises(SchemaError):
        read_record(bad)


def _valid_generator_yaml() -> str:
    return f"""\
schema_version: 1
mission_id: {MISSION_ID}
mission_slug: test-mission
mission_number: 7
friendly_name: Test Mission
mission_type: software-dev
target_branch: main
created_at: "2026-05-21T08:09:55+00:00"
created_by:
  kind: human
  id: cli
  display: spec-kitty retrospect
provenance:
  kind: explicit_create
  invoked_at: "2026-05-21T08:09:55+00:00"
  policy_resolved_from: {{}}
  command: spec-kitty retrospect create
policy_source: {{}}
findings_status: has_findings
helped: []
not_helpful:
  - id: n-001
    category: process
    summary: lane bounce before approval
    evidence_refs: [e-001]
gaps: []
proposals: []
evidence_refs:
  - id: e-001
    kind: event_range
    path: kitty-specs/test-mission/status.events.jsonl
    range: "event-1"
generator_version: "1.0"
provenance_history: []
"""


def test_generator_record_reads_correctly(tmp_path: Path) -> None:
    """The generator record shape written by retrospect create is accepted."""
    good = tmp_path / "retrospective.yaml"
    good.write_text(_valid_generator_yaml(), encoding="utf-8")

    from specify_cli.retrospective.reader import read_gen_record

    record = read_gen_record(good)
    assert record.findings_status == "has_findings"
    assert record.mission_id == MISSION_ID


@pytest.mark.parametrize(
    "mutated_yaml",
    [
        _valid_generator_yaml().replace("schema_version: 1", "schema_version: 2"),
        _valid_generator_yaml().replace("kind: human", "kind: alien", 1),
        _valid_generator_yaml().replace("category: process", "category: nonsense"),
        _valid_generator_yaml().replace("friendly_name: Test Mission\n", ""),
        _valid_generator_yaml() + "unknown_field: no\n",
    ],
)
def test_generator_record_schema_errors_are_rejected(tmp_path: Path, mutated_yaml: str) -> None:
    """Generator reader rejects invalid enums, version drift, and extra fields."""
    bad = tmp_path / "retrospective.yaml"
    bad.write_text(mutated_yaml, encoding="utf-8")

    from specify_cli.retrospective.reader import read_gen_record

    with pytest.raises(SchemaError):
        read_gen_record(bad)


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
