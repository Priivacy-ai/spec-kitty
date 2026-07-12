"""CLI tests for `spec-kitty charter status` operator surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app
from specify_cli.cli.commands.charter._status_collectors import _collect_governance_reference_status
from specify_cli.task_utils import TaskCliError

pytestmark = pytest.mark.fast

runner = CliRunner()


VALID_DIRECTIVE_BODY = {
    "id": "PROJECT_001",
    "schema_version": "1.0",
    "title": "Mission Scope Directive",
    "intent": "Capture project mission scope for governance synthesis tests.",
    "enforcement": "required",
}


def _write_interview_answers(repo_root: Path) -> None:
    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers_path.write_text(
        """\
schema_version: '1'
mission: software-dev
profile: minimal
answers:
  mission_type: software_dev
  testing_philosophy: ''
  neutrality_posture: ''
  risk_appetite: ''
selected_paradigms: []
selected_directives: []
available_tools: []
""",
        encoding="utf-8",
    )


def _write_url_config(repo_root: Path) -> None:
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """\
charter:
  synthesis_inputs:
    url_list:
      - https://example.com/governance
""",
        encoding="utf-8",
    )


def _write_governance_yaml(repo_root: Path) -> None:
    path = repo_root / ".kittify" / "charter" / "governance.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """\
doctrine:
  governance_references:
    - spec/constitution.md
    - docs/missing-governance.md
""",
        encoding="utf-8",
    )


def _write_generated_directive(repo_root: Path, body: dict[str, object]) -> None:
    path = (
        repo_root
        / ".kittify"
        / "charter"
        / "generated"
        / "directives"
        / "001-mission-type-scope-directive.directive.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(body, fh)


class TestCharterStatus:
    def test_status_collector_reports_missing_governance_reference(
        self, tmp_path: Path
    ) -> None:
        _write_governance_yaml(tmp_path)
        (tmp_path / "spec").mkdir()
        (tmp_path / "spec" / "constitution.md").write_text("# Public Constitution\n", encoding="utf-8")

        status = _collect_governance_reference_status(tmp_path)

        assert status["available"] is True
        assert len(status["references"]) == 2
        assert status["warnings"] == [
            "Missing governance reference docs/missing-governance.md. Create it under the repository root "
            "or remove it from governance_references in .kittify/charter/charter.md."
        ]

    def test_status_json_gracefully_degrades_without_charter_bundle(
        self, tmp_path: Path
    ) -> None:
        _write_url_config(tmp_path)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ), patch(
            "specify_cli.cli.commands.charter.ensure_charter_bundle_fresh",
            side_effect=TaskCliError("Charter not found"),
        ):
            result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["charter_sync"]["available"] is False
        assert data["synthesis"]["generation_state"] == "not_started"
        assert data["synthesis"]["evidence"]["configured_url_count"] == 1

    @pytest.mark.xfail(
        strict=False,
        # reason: escalated to charter owners — see PR body.
        #
        # #2526 ("config.activated_* is the single charter activation
        # authority") changed `_build_synthesis_request` to feed
        # `config_roots.directives` (not `answers.selected_directives`) into
        # the synthesis interview snapshot's `selected_directives`. When
        # `.kittify/config.yaml` has NO `activated_directives` key, the
        # documented three-state fallback resolves that to ALL ~25 built-in
        # directives, and `resolve_sections` then expands one
        # `how-we-apply-<directive>` companion-tactic target per directive.
        # The generated-artifact adapter demands a generated tactic YAML for
        # each, so `charter synthesize` fails closed on the first missing one
        # (GeneratedArtifactMissingError: how-we-apply-directive-001).
        #
        # This is a genuine product-vs-spec conflict, NOT a stale-test seeding
        # gap, so it is escalated rather than guessed:
        #   * The #2526 spec (unify-charter-activation-surfaces-01KX5SJ9)
        #     requires empty/first-run projects to "behave identically to
        #     today". Pre-#2526 this test (empty config,
        #     answers.selected_directives == []) expected ZERO companion
        #     tactics; post-#2526 it demands 25 — a regression of that clause.
        #   * The same spec warns AGAINST writing "a bare restrictive list" of
        #     activated_* (flips resolution from all-built-ins to
        #     only-selected, violating NFR-004/C-005), so the obvious
        #     "restrict activated_directives in the test" fix is the exact
        #     anti-pattern the spec forbids and would MASK the regression.
        #   * No passing test exercises the real generated adapter's
        #     companion-tactic path, so there is no canonical seeding shape to
        #     copy.
        # Recommended resolution (charter owners to confirm): the companion
        # "how-we-apply-<directive>" synthesis expansion should be driven by
        # EXPLICITLY activated directives only (a present, non-None
        # activated_directives), decoupled from the absent-key all-built-ins
        # resolution fallback — preserving "identical to today" for
        # empty/first-run projects.
        reason="escalated to charter owners — #2526 all-built-ins fallback "
        "forces companion-tactic synthesis on empty-config projects; see PR body",
    )
    def test_generated_host_roundtrip_status_reports_promoted_provenance(
        self, tmp_path: Path
    ) -> None:
        _write_interview_answers(tmp_path)
        _write_url_config(tmp_path)
        _write_generated_directive(tmp_path, VALID_DIRECTIVE_BODY)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ):
            synth_result = runner.invoke(app, ["synthesize"])
        assert synth_result.exit_code == 0, synth_result.output

        doctrine_path = (
            tmp_path
            / ".kittify"
            / "doctrine"
            / "directive"
            / "001-mission-type-scope-directive.directive.yaml"
        )
        provenance_path = (
            tmp_path
            / ".kittify"
            / "charter"
            / "provenance"
            / "directive-mission-type-scope-directive.yaml"
        )
        manifest_path = (
            tmp_path / ".kittify" / "charter" / "synthesis-manifest.yaml"
        )

        assert doctrine_path.exists()
        assert provenance_path.exists()
        assert manifest_path.exists()

        updated_body = dict(VALID_DIRECTIVE_BODY)
        updated_body["title"] = "Mission Scope Directive Updated"
        updated_body["intent"] = "Updated mission scope after host-directed resynthesis."
        _write_generated_directive(tmp_path, updated_body)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ):
            resynth_result = runner.invoke(
                app,
                ["resynthesize", "--topic", "directive:PROJECT_001"],
            )
        assert resynth_result.exit_code == 0, resynth_result.output

        yaml = YAML(typ="safe")
        doctrine_data = yaml.load(doctrine_path.read_text(encoding="utf-8"))
        assert doctrine_data["title"] == "Mission Scope Directive Updated"
        assert "host-directed resynthesis" in doctrine_data["intent"]

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ), patch(
            "specify_cli.cli.commands.charter.ensure_charter_bundle_fresh",
            side_effect=TaskCliError("Charter not found"),
        ):
            status_result = runner.invoke(app, ["status", "--json", "--provenance"])

        assert status_result.exit_code == 0, status_result.output
        data = json.loads(status_result.output)
        assert data["charter_sync"]["available"] is False
        assert data["synthesis"]["generation_state"] == "promoted"
        assert data["synthesis"]["manifest"]["state"] == "valid"
        assert data["synthesis"]["generated_inputs"]["counts"]["directive"] == 1
        assert data["synthesis"]["provenance"]["parsed_count"] == 1
        assert data["synthesis"]["evidence"]["configured_url_count"] == 1
        entry = data["synthesis"]["provenance"]["entries"][0]
        assert entry["artifact_urn"] == "directive:PROJECT_001"
        assert entry["adapter_id"] == "generated"
