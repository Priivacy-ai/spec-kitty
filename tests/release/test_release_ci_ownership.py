"""Release workflow ownership regression tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

RELEASE_OWNER_PATHS = {
    "pyproject.toml",
    "uv.lock",
    "CHANGELOG.md",
    "RELEASE_CHECKLIST.md",
    "scripts/release/**",
    ".github/workflows/release-readiness.yml",
    ".github/workflows/check-spec-kitty-events-alignment.yml",
}


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


def test_ci_quality_runs_for_release_owned_paths() -> None:
    workflow = load_workflow("ci-quality.yml")

    for event in ("pull_request", "push"):
        missing = RELEASE_OWNER_PATHS - event_paths(workflow, event)
        assert not missing, f"CI Quality {event} trigger misses release paths: {sorted(missing)}"


def test_ci_quality_release_slice_covers_release_owned_paths() -> None:
    filters = path_filter_text(load_workflow("ci-quality.yml"))

    for path in RELEASE_OWNER_PATHS:
        assert f"- '{path}'" in filters, f"release path filter misses {path}"


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
    assert "CROSS_REPO_TOKEN" not in repr(job.get("env", {}))
    assert "check_candidate_consumer_compat.py" in job_dump

    fetch_step = next(step for step in job["steps"] if step.get("id") == "fetch_contract")
    assert "CROSS_REPO_TOKEN" in fetch_step["env"]
