"""WP03 (design-phase-orchestrator-api-01M1HE6M) — ``specify``/``plan``/
``tasks`` orchestrator-api verbs (FR-001/002/003).

Acceptance scenarios (see
``kitty-specs/design-phase-orchestrator-api-01M1HE6M/tasks/WP03-specify-plan-tasks-verbs.md``):

1. ``specify --mission-type <type> --mission <slug> --policy <...>`` against a
   scratch project with no existing mission → ``success: true`` and the
   ENRICHED ``data`` shape (``scaffold_only``/``spec_state``/``next_action``/
   ``next_step`` plus mission identity + ``spec_file``) — the enrichment
   ``lifecycle._create_mission_for_specify_json`` adds on top of
   ``agent_feature.create_mission``'s raw payload (Clarification 1).
2. ``plan --mission <slug> --policy <...>`` against an already-``specify``'d
   mission (with a substantive, committed spec.md) → ``data.plan_file`` and
   the file exists on disk. NOTE: the WP prompt's own prose calls this field
   ``plan_path``; the real, verified ``agent_feature.setup_plan(...,
   json_output=True)`` payload key is ``plan_file`` (confirmed against
   production by direct invocation during implementation) — asserting on the
   real key is the genuine "unenriched pass-through" contract T011 requires;
   asserting on a field that does not exist would not be a meaningful test.
3. ``tasks --mission <slug> --policy <...>`` against a mission with a
   completed ``tasks/`` dir → the finalized WP-manifest shape
   (``wp_count``/``modified_wps``) matches
   ``agent_feature.finalize_tasks(..., json_output=True)``'s own shape.
4. ``specify`` called twice for the same slug → ``success: false`` with a
   structured ``error_code`` (never a bare exception), and the FIRST mission
   directory's ``meta.json`` is unchanged.

This is the RED-then-GREEN ATDD anchor (charter C-011): pre-implementation,
none of ``specify``/``plan``/``tasks`` exist as ``@app.command``s on
``orchestrator_api.commands.app``, so every scenario below fails at the
Typer "no such command" / non-zero-exit level.

Real mission scaffolding (real files under ``kitty-specs/<slug>/``, real git
commits via ``create_mission``/``setup_plan``/``finalize_tasks``) — hence
``integration``/``git_repo`` (NOT ``fast``, per this repo's own
``pytest.ini:25`` definition reserving ``fast`` for no-subprocess/no-git
tests), mirroring ``test_transition_subtask_gate.py``'s precedent.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app
from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

_POLICY = json.dumps(
    {
        "orchestrator_id": "test-orch",
        "orchestrator_version": "0.0.1",
        "agent_family": "claude",
        "approval_mode": "full_auto",
        "sandbox_mode": "workspace_write",
        "network_mode": "none",
        "dangerous_flags": [],
    }
)

_SUBSTANTIVE_SPEC = """# Spec — WP03 verbs

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Do the thing | Users can do the thing end to end. | High | Open |

## User Scenarios
A user does the thing via the orchestrator-api.
"""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    """A real, non-protected-branch git repo with an activated mission type.

    Branch name deliberately not ``main``/``master`` (the default protected
    set, ``specify_cli/git/protection_policy.py``) so the mission-creation
    commits this test drives for real are never refused by the protected-
    branch guard — no ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` escape
    hatch needed.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "wp03-work"], cwd=repo, check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    provision_test_charter(repo)
    return repo


def _run(repo: Path, args: list[str]):
    """Invoke the real orchestrator-api ``app`` with cwd pinned at ``repo``.

    ``specify``/``plan``/``tasks`` resolve their project root and mission dir
    via real filesystem discovery (``locate_project_root`` /
    ``_get_main_repo_root``), so — unlike the lighter fail-closed suites —
    this drives the genuine end-to-end path with no ``_get_main_repo_root``
    patch.
    """
    import os

    prev_cwd = Path.cwd()
    os.chdir(repo)
    try:
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(prev_cwd)


def _envelope(result) -> dict:
    return json.loads(result.output.strip().split("\n")[0])


def _specify(repo: Path, mission_slug: str, *, mission_type: str = "software-dev") -> dict:
    result = _run(
        repo,
        [
            "specify",
            "--mission",
            mission_slug,
            "--mission-type",
            mission_type,
            "--topology",
            "single_branch",
            "--policy",
            _POLICY,
        ],
    )
    return _envelope(result)


# ---------------------------------------------------------------------------
# Acceptance Scenario 1 — specify: enriched scaffold-state shape
# ---------------------------------------------------------------------------


def test_specify_creates_mission_with_enriched_scaffold_state(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    envelope = _specify(repo, "wp03-scenario1")

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]
    # The enriched shape Clarification 1 requires — NOT the raw create_mission
    # payload one layer beneath it.
    assert data["scaffold_only"] is True
    assert data["spec_state"] == "scaffold_only"
    assert "next_action" in data and data["next_action"]
    assert data["next_step"] == data["next_action"]
    # Mission identity + spec.md path, present on the raw payload too.
    assert data["mission_slug"].startswith("wp03-scenario1-")
    spec_file = Path(data["spec_file"])
    assert spec_file.name == "spec.md"
    assert spec_file.exists()
    feature_dir = Path(data["feature_dir"])
    assert feature_dir.is_dir()
    assert (feature_dir / "meta.json").exists()


# ---------------------------------------------------------------------------
# Acceptance Scenario 2 — plan: unenriched pass-through of setup_plan
# ---------------------------------------------------------------------------


def test_plan_scaffolds_plan_md_as_raw_pass_through(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    created = _specify(repo, "wp03-scenario2")
    assert created["success"] is True, created
    mission_slug = created["data"]["mission_slug"]

    # Author + commit a substantive spec so setup_plan proceeds past the
    # committed-and-substantive gate (mirrors test_specify_plan_commit_boundary.py).
    spec_file = Path(created["data"]["spec_file"])
    spec_file.write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "substantive spec")

    result = _run(
        repo,
        ["plan", "--mission", mission_slug, "--policy", _POLICY],
    )
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]
    # Real, verified setup_plan() payload key (see module docstring note 2).
    assert "plan_file" in data, data
    plan_file = Path(data["plan_file"])
    assert plan_file.name == "plan.md"
    assert plan_file.exists()
    # Unenriched pass-through: no specify-only fields leaked onto plan's data.
    assert "scaffold_only" in data  # setup_plan's OWN field, not specify's enrichment
    assert "spec_state" not in data
    assert "next_action" not in data


# ---------------------------------------------------------------------------
# Acceptance Scenario 3 — tasks: unenriched pass-through of finalize_tasks
# ---------------------------------------------------------------------------


def test_tasks_finalizes_wp_manifest_as_raw_pass_through(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    created = _specify(repo, "wp03-scenario3")
    assert created["success"] is True, created
    mission_slug = created["data"]["mission_slug"]
    feature_dir = Path(created["data"]["feature_dir"])

    spec_file = Path(created["data"]["spec_file"])
    spec_file.write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "substantive spec")

    plan_result = _run(repo, ["plan", "--mission", mission_slug, "--policy", _POLICY])
    plan_envelope = _envelope(plan_result)
    assert plan_envelope["success"] is True, plan_envelope

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "WP01-task.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Test WP01\n"
        "dependencies: []\n"
        "requirement_refs: [FR-001]\n"
        "subtasks: []\n"
        "owned_files:\n"
        "  - src/module_wp01/**\n"
        "authoritative_surface: src/module_wp01/\n"
        "execution_mode: code_change\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## Work Package WP01\n\n**Dependencies**: None\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed tasks")

    result = _run(repo, ["tasks", "--mission", mission_slug, "--policy", _POLICY])
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]
    # Real finalize_tasks() shape — WP count + modified-WP roster.
    assert data["wp_count"] == 1
    assert data["modified_wps"] == ["WP01"]
    # Unenriched pass-through: no specify-only fields leaked here either.
    assert "scaffold_only" not in data
    assert "spec_state" not in data


# ---------------------------------------------------------------------------
# Acceptance Scenario 4 — specify twice: structured duplicate-mission failure
# ---------------------------------------------------------------------------


def test_specify_twice_for_same_slug_fails_closed_with_structured_error(
    tmp_path: Path,
) -> None:
    """Second ``specify`` call for the identical slug must NOT succeed silently
    and must NOT propagate a bare exception/traceback — it must fail closed
    with a structured ``error_code``, leaving the first mission's meta.json
    byte-identical (never a silent overwrite).

    Ground truth (verified during implementation by direct invocation): a
    second ``create_mission`` call for the same slug within the same mid8
    time-bucket regenerates byte-identical scaffold content, so the
    underlying ``safe_commit`` sees an empty changeset and raises — this is
    the "already-established duplicate-mission error" the WP prompt refers
    to; classifying it into a stable ``error_code`` (rather than letting the
    bare ``{"error": ...}`` propagate uncoded) is this WP's job.
    """
    repo = _init_repo(tmp_path)

    first = _specify(repo, "wp03-scenario4")
    assert first["success"] is True, first
    feature_dir = Path(first["data"]["feature_dir"])
    meta_before = (feature_dir / "meta.json").read_text(encoding="utf-8")

    second = _specify(repo, "wp03-scenario4")

    assert second["success"] is False, second
    assert second["error_code"] is not None
    assert second["error_code"] != ""
    # Never a bare unstructured exception surface.
    assert "message" in second["data"]

    # The first mission directory is untouched.
    assert feature_dir.exists()
    assert (feature_dir / "meta.json").read_text(encoding="utf-8") == meta_before
