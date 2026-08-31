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
