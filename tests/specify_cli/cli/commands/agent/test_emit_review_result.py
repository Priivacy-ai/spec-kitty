"""Regression: ``agent status emit`` must carry a structured review verdict.

Pins issues #3547 / #1734 (FR-010/FR-012/FR-013). Before WP09, ``agent status
emit`` exposed no ``--review-result-json`` option, so a WP could not exit
``in_review`` through the emit surface with a structured verdict -- only the
``orchestrator-api transition`` surface could. These tests prove the emit-only
lifecycle walk reaches ``done`` via a structured verdict, that the misleading
``--help`` verdict example is gone, and that both surfaces validate the verdict
through the SAME hoisted parser (no duplicate validator drift).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app
from tests.status.conftest import seed_wp_to_planned

pytestmark = pytest.mark.fast

runner = CliRunner()

MISSION_SLUG = "034-test-feature"


def _extract_json(output: str) -> dict:
    """Return the first line of ``output`` that parses as a JSON object."""
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in output:\n{output}")


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Minimal mission dir with a minted identity and a checked-off WP01."""
    fd = tmp_path / "kitty-specs" / MISSION_SLUG
    fd.mkdir(parents=True)
    (fd / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KNXQS9ATWWFXS3K5ZJ9E5008",
                "mid8": "01KNXQS9",
                "mission_slug": MISSION_SLUG,
            }
        ),
        encoding="utf-8",
    )
    tasks_dir = fd / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-test-task.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test Task\nsubtasks: []\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    # The in_progress -> for_review gate requires provably-complete subtasks.
    (fd / "tasks.md").write_text(
        "# Tasks: 034-test-feature\n\n"
        "## WP01 — Verdict emit plumbing\n\n"
        "- [x] T026 Red-first emit review-result test\n"
        "- [x] T027 Thread review_result into TransitionRequest\n"
        "- [x] T028 Correct the --help verdict example\n"
        "- [x] T029 Admit ReviewResult on in_review->approved\n",
        encoding="utf-8",
    )
    return fd


def _patches(tmp_path: Path):
    return (
        patch(
            "specify_cli.cli.commands.agent.status.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.agent.status.get_main_repo_root",
            return_value=tmp_path,
        ),
        patch("specify_cli.status.emit._saas_fan_out"),
    )


def _emit(tmp_path: Path, *args: str):
    locate, main_root, fan_out = _patches(tmp_path)
    with locate, main_root, fan_out:
        return runner.invoke(
            app,
            ["emit", "WP01", *args, "--actor", "test-agent", "--mission", MISSION_SLUG],
        )


def _walk_to_in_review(tmp_path: Path, feature_dir: Path) -> None:
    seed_wp_to_planned(feature_dir, "WP01", slug=MISSION_SLUG)
    for lane in ("claimed", "in_progress", "for_review", "in_review"):
        result = _emit(tmp_path, "--to", lane)
        assert result.exit_code == 0, f"walk failed at {lane}: {result.output}"


@pytest.mark.regression
def test_emit_only_lifecycle_reaches_approved_with_verdict(
    tmp_path: Path, feature_dir: Path
) -> None:
    """#3547/#1734: emit alone advances in_review -> approved via a verdict.

    On base this is RED: ``emit`` has no ``--review-result-json`` option, so the
    verdict cannot be supplied and the in_review guard blocks the exit.
    """
    _walk_to_in_review(tmp_path, feature_dir)

    verdict = json.dumps(
        {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}
    )
    result = _emit(tmp_path, "--to", "approved", "--review-result-json", verdict, "--json")

    assert result.exit_code == 0, f"stdout: {result.output}"
    data = _extract_json(result.output)
    assert data["to_lane"] == "approved"


@pytest.mark.regression
def test_emit_only_lifecycle_reaches_done(tmp_path: Path, feature_dir: Path) -> None:
    """The full emit-only walk in_progress -> ... -> approved -> done succeeds."""
    _walk_to_in_review(tmp_path, feature_dir)

    verdict = json.dumps(
        {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}
    )
    approved = _emit(
        tmp_path, "--to", "approved", "--review-result-json", verdict, "--json"
    )
    assert approved.exit_code == 0, f"approved failed: {approved.output}"

    evidence = json.dumps(
        {"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}
    )
    done = _emit(tmp_path, "--to", "done", "--evidence-json", evidence, "--json")
    assert done.exit_code == 0, f"done failed: {done.output}"
    assert _extract_json(done.output)["to_lane"] == "done"


@pytest.mark.regression
def test_emit_rejects_malformed_review_result_json(
    tmp_path: Path, feature_dir: Path
) -> None:
    """A malformed verdict is rejected via the hoisted parser's error shape."""
    _walk_to_in_review(tmp_path, feature_dir)

    result = _emit(
        tmp_path, "--to", "approved", "--review-result-json", "{not json"
    )
    assert result.exit_code == 1, f"stdout: {result.output}"
    assert "--review-result-json" in result.output


def test_emit_help_documents_review_result_json_not_evidence_verdict() -> None:
    """FR-012: --help documents --review-result-json, no verdict-via-evidence example."""
    result = runner.invoke(app, ["emit", "--help"])
    assert result.exit_code == 0, result.output
    # Collapse Rich line-wrapping so example snippets match regardless of width.
    collapsed = " ".join(result.output.split())
    assert "--review-result-json" in collapsed
    # The misleading example routed an approval verdict through --evidence-json.
    assert '--evidence-json \'{"review"' not in collapsed
    assert '"verdict": "approved"' in collapsed  # only via the review-result-json example


def test_both_verdict_surfaces_share_one_parser() -> None:
    """Parity: emit and orchestrator transition reference the SAME validator."""
    from specify_cli.cli.commands.agent import status as emit_module
    from specify_cli.orchestrator_api import commands as transition_module
    from specify_cli.status.review_result_parse import parse_review_result_json

    assert emit_module.parse_review_result_json is parse_review_result_json
    assert transition_module.parse_review_result_json is parse_review_result_json
