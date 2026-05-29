"""Regression coverage for charter ``--json`` error-path parseability."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from charter.resolution import NotInsideRepositoryError
from charter.synthesizer.errors import TopicSelectorUnresolvedError
from specify_cli.cli.commands.charter import app as charter_app
from specify_cli.cli.commands.charter_bundle import app as bundle_app
from specify_cli.task_utils import TaskCliError

pytestmark = [pytest.mark.unit]

runner = CliRunner()


def _assert_json_error(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert payload["result"] == "error"
    assert payload["success"] is False
    assert isinstance(payload["error"], str)
    assert payload["error"]
    return payload


@pytest.mark.parametrize(
    ("argv", "exit_code"),
    [
        (["context", "--action", "specify", "--json"], 1),
        (["interview", "--defaults", "--profile", "minimal", "--json"], 1),
        (["sync", "--json"], 1),
        (["resynthesize", "--list-topics", "--json"], 1),
        (["lint", "--json"], 1),
    ],
)
def test_charter_json_commands_emit_parseable_error_when_repo_root_missing(
    argv: list[str],
    exit_code: int,
) -> None:
    with patch(
        "specify_cli.cli.commands.charter.find_repo_root",
        side_effect=TaskCliError("repo root unavailable"),
    ):
        result = runner.invoke(charter_app, argv)

    assert result.exit_code == exit_code, result.output
    payload = _assert_json_error(result.output)
    assert payload["error"] == "repo root unavailable"


def test_resynthesize_json_unresolved_topic_error_is_parseable(tmp_path: Path) -> None:
    evidence_result = SimpleNamespace(warnings=[], bundle=SimpleNamespace())
    unresolved = TopicSelectorUnresolvedError(
        raw="does-not-exist",
        candidates=("directive:PROJECT_001",),
        attempted_forms=("kind_slug",),
    )

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.charter._collect_evidence_result", return_value=evidence_result),
        patch("specify_cli.cli.commands.charter._build_synthesis_request", return_value=(SimpleNamespace(), SimpleNamespace())),
        patch("charter.synthesizer.resynthesize_pipeline.run", side_effect=unresolved),
    ):
        result = runner.invoke(charter_app, ["resynthesize", "--topic", "does-not-exist", "--json"])

    assert result.exit_code == 2, result.output
    payload = _assert_json_error(result.output)
    assert "does-not-exist" in str(payload["error"])
    assert "directive:PROJECT_001" in str(payload["error"])


def test_bundle_validate_json_resolver_error_is_parseable() -> None:
    with patch(
        "specify_cli.cli.commands.charter_bundle.resolve_canonical_repo_root",
        side_effect=NotInsideRepositoryError("not a repo"),
    ):
        result = runner.invoke(bundle_app, ["validate", "--json"])

    assert result.exit_code == 2, result.output
    payload = _assert_json_error(result.output)
    assert "not a repo" in str(payload["error"])
