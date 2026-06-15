"""Release workflow ownership regression tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.fast]

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

RELEASE_OWNER_PATHS = {
    "pyproject.toml",
    ".kittify/metadata.yaml",
    "uv.lock",
    ".kittify/release/shared-package-compatibility.json",
    "CHANGELOG.md",
    "RELEASE_CHECKLIST.md",
    "scripts/release/**",
    ".github/workflows/scripts/**",
    ".github/workflows/release-readiness.yml",
    ".github/workflows/check-spec-kitty-events-alignment.yml",
}

RELEASE_VERSION_SOURCE_PATHS = {
    "pyproject.toml",
    ".kittify/metadata.yaml",
    "CHANGELOG.md",
    "uv.lock",
}

RELEASE_VALIDATOR_SURFACE_PATHS = {
    "scripts/release/**",
    ".github/workflows/release-readiness.yml",
}

DOCS_CONTRACT_CI_PATHS = {"docs/**"}


def load_workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def on_section(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML still treats the YAML 1.1 key "on" as boolean True.
    return workflow.get("on") or workflow[True]


def event_paths(workflow: dict[str, Any], event: str) -> set[str]:
    return set(on_section(workflow)[event]["paths"])


def path_filter_text(workflow: dict[str, Any]) -> str:
    changes_steps = workflow["jobs"]["changes"]["steps"]
    filter_step = next(step for step in changes_steps if step.get("id") == "filter")
    return filter_step["with"]["filters"]


def release_readiness_filter_text(workflow: dict[str, Any]) -> str:
    steps = workflow["jobs"]["check-readiness"]["steps"]
    filter_step = next(step for step in steps if step.get("id") == "metadata_changes")
    return filter_step["with"]["filters"]


def release_readiness_step(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    steps = workflow["jobs"]["check-readiness"]["steps"]
    return next(step for step in steps if step.get("name") == name)


def workflow_script_text(name: str) -> str:
    return (WORKFLOWS / "scripts" / name).read_text(encoding="utf-8")


def test_ci_quality_runs_for_release_owned_paths() -> None:
    workflow = load_workflow("ci-quality.yml")

    for event in ("pull_request", "push"):
        missing = RELEASE_OWNER_PATHS - event_paths(workflow, event)
        assert not missing, f"CI Quality {event} trigger misses release paths: {sorted(missing)}"


def test_ci_quality_release_slice_covers_release_owned_paths() -> None:
    filters = path_filter_text(load_workflow("ci-quality.yml"))

    for path in RELEASE_OWNER_PATHS:
        assert f"- '{path}'" in filters, f"release path filter misses {path}"


def test_ci_quality_docs_contract_gate_runs_for_docs_changes() -> None:
    workflow = load_workflow("ci-quality.yml")
    filters = path_filter_text(workflow)

    for event in ("pull_request", "push"):
        missing = DOCS_CONTRACT_CI_PATHS - event_paths(workflow, event)
        assert not missing, (
            f"CI Quality {event} trigger misses docs-contract paths: "
            f"{sorted(missing)}"
        )
    for path in DOCS_CONTRACT_CI_PATHS:
        assert f"- '{path}'" in filters, f"core_misc path filter misses {path}"


def test_release_packaging_does_not_ship_removed_roo_harness() -> None:
    package_script = workflow_script_text("create-release-packages.sh")
    release_script = workflow_script_text("create-github-release.sh")

    assert "roo)" not in package_script
    assert ".roo/" not in package_script
    assert " roo " not in f" {package_script} "
    assert "spec-kitty-template-roo-" not in release_script


def test_release_readiness_runs_for_all_version_sources() -> None:
    workflow = load_workflow("release-readiness.yml")
    paths = event_paths(workflow, "pull_request")
    filters = release_readiness_filter_text(workflow)
    validate_step = next(
        step
        for step in workflow["jobs"]["check-readiness"]["steps"]
        if step.get("id") == "validate"
    )

    missing_paths = RELEASE_VERSION_SOURCE_PATHS - paths
    assert not missing_paths, (
        "Release Readiness pull_request trigger misses version source paths: "
        f"{sorted(missing_paths)}"
    )

    for path in RELEASE_VERSION_SOURCE_PATHS:
        assert f"- '{path}'" in filters, (
            f"Release Readiness metadata filter misses {path}"
        )
    for path in RELEASE_VALIDATOR_SURFACE_PATHS:
        assert f"- '{path}'" in filters, (
            f"Release Readiness validator filter misses {path}"
        )

    assert "version_sources" in filters
    assert "version_bump" in filters
    assert "validator_surface" in filters
    assert "outputs.version_sources" in validate_step["if"]
    assert "outputs.validator_surface" in validate_step["if"]
    assert "outputs.version_bump" in validate_step["run"]
    assert "--consistency-only" in validate_step["run"]
    assert "scope=full" in validate_step["run"]
    assert "scope=consistency" in validate_step["run"]


def test_release_readiness_consistency_summary_does_not_claim_release_ready() -> None:
    workflow = load_workflow("release-readiness.yml")
    summary_script = release_readiness_step(workflow, "Generate readiness summary")["run"]

    consistency_start = summary_script.index(
        '"${{ steps.validate.outputs.scope }}" == "consistency"'
    )
    full_start = summary_script.index(
        'elif [[ "${{ steps.validate.outcome }}" == "success" ]]',
        consistency_start,
    )
    consistency_block = summary_script[consistency_start:full_start]

    assert "Version-source consistency checks passed" in consistency_block
    assert "consistency-only validation" in consistency_block
    assert "This branch is ready for release" not in consistency_block
    assert "Version is properly bumped" not in consistency_block
    assert "Version progression is monotonic" not in consistency_block


def test_shared_drift_has_scheduled_and_manual_monitoring() -> None:
    workflow_on = on_section(load_workflow("check-spec-kitty-events-alignment.yml"))

    assert "schedule" in workflow_on
    assert "workflow_dispatch" in workflow_on


def test_shared_drift_secret_job_uses_trusted_scripts_only() -> None:
    workflow = load_workflow("check-spec-kitty-events-alignment.yml")
    jobs = workflow["jobs"]

    prepare_dump = repr(jobs["prepare-candidate-metadata"])
    assert "SPEC_KITTY_SAAS_READ_TOKEN" not in prepare_dump
    assert "python -m build" not in prepare_dump

    verify = jobs["verify-drift"]
    verify_dump = repr(verify)
    assert "github.event.pull_request.base.sha" in verify_dump
    assert "CROSS_REPO_TOKEN" not in repr(verify.get("env", {}))
    assert "check_candidate_consumer_compat.py" not in verify_dump
    assert "candidate/.kittify/release/shared-package-compatibility.json" in verify_dump
    assert "check_shared_package_drift.py --help" in verify_dump
    assert "MANIFEST_ARGS" in verify_dump

    fetch_step = next(step for step in verify["steps"] if step.get("id") == "fetch_refs")
    assert "CROSS_REPO_TOKEN" in fetch_step["env"]


def test_ci_quality_consumer_compatibility_reuses_ci_wheel_with_trusted_scripts() -> None:
    workflow = load_workflow("ci-quality.yml")
    job = workflow["jobs"]["consumer-compatibility"]
    job_dump = repr(job)

    assert job["needs"] == ["changes", "build-wheel"]
    assert "needs.changes.outputs.release == 'true'" in job["if"]
    assert "github.event.pull_request.base.sha" in job_dump
    assert "spec-kitty-cli-wheel" in job_dump
    assert "release-compatibility-manifest" in job_dump
    assert "candidate/.kittify/release/shared-package-compatibility.json" in job_dump
    assert "CROSS_REPO_TOKEN" not in repr(job.get("env", {}))
    assert "IS_FORK_PR" in job["env"]
    assert job["env"]["IS_CANONICAL_REPO"] == "${{ github.repository == 'Priivacy-ai/spec-kitty' }}"
    assert "check_candidate_consumer_compat.py" in job_dump
    assert "check_candidate_consumer_compat.py --help" in job_dump
    assert "MANIFEST_ARGS" in job_dump

    fetch_step = next(step for step in job["steps"] if step.get("id") == "fetch_contract")
    assert "CROSS_REPO_TOKEN" in fetch_step["env"]
    assert "saas_fetched=false" in fetch_step["run"]
    assert '[ "${IS_FORK_PR}" = "true" ] || [ "${IS_CANONICAL_REPO}" != "true" ]' in fetch_step["run"]
    assert "SPEC_KITTY_SAAS_READ_TOKEN is required" in fetch_step["run"]

    validate_step = next(
        step for step in job["steps"] if step["name"] == "Validate candidate against SaaS consumer contract"
    )
    assert validate_step["if"] == "steps.fetch_contract.outputs.saas_fetched == 'true'"


def test_quality_gate_fails_closed_for_release_required_package_jobs() -> None:
    workflow = load_workflow("ci-quality.yml")
    quality_gate = workflow["jobs"]["quality-gate"]
    needs = set(quality_gate["needs"])

    release_required = {
        "changes",
        "build-wheel",
        "clean-install-verification",
        "consumer-compatibility",
        "fast-tests-release",
        "integration-tests-release",
        "uv-lock-check",
    }
    assert not release_required - needs

    script = quality_gate["steps"][0]["run"]
    assert 'failure" ] || [ "$result" = "cancelled' in script
    assert "needs.changes.outputs.release" in script
    assert 'if [ "$result" != "success" ]; then' in script
    for job_name in release_required - {"changes"}:
        assert f"needs.{job_name}.result" in script


def test_release_publish_requires_downstream_consumer_evidence_before_pypi() -> None:
    workflow = load_workflow("release.yml")
    jobs = workflow["jobs"]
    publish_job = jobs["publish-pypi"]

    assert "downstream-consumer-verify" in jobs
    assert set(publish_job["needs"]) == {"build-release", "downstream-consumer-verify"}


def test_release_manual_dispatch_can_skip_downstream_with_explicit_waiver() -> None:
    workflow = load_workflow("release.yml")
    workflow_on = on_section(workflow)
    inputs = workflow_on["workflow_dispatch"]["inputs"]
    jobs = workflow["jobs"]

    assert inputs["tag"]["required"] is True
    assert inputs["skip_downstream"]["required"] is True
    assert (
        jobs["downstream-consumer-verify"]["if"]
        == "${{ github.event_name != 'workflow_dispatch' || inputs.skip_downstream != true }}"
    )

    publish_if = jobs["publish-pypi"]["if"]
    assert "always()" in publish_if
    assert "needs.build-release.result == 'success'" in publish_if
    assert "needs.downstream-consumer-verify.result == 'success'" in publish_if
    assert "github.event_name == 'workflow_dispatch'" in publish_if
    assert "inputs.skip_downstream == true" in publish_if


def test_release_verifies_pypi_exact_install_after_publish() -> None:
    workflow = load_workflow("release.yml")
    job = workflow["jobs"]["verify-pypi-installability"]
    job_dump = repr(job)

    assert job["needs"] == "publish-pypi"
    assert job["if"] == "${{ always() && needs.publish-pypi.result == 'success' }}"
    assert "--from-index" in job_dump
    assert "spec-kitty-cli" in job_dump


def test_publish_release_does_not_require_canary_verification_artifact() -> None:
    workflow = load_workflow("release.yml")
    jobs = workflow["jobs"]

    assert "canary-verify" not in jobs
    publish = jobs["publish-pypi"]
    assert set(publish["needs"]) == {"build-release", "downstream-consumer-verify"}

    publish_dump = repr(publish)
    assert "actions/checkout" in publish_dump
    assert publish["permissions"]["contents"] == "write"
    assert "canary" not in publish_dump.lower()
    assert "Create GitHub Release" in publish_dump
    assert "Create GitHub Release" not in repr(jobs["build-release"])
    assert "sbom.cdx.json" in repr(jobs["build-release"])
    assert "Classify release channel" in publish_dump

    step_names = [step.get("name", "") for step in publish["steps"]]
    assert step_names.index("Classify release channel") < step_names.index(
        "Create GitHub Release"
    )
