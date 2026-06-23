"""SC-6 e2e: planning-phase placement threading — the catch-22 killer (WP05, T022).

Mission ``tooling-stability-guard-coherence-01KTRC04`` (FR-003, C-GUARD-3,
contracts C-GUARD-3/C-GUARD-3a). This is the #1777/#1784 root-cause regression
net: a fresh mission on a **protected-target** repo must complete
``tasks scaffold → finalize-tasks`` with planning artifacts committed to their
**resolved destination** — NOT refused with a pre-lanes "switch to the lane
branch" instruction (refusal-to-nowhere), and NOT failing with "spec.md not
found".

The decisive structural fact (verified in WP05 design): on a protected-target
repo the mission's resolved placement is the NON-protected coordination branch,
so a ``GuardCapability.STANDARD`` commit lands there cleanly with no guard
relaxation (C-003 — the WP01 protection invariants stay green; see
``tests/git/test_protection_preserved.py``).

Topologies parametrized (FR-003 "must hold for protected-main, flattened, AND
coordination topologies"):

* ``protected-main``  — target == ``main`` (protected) + a coordination branch
  (what ``mission create`` materializes); placement = the coord ref.
* ``coordination``    — explicit coordination branch off a non-protected target.
* ``flattened``       — non-protected target, NO coordination branch; placement
  == the target itself (FLATTENED).

The fixture is WP01's real-git ``protected_target_repo`` (it asserts the
``.kittify/`` precondition so the guard is not vacuously skipped).

Per F-001 (this mission's ``research/observations.md``): a finalize RE-RUN must
be idempotent — once a coordination worktree exists the read-path resolver
selects it, but the merge-target ``meta.json`` lives on the primary checkout, so
a naive coord-anchored read raised ``PLANNING_BRANCH_NOT_PERSISTED`` on the
second finalize. The re-run assertion pins that this no longer wedges.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from mission_runtime import (
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.cli.commands.agent.mission import app

from tests.git.protected_target_fixtures import (  # noqa: F401 — pytest fixture re-export
    ProtectedTargetRepo,
    protected_target_repo,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.regression]

runner = CliRunner()

# A 26-char Crockford ULID; mid8 is its first 8 chars.
_MISSION_ID = "01SC6PLACEMENT000000000001"
_MID8 = _MISSION_ID[:8]


@dataclass(frozen=True)
class _Topology:
    name: str
    target_branch: str
    coordination_branch: str | None
    expected_routes_coord: bool


# The flattened (legacy, no-coordination-branch) topology is parametrized but
# marked xfail: the WP05 placement projection resolves it CORRECTLY to the
# FLATTENED target (see ``test_resolve_placement_only.py``), but a finalize
# *run* on a legacy mission trips a PRE-EXISTING, out-of-scope status-bootstrap
# bug — ``bootstrap_canonical_state``'s legacy path derives its commit
# destination from the process CWD git context instead of the resolved
# ``repo_root`` (it reports "Legacy mission detected at <cwd>"), so it is not
# CWD-invariant under the patched-root e2e harness. Every mission ``mission
# create`` mints today carries a coordination branch (verified in WP05 design),
# so the catch-22's live shapes are protected-main + coordination, which pass.
# The flattened run-path belongs to the legacy-bootstrap CWD-invariance surface
# (coordination/status_transition), not WP05's placement threading.
_FLATTENED_BOOTSTRAP_CWD_GAP = (
    "legacy-topology status bootstrap resolves its commit destination from the "
    "process CWD git context, not the resolved repo_root (out-of-scope "
    "pre-existing gap; placement projection itself resolves flattened correctly "
    "— see tests/mission_runtime/test_resolve_placement_only.py)"
)

_TOPOLOGIES = [
    _Topology(
        name="protected-main",
        target_branch="main",
        coordination_branch=f"kitty/mission-sc6-mission-{_MID8}",
        expected_routes_coord=True,
    ),
    _Topology(
        name="coordination",
        target_branch="feat/non-protected-target",
        coordination_branch=f"kitty/mission-sc6-mission-{_MID8}",
        expected_routes_coord=True,
    ),
    pytest.param(
        _Topology(
            name="flattened",
            target_branch="feat/non-protected-target",
            coordination_branch=None,
            expected_routes_coord=False,
        ),
        # WP06 (R9): this legacy-bootstrap CWD gap genuinely xfails today, so the
        # guard is strict — if the underlying fix lands and the test starts
        # passing, ``strict=True`` turns the unexpected XPASS into a failure that
        # forces this marker to be retired rather than silently masking a fixed
        # bug.
        marks=pytest.mark.xfail(reason=_FLATTENED_BOOTSTRAP_CWD_GAP, strict=True),
    ),
]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


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


def _scaffold_mission(repo: Path, topology: _Topology) -> tuple[str, Path, str]:
    """Build a coordination/flattened/protected-main mission in ``repo``.

    Mirrors the on-disk shape ``mission create`` produces (meta.json on the
    primary checkout; coordination branch minted when the topology has one).
    Returns (mission_dirname, feature_dir, placement_ref).
    """
    mission_slug = "sc6-mission"
    mission_dirname = f"{mission_slug}-{_MID8}"
    feature_dir = repo / "kitty-specs" / mission_dirname
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta: dict[str, object] = {
        "mission_slug": mission_dirname,
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        "target_branch": topology.target_branch,
    }
    if topology.coordination_branch is not None:
        meta["coordination_branch"] = topology.coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")

    _write_wp(tasks_dir, "WP01")
    _write_spec(feature_dir)
    _write_tasks_md(feature_dir, ["WP01"])

    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed mission")

    # Branch the non-protected target (and the coordination branch) off the seed
    # commit so they CONTAIN the mission artifacts.
    if topology.coordination_branch is not None:
        # Coordination / protected-main: HEAD stays on the protected ``main`` the
        # fixture created — exercising the catch-22 entry condition (the operator
        # is on a protected branch when planning runs); the placement is the
        # NON-protected coordination ref.
        if topology.target_branch != "main":
            _git(repo, "branch", topology.target_branch)
        _git(repo, "branch", topology.coordination_branch)
    elif topology.target_branch != "main":
        # Flattened: there is no coordination branch, so the placement IS the
        # (non-protected) target. Genuine flattened topology checks the target
        # out as HEAD — the status bootstrap and the artifact commit both land
        # on that single branch (C-001).
        _git(repo, "checkout", "-q", "-b", topology.target_branch)

    placement = resolve_placement_only(repo, mission_dirname)
    # FR-001b: the coord-vs-primary decision reads the STORED topology, not a
    # per-ref enum on the placement.
    routes_coord = routes_through_coordination(resolve_topology(repo, mission_dirname))
    assert routes_coord is topology.expected_routes_coord, (
        f"{topology.name}: expected routes_through_coordination="
        f"{topology.expected_routes_coord}, got {routes_coord}"
    )
    return mission_dirname, feature_dir, placement.ref


def _run_finalize(repo: Path, mission_slug: str) -> Result:
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
            ["finalize-tasks", "--mission", mission_slug, "--json"],
            catch_exceptions=False,
        )


@pytest.fixture(autouse=True)
def _disable_saas_fanout(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as emit_module

    monkeypatch.setattr(emit_module, "_saas_fan_out", lambda *a, **k: None)


@pytest.mark.parametrize("topology", _TOPOLOGIES, ids=lambda t: t.name)
def test_sc6_finalize_lands_on_resolved_placement_no_catch22(
    protected_target_repo: ProtectedTargetRepo,  # noqa: F811
    topology: _Topology,
) -> None:
    """SC-6: finalize-tasks commits planning artifacts to the resolved placement.

    No "spec.md not found"; no refusal-to-nowhere. The fixture guarantees the
    guard is engaged (``.kittify/`` present) so the success is non-vacuous.
    """
    repo = protected_target_repo
    repo.assert_is_spec_kitty_project()
    repo.assert_target_is_protected()

    mission_slug, _feature_dir, placement_ref = _scaffold_mission(
        repo.repo_root, topology
    )

    result = _run_finalize(repo.repo_root, mission_slug)

    assert result.exit_code == 0, (
        f"[{topology.name}] finalize-tasks refused / failed (exit "
        f"{result.exit_code}); the catch-22 is NOT killed:\n{result.output}"
    )
    payload = _parse_json_from_output(result.output)
    assert payload.get("result") == "success", (
        f"[{topology.name}] unexpected finalize result: {payload}"
    )

    # No refusal-to-nowhere and no missing-spec misfire leaked into the output.
    assert "switch to the lane branch" not in result.output.lower(), (
        f"[{topology.name}] refusal-to-nowhere leaked into finalize output"
    )
    assert "spec.md not found" not in result.output, (
        f"[{topology.name}] finalize falsely reported spec.md missing"
    )

    # The tasks commit landed on the RESOLVED placement ref — assert a commit
    # with the finalize message exists on that branch.
    log = subprocess.run(
        ["git", "log", "--oneline", "-10", placement_ref],
        cwd=repo.repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "Add tasks for feature" in log, (
        f"[{topology.name}] tasks commit not found on resolved placement "
        f"{placement_ref!r}:\n{log}"
    )


@pytest.mark.parametrize("topology", _TOPOLOGIES, ids=lambda t: t.name)
def test_sc6_finalize_is_idempotent_on_rerun(
    protected_target_repo: ProtectedTargetRepo,  # noqa: F811
    topology: _Topology,
) -> None:
    """F-001: a finalize RE-RUN does not wedge (PLANNING_BRANCH_NOT_PERSISTED).

    The first finalize may materialize a coordination worktree; the second must
    still resolve the merge target from the PRIMARY meta.json — not the
    coord worktree (which never carries meta.json) — and succeed.
    """
    repo = protected_target_repo
    mission_slug, _feature_dir, _placement_ref = _scaffold_mission(
        repo.repo_root, topology
    )

    first = _run_finalize(repo.repo_root, mission_slug)
    assert first.exit_code == 0, (
        f"[{topology.name}] first finalize failed:\n{first.output}"
    )

    second = _run_finalize(repo.repo_root, mission_slug)
    assert second.exit_code == 0, (
        f"[{topology.name}] finalize RE-RUN wedged (F-001 idempotency regression) "
        f"(exit {second.exit_code}):\n{second.output}"
    )
    assert "PLANNING_BRANCH_NOT_PERSISTED" not in second.output, (
        f"[{topology.name}] re-run raised PLANNING_BRANCH_NOT_PERSISTED:\n"
        f"{second.output}"
    )
    payload = _parse_json_from_output(second.output)
    assert payload.get("result") == "success", (
        f"[{topology.name}] re-run did not report success: {payload}"
    )
