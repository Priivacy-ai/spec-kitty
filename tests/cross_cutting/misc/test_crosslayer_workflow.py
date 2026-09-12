"""Structural guards for the crosslayer.yml CI workflow (mission M7 / WP04).

Pins the user-observable behavior WP04 owns: the workflow's trigger paths,
its static PR gate (muster-action static run + both drift-check call
sites), and its cadence scaffold (schedule/workflow_dispatch, secrets
sourced only via GitHub Actions repository secrets, never argv). None of
this can be exercised end-to-end without a real GitHub Actions run (see
kitty-specs/crosslayer-composition-suite-01KYJA33/tasks/
WP04-crosslayer-ci-workflow.md, T021) -- this test suite is the static,
locally-runnable proof that the workflow *file* has the shape FR-004/FR-005
require, mirroring tests/architectural/test_plugin_validate_workflow.py and
tests/release/test_release_ci_ownership.py's own style for asserting on
parsed workflow YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "crosslayer.yml"
_CONFORMANCE_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "conformance.yml"

# M1 post-spec finding (spec.md Dependencies & Assumptions): a profile-only
# PR must still see (and be able to fix) the persona-drift check its own
# diff affects.
_REQUIRED_PR_PATHS = {
    "conformance/**",
    "packs/built-in/agent_profiles/**",
}


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _on_section(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML treats the YAML 1.1 key "on" as boolean True.
    return workflow.get("on") or workflow[True]


def _conformance_workflow() -> dict[str, Any]:
    return yaml.safe_load(_CONFORMANCE_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _find_uses_pin(workflow: dict[str, Any], action_prefix: str) -> str:
    """The pin conformance.yml already trusts (T018) -- crosslayer.yml must
    reuse it, not introduce a new, unreviewed pin. Parsed via YAML (like
    the rest of this suite) so a trailing ``# vN`` comment on the source
    line -- stripped by yaml.safe_load, present in raw text -- doesn't
    produce a spurious mismatch against crosslayer.yml's own parsed value.
    """
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            uses = str(step.get("uses", ""))
            if uses.startswith(action_prefix):
                return uses
    raise AssertionError(f"conformance.yml has no {action_prefix} pin to reuse")


def _existing_muster_action_pin() -> str:
    return _find_uses_pin(_conformance_workflow(), "garrison-hq/muster-action@")


def _existing_checkout_pin() -> str:
    return _find_uses_pin(_conformance_workflow(), "actions/checkout@")


def test_crosslayer_workflow_file_exists() -> None:
    assert _WORKFLOW_PATH.is_file(), f"{_WORKFLOW_PATH} must exist as its own file, isolated from the shared conformance.yml (M3's PR #30 modifies that file)."


def test_crosslayer_workflow_is_not_the_shared_conformance_workflow() -> None:
    # Guards against the collision this mission's spec explicitly avoids:
    # a careless edit that merges crosslayer content into conformance.yml
    # instead of a new file.
    assert _WORKFLOW_PATH != _CONFORMANCE_WORKFLOW_PATH
    assert _WORKFLOW_PATH.name == "crosslayer.yml"


def test_pull_request_trigger_covers_both_required_path_scopes() -> None:
    workflow = _workflow()
    on_section = _on_section(workflow)
    assert "pull_request" in on_section, "crosslayer.yml must trigger on pull_request"

    paths = set(on_section["pull_request"]["paths"])
    missing = _REQUIRED_PR_PATHS - paths
    assert not missing, f"crosslayer.yml pull_request trigger misses required path scope(s): {sorted(missing)}"


def test_paid_cadence_requires_explicit_workflow_dispatch() -> None:
    on_section = _on_section(_workflow())
    assert "schedule" not in on_section, "Paid evaluation requires explicit dispatch"
    assert "workflow_dispatch" in on_section, "FR-005 cadence job needs workflow_dispatch: for on-demand manual runs"


def test_workflow_permissions_are_read_only() -> None:
    workflow = _workflow()
    assert workflow["permissions"]["contents"] == "read"


def _static_job(workflow: dict[str, Any]) -> dict[str, Any]:
    jobs = workflow["jobs"]
    # Identify the static PR-gate job by its trigger condition rather than
    # by an assumed name, so a future rename doesn't silently break these
    # tests without also breaking the workflow's own real behavior: prefer
    # the job that actually invokes crosslayer's static-only run.
    for job in jobs.values():
        steps = job.get("steps", [])
        for step in steps:
            args = str(step.get("with", {}).get("args", ""))
            if "--static-only" in args:
                return job
    raise AssertionError("no job in crosslayer.yml invokes crosslayer run --static-only")


def _cadence_job(workflow: dict[str, Any]) -> dict[str, Any]:
    for job in workflow["jobs"].values():
        if "schedule" in str(job.get("if", "")) or "workflow_dispatch" in str(job.get("if", "")):
            return job
    raise AssertionError("no job in crosslayer.yml is gated to run only on schedule/workflow_dispatch")


def test_static_job_never_references_secrets() -> None:
    static_job = _static_job(_workflow())
    dump = repr(static_job)
    assert "secrets" not in dump, (
        "The static PR gate must remain fully offline/zero-network and "
        "runnable on a fork PR with zero repository secrets available -- "
        f"found a secrets reference: {dump}"
    )


def test_static_job_checks_out_with_the_reused_pin() -> None:
    static_job = _static_job(_workflow())
    steps = static_job["steps"]
    checkout_step = next(step for step in steps if "actions/checkout@" in str(step.get("uses", "")))
    assert checkout_step["uses"] == _existing_checkout_pin(), (
        "crosslayer.yml must reuse conformance.yml's existing actions/checkout pin (T018), not introduce a new, unreviewed pin."
    )


def test_static_job_invokes_muster_action_with_reused_pin_and_correct_inputs() -> None:
    static_job = _static_job(_workflow())
    steps = static_job["steps"]
    muster_step = next(step for step in steps if "garrison-hq/muster-action@" in str(step.get("uses", "")))

    assert muster_step["uses"] == _existing_muster_action_pin(), (
        "crosslayer.yml must reuse conformance.yml's existing garrison-hq/muster-action pin (T018), not introduce a new, unreviewed pin."
    )
    with_block = muster_step["with"]
    assert with_block["command"] == "crosslayer run"
    assert "conformance/crosslayer/manifest.yaml" in with_block["args"]
    assert "--static-only" in with_block["args"]
    assert with_block["version"] == "1.2.2"


def test_static_job_wires_persona_drift_call_site_bare() -> None:
    static_job = _static_job(_workflow())
    run_step = next(step for step in static_job["steps"] if "check-persona-drift.sh" in str(step.get("run", "")))
    # Bare -- no arguments, no flags. WP01's script has no --write mode at
    # all, but this pins the call site's own contract regardless.
    assert run_step["run"].strip() == "bash conformance/scripts/check-persona-drift.sh"


def test_static_job_wires_sop_extract_drift_call_site_bare() -> None:
    static_job = _static_job(_workflow())
    run_step = next(step for step in static_job["steps"] if "check-sop-extract-drift.sh" in str(step.get("run", "")))
    # Bare invocation only. WP03's script gates a --write mode behind an
    # explicit literal "--write" argv token (see
    # conformance/scripts/check-sop-extract-drift.sh) -- CI must never
    # supply it, or a renamed AGENTS.md heading could silently regenerate
    # (and therefore blank) the committed extract instead of failing the
    # gate. This call site must never grow that argument.
    assert run_step["run"].strip() == "bash conformance/scripts/check-sop-extract-drift.sh"
    assert "--write" not in run_step["run"]


def test_static_job_has_no_env_that_could_reach_write_mode() -> None:
    static_job = _static_job(_workflow())
    dump = repr(static_job)
    assert "--write" not in dump
    assert "WRITE_MODE" not in dump


def test_cadence_job_sources_secrets_from_repository_secrets_only() -> None:
    cadence_job = _cadence_job(_workflow())
    dump = repr(cadence_job)
    assert "secrets.MUSTER_ENDPOINT" in dump
    assert "secrets.MUSTER_API_KEY" in dump

    # Never in argv: the muster-action `args` input must not embed the
    # secret interpolations directly (that would place them on a
    # process's command line / potentially a log line).
    for step in cadence_job["steps"]:
        args = str(step.get("with", {}).get("args", ""))
        assert "secrets.MUSTER_ENDPOINT" not in args
        assert "secrets.MUSTER_API_KEY" not in args


def test_cadence_has_real_behavioral_and_adversarial_cases() -> None:
    root = _WORKFLOW_PATH.parents[2] / "conformance/crosslayer"
    manifest = yaml.safe_load((root / "manifest.yaml").read_text())
    cases = [yaml.safe_load((root / entry["$ref"]).read_text()) for entry in manifest["cases"]]
    behavioral = {case["id"] for case in cases if case.get("testClass") == "behavioral"}
    assert {"rule-survival-045", "erosion-control-045"} <= behavioral
    assert "ZERO REAL CASES EXIST YET" not in _WORKFLOW_PATH.read_text()


def test_workflow_never_touches_shared_conformance_yml() -> None:
    # This is a new, isolated file by design (spec.md Dependencies &
    # Assumptions, "Workflow-file collision with M3"). Confirms the two
    # files remain textually distinct -- crosslayer.yml is not a copy or a
    # symlink of the shared file.
    assert _WORKFLOW_PATH.read_text(encoding="utf-8") != _CONFORMANCE_WORKFLOW_PATH.read_text(encoding="utf-8")
