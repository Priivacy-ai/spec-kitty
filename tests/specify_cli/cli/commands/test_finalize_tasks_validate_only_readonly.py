"""``finalize-tasks --validate-only`` is read-only (AC-C1, FR-002, #1861 Part 1).

Mission ``coordination-merge-stabilization-01KTXRVR`` / WP02 / T005.

Contract (``contracts/class-c-validate-only-readonly.md``):

GIVEN a repository where the mission target branch differs from the currently
checked-out branch, WHEN the operator runs ``finalize-tasks --validate-only``,
THEN ``git symbolic-ref HEAD`` is byte-identical before and after, AND
``git status --porcelain`` output is byte-identical before and after (no
staging, no checkout, no writes), AND validation results are identical to
those produced by the commit-phase run's validation step.

The fixture mirrors ``test_sc6_planning_placement_e2e.py`` (the canonical
finalize-tasks coordination-topology e2e harness): a real spec-kitty git repo
(``protected_target_repo``) with a coordination-topology mission whose
``meta.json`` target branch is ``main`` while HEAD is parked on a different
planning branch — exactly the state in which the pre-fix eager
``_ensure_branch_checked_out`` call mutated the checkout.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app

from tests.git.protected_target_fixtures import (  # noqa: F401 — pytest fixture re-export
    ProtectedTargetRepo,
    protected_target_repo,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.regression]

runner = CliRunner()

# A 26-char mission id; mid8 is its first 8 chars (mirrors the SC6 harness).
_MISSION_ID = "01T005VALIDATEONLY00000001"
_MID8 = _MISSION_ID[:8]

# The branch the operator is parked on when running finalize. write-surface-
# coherence (FR-002 / D-3): planning artifacts land on the primary feature
# target_branch — a NON-protected branch the operator is ON. So the planning
# branch IS the mission ``target_branch`` here; the commit-phase lands on it
# directly, and ``--validate-only`` performs ZERO git mutations regardless.
_PLANNING_BRANCH = "feat/planning-work"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _git_bytes(repo: Path, *args: str) -> bytes:
    """Raw stdout bytes of a git command — for byte-identical AC-C1 captures."""
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True
    ).stdout


def _parse_json_from_output(output: str) -> dict[str, object]:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("{"):
            return dict(json.loads(stripped))
    raise ValueError(f"No JSON object found in finalize-tasks output:\n{output}")


def _write_wp(tasks_dir: Path, wp_id: str) -> None:
    (tasks_dir / f"{wp_id}-task.md").write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"dependencies: []\n"
        f"requirement_refs: [FR-001]\n"
        f"subtasks: []\n"
        f"owned_files:\n"
        f"  - src/module_{wp_id.lower()}/**\n"
        f"authoritative_surface: src/module_{wp_id.lower()}/\n"
        f"execution_mode: code_change\n"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )


def _write_spec(feature_dir: Path) -> None:
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Test requirement | Test passes. | proposed |\n",
        encoding="utf-8",
    )


def _write_tasks_md(feature_dir: Path, wp_ids: list[str]) -> None:
    sections = "\n".join(
        f"## Work Package {wp}\n\n**Dependencies**: None\n" for wp in wp_ids
    )
    (feature_dir / "tasks.md").write_text(f"# Tasks\n\n{sections}\n", encoding="utf-8")


def _scaffold_coord_mission_on_divergent_branch(repo: Path) -> str:
    """Coordination-topology mission whose target branch differs from HEAD.

    Mirrors the SC6 ``_scaffold_mission`` shape: artifacts committed on
    ``main`` (the mission target), a coordination branch minted off the seed
    commit, and HEAD parked on a *different* planning branch afterwards.
    Returns the mission dirname.
    """
    mission_slug = "vo-mission"
    mission_dirname = f"{mission_slug}-{_MID8}"
    feature_dir = repo / "kitty-specs" / mission_dirname
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta: dict[str, object] = {
        "mission_slug": mission_dirname,
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        # The primary feature target_branch is the (non-protected) branch the
        # operator is on (FR-002 / D-3): planning artifacts land here directly.
        "target_branch": _PLANNING_BRANCH,
        "coordination_branch": f"kitty/mission-{mission_slug}-{_MID8}",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")

    _write_wp(tasks_dir, "WP01")
    _write_spec(feature_dir)
    _write_tasks_md(feature_dir, ["WP01"])

    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed mission")
    _git(repo, "branch", f"kitty/mission-{mission_slug}-{_MID8}")

    # The operator is ON the feature target_branch (D-3 invariant): the planning
    # commit lands there directly. ``--validate-only`` mutates NOTHING regardless.
    _git(repo, "checkout", "-q", "-b", _PLANNING_BRANCH)

    return mission_dirname


def _run_finalize(repo: Path, mission_slug: str, *extra_args: str) -> Result:
    with (
        patch(
            "specify_cli.cli.commands.agent.mission.locate_project_root",
            return_value=repo,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission.run_git_preflight",
            return_value=type("P", (), {"passed": True})(),
        ),
        patch(
            "specify_cli.cli.commands.agent.mission.is_saas_sync_enabled",
            return_value=False,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission.get_emitter",
            return_value=type(
                "E", (), {"generate_causation_id": lambda self: "test-id"}
            )(),
        ),
    ):
        return runner.invoke(
            app,
            ["finalize-tasks", "--mission", mission_slug, "--json", *extra_args],
            catch_exceptions=False,
        )


@pytest.fixture(autouse=True)
def _disable_saas_fanout(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as emit_module
    import specify_cli.sync.feature_flags as feature_flags_module

    monkeypatch.setattr(emit_module, "_saas_fan_out", lambda *a, **k: None)
    # Disable SaaS sync at the source module so late imports inside the dossier
    # pipeline see it disabled too — environment-dependent dossier writes would
    # otherwise leak into the byte-identical porcelain assertions.
    monkeypatch.setattr(
        feature_flags_module, "is_saas_sync_enabled", lambda *a, **k: False
    )


class TestValidateOnlyIsReadOnly:
    """AC-C1: --validate-only performs ZERO git mutations."""

    def test_head_and_porcelain_byte_identical_and_nothing_staged(
        self,
        protected_target_repo: ProtectedTargetRepo,  # noqa: F811
    ) -> None:
        repo = protected_target_repo.repo_root
        protected_target_repo.assert_is_spec_kitty_project()
        mission_slug = _scaffold_coord_mission_on_divergent_branch(repo)

        head_before = _git_bytes(repo, "symbolic-ref", "HEAD")
        porcelain_before = _git_bytes(repo, "status", "--porcelain")
        assert head_before.decode().strip().endswith(_PLANNING_BRANCH), (
            "fixture precondition violated: HEAD must start on the feature "
            "target_branch so any mutation by --validate-only (which must be "
            "ZERO) is observable against this known starting state"
        )

        result = _run_finalize(repo, mission_slug, "--validate-only")

        assert result.exit_code == 0, (
            f"--validate-only failed (exit {result.exit_code}):\n{result.output}"
        )

        head_after = _git_bytes(repo, "symbolic-ref", "HEAD")
        porcelain_after = _git_bytes(repo, "status", "--porcelain")
        staged_after = _git_bytes(repo, "diff", "--cached", "--name-only")

        assert head_after == head_before, (
            "--validate-only CHECKED OUT a branch (read-only contract "
            f"violated): HEAD {head_before!r} -> {head_after!r}"
        )
        assert porcelain_after == porcelain_before, (
            "--validate-only changed the working tree / index "
            "(read-only contract violated):\n"
            f"before: {porcelain_before!r}\nafter:  {porcelain_after!r}"
        )
        assert staged_after == b"", (
            f"--validate-only staged files: {staged_after!r}"
        )

    def test_validation_findings_match_commit_phase_run(
        self,
        protected_target_repo: ProtectedTargetRepo,  # noqa: F811
    ) -> None:
        """AC-C1 (4): validate-only findings == the commit-phase run's
        validation findings on the same fixture."""
        repo = protected_target_repo.repo_root
        mission_slug = _scaffold_coord_mission_on_divergent_branch(repo)

        validate_result = _run_finalize(repo, mission_slug, "--validate-only")
        assert validate_result.exit_code == 0, validate_result.output
        validate_payload = _parse_json_from_output(validate_result.output)
        assert validate_payload.get("result") == "validation_passed", validate_payload

        commit_result = _run_finalize(repo, mission_slug)
        assert commit_result.exit_code == 0, commit_result.output
        commit_payload = _parse_json_from_output(commit_result.output)
        assert commit_payload.get("result") == "success", commit_payload

        # The validation findings shared by both payload shapes must agree.
        assert validate_payload["wp_count"] == commit_payload["wp_count"]
        assert (
            validate_payload["updated_wp_count"]
            == commit_payload["updated_wp_count"]
        )
        assert (
            validate_payload["ownership_warnings"]
            == commit_payload["ownership_warnings"]
        )
