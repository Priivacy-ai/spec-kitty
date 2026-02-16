"""Tests for the glossary management CLI commands.

Tests all three glossary subcommands:
  - glossary list: term listing with scope/status/json filters
  - glossary conflicts: conflict history from event log
  - glossary resolve: interactive conflict resolution

Each test uses tmp_path fixtures with mock glossary seed files and
mock event logs to avoid filesystem coupling.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

# We import the top-level app so the glossary subcommand is registered
from specify_cli.cli.commands.glossary import app as glossary_app

runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_glossary_store(tmp_path):
    """Create mock glossary store with seed files containing test data.

    Creates team_domain and mission_local seed files.
    """
    glossaries_dir = tmp_path / ".kittify" / "glossaries"
    glossaries_dir.mkdir(parents=True)

    team_domain = glossaries_dir / "team_domain.yaml"
    team_domain.write_text(
        "terms:\n"
        "  - surface: workspace\n"
        "    definition: Git worktree directory for a work package\n"
        "    confidence: 0.9\n"
        "    status: active\n"
        "  - surface: mission\n"
        "    definition: Purpose-specific workflow machine\n"
        "    confidence: 1.0\n"
        "    status: active\n"
    )

    mission_local = glossaries_dir / "mission_local.yaml"
    mission_local.write_text(
        "terms:\n"
        "  - surface: primitive\n"
        "    definition: Atomic unit of work in a mission step\n"
        "    confidence: 0.85\n"
        "    status: draft\n"
    )

    return tmp_path


@pytest.fixture
def mock_glossary_empty(tmp_path):
    """Create empty glossary directory (no seed files)."""
    glossaries_dir = tmp_path / ".kittify" / "glossaries"
    glossaries_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_no_glossary(tmp_path):
    """Create repo without glossary directory."""
    return tmp_path


@pytest.fixture
def mock_event_log(tmp_path):
    """Create mock event log with both blocked and resolved conflict events.

    Events:
    - SemanticCheckEvaluated (blocked, 1 finding: workspace, ambiguous, high)
    - GlossaryClarificationResolved (resolves the workspace conflict)
    """
    events_dir = tmp_path / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)

    events = [
        {
            "event_type": "SemanticCheckEvaluated",
            "step_id": "test-001",
            "mission_id": "software-dev",
            "run_id": "run-1",
            "timestamp": "2026-02-16T12:00:00Z",
            "blocked": True,
            "effective_strictness": "medium",
            "findings": [
                {
                    "term": {"surface_text": "workspace"},
                    "conflict_type": "ambiguous",
                    "severity": "high",
                    "confidence": 0.9,
                    "candidate_senses": [
                        {
                            "surface": "workspace",
                            "scope": "team_domain",
                            "definition": "Git worktree directory",
                            "confidence": 0.9,
                        },
                        {
                            "surface": "workspace",
                            "scope": "mission_local",
                            "definition": "IDE workspace folder",
                            "confidence": 0.7,
                        },
                    ],
                    "context": "description field",
                }
            ],
            "overall_severity": "high",
            "confidence": 0.9,
            "recommended_action": "block",
        },
        {
            "event_type": "GlossaryClarificationResolved",
            "conflict_id": "test-001-workspace",
            "term_surface": "workspace",
            "selected_sense": {
                "surface": "workspace",
                "scope": "team_domain",
                "definition": "Git worktree directory",
                "confidence": 0.9,
            },
            "actor": {"actor_id": "user:alice"},
            "resolution_mode": "interactive",
            "provenance": {"source": "user_clarification"},
            "timestamp": "2026-02-16T12:05:00Z",
        },
    ]

    event_file = events_dir / "software-dev.events.jsonl"
    with event_file.open("w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return tmp_path


@pytest.fixture
def mock_event_log_unresolved(tmp_path):
    """Create mock event log with only unresolved conflicts.

    Events:
    - SemanticCheckEvaluated (blocked, 2 findings: workspace and config)
    """
    events_dir = tmp_path / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)

    events = [
        {
            "event_type": "SemanticCheckEvaluated",
            "step_id": "test-002",
            "mission_id": "software-dev",
            "run_id": "run-2",
            "timestamp": "2026-02-16T13:00:00Z",
            "blocked": True,
            "effective_strictness": "max",
            "findings": [
                {
                    "term": {"surface_text": "workspace"},
                    "conflict_type": "ambiguous",
                    "severity": "high",
                    "confidence": 0.9,
                    "candidate_senses": [
                        {
                            "surface": "workspace",
                            "scope": "team_domain",
                            "definition": "Git worktree directory",
                            "confidence": 0.9,
                        },
                    ],
                    "context": "step input",
                },
                {
                    "term": {"surface_text": "config"},
                    "conflict_type": "unknown",
                    "severity": "medium",
                    "confidence": 0.6,
                    "candidate_senses": [],
                    "context": "metadata field",
                },
            ],
            "overall_severity": "high",
            "confidence": 0.9,
            "recommended_action": "block",
        },
    ]

    event_file = events_dir / "software-dev.events.jsonl"
    with event_file.open("w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return tmp_path


@pytest.fixture
def mock_event_log_multi_mission(tmp_path):
    """Create event logs spanning multiple missions."""
    events_dir = tmp_path / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)

    # software-dev mission
    sw_events = [
        {
            "event_type": "SemanticCheckEvaluated",
            "step_id": "sw-001",
            "mission_id": "software-dev",
            "run_id": "run-1",
            "timestamp": "2026-02-16T12:00:00Z",
            "blocked": True,
            "effective_strictness": "medium",
            "findings": [
                {
                    "term": {"surface_text": "workspace"},
                    "conflict_type": "ambiguous",
                    "severity": "high",
                    "confidence": 0.9,
                    "candidate_senses": [],
                    "context": "description",
                }
            ],
            "overall_severity": "high",
            "confidence": 0.9,
            "recommended_action": "block",
        },
    ]

    sw_file = events_dir / "software-dev.events.jsonl"
    with sw_file.open("w") as f:
        for event in sw_events:
            f.write(json.dumps(event) + "\n")

    # documentation mission
    doc_events = [
        {
            "event_type": "SemanticCheckEvaluated",
            "step_id": "doc-001",
            "mission_id": "documentation",
            "run_id": "run-2",
            "timestamp": "2026-02-16T13:00:00Z",
            "blocked": True,
            "effective_strictness": "max",
            "findings": [
                {
                    "term": {"surface_text": "tutorial"},
                    "conflict_type": "unknown",
                    "severity": "low",
                    "confidence": 0.5,
                    "candidate_senses": [],
                    "context": "content",
                }
            ],
            "overall_severity": "low",
            "confidence": 0.5,
            "recommended_action": "warn",
        },
    ]

    doc_file = events_dir / "documentation.events.jsonl"
    with doc_file.open("w") as f:
        for event in doc_events:
            f.write(json.dumps(event) + "\n")

    return tmp_path


@pytest.fixture
def mock_empty_event_log(tmp_path):
    """Create empty events directory (no event log files)."""
    events_dir = tmp_path / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    return tmp_path


# =============================================================================
# Tests: glossary list
# =============================================================================


class TestGlossaryList:
    """Tests for the 'glossary list' command."""

    def test_list_all_scopes(self, mock_glossary_store, monkeypatch):
        """Verify glossary list displays all terms from all scopes."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list"])

        assert result.exit_code == 0
        assert "workspace" in result.stdout
        assert "mission" in result.stdout
        assert "primitive" in result.stdout
        assert "Total: 3 term(s)" in result.stdout

    def test_list_scope_filter(self, mock_glossary_store, monkeypatch):
        """Verify --scope filter restricts output to one scope."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list", "--scope", "team_domain"])

        assert result.exit_code == 0
        assert "workspace" in result.stdout
        assert "mission" in result.stdout
        # primitive is in mission_local, should not appear
        assert "primitive" not in result.stdout
        assert "Total: 2 term(s)" in result.stdout

    def test_list_status_filter(self, mock_glossary_store, monkeypatch):
        """Verify --status filter restricts output by status."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list", "--status", "draft"])

        assert result.exit_code == 0
        assert "primitive" in result.stdout
        # workspace and mission terms (active) should not appear as Term entries
        # Note: "mission" substring also appears in scope name "mission_local"
        # and in the definition, so we check the active terms specifically
        assert "workspace" not in result.stdout
        assert "Total: 1 term(s)" in result.stdout

    def test_list_json_output(self, mock_glossary_store, monkeypatch):
        """Verify --json produces valid JSON output."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 3

        # Check structure
        surfaces = {d["surface"] for d in data}
        assert "workspace" in surfaces
        assert "mission" in surfaces
        assert "primitive" in surfaces

        # Check all fields present
        for item in data:
            assert "surface" in item
            assert "scope" in item
            assert "definition" in item
            assert "status" in item
            assert "confidence" in item

    def test_list_json_with_scope_filter(self, mock_glossary_store, monkeypatch):
        """Verify --json with --scope produces filtered JSON."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(
            glossary_app, ["list", "--json", "--scope", "mission_local"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["surface"] == "primitive"

    def test_list_empty_glossary(self, mock_glossary_empty, monkeypatch):
        """Verify graceful message when glossary has no terms."""
        monkeypatch.chdir(mock_glossary_empty)
        result = runner.invoke(glossary_app, ["list"])

        assert result.exit_code == 0
        assert "No terms found" in result.stdout

    def test_list_no_glossary_dir(self, mock_no_glossary, monkeypatch):
        """Verify error when glossary is not initialized."""
        monkeypatch.chdir(mock_no_glossary)
        result = runner.invoke(glossary_app, ["list"])

        assert result.exit_code == 1
        assert "not initialized" in result.stdout.lower()

    def test_list_invalid_scope(self, mock_glossary_store, monkeypatch):
        """Verify error on invalid --scope value."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list", "--scope", "invalid_scope"])

        assert result.exit_code == 1
        assert "Invalid scope" in result.stdout

    def test_list_invalid_status(self, mock_glossary_store, monkeypatch):
        """Verify error on invalid --status value."""
        monkeypatch.chdir(mock_glossary_store)
        result = runner.invoke(glossary_app, ["list", "--status", "bogus"])

        assert result.exit_code == 1
        assert "Invalid status" in result.stdout

    def test_list_long_definition_truncated(self, tmp_path, monkeypatch):
        """Verify definitions longer than 60 chars are truncated in table."""
        monkeypatch.chdir(tmp_path)
        glossaries_dir = tmp_path / ".kittify" / "glossaries"
        glossaries_dir.mkdir(parents=True)

        long_def = "A" * 100
        seed = glossaries_dir / "team_domain.yaml"
        seed.write_text(
            "terms:\n"
            "  - surface: longterm\n"
            f"    definition: {long_def}\n"
            "    confidence: 0.8\n"
            "    status: active\n"
        )

        result = runner.invoke(glossary_app, ["list"])
        assert result.exit_code == 0
        # In Rich table output, the definition should be truncated with ellipsis
        # Rich uses unicode ellipsis character U+2026
        assert "\u2026" in result.stdout or "..." in result.stdout

    def test_list_long_definition_full_in_json(self, tmp_path, monkeypatch):
        """Verify full definition is preserved in JSON output."""
        monkeypatch.chdir(tmp_path)
        glossaries_dir = tmp_path / ".kittify" / "glossaries"
        glossaries_dir.mkdir(parents=True)

        long_def = "A" * 100
        seed = glossaries_dir / "team_domain.yaml"
        seed.write_text(
            "terms:\n"
            "  - surface: longterm\n"
            f"    definition: {long_def}\n"
            "    confidence: 0.8\n"
            "    status: active\n"
        )

        result = runner.invoke(glossary_app, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data[0]["definition"] == long_def

    def test_list_empty_json_output(self, mock_glossary_empty, monkeypatch):
        """Verify --json with no terms returns empty array."""
        monkeypatch.chdir(mock_glossary_empty)
        result = runner.invoke(glossary_app, ["list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == []


# =============================================================================
# Tests: glossary conflicts
# =============================================================================


class TestGlossaryConflicts:
    """Tests for the 'glossary conflicts' command."""

    def test_conflicts_all(self, mock_event_log, monkeypatch):
        """Verify conflicts command displays all conflicts from event log."""
        monkeypatch.chdir(mock_event_log)
        result = runner.invoke(glossary_app, ["conflicts"])

        assert result.exit_code == 0
        assert "workspace" in result.stdout
        assert "ambiguous" in result.stdout
        assert "high" in result.stdout
        assert "resolved" in result.stdout
        assert "Total: 1 conflict(s)" in result.stdout

    def test_conflicts_unresolved_only(self, mock_event_log, monkeypatch):
        """Verify --unresolved filter excludes resolved conflicts."""
        monkeypatch.chdir(mock_event_log)
        result = runner.invoke(glossary_app, ["conflicts", "--unresolved"])

        assert result.exit_code == 0
        # All conflicts in mock_event_log are resolved
        assert "No conflicts found" in result.stdout
        assert "Total: 0 conflict(s)" in result.stdout

    def test_conflicts_unresolved_present(self, mock_event_log_unresolved, monkeypatch):
        """Verify --unresolved shows unresolved conflicts when they exist."""
        monkeypatch.chdir(mock_event_log_unresolved)
        result = runner.invoke(glossary_app, ["conflicts", "--unresolved"])

        assert result.exit_code == 0
        assert "workspace" in result.stdout
        assert "config" in result.stdout
        assert "Total: 2 conflict(s)" in result.stdout
        assert "Unresolved: 2" in result.stdout

    def test_conflicts_mission_filter(self, mock_event_log_multi_mission, monkeypatch):
        """Verify --mission filter restricts to specific mission."""
        monkeypatch.chdir(mock_event_log_multi_mission)
        result = runner.invoke(
            glossary_app, ["conflicts", "--mission", "documentation"]
        )

        assert result.exit_code == 0
        assert "tutorial" in result.stdout
        assert "workspace" not in result.stdout
        assert "Total: 1 conflict(s)" in result.stdout

    def test_conflicts_strictness_filter(self, mock_event_log_multi_mission, monkeypatch):
        """Verify --strictness filter restricts to specific strictness level."""
        monkeypatch.chdir(mock_event_log_multi_mission)
        result = runner.invoke(
            glossary_app, ["conflicts", "--strictness", "max"]
        )

        assert result.exit_code == 0
        assert "tutorial" in result.stdout
        # workspace conflict has medium strictness, should be filtered out
        assert "Total: 1 conflict(s)" in result.stdout

    def test_conflicts_invalid_strictness(self, mock_event_log, monkeypatch):
        """Verify error on invalid --strictness value."""
        monkeypatch.chdir(mock_event_log)
        result = runner.invoke(
            glossary_app, ["conflicts", "--strictness", "invalid"]
        )

        assert result.exit_code == 1
        assert "Invalid strictness" in result.stdout

    def test_conflicts_json_output(self, mock_event_log, monkeypatch):
        """Verify --json produces valid JSON conflict list."""
        monkeypatch.chdir(mock_event_log)
        result = runner.invoke(glossary_app, ["conflicts", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["term"] == "workspace"
        assert data[0]["status"] == "resolved"
        assert data[0]["type"] == "ambiguous"
        assert data[0]["severity"] == "high"
        assert "effective_strictness" in data[0]

    def test_conflicts_no_events(self, mock_empty_event_log, monkeypatch):
        """Verify graceful message when no events exist."""
        monkeypatch.chdir(mock_empty_event_log)
        result = runner.invoke(glossary_app, ["conflicts"])

        assert result.exit_code == 0
        assert "No events found" in result.stdout

    def test_conflicts_no_events_dir(self, tmp_path, monkeypatch):
        """Verify graceful message when events directory does not exist."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(glossary_app, ["conflicts"])

        assert result.exit_code == 0
        assert "No events found" in result.stdout

    def test_conflicts_json_empty(self, mock_empty_event_log, monkeypatch):
        """Verify --json returns empty array when no events."""
        monkeypatch.chdir(mock_empty_event_log)
        result = runner.invoke(glossary_app, ["conflicts", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == []

    def test_conflicts_malformed_event_skipped(self, tmp_path, monkeypatch):
        """Verify malformed JSONL lines are skipped without crashing."""
        monkeypatch.chdir(tmp_path)
        events_dir = tmp_path / ".kittify" / "events" / "glossary"
        events_dir.mkdir(parents=True)

        event_file = events_dir / "test.events.jsonl"
        good_event = {
            "event_type": "SemanticCheckEvaluated",
            "step_id": "good-001",
            "mission_id": "test",
            "timestamp": "2026-02-16T12:00:00Z",
            "blocked": True,
            "effective_strictness": "medium",
            "findings": [
                {
                    "term": {"surface_text": "valid"},
                    "conflict_type": "unknown",
                    "severity": "low",
                    "confidence": 0.5,
                    "candidate_senses": [],
                    "context": "test",
                }
            ],
        }

        with event_file.open("w") as f:
            f.write("this is not valid json\n")
            f.write(json.dumps(good_event) + "\n")
            f.write("{broken json\n")

        result = runner.invoke(glossary_app, ["conflicts"])
        assert result.exit_code == 0
        assert "valid" in result.stdout
        assert "Total: 1 conflict(s)" in result.stdout

    def test_conflicts_summary_shows_unresolved_count(
        self, mock_event_log_unresolved, monkeypatch
    ):
        """Verify unresolved summary count is displayed."""
        monkeypatch.chdir(mock_event_log_unresolved)
        result = runner.invoke(glossary_app, ["conflicts"])

        assert result.exit_code == 0
        assert "Unresolved: 2" in result.stdout

    def test_conflicts_non_blocked_events_ignored(self, tmp_path, monkeypatch):
        """Verify events with blocked=False are not shown as conflicts."""
        monkeypatch.chdir(tmp_path)
        events_dir = tmp_path / ".kittify" / "events" / "glossary"
        events_dir.mkdir(parents=True)

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "pass-001",
                "mission_id": "test",
                "timestamp": "2026-02-16T12:00:00Z",
                "blocked": False,
                "effective_strictness": "off",
                "findings": [],
            },
        ]

        event_file = events_dir / "test.events.jsonl"
        with event_file.open("w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        result = runner.invoke(glossary_app, ["conflicts"])
        assert result.exit_code == 0
        assert "No events found" not in result.stdout or "No conflicts found" in result.stdout


# =============================================================================
# Tests: glossary resolve
# =============================================================================


class TestGlossaryResolve:
    """Tests for the 'glossary resolve' command."""

    def test_resolve_not_found(self, mock_event_log, monkeypatch):
        """Verify error when conflict ID does not exist."""
        monkeypatch.chdir(mock_event_log)
        result = runner.invoke(glossary_app, ["resolve", "nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_resolve_select_candidate(self, mock_event_log_unresolved, monkeypatch):
        """Verify resolving by selecting a candidate sense."""
        monkeypatch.chdir(mock_event_log_unresolved)

        # Input: select candidate #1
        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace"],
            input="1\n",
        )

        assert result.exit_code == 0
        assert "resolved successfully" in result.stdout.lower()

        # Verify event was written
        event_file = (
            mock_event_log_unresolved
            / ".kittify"
            / "events"
            / "glossary"
            / "software-dev.events.jsonl"
        )
        lines = event_file.read_text().strip().split("\n")
        last_event = json.loads(lines[-1])
        assert last_event["event_type"] == "GlossaryClarificationResolved"
        assert last_event["conflict_id"] == "test-002-workspace"
        assert last_event["resolution_mode"] == "async"

    def test_resolve_custom_definition(self, mock_event_log_unresolved, monkeypatch):
        """Verify resolving with a custom definition."""
        monkeypatch.chdir(mock_event_log_unresolved)

        # Input: 'C' for custom, then the definition
        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace"],
            input="C\nMy custom definition for workspace\n",
        )

        assert result.exit_code == 0
        assert "resolved successfully" in result.stdout.lower()

        # Verify event was written with custom sense
        event_file = (
            mock_event_log_unresolved
            / ".kittify"
            / "events"
            / "glossary"
            / "software-dev.events.jsonl"
        )
        lines = event_file.read_text().strip().split("\n")
        last_event = json.loads(lines[-1])
        assert last_event["event_type"] == "GlossaryClarificationResolved"
        assert last_event["selected_sense"]["definition"] == "My custom definition for workspace"
        assert last_event["selected_sense"]["scope"] == "team_domain"

    def test_resolve_defer(self, mock_event_log_unresolved, monkeypatch):
        """Verify deferring resolution exits cleanly."""
        monkeypatch.chdir(mock_event_log_unresolved)

        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace"],
            input="D\n",
        )

        assert result.exit_code == 0
        assert "deferred" in result.stdout.lower()

    def test_resolve_already_resolved_confirm_no(self, mock_event_log, monkeypatch):
        """Verify already-resolved conflict shows warning, exits on 'no'."""
        monkeypatch.chdir(mock_event_log)

        result = runner.invoke(
            glossary_app,
            ["resolve", "test-001-workspace"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "already resolved" in result.stdout.lower()

    def test_resolve_already_resolved_confirm_yes(self, mock_event_log, monkeypatch):
        """Verify re-resolving an already-resolved conflict when confirmed."""
        monkeypatch.chdir(mock_event_log)

        # Confirm yes, then select candidate 1
        result = runner.invoke(
            glossary_app,
            ["resolve", "test-001-workspace"],
            input="y\n1\n",
        )

        assert result.exit_code == 0
        assert "resolved successfully" in result.stdout.lower()

    def test_resolve_invalid_selection(self, mock_event_log_unresolved, monkeypatch):
        """Verify error on invalid numeric selection."""
        monkeypatch.chdir(mock_event_log_unresolved)

        # Candidate index out of range (only 1 candidate)
        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace"],
            input="99\n",
        )

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()

    def test_resolve_no_events_dir(self, tmp_path, monkeypatch):
        """Verify error when events directory does not exist."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(glossary_app, ["resolve", "any-id"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_resolve_with_mission_flag(self, mock_event_log_unresolved, monkeypatch):
        """Verify --mission flag overrides auto-detected mission."""
        monkeypatch.chdir(mock_event_log_unresolved)

        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace", "--mission", "custom-mission"],
            input="1\n",
        )

        assert result.exit_code == 0
        assert "resolved successfully" in result.stdout.lower()

        # Verify event was written to custom mission log
        custom_file = (
            mock_event_log_unresolved
            / ".kittify"
            / "events"
            / "glossary"
            / "custom-mission.events.jsonl"
        )
        assert custom_file.exists()
        lines = custom_file.read_text().strip().split("\n")
        last_event = json.loads(lines[-1])
        assert last_event["event_type"] == "GlossaryClarificationResolved"

    def test_resolve_shows_conflict_details(self, mock_event_log_unresolved, monkeypatch):
        """Verify conflict details are displayed before prompting."""
        monkeypatch.chdir(mock_event_log_unresolved)

        result = runner.invoke(
            glossary_app,
            ["resolve", "test-002-workspace"],
            input="D\n",
        )

        assert result.exit_code == 0
        assert "workspace" in result.stdout
        assert "ambiguous" in result.stdout
        assert "high" in result.stdout
        assert "Git worktree directory" in result.stdout


# =============================================================================
# Tests: _extract_conflicts_from_events (internal helper)
# =============================================================================


class TestExtractConflicts:
    """Tests for the internal _extract_conflicts_from_events helper."""

    def test_extracts_blocked_findings(self):
        """Verify findings from blocked events are extracted."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "mission_id": "m1",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "medium",
                "findings": [
                    {
                        "term": {"surface_text": "test"},
                        "conflict_type": "unknown",
                        "severity": "low",
                    }
                ],
            }
        ]

        result = _extract_conflicts_from_events(events)
        assert len(result) == 1
        assert result[0]["term"] == "test"
        assert result[0]["conflict_id"] == "s1-test"
        assert result[0]["status"] == "unresolved"

    def test_marks_resolved(self):
        """Verify resolved events mark conflicts as resolved."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "mission_id": "m1",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "medium",
                "findings": [
                    {
                        "term": {"surface_text": "test"},
                        "conflict_type": "ambiguous",
                        "severity": "high",
                    }
                ],
            },
            {
                "event_type": "GlossaryClarificationResolved",
                "conflict_id": "s1-test",
                "timestamp": "2026-01-01T00:01:00Z",
            },
        ]

        result = _extract_conflicts_from_events(events)
        assert len(result) == 1
        assert result[0]["status"] == "resolved"

    def test_skips_non_blocked(self):
        """Verify non-blocked events are ignored."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "blocked": False,
                "findings": [],
            }
        ]

        result = _extract_conflicts_from_events(events)
        assert len(result) == 0

    def test_mission_filter(self):
        """Verify mission filter works."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "mission_id": "m1",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "medium",
                "findings": [{"term": {"surface_text": "a"}, "conflict_type": "unknown", "severity": "low"}],
            },
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s2",
                "mission_id": "m2",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "max",
                "findings": [{"term": {"surface_text": "b"}, "conflict_type": "unknown", "severity": "low"}],
            },
        ]

        result = _extract_conflicts_from_events(events, mission_filter="m1")
        assert len(result) == 1
        assert result[0]["term"] == "a"

    def test_strictness_filter(self):
        """Verify strictness filter works."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "mission_id": "m1",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "medium",
                "findings": [{"term": {"surface_text": "a"}, "conflict_type": "unknown", "severity": "low"}],
            },
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s2",
                "mission_id": "m2",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "max",
                "findings": [{"term": {"surface_text": "b"}, "conflict_type": "unknown", "severity": "low"}],
            },
        ]

        result = _extract_conflicts_from_events(events, strictness_filter="max")
        assert len(result) == 1
        assert result[0]["term"] == "b"

    def test_handles_plain_string_term(self):
        """Verify term as plain string (not dict) is handled."""
        from specify_cli.cli.commands.glossary import _extract_conflicts_from_events

        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "s1",
                "mission_id": "m1",
                "timestamp": "2026-01-01T00:00:00Z",
                "blocked": True,
                "effective_strictness": "medium",
                "findings": [
                    {
                        "term": "plaintext",
                        "conflict_type": "unknown",
                        "severity": "low",
                    }
                ],
            }
        ]

        result = _extract_conflicts_from_events(events)
        assert len(result) == 1
        assert result[0]["term"] == "plaintext"


# =============================================================================
# Tests: _load_store_from_seeds and _get_all_terms_from_store
# =============================================================================


class TestStoreHelpers:
    """Tests for the internal store helper functions."""

    def test_load_store_from_seeds(self, mock_glossary_store):
        """Verify store is populated from seed files."""
        from specify_cli.cli.commands.glossary import _load_store_from_seeds

        store = _load_store_from_seeds(mock_glossary_store)
        assert "team_domain" in store._cache
        assert "workspace" in store._cache["team_domain"]
        assert "mission" in store._cache["team_domain"]
        assert "mission_local" in store._cache
        assert "primitive" in store._cache["mission_local"]

    def test_get_all_terms_no_filter(self, mock_glossary_store):
        """Verify all terms returned without filters."""
        from specify_cli.cli.commands.glossary import (
            _get_all_terms_from_store,
            _load_store_from_seeds,
        )

        store = _load_store_from_seeds(mock_glossary_store)
        terms = _get_all_terms_from_store(store)
        assert len(terms) == 3

    def test_get_all_terms_scope_filter(self, mock_glossary_store):
        """Verify scope filter works."""
        from specify_cli.cli.commands.glossary import (
            _get_all_terms_from_store,
            _load_store_from_seeds,
        )
        from specify_cli.glossary.scope import GlossaryScope

        store = _load_store_from_seeds(mock_glossary_store)
        terms = _get_all_terms_from_store(store, scope_filter=GlossaryScope.TEAM_DOMAIN)
        assert len(terms) == 2
        assert all(t.scope == "team_domain" for t in terms)

    def test_get_all_terms_status_filter(self, mock_glossary_store):
        """Verify status filter works."""
        from specify_cli.cli.commands.glossary import (
            _get_all_terms_from_store,
            _load_store_from_seeds,
        )

        store = _load_store_from_seeds(mock_glossary_store)
        terms = _get_all_terms_from_store(store, status_filter="active")
        assert len(terms) == 2
        assert all(t.status.value == "active" for t in terms)

    def test_get_all_terms_sorted(self, mock_glossary_store):
        """Verify terms are sorted by scope then surface."""
        from specify_cli.cli.commands.glossary import (
            _get_all_terms_from_store,
            _load_store_from_seeds,
        )

        store = _load_store_from_seeds(mock_glossary_store)
        terms = _get_all_terms_from_store(store)
        surfaces = [t.surface.surface_text for t in terms]
        # mission_local comes before team_domain alphabetically
        assert surfaces[0] == "primitive"  # mission_local
        assert "mission" in surfaces
        assert "workspace" in surfaces

    def test_empty_store(self, tmp_path):
        """Verify empty store returns no terms."""
        from specify_cli.cli.commands.glossary import (
            _get_all_terms_from_store,
            _load_store_from_seeds,
        )

        (tmp_path / ".kittify" / "glossaries").mkdir(parents=True)
        store = _load_store_from_seeds(tmp_path)
        terms = _get_all_terms_from_store(store)
        assert len(terms) == 0
