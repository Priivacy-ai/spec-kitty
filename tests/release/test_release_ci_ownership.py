"""Ownership guards for the interim restored CI producers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.fast]

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
CONVERGENCE_MAP = ROOT / "docs" / "convergence" / "interim-ci-producer.md"

RESTORED_WORKFLOWS = {
    "ci-quality.yml",
    "protect-main.yml",
    "ci-windows.yml",
    "docs-pages.yml",
    "check-spec-kitty-events-alignment.yml",
}

UPSTREAM_WORKFLOW_PATHS = {
    "all-contributors-normalize.yml",
    "all-contributors-sync.yml",
    "canonical-producer-lint.yml",
    "check-spec-kitty-events-alignment.yml",
    "ci-flake-report.yml",
    "ci-quality.yml",
    "ci-windows.yml",
    "docs-build-pr.yml",
    "docs-freshness.yml",
    "docs-pages.yml",
    "doctrine-charter-tests.yml",
    "drift-detector.yml",
    "module-doctrine-fast.yml",
    "module-doctrine-integration.yml",
    "module-kernel.yml",
    "module-packs.yml",
    "mutation-remediation.md",
    "orchestrator-boundary.yml",
    "performance.yml",
    "plantuml-egress-spike.yml",
    "plugin-validate.yml",
    "project-sync-consent-evidence.yml",
    "protect-main.yml",
    "regen-assets.yml",
    "release-readiness.yml",
    "release.yml",
    "review-verdict-durability.yml",
    "teamspace-mission-state-readiness.yml",
    "ui-e2e.yml",
}

UPSTREAM_SCRIPT_PATHS = {
    "scripts/check-release-exists.sh",
    "scripts/create-github-release.sh",
    "scripts/create-release-packages.sh",
    "scripts/generate-release-notes.sh",
    "scripts/get-next-version.sh",
    "scripts/update-version.sh",
}


def load_workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def workflow_text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_reduced_ci_quality_has_exact_jobs() -> None:
    workflow = load_workflow("ci-quality.yml")

    assert set(workflow["jobs"]) == {
        "lint",
        "build-wheel",
        "clean-install-verification",
        "uv-lock-check",
        "quality-gate",
    }
    assert workflow["jobs"]["clean-install-verification"]["needs"] == ["build-wheel"]


def test_clean_install_check_name_is_branch_protection_ready() -> None:
    workflow = load_workflow("ci-quality.yml")
    job = workflow["jobs"]["clean-install-verification"]

    assert job["name"] == "Clean install verification"
    assert "spec-kitty-runtime" in workflow_text("ci-quality.yml")
    assert "tests/fixtures/clean_install_fixture_mission" in workflow_text("ci-quality.yml")


def test_quality_gate_blocks_every_reduced_producer_job() -> None:
    workflow = load_workflow("ci-quality.yml")
    gate = workflow["jobs"]["quality-gate"]

    assert set(gate["needs"]) == {
        "lint",
        "build-wheel",
        "clean-install-verification",
        "uv-lock-check",
    }
    assert "NEEDS_JSON: ${{ toJSON(needs) }}" in workflow_text("ci-quality.yml")


def test_ci_windows_has_no_sync_path_filters() -> None:
    workflow = load_workflow("ci-windows.yml")
    changes = workflow["jobs"]["changes"]["steps"]
    filter_step = next(step for step in changes if step.get("id") == "filter")
    filters = filter_step["with"]["filters"]

    assert "tests/sync/" not in filters
    assert workflow["jobs"]["windows-critical"]["runs-on"] == "windows-latest"


def test_ci_windows_filter_can_read_pull_request_files() -> None:
    workflow = load_workflow("ci-windows.yml")

    assert workflow["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
    }


def test_ci_windows_configures_private_git_dependencies_before_install() -> None:
    workflow = load_workflow("ci-windows.yml")
    steps = workflow["jobs"]["windows-critical"]["steps"]
    step_names = [step.get("name") for step in steps]

    assert step_names.index("Configure private git dependencies") < step_names.index("Install spec-kitty-cli (editable) + test deps")
    configure_step = steps[step_names.index("Configure private git dependencies")]
    install_step = steps[step_names.index("Install spec-kitty-cli (editable) + test deps")]
    assert configure_step["env"]["GH_TOKEN"] == "${{ secrets.SK_CI_TOKEN }}"
    assert install_step["env"]["TMP"] == "${{ runner.temp }}"
    assert install_step["env"]["TEMP"] == "${{ runner.temp }}"
    assert 'git config --global "url.https://x-access-token:${GH_TOKEN}@github.com/.insteadOf" "https://github.com/"' in configure_step["run"]


def test_docs_pages_skips_cleanly_when_pages_is_unavailable() -> None:
    workflow = load_workflow("docs-pages.yml")
    pages_job = workflow["jobs"]["pages"]
    setup_step = pages_job["steps"][0]
    build_job = workflow["jobs"]["build"]
    deploy_job = workflow["jobs"]["deploy"]

    assert pages_job["outputs"] == {"configured": "${{ steps.setup-pages.outcome }}"}
    assert setup_step["id"] == "setup-pages"
    assert setup_step["uses"] == "actions/configure-pages@v6"
    assert setup_step["continue-on-error"] is True
    assert build_job["needs"] == ["pages"]
    assert build_job["if"] == "needs.pages.outputs.configured == 'success'"
    assert deploy_job["if"] == "github.ref == 'refs/heads/main' && needs.build.result == 'success'"


@pytest.mark.parametrize("name", sorted(RESTORED_WORKFLOWS))
def test_restored_workflows_use_stock_runners(name: str) -> None:
    text = workflow_text(name)

    assert "blacksmith" not in text.lower()
    assert "runner-group" not in text.lower()


def test_convergence_map_dispositions_every_upstream_workflow_and_script() -> None:
    rows = {
        match.group(1): match.group(2)
        for match in re.finditer(r"^\| `([^`]+)` \| (restore|never-restore|defer) \|", CONVERGENCE_MAP.read_text(encoding="utf-8"), re.MULTILINE)
    }
    expected = {f".github/workflows/{name}" for name in UPSTREAM_WORKFLOW_PATHS} | {f".github/workflows/{name}" for name in UPSTREAM_SCRIPT_PATHS}

    assert set(rows) == expected, f"convergence map path mismatch: missing={sorted(expected - set(rows))}, extra={sorted(set(rows) - expected)}"
    assert {rows[path] for path in expected if path.endswith(".yml")} <= {
        "restore",
        "never-restore",
        "defer",
    }
