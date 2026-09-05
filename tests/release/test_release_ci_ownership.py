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
RELEASE_CHECKLIST = ROOT / "RELEASE_CHECKLIST.md"
DOCS_REFERENCE_INDEX = ROOT / "docs" / "development" / "reference" / "index.md"

RESTORED_WORKFLOWS = {
    "ci-quality.yml",
    "protect-main.yml",
    "ci-windows.yml",
    "docs-pages.yml",
    "check-spec-kitty-events-alignment.yml",
    "release-readiness.yml",
    "release.yml",
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


def test_release_checklist_marks_deferred_publish_workflows_as_p3_4b_prerequisite() -> None:
    checklist = RELEASE_CHECKLIST.read_text(encoding="utf-8")
    assert "P3.4b prerequisite" in checklist
    assert "release.yml" in checklist
    assert "release-readiness.yml" in checklist


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


@pytest.mark.parametrize("name", ["ci-quality.yml", "ci-windows.yml"])
def test_public_ci_uses_released_dependencies_without_private_credentials(name: str) -> None:
    text = workflow_text(name)

    assert "SK_CI_TOKEN" not in text
    assert "Configure private git dependencies" not in text


def test_ci_windows_install_uses_runner_temp() -> None:
    workflow = load_workflow("ci-windows.yml")
    steps = workflow["jobs"]["windows-critical"]["steps"]
    install_step = next(step for step in steps if step.get("name") == "Install spec-kitty-cli (editable) + test deps")

    assert install_step["env"]["TMP"] == "${{ runner.temp }}"
    assert install_step["env"]["TEMP"] == "${{ runner.temp }}"


def test_private_factory_ci_is_scoped_to_experimental_repo() -> None:
    workflow = load_workflow("ci.yml")

    assert "github.repository == 'spec-kitty/EXPERIMENTAL-spec-kitty'" in workflow["jobs"]["suite"]["if"]


def test_docs_pages_deploys_only_from_promotion_repo_and_fails_transient_setup_errors() -> None:
    workflow = load_workflow("docs-pages.yml")
    pages_job = workflow["jobs"]["pages"]
    probe_step, setup_step = pages_job["steps"]
    build_job = workflow["jobs"]["build"]
    deploy_job = workflow["jobs"]["deploy"]

    assert pages_job["outputs"] == {"configured": "${{ steps.probe-pages.outputs.available }}"}
    assert probe_step["id"] == "probe-pages"
    assert probe_step["env"]["GITHUB_TOKEN"] == "${{ github.token }}"
    assert 'status="$(curl' in probe_step["run"]
    assert "200)" in probe_step["run"]
    assert 'echo "available=true" >> "$GITHUB_OUTPUT"' in probe_step["run"]
    assert "404)" in probe_step["run"]
    assert 'echo "available=false" >> "$GITHUB_OUTPUT"' in probe_step["run"]
    assert "::error::GitHub Pages configuration probe failed with HTTP $status." in probe_step["run"]
    assert setup_step["id"] == "setup-pages"
    assert setup_step["if"] == "steps.probe-pages.outputs.available == 'true'"
    assert setup_step["uses"] == "actions/configure-pages@v6"
    assert "continue-on-error" not in setup_step
    assert build_job["needs"] == ["pages"]
    assert build_job["if"] == "needs.pages.outputs.configured == 'true' && needs.pages.result == 'success'"
    assert deploy_job["if"] == "github.repository == 'Priivacy-ai/spec-kitty' && github.ref == 'refs/heads/main' && needs.build.result == 'success'"

    publication_policy = DOCS_REFERENCE_INDEX.read_text(encoding="utf-8")
    assert "intentionally deployed from the promotion-only" in publication_policy
    assert "does not claim the custom domain" in publication_policy
    assert "controller's promotion loop" in publication_policy


@pytest.mark.parametrize("name", sorted(RESTORED_WORKFLOWS))
def test_restored_workflows_use_stock_runners(name: str) -> None:
    text = workflow_text(name)

    assert "blacksmith" not in text.lower()
    assert "runner-group" not in text.lower()


def test_release_wheel_gate_counts_charter_offering_and_skills() -> None:
    workflow = load_workflow("release.yml")
    step = next(step for step in workflow["jobs"]["build-release"]["steps"] if step.get("name") == "Verify wheel contents")
    run = step["run"]

    assert "git ls-files src/charter/offering" in run
    assert "find " in run
    assert "wheel_check/charter/offering" in run
    assert "git ls-files src/charter/offering/skills" in run
    assert "wheel_check/charter/offering/skills" in run
    assert "git ls-files src/doctrine" not in run


def test_release_readiness_cutover_guard_uses_public_lock_dependencies() -> None:
    workflow = load_workflow("release-readiness.yml")
    job = workflow["jobs"]["cutover-guard"]
    job_dump = repr(job)

    assert "pip install -e ." not in job_dump
    assert "git+https" not in job_dump
    assert ".cutover-deps" not in job_dump
    assert "grep -vE" not in job_dump

    install = next(step for step in job["steps"] if step.get("name") == "Install the source-only guard environment")
    assert "uv export --frozen --no-dev" in install["run"]
    assert "python -m pip install -r .cutover-requirements.lock.txt" in install["run"]

    guard = next(step for step in job["steps"] if step.get("name") == "Run cutover guard (fail-closed on any un-cut-over mission)")
    assert "PYTHONPATH=src" in guard["run"]
    assert "from specify_cli.cli.commands.cutover_guard import cutover_guard" in guard["run"]


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
