"""CLI contract tests for cyclic execution-lane rejection during finalization."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from tests.specify_cli.cli.commands.agent.test_feature_finalize_bootstrap import (
    MODULE,
    _common_patches,
    _make_bootstrap_result,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.git_repo,
    pytest.mark.non_sandbox,
    pytest.mark.regression,
]

_MISSION_SLUG = "099-cyclic-finalize"
_EXPECTED_PATH = ["lane-a", "lane-b", "lane-a"]
_EXPECTED_LANES = [
    {"lane_id": "lane-a", "wp_ids": ["WP01", "WP04"]},
    {"lane_id": "lane-b", "wp_ids": ["WP02", "WP03"]},
]


@pytest.fixture(autouse=True)
def _disable_saas_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the command on its local finalization path for this contract suite."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _write_cyclic_mission(repo_root: Path, *, planning_lane: bool = False) -> Path:
    """Create an acyclic WP graph whose post-collapse lane graph is cyclic."""
    mission_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "a.py").write_bytes(b"# a\n")
    (repo_root / "src" / "b.py").write_bytes(b"# b\n")

    requirements = "\n".join(
        f"- FR-{index:03d}: Requirement {index}" for index in range(1, 5)
    )
    (mission_dir / "spec.md").write_text(
        f"---\ntitle: Cyclic finalize\n---\n\n## Requirements\n\n{requirements}\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "## WP01\n\nDepends on WP02.\n\n"
        "## WP02\n\nNo dependencies.\n\n"
        "## WP03\n\nDepends on WP04.\n\n"
        "## WP04\n\nNo dependencies.\n",
        encoding="utf-8",
    )
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_slug": _MISSION_SLUG, "target_branch": "main"}),
        encoding="utf-8",
    )

    definitions = (
        (
            "WP01",
            "src/a.py",
            ["WP02"],
            "planning_artifact" if planning_lane else "code_change",
        ),
        ("WP02", "src/b.py", [], "code_change"),
        ("WP03", "src/b.py", ["WP04"], "code_change"),
        (
            "WP04",
            "src/a.py",
            [],
            "planning_artifact" if planning_lane else "code_change",
        ),
    )
    for index, (wp_id, owned_file, dependencies, execution_mode) in enumerate(
        definitions, start=1
    ):
        dependency_yaml = (
            "dependencies:\n" + "".join(f"  - {dep}\n" for dep in dependencies)
            if dependencies
            else "dependencies: []\n"
        )
        authoritative_surface = (
            f"kitty-specs/{_MISSION_SLUG}/"
            if execution_mode == "planning_artifact"
            else "src/"
        )
        owned = (
            f"kitty-specs/{_MISSION_SLUG}/tasks/WP04-test.md"
            if execution_mode == "planning_artifact"
            else owned_file
        )
        (tasks_dir / f"{wp_id}-test.md").write_text(
            "---\n"
            f'work_package_id: "{wp_id}"\n'
            f'title: "Test {wp_id}"\n'
            f"requirement_refs:\n  - FR-{index:03d}\n"
            f'execution_mode: "{execution_mode}"\n'
            f"owned_files:\n  - {owned}\n"
            f'authoritative_surface: "{authoritative_surface}"\n'
            f"{dependency_yaml}"
            "---\n\n"
            f"# {wp_id}\n",
            encoding="utf-8",
        )
    return mission_dir


def _inventory(root: Path) -> dict[str, tuple[str, bytes]]:
    """Return a recursive path/type/raw-byte inventory without using mtimes."""
    inventory: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        inventory[relative] = (
            "dir" if path.is_dir() else "file",
            b"" if path.is_dir() else path.read_bytes(),
        )
    return inventory


def _run_finalize(
    repo_root: Path,
    *,
    validate_only: bool,
    json_output: bool,
) -> tuple[int, str]:
    """Run the canonical mission finalize callable with unrelated seams isolated."""
    patches = _common_patches(repo_root, _MISSION_SLUG)
    patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(
        return_value=_make_bootstrap_result(total=4, seeded=4)
    )
    started = [patch(target, value) for target, value in patches.items()]
    for active_patch in started:
        active_patch.start()
    try:
        from specify_cli.cli.commands.agent.mission import finalize_tasks

        try:
            finalize_tasks(
                feature=_MISSION_SLUG,
                json_output=json_output,
                validate_only=validate_only,
            )
        except typer.Exit as error:
            return int(error.exit_code), ""
    finally:
        for active_patch in started:
            active_patch.stop()
    return 0, ""


@pytest.mark.parametrize("validate_only", [False, True])
def test_cycle_json_contract_and_manifest_absence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    validate_only: bool,
) -> None:
    """Both modes expose one structured terminal envelope and write no manifest."""
    mission_dir = _write_cyclic_mission(tmp_path)

    exit_code, _ = _run_finalize(
        tmp_path, validate_only=validate_only, json_output=True
    )
    output = capsys.readouterr()
    payloads = [json.loads(line) for line in output.out.splitlines() if line.strip()]

    assert exit_code != 0
    assert output.err == ""
    assert len(payloads) == 1
    expected_path = _EXPECTED_PATH
    expected_lanes = _EXPECTED_LANES
    if validate_only:
        assert payloads[0]["error_code"] == "LANE_DEPENDENCY_CYCLE"
    assert payloads[0]["error"] == (
        "Execution-lane dependency cycle detected: lane-a -> lane-b -> lane-a"
    )
    assert payloads[0]["cycle_path"] == expected_path
    assert payloads[0]["cycle_lanes"] == expected_lanes
    assert not (mission_dir / "lanes.json").exists()


def test_mutating_cycle_preserves_existing_manifest_bytes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cycle rejection cannot replace a previously valid lane manifest."""
    mission_dir = _write_cyclic_mission(tmp_path)
    lanes_path = mission_dir / "lanes.json"
    original = b'{"sentinel":"preserve byte-for-byte"}\n'
    lanes_path.write_bytes(original)

    exit_code, _ = _run_finalize(tmp_path, validate_only=False, json_output=True)
    capsys.readouterr()

    assert exit_code != 0
    assert lanes_path.read_bytes() == original


def test_validate_only_cycle_preserves_complete_mission_inventory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Validate-only rejection leaves every path, type, and file byte unchanged."""
    mission_dir = _write_cyclic_mission(tmp_path)
    before = _inventory(mission_dir)

    exit_code, _ = _run_finalize(tmp_path, validate_only=True, json_output=True)
    output = capsys.readouterr().out
    after = _inventory(mission_dir)

    assert exit_code != 0
    assert before == after
    assert "validation_passed" not in output
    assert '"count"' not in output
    for artifact in (
        "status.events.jsonl",
        "status.json",
        "acceptance-matrix.json",
        "lanes.json",
    ):
        assert not (mission_dir / artifact).exists()


@pytest.mark.parametrize("validate_only", [False, True])
def test_human_cycle_diagnostic_contains_complete_actionable_facts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    validate_only: bool,
) -> None:
    """Human output names the closed path and every lane membership fact."""
    _write_cyclic_mission(tmp_path)

    exit_code, _ = _run_finalize(
        tmp_path, validate_only=validate_only, json_output=False
    )
    output = capsys.readouterr().out

    assert exit_code != 0
    assert "Traceback" not in output
    assert "lane-a -> lane-b -> lane-a" in output
    assert "lane-a: WP01, WP04" in output
    assert "lane-b: WP02, WP03" in output


def test_planning_lane_cycle_is_rendered_with_sorted_membership(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A final cycle that crosses lane-planning uses the same typed envelope."""
    _write_cyclic_mission(tmp_path, planning_lane=True)

    exit_code, _ = _run_finalize(tmp_path, validate_only=True, json_output=True)
    output = capsys.readouterr().out

    assert exit_code != 0
    payload = json.loads(output.strip())
    assert payload["error_code"] == "LANE_DEPENDENCY_CYCLE"
    assert "lane-planning" in payload["cycle_path"]
    planning = next(
        lane for lane in payload["cycle_lanes"] if lane["lane_id"] == "lane-planning"
    )
    assert planning["wp_ids"] == sorted(planning["wp_ids"])


def test_generic_finalize_error_payload_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The specialized renderer preserves the legacy generic JSON contract."""
    from specify_cli.cli.commands.agent import mission_finalize

    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(mission_finalize, "_emit_json", emitted.append)

    mission_finalize._emit_finalize_error_with_revert_note(
        ValueError("ordinary failure"), None, json_output=True
    )

    assert emitted == [{"error": "ordinary failure"}]
