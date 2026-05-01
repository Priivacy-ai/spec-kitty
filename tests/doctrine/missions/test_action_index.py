"""Tests for doctrine.missions.action_index.load_action_index.

Targets mutation-prone areas:
- Path construction (mission / "actions" / action / "index.yaml")
- Fallback behavior (missing file, invalid YAML, non-dict data)
- Per-field list extraction (_str_list helper)

Patterns: Boundary Pair (file present/absent), Non-Identity Inputs (distinct
field values), Bi-Directional Logic (fallback vs. populated ActionIndex).
"""

from pathlib import Path

import pytest

from doctrine.missions.action_index import ActionIndex, load_action_index

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _write_index(root: Path, mission: str, action: str, text: str) -> Path:
    d = root / mission / "actions" / action
    d.mkdir(parents=True, exist_ok=True)
    p = d / "index.yaml"
    p.write_text(text)
    return p


# ── Fallback behavior ──────────────────────────────────────────────────────────


class TestLoadActionIndexFallback:
    """Fallback ActionIndex returned when file cannot be loaded."""

    def test_missing_file_returns_fallback(self, tmp_path: Path):
        result = load_action_index(tmp_path, "software-dev", "implement")
        assert isinstance(result, ActionIndex)
        assert result.action == "implement"
        assert result.directives == []
        assert result.tactics == []

    def test_fallback_action_name_matches_argument(self, tmp_path: Path):
        result = load_action_index(tmp_path, "any-mission", "review")
        assert result.action == "review"

    def test_invalid_yaml_returns_fallback(self, tmp_path: Path):
        _write_index(tmp_path, "m", "act", "bad: yaml: {")
        result = load_action_index(tmp_path, "m", "act")
        assert result.action == "act"
        assert result.directives == []

    def test_non_dict_yaml_returns_fallback(self, tmp_path: Path):
        _write_index(tmp_path, "m", "act", "- item1\n- item2\n")
        result = load_action_index(tmp_path, "m", "act")
        assert result.action == "act"
        assert result.directives == []

    def test_empty_yaml_returns_fallback(self, tmp_path: Path):
        _write_index(tmp_path, "m", "act", "")
        result = load_action_index(tmp_path, "m", "act")
        assert result.action == "act"
        assert result.directives == []


# ── Happy path — path construction ────────────────────────────────────────────


class TestLoadActionIndexPathConstruction:
    """Verify the path used is mission/actions/action/index.yaml."""

    def test_reads_from_correct_path(self, tmp_path: Path):
        # Only the exact path should be found
        yaml = "directives:\n  - DIR-001\n"
        _write_index(tmp_path, "software-dev", "implement", yaml)
        result = load_action_index(tmp_path, "software-dev", "implement")
        assert result.directives == ["DIR-001"]

    def test_wrong_action_name_yields_fallback(self, tmp_path: Path):
        _write_index(tmp_path, "software-dev", "implement", "directives:\n  - DIR-001\n")
        result = load_action_index(tmp_path, "software-dev", "review")
        assert result.directives == []

    def test_wrong_mission_name_yields_fallback(self, tmp_path: Path):
        _write_index(tmp_path, "software-dev", "implement", "directives:\n  - DIR-001\n")
        result = load_action_index(tmp_path, "other-mission", "implement")
        assert result.directives == []


# ── Field extraction ───────────────────────────────────────────────────────────


class TestLoadActionIndexFields:
    """Each field populated from YAML independently."""

    def test_directives_populated(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "directives:\n  - DIR-001\n  - DIR-002\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.directives == ["DIR-001", "DIR-002"]

    def test_tactics_populated(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "tactics:\n  - tactic-alpha\n  - tactic-beta\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.tactics == ["tactic-alpha", "tactic-beta"]

    def test_styleguides_populated(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "styleguides:\n  - style-x\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.styleguides == ["style-x"]

    def test_toolguides_populated(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "toolguides:\n  - tool-y\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.toolguides == ["tool-y"]

    def test_procedures_populated(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "procedures:\n  - proc-z\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.procedures == ["proc-z"]

    def test_all_fields_populated(self, tmp_path: Path):
        yaml = (
            "action: custom-action\ndirectives:\n  - DIR-001\ntactics:\n  - tactic-a\nstyleguides:\n  - style-b\ntoolguides:\n  - tool-c\nprocedures:\n  - proc-d\n"
        )
        _write_index(tmp_path, "m", "act", yaml)
        result = load_action_index(tmp_path, "m", "act")
        assert result.action == "custom-action"
        assert result.directives == ["DIR-001"]
        assert result.tactics == ["tactic-a"]
        assert result.styleguides == ["style-b"]
        assert result.toolguides == ["tool-c"]
        assert result.procedures == ["proc-d"]

    def test_missing_field_defaults_to_empty_list(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "directives:\n  - DIR-001\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.tactics == []
        assert result.styleguides == []
        assert result.toolguides == []
        assert result.procedures == []

    def test_action_field_overrides_argument(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "action: renamed-action\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.action == "renamed-action"

    def test_non_list_field_value_returns_empty_list(self, tmp_path: Path):
        _write_index(tmp_path, "m", "a", "directives: not-a-list\n")
        result = load_action_index(tmp_path, "m", "a")
        assert result.directives == []
