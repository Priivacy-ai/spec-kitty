"""Acceptance coverage for cancellation-aware ``finalize-tasks`` (#3432)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import mission_finalize as finalizer
from specify_cli.cli.commands.agent.mission import app
from specify_cli.lanes.compute import compute_lanes
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.ownership.models import OwnershipManifest, WorkProductKind
from specify_cli.status.bootstrap import BootstrapResult
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()


def _wp_document(
    wp_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    execution_mode: str = "code_change",
    owned_files: tuple[str, ...] = (),
    authoritative_surface: str = "src/example/",
    include_ownership_fields: bool = True,
    include_static_bootstrap_fields: bool = False,
) -> str:
    dependency_yaml = "[]" if not dependencies else "[" + ", ".join(dependencies) + "]"
    owned_yaml = "[]\n" if not owned_files else "\n" + "".join(f"  - {path}\n" for path in owned_files)
    ownership = (
        f"execution_mode: {execution_mode}\n"
        f"owned_files: {owned_yaml}"
        f"authoritative_surface: {authoritative_surface}\n"
        if include_ownership_fields
        else ""
    )
    static_bootstrap = (
        "planning_base_branch: main\n"
        "merge_target_branch: main\n"
        f"branch_strategy: {json.dumps(finalizer._branch_strategy_text('main'))}\n"
        if include_static_bootstrap_fields
        else ""
    )
    return (
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id} cancellation acceptance fixture\n"
        f"dependencies: {dependency_yaml}\n"
        "requirement_refs: [FR-001]\n"
        f"{static_bootstrap}"
        f"{ownership}"
        "---\n"
        f"# {wp_id}\n"
    )


def _build_mission(tmp_path: Path, wp_documents: dict[str, str]) -> Path:
    mission_slug = "3432-canceled-finalization"
    mission_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tmp_path / "src" / "example").mkdir(parents=True)
    (tmp_path / "src" / "example" / "active.py").write_text("ACTIVE = True\n", encoding="utf-8")
    (tmp_path / "src" / "example" / "other.py").write_text("OTHER = True\n", encoding="utf-8")
    (mission_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (mission_dir / "spec.md").write_text(
        "# Spec\n## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Finalize cancellation-aware lanes | Covered by every WP. | proposed |\n",
        encoding="utf-8",
    )
    (mission_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    task_sections: list[str] = []
    for wp_id, document in wp_documents.items():
        (tasks_dir / f"{wp_id}-fixture.md").write_text(document, encoding="utf-8")
        task_sections.append(f"## {wp_id}\n**Requirement Refs**: FR-001\n")
    (mission_dir / "tasks.md").write_text("\n".join(task_sections), encoding="utf-8")
    return mission_dir


def _set_lane(mission_dir: Path, wp_id: str, lane: Lane) -> None:
    append_event(
        mission_dir,
        StatusEvent(
            event_id=f"01J3432{wp_id}{lane.value.upper()}EVENT000",
            mission_slug=mission_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=lane,
            at="2026-08-24T00:00:00Z",
            actor="codex",
            force=False,
            execution_mode="worktree",
        ),
    )


def _cancel(mission_dir: Path, wp_id: str) -> None:
    _set_lane(mission_dir, wp_id, Lane.CANCELED)


def _transition(mission_dir: Path, wp_id: str, from_lane: Lane, to_lane: Lane) -> None:
    append_event(
        mission_dir,
        StatusEvent(
            event_id=f"01J3432{wp_id}{from_lane.value.upper()}{to_lane.value.upper()}000",
            mission_slug=mission_dir.name,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-08-24T00:02:00Z",
            actor="codex",
            force=False,
            execution_mode="worktree",
        ),
    )


def _reopen(mission_dir: Path, wp_id: str) -> None:
    append_event(
        mission_dir,
        StatusEvent(
            event_id=f"01J3432{wp_id}REOPENED0000000",
            mission_slug=mission_dir.name,
            wp_id=wp_id,
            from_lane=Lane.CANCELED,
            to_lane=Lane.PLANNED,
            at="2026-08-24T00:01:00Z",
            actor="codex",
            force=True,
            execution_mode="worktree",
        ),
    )


def _invoke(
    tmp_path: Path,
    mission_dir: Path,
    *,
    validate_only: bool = True,
    json_output: bool = True,
):
    args = ["finalize-tasks", "--mission", mission_dir.name]
    if validate_only:
        args.append("--validate-only")
    if json_output:
        args.append("--json")
    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.mission._find_feature_directory", return_value=mission_dir),
        patch("specify_cli.cli.commands.agent.mission._show_branch_context", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.mission_finalize._run_saas_boundary_preflight"),
    ):
        return runner.invoke(app, args)


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def _invoke_normal(tmp_path: Path, mission_dir: Path):
    """Run the real command/finalizer path while isolating external writers."""
    bootstrap = BootstrapResult(
        total_wps=len(list((mission_dir / "tasks").glob("WP*.md"))),
        already_initialized=0,
        newly_seeded=0,
        skipped=0,
    )
    commit_outcome = MagicMock(
        commit_created=False,
        commit_hash=None,
        commit_hashes=[],
        files_committed=[],
    )
    with (
        patch(
            "specify_cli.cli.commands.agent.mission_finalize._bootstrap_canonical_state_via_mission",
            return_value=bootstrap,
        ),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_local_canonical_events"),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_tasks_started"),
        patch(
            "specify_cli.cli.commands.agent.mission_finalize._scaffold_acceptance_matrix_if_lane_based"
        ),
        patch(
            "specify_cli.cli.commands.agent.mission_finalize._commit_finalize_artifacts",
            return_value=commit_outcome,
        ),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_saas_wp_created"),
        patch("specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled"),
    ):
        return _invoke(tmp_path, mission_dir, validate_only=False)


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_canceled_wp_is_excluded_from_ownership_validation(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01",
                owned_files=("kitty-specs/3432-canceled-finalization/plan.md",),
            ),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )
    _cancel(mission_dir, "WP01")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    payload = _payload(result.stdout)
    assert payload["validation"]["lanes_preview"]["count"] == 1  # type: ignore[index]


def test_every_eligible_to_canceled_dependency_is_reported(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
            "WP02": _wp_document(
                "WP02",
                dependencies=("WP01",),
                owned_files=("src/example/active.py",),
            ),
        },
    )
    _cancel(mission_dir, "WP01")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 1
    payload = _payload(result.stdout)
    assert payload["error_code"] == "CANCELED_WP_DEPENDENCY"
    assert payload["stale_dependencies"] == [
        {
            "dependent_wp_id": "WP02",
            "canceled_dependency_wp_id": "WP01",
            "recovery": "Remove the dependency or repoint WP02 to a non-canceled prerequisite.",
        }
    ]


def test_all_canceled_validate_only_reports_zero_lanes(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01",
                execution_mode="planning_artifact",
                owned_files=(),
                authoritative_surface="kitty-specs/3432-canceled-finalization/",
            )
        },
    )
    _cancel(mission_dir, "WP01")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    payload = _payload(result.stdout)
    preview = payload["validation"]["lanes_preview"]  # type: ignore[index]
    assert preview["computed"] is True  # type: ignore[index]
    assert preview["count"] == 0  # type: ignore[index]
    assert preview["lane_ids"] == []  # type: ignore[index]


def test_stale_refusal_precedes_every_finalization_writer(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
            "WP02": _wp_document(
                "WP02",
                dependencies=("WP01",),
                owned_files=("src/example/active.py",),
            ),
        },
    )
    _cancel(mission_dir, "WP01")
    writer_names = (
        "_persist_target_branch_override",
        "_scaffold_issue_matrix_if_present",
        "_run_bootstrap_loop",
        "_flush_frontmatter_writes",
        "_emit_tasks_started",
        "_run_commit_pipeline",
    )
    writers = {name: MagicMock() for name in writer_names}
    before = _file_snapshot(tmp_path)

    with ExitStack() as stack:
        for name, writer in writers.items():
            stack.enter_context(
                patch(f"specify_cli.cli.commands.agent.mission_finalize.{name}", writer)
            )
        result = _invoke(tmp_path, mission_dir, validate_only=False)

    assert result.exit_code == 1
    assert _payload(result.stdout)["error_code"] == "CANCELED_WP_DEPENDENCY"
    assert _file_snapshot(tmp_path) == before
    for writer in writers.values():
        writer.assert_not_called()


def test_human_refusal_renders_every_sorted_pair(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
            "WP03": _wp_document(
                "WP03",
                dependencies=("WP02", "WP01"),
                owned_files=("src/example/active.py",),
            ),
        },
    )
    _cancel(mission_dir, "WP01")
    _cancel(mission_dir, "WP02")

    result = _invoke(tmp_path, mission_dir, json_output=False)

    assert result.exit_code == 1
    assert "WP03 depends on canceled WP01" in result.stdout
    assert "WP03 depends on canceled WP02" in result.stdout
    assert result.stdout.index("canceled WP01") < result.stdout.index("canceled WP02")
    assert result.stdout.count("Remove the dependency or repoint WP03") == 2


@pytest.mark.parametrize("scenario", ["success", "stale", "all_canceled"])
def test_canonical_lifecycle_reader_is_called_once(
    tmp_path: Path, scenario: str
) -> None:
    if scenario == "stale":
        documents = {
            "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
            "WP02": _wp_document(
                "WP02", dependencies=("WP01",), owned_files=("src/example/active.py",)
            ),
        }
    elif scenario == "all_canceled":
        documents = {
            "WP01": _wp_document(
                "WP01", execution_mode="planning_artifact", owned_files=()
            )
        }
    else:
        documents = {
            "WP01": _wp_document("WP01", owned_files=("src/example/active.py",))
        }
    mission_dir = _build_mission(tmp_path, documents)
    if scenario in {"stale", "all_canceled"}:
        _cancel(mission_dir, "WP01")
    else:
        _set_lane(mission_dir, "WP01", Lane.PLANNED)

    from specify_cli.status.store import read_events as real_reader

    reader = MagicMock(side_effect=real_reader)
    with patch("specify_cli.status.store.read_events", reader):
        result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == (1 if scenario == "stale" else 0)
    reader.assert_called_once()


def test_canceled_invalid_surface_and_missing_literal_are_ignored(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01",
                owned_files=("src/example/does-not-exist.py",),
                authoritative_surface="not-a-prefix/",
            ),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )
    _cancel(mission_dir, "WP01")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout


@pytest.mark.parametrize("validate_only", [False, True])
def test_canceled_prompt_without_ownership_is_never_fabricated_or_warned(
    tmp_path: Path,
    validate_only: bool,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01",
                include_ownership_fields=False,
                include_static_bootstrap_fields=True,
            ),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )
    _cancel(mission_dir, "WP01")
    prompt = mission_dir / "tasks" / "WP01-fixture.md"
    before = prompt.read_bytes()

    result = (
        _invoke(tmp_path, mission_dir, validate_only=True)
        if validate_only
        else _invoke_normal(tmp_path, mission_dir)
    )

    assert result.exit_code == 0, result.stdout
    assert prompt.read_bytes() == before
    assert "execution_mode" not in prompt.read_text(encoding="utf-8")
    payload = _payload(result.stdout)
    assert not any(
        row.get("wp_id") == "WP01"
        for row in payload.get("would_modify", [])  # type: ignore[union-attr]
    )
    assert not any("WP01" in warning for warning in payload["ownership_warnings"])  # type: ignore[union-attr]


def test_eligible_prompt_without_ownership_still_infers_and_fails(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", include_ownership_fields=False),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 1
    assert "ownership" in str(_payload(result.stdout)["error"]).lower()


def test_all_canceled_dependency_cycle_is_excluded_before_cycle_validation(
    tmp_path: Path,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", dependencies=("WP02",)),
            "WP02": _wp_document("WP02", dependencies=("WP01",)),
        },
    )
    _cancel(mission_dir, "WP01")
    _cancel(mission_dir, "WP02")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    assert _payload(result.stdout)["validation"]["lanes_preview"]["count"] == 0  # type: ignore[index]


def test_isolated_canceled_cycle_does_not_block_active_graph(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", dependencies=("WP02",)),
            "WP02": _wp_document("WP02", dependencies=("WP01",)),
            "WP03": _wp_document("WP03", owned_files=("src/example/active.py",)),
        },
    )
    _cancel(mission_dir, "WP01")
    _cancel(mission_dir, "WP02")

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    assert _payload(result.stdout)["validation"]["lanes_preview"]["count"] == 1  # type: ignore[index]


def test_eligible_dependency_cycle_still_fails(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document("WP01", dependencies=("WP02",)),
            "WP02": _wp_document("WP02", dependencies=("WP01",)),
        },
    )

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 1
    assert _payload(result.stdout)["cycles"]


def test_corrupt_canonical_status_fails_closed(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    (mission_dir / "status.events.jsonl").write_text("{not-json}\n", encoding="utf-8")
    before = _file_snapshot(tmp_path)

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 1
    assert "error" in _payload(result.stdout)
    assert _file_snapshot(tmp_path) == before


def test_all_canceled_normal_finalize_writes_zero_lane_manifest(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01", execution_mode="planning_artifact", owned_files=()
            )
        },
    )
    _cancel(mission_dir, "WP01")

    from specify_cli.status.bootstrap import BootstrapResult

    with (
        patch(
            "specify_cli.cli.commands.agent.mission.bootstrap_canonical_state",
            return_value=BootstrapResult(
                total_wps=1, already_initialized=1, newly_seeded=0, skipped=0
            ),
        ),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_local_canonical_events"),
        patch("specify_cli.cli.commands.agent.mission_finalize._commit_finalize_artifacts") as commit,
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_saas_wp_created"),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_success_report"),
    ):
        commit.return_value = MagicMock(
            commit_created=False,
            commit_hash=None,
            commit_hashes=[],
            files_committed=[],
        )
        result = _invoke(tmp_path, mission_dir, validate_only=False)

    assert result.exit_code == 0, result.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.lanes == []
    assert (mission_dir / "tasks" / "WP01-fixture.md").exists()
    assert (mission_dir / "status.events.jsonl").exists()


def test_governed_reopen_is_included_by_real_finalizer(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    _cancel(mission_dir, "WP01")
    _reopen(mission_dir, "WP01")

    result = _invoke_normal(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.lane_for_wp("WP01") is not None
    assert manifest.planning_artifact_wps == []


def test_mixed_canceled_first_normal_finalize_writes_surviving_active_lane(
    tmp_path: Path,
) -> None:
    """Cancellation alone must not masquerade as begun execution provenance."""
    mission_dir = _build_mission(
        tmp_path,
        {
            "WP01": _wp_document(
                "WP01", owned_files=("src/example/other.py",)
            ),
            "WP02": _wp_document(
                "WP02", owned_files=("src/example/active.py",)
            ),
        },
    )
    _cancel(mission_dir, "WP01")
    assert not (mission_dir / "lanes.json").exists()

    result = _invoke_normal(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.lane_for_wp("WP01") is None
    assert manifest.lane_for_wp("WP02") is not None
    assert [wp_id for lane in manifest.lanes for wp_id in lane.wp_ids] == ["WP02"]


@pytest.mark.parametrize(
    ("lifecycle_lanes", "expected"),
    [
        ({"WP01": Lane.PLANNED}, False),
        ({"WP01": Lane.CANCELED}, False),
        ({"WP01": Lane.CANCELED, "WP02": Lane.PLANNED}, False),
        ({"WP01": Lane.CANCELED, "WP02": Lane.CLAIMED}, True),
        ({"WP01": Lane.IN_PROGRESS}, True),
        ({"WP01": Lane.DONE}, True),
    ],
)
def test_execution_begun_ignores_only_planned_and_canceled_states(
    tmp_path: Path,
    lifecycle_lanes: dict[str, Lane],
    expected: bool,
) -> None:
    assert (
        finalizer._execution_has_begun(
            tmp_path,
            "3432-canceled-finalization",
            lifecycle_lanes,
        )
        is expected
    )


def test_execution_begun_reads_cancellation_as_pre_execution_but_claim_as_begun(
    tmp_path: Path,
) -> None:
    canceled_root = tmp_path / "canceled"
    canceled_dir = _build_mission(
        canceled_root,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    _cancel(canceled_dir, "WP01")
    assert not finalizer._execution_has_begun(canceled_root, canceled_dir.name)

    claimed_root = tmp_path / "claimed"
    claimed_dir = _build_mission(
        claimed_root,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    _set_lane(claimed_dir, "WP01", Lane.CLAIMED)
    assert finalizer._execution_has_begun(claimed_root, claimed_dir.name)


def test_no_cancellation_retains_full_finalizer_structure(tmp_path: Path) -> None:
    mission_slug = "3432-canceled-finalization"
    planning_path = f"kitty-specs/{mission_slug}/plan.md"
    documents = {
        "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
        "WP02": _wp_document(
            "WP02",
            dependencies=("WP01",),
            owned_files=("src/example/other.py",),
        ),
        "WP03": _wp_document(
            "WP03",
            execution_mode="planning_artifact",
            owned_files=(planning_path,),
            authoritative_surface=f"kitty-specs/{mission_slug}/",
        ),
    }
    mission_dir = _build_mission(tmp_path, documents)

    result = _invoke_normal(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    payload = _payload(result.stdout)
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    expected = compute_lanes(
        dependency_graph={"WP01": [], "WP02": ["WP01"], "WP03": []},
        ownership_manifests={
            "WP01": OwnershipManifest(
                execution_mode=WorkProductKind.CODE_CHANGE,
                owned_files=("src/example/active.py",),
                authoritative_surface="src/example/",
            ),
            "WP02": OwnershipManifest(
                execution_mode=WorkProductKind.CODE_CHANGE,
                owned_files=("src/example/other.py",),
                authoritative_surface="src/example/",
            ),
            "WP03": OwnershipManifest(
                execution_mode=WorkProductKind.PLANNING_ARTIFACT,
                owned_files=(planning_path,),
                authoritative_surface=f"kitty-specs/{mission_slug}/",
            ),
        },
        mission_slug=mission_slug,
        target_branch="main",
        wp_bodies={wp_id: f"# {wp_id}\n" for wp_id in documents},
    )
    assert [lane.to_dict() for lane in manifest.lanes] == [
        lane.to_dict() for lane in expected.lanes
    ]
    assert manifest.planning_artifact_wps == expected.planning_artifact_wps == ["WP03"]
    assert expected.collapse_report is not None
    # Empty collapse reports are intentionally omitted from persisted JSON,
    # while the command result still reports the complete baseline structure.
    assert manifest.collapse_report is None
    assert payload["lanes"]["collapse_report"] == expected.collapse_report.to_dict()  # type: ignore[index]
    assert payload["ownership_warnings"] == []
    assert "cycle_path" not in payload
    by_wp = {wp_id: manifest.lane_for_wp(wp_id) for wp_id in documents}
    assert by_wp["WP01"] is not None
    assert by_wp["WP02"] is not None
    assert by_wp["WP02"].depends_on_lanes == (by_wp["WP01"].lane_id,)


def test_repeated_finalize_replaces_prior_lane_with_zero_lane_manifest(
    tmp_path: Path,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    first = _invoke_normal(tmp_path, mission_dir)
    assert first.exit_code == 0, first.stdout
    prior = read_lanes_json(mission_dir)
    assert prior is not None
    assert prior.lane_for_wp("WP01") is not None

    _cancel(mission_dir, "WP01")
    prompt = mission_dir / "tasks" / "WP01-fixture.md"
    retained = {
        "prompt": prompt.read_bytes(),
        "tasks": (mission_dir / "tasks.md").read_bytes(),
        "events": (mission_dir / "status.events.jsonl").read_bytes(),
    }

    second = _invoke_normal(tmp_path, mission_dir)

    assert second.exit_code == 0, second.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.lanes == []
    assert all(not lane.depends_on_lanes for lane in manifest.lanes)
    assert prompt.read_bytes() == retained["prompt"]
    assert (mission_dir / "tasks.md").read_bytes() == retained["tasks"]
    assert (mission_dir / "status.events.jsonl").read_bytes() == retained["events"]


def test_fresh_no_event_mission_finalizes_without_inventing_status(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    event_log = mission_dir / "status.events.jsonl"
    assert not event_log.exists()

    result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    payload = _payload(result.stdout)
    assert payload["validation"]["lanes_preview"]["count"] == 1  # type: ignore[index]
    assert not event_log.exists()


def test_unavailable_coordination_surface_fails_closed_at_command_boundary(
    tmp_path: Path,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    before = _file_snapshot(tmp_path)
    reader = MagicMock()
    with (
        patch(
            "specify_cli.coordination.surface_resolver.resolve_status_surface_with_anchor",
            side_effect=RuntimeError("coordination surface unavailable"),
        ),
        patch("specify_cli.status.lane_reader.get_all_wp_lanes", reader),
    ):
        result = _invoke(tmp_path, mission_dir)

    assert result.exit_code == 1
    assert "coordination surface unavailable" in str(_payload(result.stdout)["error"])
    reader.assert_not_called()
    assert _file_snapshot(tmp_path) == before


def test_planning_tip_capture_returns_stripped_sha(tmp_path: Path) -> None:
    completed = MagicMock(returncode=0, stdout="abc123\n")
    with patch("subprocess.run", return_value=completed):
        assert finalizer._capture_target_branch_tip(tmp_path, "main") == "abc123"


@pytest.mark.parametrize("json_output", [False, True])
def test_missing_prior_manifest_refuses_execution_begun(
    tmp_path: Path,
    json_output: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit = MagicMock()
    with (
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_json", emit),
        pytest.raises(typer.Exit),
    ):
        finalizer._preserve_or_capture_planning_commit_sha(
            tmp_path,
            tmp_path,
            "3432-canceled-finalization",
            "main",
            lifecycle_lanes={"WP01": Lane.CLAIMED},
            json_output=json_output,
        )
    if json_output:
        assert "no lanes.json exists" in emit.call_args.args[0]["error"]
    else:
        assert "no lanes.json exists" in capsys.readouterr().out
        emit.assert_not_called()


def test_existing_manifest_preserves_planning_sha_after_claim_then_cancel(
    tmp_path: Path,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", owned_files=("src/example/active.py",))},
    )
    capture = MagicMock(side_effect=["planning-old", "planning-new"])
    with patch(
        "specify_cli.cli.commands.agent.mission_finalize._capture_target_branch_tip",
        capture,
    ):
        first = _invoke_normal(tmp_path, mission_dir)
        assert first.exit_code == 0, first.stdout
        _transition(mission_dir, "WP01", Lane.PLANNED, Lane.CLAIMED)
        _transition(mission_dir, "WP01", Lane.CLAIMED, Lane.CANCELED)
        second = _invoke_normal(tmp_path, mission_dir)

    assert second.exit_code == 0, second.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.planning_commit_sha == "planning-old"
    capture.assert_called_once()


def test_planned_to_canceled_without_manifest_is_pre_execution(tmp_path: Path) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", include_ownership_fields=False)},
    )
    _transition(mission_dir, "WP01", Lane.PLANNED, Lane.CANCELED)
    assert not (mission_dir / "lanes.json").exists()

    result = _invoke_normal(tmp_path, mission_dir)

    assert result.exit_code == 0, result.stdout
    manifest = read_lanes_json(mission_dir)
    assert manifest is not None
    assert manifest.lanes == []


@pytest.mark.parametrize("executing_lane", [Lane.CLAIMED, Lane.IN_PROGRESS])
def test_execution_then_canceled_without_manifest_refuses_provenance_guess(
    tmp_path: Path,
    executing_lane: Lane,
) -> None:
    mission_dir = _build_mission(
        tmp_path,
        {"WP01": _wp_document("WP01", include_ownership_fields=False)},
    )
    _transition(mission_dir, "WP01", Lane.PLANNED, executing_lane)
    _transition(mission_dir, "WP01", executing_lane, Lane.CANCELED)
    assert not (mission_dir / "lanes.json").exists()

    result = _invoke_normal(tmp_path, mission_dir)

    assert result.exit_code == 1
    assert "no lanes.json exists" in str(_payload(result.stdout)["error"])
    assert not (mission_dir / "lanes.json").exists()


@pytest.mark.parametrize("json_output", [False, True])
def test_missing_tasks_directory_has_explicit_command_diagnostic(
    tmp_path: Path,
    json_output: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit):
        finalizer._load_work_package_files(tmp_path, json_output=json_output)
    assert "Tasks directory not found" in capsys.readouterr().out


def test_canceled_empty_ownership_is_bypassed_but_eligible_control_fails(
    tmp_path: Path,
) -> None:
    canceled_root = tmp_path / "canceled"
    canceled_dir = _build_mission(
        canceled_root,
        {
            "WP01": _wp_document("WP01", owned_files=()),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )
    _cancel(canceled_dir, "WP01")
    canceled = _invoke(canceled_root, canceled_dir)
    assert canceled.exit_code == 0, canceled.stdout

    eligible_root = tmp_path / "eligible"
    eligible_dir = _build_mission(
        eligible_root,
        {
            "WP01": _wp_document("WP01", owned_files=()),
            "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
        },
    )
    eligible = _invoke(eligible_root, eligible_dir)
    assert eligible.exit_code == 1
    assert _payload(eligible.stdout)["error_code"] == (
        "OWNERSHIP_CONTRADICTION_CODE_CHANGE_EMPTY_OWNED_FILES"
    )


def test_canceled_invalid_surface_is_bypassed_but_eligible_control_fails(
    tmp_path: Path,
) -> None:
    def build(root: Path) -> Path:
        return _build_mission(
            root,
            {
                "WP01": _wp_document(
                    "WP01",
                    owned_files=("src/example/other.py",),
                    authoritative_surface="not-a-prefix/",
                ),
                "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
            },
        )

    canceled_root = tmp_path / "canceled"
    canceled_dir = build(canceled_root)
    _cancel(canceled_dir, "WP01")
    assert _invoke(canceled_root, canceled_dir).exit_code == 0

    eligible_root = tmp_path / "eligible"
    eligible = _invoke(eligible_root, build(eligible_root))
    assert eligible.exit_code == 1
    assert any(
        "authoritative_surface" in error
        for error in _payload(eligible.stdout)["ownership_errors"]  # type: ignore[union-attr]
    )


def test_canceled_unmatched_literal_is_bypassed_but_eligible_control_fails(
    tmp_path: Path,
) -> None:
    def build(root: Path) -> Path:
        return _build_mission(
            root,
            {
                "WP01": _wp_document(
                    "WP01", owned_files=("src/example/missing.py",)
                ),
                "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
            },
        )

    canceled_root = tmp_path / "canceled"
    canceled_dir = build(canceled_root)
    _cancel(canceled_dir, "WP01")
    assert _invoke(canceled_root, canceled_dir).exit_code == 0

    eligible_root = tmp_path / "eligible"
    eligible = _invoke(eligible_root, build(eligible_root))
    assert eligible.exit_code == 1
    assert _payload(eligible.stdout)["ownership_literal_path_errors"]


def test_canceled_overlap_is_bypassed_but_eligible_control_fails(
    tmp_path: Path,
) -> None:
    documents = {
        "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
        "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
    }
    canceled_root = tmp_path / "canceled"
    canceled_dir = _build_mission(canceled_root, documents)
    _cancel(canceled_dir, "WP01")
    assert _invoke(canceled_root, canceled_dir).exit_code == 0

    eligible_root = tmp_path / "eligible"
    eligible = _invoke(eligible_root, _build_mission(eligible_root, documents))
    assert eligible.exit_code == 1
    assert any(
        "overlapping paths" in error
        for error in _payload(eligible.stdout)["ownership_errors"]  # type: ignore[union-attr]
    )


def test_canceled_planning_mode_warning_is_bypassed_but_control_is_active(
    tmp_path: Path,
) -> None:
    documents = {
        "WP01": _wp_document(
            "WP01",
            execution_mode="planning_artifact",
            owned_files=("src/example/other.py",),
        ),
        "WP02": _wp_document("WP02", owned_files=("src/example/active.py",)),
    }
    canceled_root = tmp_path / "canceled"
    canceled_dir = _build_mission(canceled_root, documents)
    _cancel(canceled_dir, "WP01")
    canceled = _invoke(canceled_root, canceled_dir, json_output=False)
    assert canceled.exit_code == 0, canceled.stdout
    assert "planning_artifact WP owns files outside planning paths" not in canceled.stdout

    eligible_root = tmp_path / "eligible"
    eligible = _invoke(
        eligible_root,
        _build_mission(eligible_root, documents),
        json_output=False,
    )
    assert eligible.exit_code == 0, eligible.stdout
    assert "planning_artifact WP owns files outside planning paths" in eligible.stdout


def test_canceled_work_cannot_influence_collapse_but_eligible_control_does(
    tmp_path: Path,
) -> None:
    documents = {
        "WP01": _wp_document("WP01", owned_files=("src/example/active.py",)),
        "WP02": _wp_document(
            "WP02",
            dependencies=("WP01",),
            owned_files=("src/example/active.py",),
        ),
    }
    canceled_root = tmp_path / "canceled"
    canceled_dir = _build_mission(canceled_root, documents)
    _cancel(canceled_dir, "WP02")
    canceled = _invoke(canceled_root, canceled_dir)
    assert canceled.exit_code == 0, canceled.stdout
    canceled_report = _payload(canceled.stdout)["validation"]["lanes_preview"][  # type: ignore[index]
        "collapse_report"
    ]
    assert canceled_report["events"] == []  # type: ignore[index]

    eligible_root = tmp_path / "eligible"
    eligible = _invoke(eligible_root, _build_mission(eligible_root, documents))
    assert eligible.exit_code == 0, eligible.stdout
    eligible_report = _payload(eligible.stdout)["validation"]["lanes_preview"][  # type: ignore[index]
        "collapse_report"
    ]
    assert eligible_report["events"]  # type: ignore[index]
    assert eligible_report["by_rule"]["write_scope_overlap"] == 1  # type: ignore[index]
