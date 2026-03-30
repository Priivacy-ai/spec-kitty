"""Tests for constitution CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.constitution import app

pytestmark = pytest.mark.fast

runner = CliRunner()


SAMPLE_CONSTITUTION = """# Testing Standards

## Coverage Requirements
- Minimum 80% coverage

## Quality Gates
- Pass all linters

## Project Directives
1. Write tests for new features
"""


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "mock_repo"
    repo_root.mkdir()

    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)

    constitution_file = constitution_dir / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    return repo_root


def test_sync_command_success(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "✅ Constitution synced successfully" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout
        assert "metadata.yaml" in result.stdout


def test_sync_command_already_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result1 = runner.invoke(app, ["sync"])
        assert result1.exit_code == 0

        result2 = runner.invoke(app, ["sync"])
        assert result2.exit_code == 0
        assert "already in sync" in result2.stdout


def test_sync_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["files_written"]) == 3


def test_sync_command_missing_constitution(tmp_path: Path) -> None:
    repo_root = tmp_path / "no_constitution"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 1
        assert "Constitution not found" in result.stdout


def test_status_command_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "✅ SYNCED" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout


def test_status_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "synced"
        assert len(data["files"]) == 4


def test_interview_defaults_writes_answers(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["interview", "--defaults", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"
        answers_path = repo_root / payload["answers_file"]
        assert answers_path.exists()


def test_generate_command_success(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--no-from-interview"])

        assert result.exit_code == 0
        assert "generated and synced" in result.stdout
        assert (repo_root / ".kittify" / "constitution" / "constitution.md").exists()
        assert (repo_root / ".kittify" / "constitution" / "references.yaml").exists()
        assert (repo_root / ".kittify" / "constitution" / "governance.yaml").exists()
        # library/ materialization has been removed; directory must NOT exist.
        assert not (repo_root / ".kittify" / "constitution" / "library").exists()


def test_generate_command_prompts_when_existing_and_user_declines(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "constitution.md").write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        # Simulate user entering "n" at the overwrite prompt.
        result = runner.invoke(app, ["generate", "--no-from-interview"], input="n\n")

        assert result.exit_code == 1
        assert "constitution.md" in result.stdout


def test_generate_command_prompts_when_existing_and_user_confirms(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "constitution.md").write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        # Simulate user entering "y" at the overwrite prompt.
        result = runner.invoke(app, ["generate", "--no-from-interview"], input="y\n")

        assert result.exit_code == 0
        assert "generated and synced" in result.stdout


def test_generate_command_force_overwrites(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    constitution_file = constitution_dir / "constitution.md"
    constitution_file.write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--force", "--no-from-interview", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["result"] == "success"
        assert data["template_set"]
        assert "selected_directives" in data
        assert data["references_count"] >= 1


def test_generate_for_agent_command_success(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(
            app, ["generate-for-agent", "--profile", "reviewer", "--no-from-interview", "--json"]
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["result"] == "success"
        assert data["agent_profile"] == "reviewer"
        assert "selected_directives" in data
        assert (repo_root / ".kittify" / "constitution" / "constitution.md").exists()


def test_generate_for_agent_command_missing_profile_fails(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(
            app, ["generate-for-agent", "--profile", "missing-profile", "--no-from-interview"]
        )

        assert result.exit_code == 1
        assert "missing-profile" in result.stdout


def test_context_bootstrap_then_compact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])
        assert generate_result.exit_code == 0

        first = runner.invoke(app, ["context", "--action", "specify", "--json"])
        assert first.exit_code == 0
        first_payload = json.loads(first.stdout)
        assert first_payload["mode"] == "bootstrap"
        assert first_payload["first_load"] is True

        second = runner.invoke(app, ["context", "--action", "specify", "--json"])
        assert second.exit_code == 0
        second_payload = json.loads(second.stdout)
        assert second_payload["mode"] == "compact"
        assert second_payload["first_load"] is False


def test_interview_json_shape(tmp_path: Path) -> None:
    """interview --json must emit result/answers_file, not success/interview_path."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["interview", "--defaults", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        # New contract keys
        assert "result" in payload
        assert payload["result"] == "success"
        assert "answers_file" in payload
        # Legacy keys must NOT appear
        assert "success" not in payload
        assert "interview_path" not in payload


def test_generate_missing_interview_hard_fails(tmp_path: Path) -> None:
    """generate --from-interview (default) must exit 1 when answers.yaml is absent."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate"])

        assert result.exit_code == 1
        assert "answers.yaml" in result.stdout or "interview" in result.stdout.lower()
        assert "spec-kitty constitution interview" in result.stdout


def test_generate_missing_interview_hard_fails_json(tmp_path: Path) -> None:
    """generate --json must emit {error: ...} when answers.yaml is absent."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert "error" in payload
        assert "result" not in payload


def test_generate_for_agent_missing_interview_hard_fails(tmp_path: Path) -> None:
    """generate-for-agent with --from-interview (default) exits 1 when answers.yaml is absent."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate-for-agent", "--profile", "reviewer"])

        assert result.exit_code == 1
        assert "spec-kitty constitution interview" in result.stdout


def test_generate_for_agent_missing_interview_hard_fails_json(tmp_path: Path) -> None:
    """generate-for-agent --json emits {error: ...} when answers.yaml is absent."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate-for-agent", "--profile", "reviewer", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert "error" in payload
        assert "result" not in payload


def test_generate_json_success_shape(tmp_path: Path) -> None:
    """generate --json must emit result=success (not success=True)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"
        assert "success" not in payload


def test_generate_for_agent_json_success_shape(tmp_path: Path) -> None:
    """generate-for-agent --json must emit result=success (not success=True)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(
            app, ["generate-for-agent", "--profile", "reviewer", "--no-from-interview", "--json"]
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"
        assert "success" not in payload


def test_generate_overwrite_prompt_json_abort_shape(tmp_path: Path) -> None:
    """In JSON mode with conflicts, emits {error: ...} without prompting."""
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "constitution.md").write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert "error" in payload
        assert "result" not in payload
        assert "constitution.md" in payload["error"]


def test_generate_from_interview_when_answers_present(tmp_path: Path) -> None:
    """generate uses interview file when answers.yaml is present."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        # First capture an interview
        interview_result = runner.invoke(app, ["interview", "--defaults"])
        assert interview_result.exit_code == 0

        # Now generate from interview answers
        gen_result = runner.invoke(app, ["generate", "--json"])
        assert gen_result.exit_code == 0
        payload = json.loads(gen_result.stdout)
        assert payload["result"] == "success"
        assert payload["interview_source"] == "interview"


def test_context_json_includes_context_and_depth(tmp_path: Path) -> None:
    """context --json must include 'context' (canonical) and 'depth'; 'text' is removed."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])
        assert generate_result.exit_code == 0

        result = runner.invoke(app, ["context", "--action", "specify", "--no-mark-loaded", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert "context" in payload
        assert "text" not in payload
        assert "depth" in payload
        assert isinstance(payload["depth"], int)


def test_context_json_does_not_duplicate_content_under_text_key(tmp_path: Path) -> None:
    """context --json must not duplicate the constitution content under both 'context' and 'text'.

    The 'text' key is deprecated. The canonical key is 'context'. This acceptance
    test confirms the content appears exactly once in the JSON response — under
    'context' only. The presence of 'text' with the same value as 'context' is
    the bug being guarded against.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])
        assert generate_result.exit_code == 0

        result = runner.invoke(app, ["context", "--action", "specify", "--no-mark-loaded", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert "context" in payload, "canonical 'context' key must be present"
        assert isinstance(payload["context"], str)
        assert payload["context"], "context must be non-empty"

        assert "text" not in payload, (
            "deprecated 'text' key must not appear in JSON output — "
            "it duplicates 'context' and was removed in this remediation"
        )


def test_context_json_depth_option(tmp_path: Path) -> None:
    """context --depth option is passed through and reflected in the JSON output."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])
        assert generate_result.exit_code == 0

        result = runner.invoke(
            app, ["context", "--action", "specify", "--no-mark-loaded", "--depth", "1", "--json"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["depth"] == 1
        assert payload["mode"] == "compact"


def test_help_output() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "constitution" in result.stdout.lower() or "Constitution" in result.stdout
    assert "interview" in result.stdout
    assert "generate" in result.stdout
    assert "context" in result.stdout
    assert "sync" in result.stdout
    assert "status" in result.stdout


# ---------------------------------------------------------------------------
# T009: generate --json success payload shape
# ---------------------------------------------------------------------------


def test_generate_json_payload_includes_new_fields(tmp_path: Path) -> None:
    """generate --json must include constitution_file, references_file, generated_files, library_files."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--no-from-interview", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"
        # New required keys
        assert "constitution_file" in payload
        assert "references_file" in payload
        assert "generated_files" in payload
        assert "library_files" in payload
        # Basic value assertions
        assert payload["constitution_file"].endswith("constitution.md")
        assert payload["references_file"].endswith("references.yaml")
        assert isinstance(payload["generated_files"], list)
        assert isinstance(payload["library_files"], list)
        # No local supporting files → library_files must be empty
        assert payload["library_files"] == []


def test_generate_json_payload_library_files_with_local_support(tmp_path: Path) -> None:
    """library_files in generate --json payload lists paths from local support declarations."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    interview_dir = constitution_dir / "interview"
    interview_dir.mkdir(parents=True)

    # Write an answers.yaml with a local supporting file
    answers = {
        "schema_version": "1.0.0",
        "mission": "software-dev",
        "profile": "minimal",
        "answers": {
            "project_intent": "test",
            "languages_frameworks": "Python",
            "testing_requirements": "pytest",
            "quality_gates": "tests pass",
            "review_policy": "1 reviewer",
            "performance_targets": "N/A",
            "deployment_constraints": "Linux",
        },
        "selected_paradigms": ["test-first"],
        "selected_directives": ["DIRECTIVE_004"],
        "available_tools": ["git"],
        "local_supporting_files": [
            {"path": "docs/custom-guide.md"},
        ],
    }
    import ruamel.yaml as ryaml
    y = ryaml.YAML()
    y.default_flow_style = False
    with (interview_dir / "answers.yaml").open("w") as f:
        y.dump(answers, f)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"
        assert "docs/custom-guide.md" in payload["library_files"]
