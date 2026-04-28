"""Strict envelope shape test for ``charter synthesize --dry-run --json``.

WP03 / T013 — locks the JSON shape declared in
``contracts/charter-synthesize-dry-run.json``:

    {
      "result": "success" | "blocked" | "error",
      "adapter": "<adapter-id>",
      "planned_artifacts": [{"path": "...", "kind": "..."}, ...],
      "warnings": [...]   # optional
    }

The dry-run path itself is exercised inside the Typer CliRunner so we hit
the real ``--json`` writer in ``charter synthesize``. The fixture-corpus
gap that motivates WP03's auto-stub is sidestepped here by patching
``_run_synthesis_dry_run`` to return a stable list of staged selectors —
this test locks the **envelope shape**, not the synthesis output. The
on-disk artifact assertion lives in
``test_synthesize_writes_artifacts.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app

pytestmark = pytest.mark.fast

runner = CliRunner()


def _write_interview_answers(repo_root: Path) -> None:
    """Write minimal interview answers YAML so the dry-run can build a request."""
    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers_path.write_text(
        """\
schema_version: '1'
mission: software-dev
profile: minimal
answers:
  mission_type: software_dev
  testing_philosophy: test-driven
  neutrality_posture: balanced
  risk_appetite: moderate
  language_scope: python
selected_paradigms: []
selected_directives:
  - DIRECTIVE_003
available_tools: []
""",
        encoding="utf-8",
    )


class TestStrictDryRunEnvelope:
    def test_envelope_required_keys_present(self, tmp_path: Path) -> None:
        _write_interview_answers(tmp_path)

        with (
            patch(
                "specify_cli.cli.commands.charter.find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.charter._run_synthesis_dry_run",
                return_value=["directive:mission-type-scope-directive"],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        assert result.exit_code == 0, result.output
        # stdout MUST be exactly one JSON document — strict parse.
        data = json.loads(result.output)
        assert {"result", "adapter", "planned_artifacts"} <= set(data.keys())

    def test_envelope_result_is_enum_value(self, tmp_path: Path) -> None:
        _write_interview_answers(tmp_path)

        with (
            patch(
                "specify_cli.cli.commands.charter.find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.charter._run_synthesis_dry_run",
                return_value=["directive:mission-type-scope-directive"],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        data = json.loads(result.output)
        assert data["result"] in {"success", "blocked", "error"}

    def test_envelope_adapter_is_echoed(self, tmp_path: Path) -> None:
        _write_interview_answers(tmp_path)

        with (
            patch(
                "specify_cli.cli.commands.charter.find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.charter._run_synthesis_dry_run",
                return_value=["directive:mission-type-scope-directive"],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        data = json.loads(result.output)
        assert data["adapter"] == "fixture"

    def test_envelope_planned_artifacts_shape(self, tmp_path: Path) -> None:
        _write_interview_answers(tmp_path)

        with (
            patch(
                "specify_cli.cli.commands.charter.find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.charter._run_synthesis_dry_run",
                return_value=[
                    "directive:mission-type-scope-directive",
                    "tactic:testing-philosophy-tactic",
                    "styleguide:python-style-guide",
                ],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        data = json.loads(result.output)
        assert isinstance(data["planned_artifacts"], list)
        assert len(data["planned_artifacts"]) >= 1
        kinds_seen: set[str] = set()
        for entry in data["planned_artifacts"]:
            assert isinstance(entry, dict)
            assert {"path", "kind"} <= set(entry.keys())
            assert isinstance(entry["path"], str)
            assert isinstance(entry["kind"], str)
            assert entry["path"].startswith(".kittify/doctrine/")
            kinds_seen.add(entry["kind"])
        assert {"directive", "tactic", "styleguide"} <= kinds_seen

    def test_warnings_field_is_array_when_present(self, tmp_path: Path) -> None:
        _write_interview_answers(tmp_path)

        with (
            patch(
                "specify_cli.cli.commands.charter.find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.charter._run_synthesis_dry_run",
                return_value=["directive:mission-type-scope-directive"],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        data = json.loads(result.output)
        if "warnings" in data:
            assert isinstance(data["warnings"], list)
            for entry in data["warnings"]:
                assert isinstance(entry, dict)
                assert {"code", "message"} <= set(entry.keys())
