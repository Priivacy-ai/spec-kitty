"""Regression tests for spec-kitty#4135 — empty frontmatter ``dependencies: []``
must not masquerade as a TIER-2 declaration in finalize-tasks.

``agent tasks map-requirements`` rewrites WP frontmatter for its own purposes
via ``WPMetadata.model_dump(exclude_none=True)`` — and ``WPMetadata.dependencies``
defaults to ``[]`` (never ``None``), so every WP that command touches gains a
literal ``dependencies: []`` line the operator never wrote. The 3-tier resolver
in ``mission_finalize._resolve_dependencies_and_refs`` used to treat "the
``dependencies`` field exists at all" as an authoritative TIER-2 declaration,
so after any map-requirements run the tasks.md-declared chain was silently
discarded: lanes.json computed every WP as independent/parallel
(``depends_on_lanes: []``, ``parallel_group: 0``) with no warning.

Contract (mirrors the field report in #4135): GIVEN a mission whose tasks.md
declares a linear WP chain and whose WP frontmatter carries the incidental
``dependencies: []`` serialization artifact, WHEN ``finalize-tasks`` runs, THEN
the resolver falls through to the tasks.md chain (TIER-3) instead of treating
the empty list as authoritative. A *non-empty* frontmatter ``dependencies``
list remains authoritative TIER-2 input.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import mission_finalize as seam
from specify_cli.cli.commands.agent.mission import app
from specify_cli.coordination.commit_router import CommitRouterResult

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

_FAKE_SHA = "b" * 40
_MISSION = "069-empty-frontmatter-deps"


# ---------------------------------------------------------------------------
# Unit tests — _resolve_dependencies_and_refs
# ---------------------------------------------------------------------------

_TASKS_MD_CHAIN = (
    "# Tasks\n"
    "\n"
    "## WP01 — Foundation\n"
    "\n"
    "- [ ] lay the groundwork\n"
    "\n"
    "## WP02 — Core\n"
    "\n"
    "Depends on WP01\n"
    "\n"
    "- [ ] build on it\n"
    "\n"
    "## WP03 — Polish\n"
    "\n"
    "Depends on WP02\n"
    "\n"
    "- [ ] finish it\n"
)

_EXPECTED_WP_IDS = ["WP01", "WP02", "WP03"]


def _write_wp(tasks_dir: Path, wp_id: str, dependencies_yaml: str | None, *, title: str = "T") -> Path:
    """Write a WP file; ``dependencies_yaml`` None omits the field entirely."""
    lines = ["---", f"work_package_id: {wp_id}", f"title: {title}"]
    if dependencies_yaml is not None:
        lines.append(f"dependencies: {dependencies_yaml}")
    lines += ["---", f"# {wp_id}"]
    wp_file = tasks_dir / f"{wp_id}-{title.lower()}.md"
    wp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return wp_file


def _build_planning_dir(tmp_path: Path, *, wp_dependencies_yaml: str | None) -> tuple[Path, list[Path]]:
    planning_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = planning_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (planning_dir / "tasks.md").write_text(_TASKS_MD_CHAIN, encoding="utf-8")
    wp_files = [_write_wp(tasks_dir, wp_id, wp_dependencies_yaml) for wp_id in _EXPECTED_WP_IDS]
    return planning_dir, wp_files


def test_empty_frontmatter_dependencies_falls_through_to_tasks_md_chain(tmp_path: Path) -> None:
    """The #4135 reproduction at the resolver seam: ``dependencies: []`` (the
    map-requirements serialization artifact) is treated as absent, so the
    tasks.md-declared chain is resolved instead of silently discarded."""
    planning_dir, wp_files = _build_planning_dir(tmp_path, wp_dependencies_yaml="[]")

    res = seam._resolve_dependencies_and_refs(planning_dir, None, wp_files, _EXPECTED_WP_IDS, json_output=False)

    assert res.wp_dependencies == {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}


def test_nonempty_frontmatter_dependencies_remain_tier2_authoritative(tmp_path: Path) -> None:
    """A hand-written, non-empty frontmatter dependencies list still wins over
    the tasks.md text (TIER-2 authority is preserved — #4135 only reclassifies
    the *empty* list as a serialization artifact)."""
    planning_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = planning_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    # tasks.md says WP02 depends on WP01; frontmatter says WP03. The
    # non-empty frontmatter value must win for WP02, while WP03's empty
    # artifact falls through to the tasks.md chain.
    (planning_dir / "tasks.md").write_text(_TASKS_MD_CHAIN, encoding="utf-8")
    wp_files = [
        _write_wp(tasks_dir, "WP01", None),
        _write_wp(tasks_dir, "WP02", "[WP03]"),
        _write_wp(tasks_dir, "WP03", "[]"),
    ]

    res = seam._resolve_dependencies_and_refs(planning_dir, None, wp_files, _EXPECTED_WP_IDS, json_output=False)

    assert res.wp_dependencies == {"WP01": [], "WP02": ["WP03"], "WP03": ["WP02"]}


def test_absent_dependencies_field_falls_through_to_tasks_md_chain(tmp_path: Path) -> None:
    """Pre-#4135 behavior guard: a WP file with no ``dependencies`` field at
    all still resolves from tasks.md (TIER-3)."""
    planning_dir, wp_files = _build_planning_dir(tmp_path, wp_dependencies_yaml=None)

    res = seam._resolve_dependencies_and_refs(planning_dir, None, wp_files, _EXPECTED_WP_IDS, json_output=False)

    assert res.wp_dependencies == {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}


def test_empty_frontmatter_dependencies_with_no_tasks_md_deps_stays_empty(tmp_path: Path) -> None:
    """An explicitly dependency-free WP resolves to ``[]`` through either tier:
    the empty-artifact fallthrough changes nothing when tasks.md also declares
    no dependencies for the WP."""
    planning_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = planning_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (planning_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 — Foundation\n\n- [ ] standalone\n",
        encoding="utf-8",
    )
    wp_files = [_write_wp(tasks_dir, "WP01", "[]")]

    res = seam._resolve_dependencies_and_refs(planning_dir, None, wp_files, ["WP01"], json_output=False)

    assert res.wp_dependencies == {"WP01": []}


# ---------------------------------------------------------------------------
# End-to-end — finalize-tasks --validate-only over a map-requirements-poisoned mission
# ---------------------------------------------------------------------------


def _run_command(git_status_out: str = ""):  # noqa: ANN202
    def _side_effect(cmd, **kwargs):  # noqa: ANN001, ANN003
        if "status" in cmd and "--porcelain" in cmd:
            return (0, git_status_out, "")
        if "rev-parse" in cmd and "HEAD" in cmd:
            return (0, _FAKE_SHA, "")
        if "branch" in cmd or "checkout" in cmd or "current-branch" in cmd:
            return (0, "main", "")
        return (0, "", "")

    return _side_effect


def _build_poisoned_feature(tmp_path: Path) -> Path:
    """Mission dir with tasks.md (linear chain), spec.md, and WP files whose
    frontmatter carries exactly what map-requirements leaves behind:
    ``requirement_refs`` populated and an incidental ``dependencies: []``."""
    feature_dir = tmp_path / "kitty-specs" / _MISSION
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (feature_dir / "spec.md").write_text(
        "# Spec\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | First | Covered by WP01. | proposed |\n"
        "| FR-002 | Second | Covered by WP02. | proposed |\n"
        "| FR-003 | Third | Covered by WP03. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(_TASKS_MD_CHAIN, encoding="utf-8")
    for wp_id, req, module in (("WP01", "FR-001", "a"), ("WP02", "FR-002", "b"), ("WP03", "FR-003", "c")):
        (tasks_dir / f"{wp_id}-wp.md").write_text(
            "---\n"
            f"work_package_id: {wp_id}\n"
            f"title: WP {wp_id}\n"
            "dependencies: []\n"
            f"requirement_refs: [{req}]\n"
            "owned_files:\n"
            f"  - src/module_{module}/**\n"
            f"authoritative_surface: src/module_{module}/\n"
            "execution_mode: code_change\n"
            "---\n"
            f"# {wp_id}\n",
            encoding="utf-8",
        )
    return feature_dir


def _invoke_validate_only(tmp_path: Path, feature_dir: Path) -> object:
    args = ["finalize-tasks", "--mission", _MISSION, "--json", "--validate-only"]
    with (
        patch(
            "specify_cli.cli.commands.agent.mission.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission._find_feature_directory",
            return_value=feature_dir,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission._show_branch_context",
            return_value=(None, "main"),
        ),
        patch(
            "specify_cli.coordination.commit_router.commit_for_mission",
            return_value=CommitRouterResult(status="committed", placement_ref="main", commit_hash=_FAKE_SHA),
        ),
        patch(
            "specify_cli.cli.commands.agent.mission.run_command",
            side_effect=_run_command(),
        ),
    ):
        return runner.invoke(app, args)


def _payload(result: object) -> dict[str, object]:
    for line in result.output.splitlines():  # type: ignore[attr-defined]
        stripped = line.strip()
        if stripped.startswith("{"):
            return json.loads(stripped)  # type: ignore[no-any-return]
    raise AssertionError(f"no JSON payload in output: {result.output}")  # type: ignore[attr-defined]


def test_validate_only_resolves_chain_despite_poisoned_frontmatter(tmp_path: Path) -> None:
    """End-to-end #4135 reproduction: after map-requirements pre-poisons every
    WP with ``dependencies: []``, finalize-tasks still resolves the tasks.md
    chain — observable as pending dependency writes in the validate-only
    report (with the bug, the resolved deps equalled the empty frontmatter and
    no dependency write was ever queued)."""
    feature_dir = _build_poisoned_feature(tmp_path)

    result = _invoke_validate_only(tmp_path, feature_dir)

    assert result.exit_code == 0, result.output
    payload = _payload(result)
    assert payload["result"] == "validation_passed", payload
    would_modify = {entry["wp_id"]: entry["changes"] for entry in payload["would_modify"]}
    assert would_modify.get("WP02", {}).get("dependencies") == ["WP01"], would_modify
    assert would_modify.get("WP03", {}).get("dependencies") == ["WP02"], would_modify
