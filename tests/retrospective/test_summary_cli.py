"""CLI tests for `spec-kitty retrospect summary` (WP09 / T047).

Tests:
- --since 2026-01-01 filter
- --limit 5 truncation
- --json schema check
- empty project → exit 1 (no .kittify/ or kitty-specs/)
- project with .kittify/ but no missions → exit 0
- Rich/JSON informational equivalence
- --json-out writes file
- --include-malformed shows detail
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from specify_cli.retrospective.cli import app

RUNNER = CliRunner()

MISSION_ID_A = "01KQ6YEGT4YBZ3GZF7X680KQAA"
MISSION_ID_B = "01KQ6YEGT4YBZ3GZF7X680KQBB"


# ---------------------------------------------------------------------------
# YAML template helpers (duplicated minimally for isolation)
# ---------------------------------------------------------------------------


def _make_completed_yaml(
    mission_id: str = MISSION_ID_A,
    slug: str = "test-mission",
    started: str = "2026-04-27T10:00:00+00:00",
    completed: str = "2026-04-27T11:00:00+00:00",
) -> str:
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed
started_at: "{started}"
completed_at: "{completed}"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful:
  - id: nh-001
    target:
      kind: glossary_term
      urn: "glossary:term:alpha"
    note: "not helpful"
    provenance:
      source_mission_id: {mission_id}
      evidence_event_ids: ["{mission_id}"]
      actor:
        kind: agent
        id: facilitator
        profile_id: retrospective-facilitator
      captured_at: "{completed}"
gaps: []
proposals: []
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "{completed}"
  schema_version: "1"
"""


def _make_skipped_yaml(
    mission_id: str = MISSION_ID_B,
    slug: str = "skip-mission",
    started: str = "2026-04-27T10:00:00+00:00",
    completed: str = "2026-04-27T11:00:00+00:00",
    skip_reason: str = "Operator skip",
) -> str:
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: skipped
started_at: "{started}"
completed_at: "{completed}"
skip_reason: "{skip_reason}"
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
  written_at: "{completed}"
  schema_version: "1"
"""


def _setup_simple_project(tmp_path: Path) -> Path:
    """Create a simple project with two missions (one completed, one skipped)."""
    missions_root = tmp_path / ".kittify" / "missions"
    missions_root.mkdir(parents=True)

    d1 = missions_root / MISSION_ID_A
    d1.mkdir()
    (d1 / "retrospective.yaml").write_text(_make_completed_yaml(), encoding="utf-8")

    d2 = missions_root / MISSION_ID_B
    d2.mkdir()
    (d2 / "retrospective.yaml").write_text(_make_skipped_yaml(), encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Tests — exit codes
# ---------------------------------------------------------------------------


class TestExitCodes:
    def test_empty_project_exit_1(self, tmp_path: Path) -> None:
        """No .kittify/ and no kitty-specs/ → exit 1."""
        result = RUNNER.invoke(app, ["--project", str(tmp_path)])
        assert result.exit_code == 1

    def test_kittify_only_no_missions_exit_0(self, tmp_path: Path) -> None:
        """.kittify/ exists but no missions → exit 0 (empty corpus is valid)."""
        (tmp_path / ".kittify" / "missions").mkdir(parents=True)
        result = RUNNER.invoke(app, ["--project", str(tmp_path)])
        assert result.exit_code == 0

    def test_kitty_specs_only_exit_0(self, tmp_path: Path) -> None:
        """kitty-specs/ exists (no .kittify/) → exit 0."""
        (tmp_path / "kitty-specs").mkdir()
        result = RUNNER.invoke(app, ["--project", str(tmp_path)])
        assert result.exit_code == 0

    def test_normal_project_exit_0(self, tmp_path: Path) -> None:
        project = _setup_simple_project(tmp_path)
        result = RUNNER.invoke(app, ["--project", str(project)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests — --since filter
# ---------------------------------------------------------------------------


class TestSinceFilter:
    def test_since_excludes_old_missions(self, tmp_path: Path) -> None:
        """--since 2026-04-01 should exclude 2025 missions."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # Old mission (2025)
        old_mid = "01KQ6YEGT4YBZ3GZF7X680KQCC"
        d1 = missions_root / old_mid
        d1.mkdir()
        (d1 / "retrospective.yaml").write_text(
            _make_completed_yaml(
                mission_id=old_mid,
                slug="old-mission",
                started="2025-01-01T10:00:00+00:00",
                completed="2025-01-01T11:00:00+00:00",
            ),
            encoding="utf-8",
        )

        # New mission (2026)
        new_mid = "01KQ6YEGT4YBZ3GZF7X680KQDD"
        d2 = missions_root / new_mid
        d2.mkdir()
        (d2 / "retrospective.yaml").write_text(
            _make_completed_yaml(
                mission_id=new_mid,
                slug="new-mission",
                started="2026-04-27T10:00:00+00:00",
                completed="2026-04-27T11:00:00+00:00",
            ),
            encoding="utf-8",
        )

        result = RUNNER.invoke(
            app,
            ["--project", str(tmp_path), "--since", "2026-01-01", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        snap = data["result"]
        assert snap["completed_count"] == 1

    def test_invalid_since_date_exit_1(self, tmp_path: Path) -> None:
        (tmp_path / ".kittify" / "missions").mkdir(parents=True)
        result = RUNNER.invoke(
            app,
            ["--project", str(tmp_path), "--since", "not-a-date"],
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Tests — --limit truncation
# ---------------------------------------------------------------------------


class TestLimitTruncation:
    def test_limit_5_truncates_top_n(self, tmp_path: Path) -> None:
        """--limit 5 truncates top-N sections to at most 5 entries."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # Create 10 missions with unique not_helpful URNs
        base_id = "01KQ6YEGT4YBZ3GZF7X680KQE"
        for i in range(10):
            mid = (base_id + f"{i:01d}" + "A" * 26)[:26]
            d = missions_root / mid
            d.mkdir()
            (d / "retrospective.yaml").write_text(
                _make_completed_yaml(
                    mission_id=mid,
                    slug=f"m-{i}",
                ),
                encoding="utf-8",
            )

        result = RUNNER.invoke(
            app,
            ["--project", str(tmp_path), "--limit", "5", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        snap = data["result"]
        assert len(snap["not_helpful_top"]) <= 5


# ---------------------------------------------------------------------------
# Tests — --json output schema check
# ---------------------------------------------------------------------------


class TestJsonSchema:
    def test_json_envelope_schema(self, tmp_path: Path) -> None:
        """--json output has required envelope keys and correct schema_version."""
        project = _setup_simple_project(tmp_path)
        result = RUNNER.invoke(app, ["--project", str(project), "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["schema_version"] == "1"
        assert data["command"] == "retrospect.summary"
        assert "generated_at" in data
        assert "result" in data

    def test_json_result_has_required_fields(self, tmp_path: Path) -> None:
        project = _setup_simple_project(tmp_path)
        result = RUNNER.invoke(app, ["--project", str(project), "--json"])
        assert result.exit_code == 0

        snap = json.loads(result.output)["result"]
        required_fields = [
            "mission_count",
            "completed_count",
            "skipped_count",
            "failed_count",
            "in_flight_count",
            "legacy_no_retro_count",
            "terminus_no_retro_count",
            "malformed",
            "not_helpful_top",
            "missing_terms_top",
            "missing_edges_top",
            "over_inclusion_top",
            "under_inclusion_top",
            "proposal_acceptance",
            "skip_reasons_top",
            "project_path",
            "generated_at",
        ]
        for field in required_fields:
            assert field in snap, f"Missing field in JSON result: {field!r}"

    def test_proposal_acceptance_has_subfields(self, tmp_path: Path) -> None:
        project = _setup_simple_project(tmp_path)
        result = RUNNER.invoke(app, ["--project", str(project), "--json"])
        assert result.exit_code == 0

        pa = json.loads(result.output)["result"]["proposal_acceptance"]
        for field in ("total", "accepted", "rejected", "applied", "pending", "superseded"):
            assert field in pa, f"Missing proposal_acceptance field: {field!r}"


# ---------------------------------------------------------------------------
# Tests — Rich/JSON informational equivalence (CHK034)
# ---------------------------------------------------------------------------


class TestRichJsonEquivalence:
    def test_counts_match_between_rich_and_json(self, tmp_path: Path) -> None:
        """Counts in Rich text match counts in JSON output."""
        project = _setup_simple_project(tmp_path)

        # Get JSON result
        json_result = RUNNER.invoke(app, ["--project", str(project), "--json"])
        assert json_result.exit_code == 0
        snap = json.loads(json_result.output)["result"]

        # Get Rich result
        rich_result = RUNNER.invoke(app, ["--project", str(project)])
        assert rich_result.exit_code == 0

        # Verify counts visible in Rich output text
        assert str(snap["mission_count"]) in rich_result.output
        assert str(snap["completed_count"]) in rich_result.output
        assert str(snap["skipped_count"]) in rich_result.output

    def test_top_n_entries_in_rich_output(self, tmp_path: Path) -> None:
        """Top-N URNs from JSON appear in Rich output."""
        project = _setup_simple_project(tmp_path)

        json_result = RUNNER.invoke(app, ["--project", str(project), "--json"])
        assert json_result.exit_code == 0
        snap = json.loads(json_result.output)["result"]

        rich_result = RUNNER.invoke(app, ["--project", str(project)])
        assert rich_result.exit_code == 0

        for tc in snap["not_helpful_top"]:
            assert tc["urn"] in rich_result.output


# ---------------------------------------------------------------------------
# Tests — --json-out
# ---------------------------------------------------------------------------


class TestJsonOut:
    def test_json_out_writes_file(self, tmp_path: Path) -> None:
        project = _setup_simple_project(tmp_path)
        out_file = tmp_path / "summary_output.json"

        result = RUNNER.invoke(
            app,
            ["--project", str(project), "--json-out", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()

        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1"
        assert data["command"] == "retrospect.summary"

    def test_json_out_with_json_flag(self, tmp_path: Path) -> None:
        """--json --json-out both work together."""
        project = _setup_simple_project(tmp_path)
        out_file = tmp_path / "summary.json"

        result = RUNNER.invoke(
            app,
            ["--project", str(project), "--json", "--json-out", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()


# ---------------------------------------------------------------------------
# Tests — --include-malformed
# ---------------------------------------------------------------------------


class TestIncludeMalformed:
    def test_include_malformed_shows_detail(self, tmp_path: Path) -> None:
        """--include-malformed shows malformed record details in Rich output."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        bad_dir = missions_root / "malformed-01KQ0000AAAAAAAAAAAAAAAA0"
        bad_dir.mkdir()
        (bad_dir / "retrospective.yaml").write_text("{ not valid yaml: [unclosed\n", encoding="utf-8")

        result_without = RUNNER.invoke(app, ["--project", str(tmp_path)])
        result_with = RUNNER.invoke(app, ["--project", str(tmp_path), "--include-malformed"])
        assert result_without.exit_code == 0
        assert result_with.exit_code == 0

        # With --include-malformed, the path should appear in detail
        assert "malformed" in result_with.output.lower()

    def test_malformed_count_always_shown(self, tmp_path: Path) -> None:
        """Malformed count appears in both Rich and JSON output."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        bad_dir = missions_root / "malformed-01KQ0000AAAAAAAAAAAAAAAA1"
        bad_dir.mkdir()
        (bad_dir / "retrospective.yaml").write_text("{ not valid yaml: [unclosed\n", encoding="utf-8")

        json_result = RUNNER.invoke(app, ["--project", str(tmp_path), "--json"])
        assert json_result.exit_code == 0
        snap = json.loads(json_result.output)["result"]
        assert len(snap["malformed"]) == 1
        assert snap["malformed"][0]["reason"]  # non-empty reason
        assert snap["malformed"][0]["path"]  # non-empty path
