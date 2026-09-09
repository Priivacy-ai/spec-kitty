"""Release workflow ownership regression tests."""

from __future__ import annotations

import fnmatch
import os
import subprocess
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


def workflow_text(name: str) -> str:
    """Raw workflow source, for asserting a retired token is absent everywhere."""
    return (Path(__file__).resolve().parents[2] / ".github" / "workflows" / name).read_text(encoding="utf-8")


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


@pytest.mark.parametrize(
    ("workflow_name", "event"),
    [
        ("check-spec-kitty-events-alignment.yml", "pull_request"),
        ("check-spec-kitty-events-alignment.yml", "push"),
        ("ci-quality.yml", "pull_request"),
        ("ci-quality.yml", "push"),
        ("release-readiness.yml", "pull_request"),
        ("ci-windows.yml", "pull_request"),
        ("ci-windows.yml", "push"),
        ("drift-detector.yml", "pull_request"),
        ("drift-detector.yml", "push"),
    ],
)
def test_maintenance_branch_receives_release_gates(workflow_name: str, event: str) -> None:
    trigger = on_section(load_workflow(workflow_name))[event]

    assert any(fnmatch.fnmatchcase("release/3.2.6.x", pattern) for pattern in trigger["branches"]), f"{workflow_name} {event} excludes the maintenance branch"


@pytest.mark.parametrize("job_name", ["build-release", "publish-pypi"])
@pytest.mark.parametrize(
    ("version", "is_prerelease"),
    [
        ("3.2.6.1", False),
        ("3.2.6.1rc1", True),
        ("3.2.6.1RC1", True),
        ("3.2.6.1ALPHA", True),
        ("3.2.7BETA2", True),
        ("3.2.6.1alpha", True),
        ("3.2.7beta2", True),
        ("3.2.7", False),
    ],
)
def test_release_workflow_classifies_hotfix_channel(tmp_path: Path, job_name: str, version: str, is_prerelease: bool) -> None:
    workflow = load_workflow("release.yml")
    script = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == "Classify release channel")
    output = tmp_path / "github-output"

    result = subprocess.run(
        ["bash", "-eu", "-c", script],
        env={**os.environ, "RELEASE_TAG": f"v{version}", "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.read_text().strip() == f"is_prerelease={str(is_prerelease).lower()}"


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
        assert not missing, f"CI Quality {event} trigger misses docs-contract paths: {sorted(missing)}"
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
    validate_step = next(step for step in workflow["jobs"]["check-readiness"]["steps"] if step.get("id") == "validate")

    missing_paths = RELEASE_VERSION_SOURCE_PATHS - paths
    assert not missing_paths, f"Release Readiness pull_request trigger misses version source paths: {sorted(missing_paths)}"

    for path in RELEASE_VERSION_SOURCE_PATHS:
        assert f"- '{path}'" in filters, f"Release Readiness metadata filter misses {path}"
    for path in RELEASE_VALIDATOR_SURFACE_PATHS:
        assert f"- '{path}'" in filters, f"Release Readiness validator filter misses {path}"

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

    consistency_start = summary_script.index('"${{ steps.validate.outputs.scope }}" == "consistency"')
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


def test_shared_drift_checks_candidate_metadata_without_retired_consumer() -> None:
    workflow = load_workflow("check-spec-kitty-events-alignment.yml")
    jobs = workflow["jobs"]

    prepare_dump = repr(jobs["prepare-candidate-metadata"])
    assert "SPEC_KITTY_SAAS_READ_TOKEN" not in prepare_dump
    assert "python -m build" not in prepare_dump
    upload = next(step for step in jobs["prepare-candidate-metadata"]["steps"] if step.get("name") == "Upload candidate package metadata")
    assert upload["with"]["include-hidden-files"] is True
    assert set(upload["with"]["path"].split()) == {"pyproject.toml", "uv.lock", ".kittify/release/shared-package-compatibility.json"}

    verify = jobs["verify-drift"]
    verify_dump = repr(verify)
    assert "github.event.pull_request.base.sha" in verify_dump
    assert "CROSS_REPO_TOKEN" not in repr(verify.get("env", {}))
    assert "check_candidate_consumer_compat.py" not in verify_dump
    assert "candidate/.kittify/release/shared-package-compatibility.json" in verify_dump
    assert "check_shared_package_drift.py --help" in verify_dump
    assert "MANIFEST_ARGS" in verify_dump

    for retired in ("fetch_refs", "CROSS_REPO_TOKEN", "--saas-pyproject", "SPEC_KITTY_SAAS_READ_TOKEN"):
        assert retired not in verify_dump
    validate = next(step for step in verify["steps"] if step.get("name") == "Validate shared package drift")
    assert "if" not in validate
    assert "--pyproject candidate/pyproject.toml" in validate["run"]
    assert "--lockfile candidate/uv.lock" in validate["run"]


def test_ci_quality_has_no_saas_consumer_compatibility_job() -> None:
    """Backport of #3979: the SaaS consumer comparison is retired.

    It fetched ``${owner}/spec-kitty-saas/contents/contracts/consumer-compatibility.json``;
    the live Team Kitty repository pins shared packages by exact git revision under
    its own constitution and publishes no such contract, so the fetch 404s on every
    run and there is nothing for a CLI release to check against. Its
    ``IS_CANONICAL_REPO`` guard was also hardcoded to the retired ``Priivacy-ai``
    org name. Pin the removal so it cannot quietly return.
    """
    workflow = load_workflow("ci-quality.yml")
    assert "consumer-compatibility" not in workflow["jobs"]
    text = workflow_text("ci-quality.yml")
    for retired in ("check_candidate_consumer_compat.py", "consumer-compatibility.json", "IS_CANONICAL_REPO", "fetch_contract"):
        assert retired not in text, retired


def test_quality_gate_fails_closed_for_release_required_package_jobs() -> None:
    workflow = load_workflow("ci-quality.yml")
    quality_gate = workflow["jobs"]["quality-gate"]
    needs = set(quality_gate["needs"])

    release_required = {
        "changes",
        "build-wheel",
        "clean-install-verification",
        "fast-tests-release",
        "integration-tests-release",
        "uv-lock-check",
    }
    assert not release_required - needs

    # Post-FR-011 (mission ci-suite-map-bind WP03): the verdict is computed
    # by scripts/ci/quality_gate_decision.py over the full ``toJSON(needs)``
    # context. The release-required set is passed to the script as DATA
    # (RELEASE_REQUIRED_JOBS in the payload assembly); the script exits 2 if
    # any entry is absent from ``needs`` and FAILS any release-touching PR
    # where one did not succeed (skipped is not enough) — semantics pinned by
    # tests/scripts/test_quality_gate_decision.py.
    decision_step = next(step for step in quality_gate["steps"] if step.get("name") == "Evaluate quality-gate decision")
    assert decision_step["env"]["NEEDS_JSON"] == "${{ toJSON(needs) }}"
    # The step pipes the script into ``tee -a "$GITHUB_STEP_SUMMARY"``. Without
    # ``shell: bash`` GitHub runs it under ``bash -e {0}`` (no pipefail), so the
    # pipe returns tee's always-zero exit and the script's exit 2 on an absent
    # release-required job (or exit 1 blocking verdict) is swallowed — the gate
    # never fails. ``shell: bash`` turns pipefail on. Pin it here too.
    assert decision_step.get("shell") == "bash", (
        "quality-gate decision step must set ``shell: bash`` so pipefail propagates the script's non-zero exit through ``| tee``"
    )
    script = decision_step["run"]
    assert "scripts/ci/quality_gate_decision.py" in script
    release_block = script.split("RELEASE_REQUIRED_JOBS = [", 1)[1].split("]", 1)[0]
    for job_name in release_required - {"changes"}:
        assert f'"{job_name}"' in release_block, f"release-required job {job_name!r} missing from the RELEASE_REQUIRED_JOBS payload data"


def test_release_publish_needs_only_build_release() -> None:
    """Backport of #3979: publish gates on the CLI's own evidence, not a consumer's.

    The former ``downstream-consumer-verify`` job checked out
    ``${owner}/spec-kitty-end-to-end-testing`` and the SaaS consumer contract, neither
    of which exists under the current owner, so a plain tag push could not publish.
    """
    workflow = load_workflow("release.yml")
    jobs = workflow["jobs"]
    assert "downstream-consumer-verify" not in jobs
    assert jobs["publish-pypi"]["needs"] == ["build-release"]
    assert "if" not in jobs["publish-pypi"]


def test_release_has_no_saas_fetch_and_no_downstream_waiver() -> None:
    """Backport of #3979: nothing in the tag-time release depends on a SaaS read token.

    The ``Fetch compatibility references`` step ran unconditionally with ``curl -f``
    against a file that does not exist, so even the manual ``skip_downstream`` waiver
    could not get a tag published. Both are gone; the drift check is local-only.
    """
    workflow = load_workflow("release.yml")
    inputs = on_section(workflow)["workflow_dispatch"]["inputs"]
    assert inputs["tag"]["required"] is True
    assert "skip_downstream" not in inputs
    text = workflow_text("release.yml")
    retired_tokens = (
        "SKIP_DOWNSTREAM",
        "fetch_refs",
        "HAS_SAAS_READ_TOKEN",
        "CROSS_REPO_TOKEN",
        "SPEC_KITTY_SAAS_READ_TOKEN",
        "--saas-pyproject",
        "check_candidate_consumer_compat.py",
        "spec-kitty-saas",
    )
    for retired in retired_tokens:
        assert retired not in text, retired
    build = workflow["jobs"]["build-release"]
    drift = next(step for step in build["steps"] if step.get("name") == "Validate shared package drift")
    assert drift["run"].strip() == "python scripts/release/check_shared_package_drift.py --check-installed"


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
    assert set(publish["needs"]) == {"build-release"}  # downstream-consumer-verify retired (#3979 backport)

    publish_dump = repr(publish)
    assert "actions/checkout" in publish_dump
    assert publish["permissions"]["contents"] == "write"
    assert "canary" not in publish_dump.lower()
    assert "Create GitHub Release" in publish_dump
    assert "Create GitHub Release" not in repr(jobs["build-release"])
    assert "sbom.cdx.json" in repr(jobs["build-release"])
    assert "Classify release channel" in publish_dump

    step_names = [step.get("name", "") for step in publish["steps"]]
    assert step_names.index("Classify release channel") < step_names.index("Create GitHub Release")
