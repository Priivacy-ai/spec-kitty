"""Integration tests for ``spec-kitty glossary validate`` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast
from typer.testing import CliRunner

from specify_cli.cli.commands.glossary import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SEED = """\
terms:
  - surface: deployment target
    definition: A server or environment where code is released.
  - surface: rollback
    definition: Reverting to a previous release.
"""

INVALID_SURFACE_SEED = """\
terms:
  - surface: Deployment Target
    definition: A server or environment where code is released.
"""

MISSING_DEFINITION_SEED = """\
terms:
  - surface: rollback
    definition: ""
"""

BAD_YAML = """\
terms:
  - surface: hello
    definition: [unterminated
"""


# ---------------------------------------------------------------------------
# Single-file mode
# ---------------------------------------------------------------------------


class TestValidateSingleFileValid:
    """Valid file produces exit 0 and success output."""

    def test_exit_code_zero(self, tmp_path: Path) -> None:
        seed = tmp_path / "spec_kitty_core.yaml"
        seed.write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert result.exit_code == 0

    def test_human_output_shows_valid(self, tmp_path: Path) -> None:
        seed = tmp_path / "spec_kitty_core.yaml"
        seed.write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert "Valid" in result.output
        assert "2 terms" in result.output


class TestValidateSingleFileInvalidSurface:
    """Non-normalized surface produces exit 1 with error details."""

    def test_exit_code_one(self, tmp_path: Path) -> None:
        seed = tmp_path / "bad.yaml"
        seed.write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert result.exit_code == 1

    def test_human_output_mentions_surface(self, tmp_path: Path) -> None:
        seed = tmp_path / "bad.yaml"
        seed.write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert "surface" in result.output.lower()
        assert "normalized" in result.output.lower()


class TestValidateSingleFileMissingDefinition:
    """Empty definition produces exit 1 with error details."""

    def test_exit_code_one(self, tmp_path: Path) -> None:
        seed = tmp_path / "bad.yaml"
        seed.write_text(MISSING_DEFINITION_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert result.exit_code == 1

    def test_human_output_mentions_definition(self, tmp_path: Path) -> None:
        seed = tmp_path / "bad.yaml"
        seed.write_text(MISSING_DEFINITION_SEED)
        result = runner.invoke(app, ["validate", str(seed)])
        assert "definition" in result.output.lower()


class TestValidateYamlParseError:
    """Malformed YAML produces exit 1."""

    def test_exit_code_one(self, tmp_path: Path) -> None:
        seed = tmp_path / "broken.yaml"
        seed.write_text(BAD_YAML)
        result = runner.invoke(app, ["validate", str(seed)])
        assert result.exit_code == 1

    def test_human_output_mentions_parse_error(self, tmp_path: Path) -> None:
        seed = tmp_path / "broken.yaml"
        seed.write_text(BAD_YAML)
        result = runner.invoke(app, ["validate", str(seed)])
        assert "YAML parse error" in result.output or "parse error" in result.output.lower()


# ---------------------------------------------------------------------------
# Directory mode
# ---------------------------------------------------------------------------


class TestValidateDirectoryMixed:
    """Directory with valid and invalid files reports summary and exit 1."""

    def test_exit_code_one(self, tmp_path: Path) -> None:
        (tmp_path / "spec_kitty_core.yaml").write_text(VALID_SEED)
        (tmp_path / "team_domain.yaml").write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 1

    def test_summary_output(self, tmp_path: Path) -> None:
        (tmp_path / "spec_kitty_core.yaml").write_text(VALID_SEED)
        (tmp_path / "team_domain.yaml").write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert "1 of 2" in result.output
        assert "failed" in result.output.lower()


class TestValidateDirectoryAllValid:
    """Directory where every file is valid produces exit 0."""

    def test_exit_code_zero(self, tmp_path: Path) -> None:
        (tmp_path / "spec_kitty_core.yaml").write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 0

    def test_all_valid_message(self, tmp_path: Path) -> None:
        (tmp_path / "spec_kitty_core.yaml").write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert "valid" in result.output.lower()


class TestValidateEmptyDirectory:
    """Empty directory (no .yaml files) produces exit 0."""

    def test_exit_code_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 0

    def test_no_files_message(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert "No .yaml files" in result.output


class TestValidateUnknownScopeFilename:
    """Unknown scope filename produces a warning (yellow), not an error."""

    def test_warning_in_human_output(self, tmp_path: Path) -> None:
        (tmp_path / "custom_scope.yaml").write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        # Should succeed (exit 0) but warn about unknown scope
        assert result.exit_code == 0
        assert "not a recognized scope filename" in result.output


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestValidateJsonOutputValid:
    """--json flag produces valid JSON with correct structure for valid file."""

    def test_json_structure(self, tmp_path: Path) -> None:
        seed = tmp_path / "spec_kitty_core.yaml"
        seed.write_text(VALID_SEED)
        result = runner.invoke(app, ["validate", str(seed), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_files"] == 1
        assert data["valid_files"] == 1
        assert data["invalid_files"] == 0
        assert len(data["files"]) == 1
        assert data["files"][0]["valid"] is True
        assert data["files"][0]["term_count"] == 2
        assert data["files"][0]["errors"] == []


class TestValidateJsonOutputInvalid:
    """--json flag produces valid JSON with errors for invalid file."""

    def test_json_structure(self, tmp_path: Path) -> None:
        seed = tmp_path / "bad.yaml"
        seed.write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(seed), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["total_files"] == 1
        assert data["valid_files"] == 0
        assert data["invalid_files"] == 1
        assert len(data["files"]) == 1
        assert data["files"][0]["valid"] is False
        assert len(data["files"][0]["errors"]) >= 1
        err = data["files"][0]["errors"][0]
        assert "term_index" in err
        assert "term_surface" in err
        assert "field" in err
        assert "message" in err


class TestValidateJsonOutputDirectory:
    """--json flag works in directory mode."""

    def test_json_structure(self, tmp_path: Path) -> None:
        (tmp_path / "spec_kitty_core.yaml").write_text(VALID_SEED)
        (tmp_path / "team_domain.yaml").write_text(INVALID_SURFACE_SEED)
        result = runner.invoke(app, ["validate", str(tmp_path), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["total_files"] == 2
        assert data["valid_files"] == 1
        assert data["invalid_files"] == 1


class TestValidateJsonOutputYamlError:
    """--json flag works for YAML parse errors."""

    def test_json_structure(self, tmp_path: Path) -> None:
        seed = tmp_path / "broken.yaml"
        seed.write_text(BAD_YAML)
        result = runner.invoke(app, ["validate", str(seed), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["invalid_files"] == 1
        assert "YAML parse error" in data["files"][0]["errors"][0]["message"]


class TestValidateJsonOutputEmptyDirectory:
    """--json flag for empty directory returns empty results."""

    def test_json_structure(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_files"] == 0
        assert data["valid_files"] == 0
        assert data["invalid_files"] == 0
        assert data["files"] == []
