"""Regression tests for the confined planning_artifact kitty-specs exemption.

Mission ``planning-artifact-kitty-specs-ownership-01M0AEV7`` (#3222 / #2643):
``finalize-tasks`` must ACCEPT a ``planning_artifact`` work package whose
``owned_files`` are all confined to planning surfaces (``kitty-specs/``/``docs/``)
while staying fail-closed (``INVALID_WP_OWNED_FILES_KITTY_SPECS``) for
``code_change`` and for any planning WP that also owns a non-planning path.

The tests here pin the decision table in ``data-model.md`` and the contract in
``contracts/finalize-ownership-contract.md``. Each behavior-changing row has a
dedicated test; the seam-bound regression guards (surface inference, durability,
predicate identity) live in ``test_mission_parsing.py`` /
``test_mission_finalize_phases.py`` and this file's seam sections.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mission_runtime.artifacts import MissionArtifactKind, kind_for_mission_file
from specify_cli.cli.commands.agent import mission_parsing as seam
from specify_cli.cli.commands.agent.mission import (
    INVALID_WP_OWNED_FILES_KITTY_SPECS,
    app,
)
from specify_cli.lanes.auto_rebase import _AUTO_REBASE_MANAGED_LAYOUT_KINDS
from specify_cli.lanes.compute import compute_lanes
from specify_cli.ownership.inference import infer_authoritative_surface, infer_ownership
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import (
    validate_authoritative_surface,
    validate_execution_mode_consistency,
    validate_no_overlap,
)
from specify_cli.status import WPMetadata

pytestmark = pytest.mark.fast

runner = CliRunner()

MISSION_SLUG = "3222-planning-owns-kitty-specs"


def _write_common(feature_dir: Path) -> Path:
    """Write the mission-level artifacts shared by every fixture in this module."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (feature_dir / "spec.md").write_text(
        "# Spec\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Test requirement | Covered by WP01. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01\n**Requirement Refs**: FR-001\n",
        encoding="utf-8",
    )
    return tasks_dir


def _build_planning_wp(
    tmp_path: Path,
    *,
    owned_files: list[str],
    execution_mode: str | None = "planning_artifact",
    authoritative_surface: str = "src/example/",
    create_intent: list[str] | None = None,
    body: str = "# WP01\n",
) -> Path:
    """Author a single-WP mission whose WP01 is a planning-artifact fixture.

    Mirrors ``_build_feature`` in ``test_finalize_tasks_owned_files_validation``
    but shapes WP01 as a ``planning_artifact`` and lets the caller override the
    ``authoritative_surface`` (the default ``src/example/`` hard-fails the surface
    check against a kitty-specs owned file — the D-1 trap).
    """
    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    tasks_dir = _write_common(feature_dir)

    lines = [
        "---",
        "work_package_id: WP01",
        "title: Planning checkpoint",
        "dependencies: []",
        "requirement_refs: [FR-001]",
    ]
    if execution_mode is not None:
        lines.append(f"execution_mode: {execution_mode}")
    lines.append("owned_files:")
    lines.extend(f"  - {of}" for of in owned_files)
    lines.append(f"authoritative_surface: {authoritative_surface}")
    if create_intent:
        lines.append("create_intent:")
        lines.extend(f"  - {ci}" for ci in create_intent)
    lines.append("---")
    frontmatter = "\n".join(lines) + "\n"
    (tasks_dir / "WP01-planning.md").write_text(frontmatter + body, encoding="utf-8")
    return feature_dir


def _run_command(cmd: list[str], **_kwargs: object) -> tuple[int, str, str]:
    if "status" in cmd and "--porcelain" in cmd:
        return (0, "M tasks.md", "")
    if "rev-parse" in cmd and "HEAD" in cmd:
        return (0, "c" * 40, "")
    return (0, "", "")


def _invoke_finalize(
    tmp_path: Path, feature_dir: Path, extra_args: list[str] | None = None
):
    args = ["finalize-tasks", "--mission", feature_dir.name, "--json"]
    if extra_args:
        args.extend(extra_args)
    commit_patcher = patch(
        "specify_cli.coordination.commit_router.commit_for_mission",
        return_value=True,
    )
    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.mission._find_feature_directory", return_value=feature_dir),
        patch("specify_cli.cli.commands.agent.mission._show_branch_context", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.mission.run_command", side_effect=_run_command),
        commit_patcher as commit_for_mission,
    ):
        return runner.invoke(app, args), commit_for_mission


def _json_payload(stdout: str) -> dict[str, object]:
    lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    assert lines, stdout
    return json.loads(lines[-1])


def _owned_files_from_wp(feature_dir: Path) -> list[str]:
    """Read WP01's finalized ``owned_files`` from the on-disk frontmatter."""
    raw = (feature_dir / "tasks" / "WP01-planning.md").read_text(encoding="utf-8")
    frontmatter = raw.split("---", 2)[1]
    owned: list[str] = []
    collecting = False
    for line in frontmatter.splitlines():
        if line.startswith("owned_files:"):
            collecting = True
            continue
        if collecting:
            stripped = line.strip()
            if stripped.startswith("- "):
                owned.append(stripped[2:].strip())
            else:
                break
    return owned


# ---------------------------------------------------------------------------
# T001 — Red-first positive acceptance (decision-table row 1, FR-001/FR-002)
# ---------------------------------------------------------------------------


def test_planning_artifact_owning_kitty_specs_finalizes_and_lands_in_planning_lane(
    tmp_path: Path,
) -> None:
    """A confined ``planning_artifact`` WP owning only ``kitty-specs/`` finalizes
    cleanly (clearing the two downstream hard-gates) and routes to the planning
    lane — not merely "the ban did not fire" (findings D-1, D-5, renata-HIGH)."""
    owned = [f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md"]
    feature_dir = _build_planning_wp(
        tmp_path,
        owned_files=owned,
        authoritative_surface=f"kitty-specs/{MISSION_SLUG}/",
        create_intent=owned,
    )

    # (1) anti-vacuity: the ban's trigger condition is mechanically present in
    # what finalize reasoned over — a kitty-specs owned_files entry.
    finalized_owned = _owned_files_from_wp(feature_dir)
    assert any(f.startswith("kitty-specs/") for f in finalized_owned), finalized_owned

    # (2) finalize (--validate-only) clears the ban AND the two hard-gates it shadowed.
    result, commit_for_mission = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])
    assert result.exit_code == 0, result.stdout
    commit_for_mission.assert_not_called()

    # (3) placement is positive: WP01 lands in the planning lane.
    manifests = {
        "WP01": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=tuple(owned),
            authoritative_surface=f"kitty-specs/{MISSION_SLUG}/",
        )
    }
    lanes = compute_lanes({"WP01": []}, manifests, MISSION_SLUG)
    assert "WP01" in lanes.planning_artifact_wps


def _planning_meta(owned_files: list[str], *, mode: str | None = "planning_artifact") -> WPMetadata:
    return WPMetadata(
        work_package_id="WP01",
        title="t",
        execution_mode=mode,
        owned_files=owned_files,
    )


# ---------------------------------------------------------------------------
# T003 — Confinement + fail-closed floor (FR-003, FR-004, FR-005, FR-006, SC-004)
# ---------------------------------------------------------------------------


def test_confinement_code_prefix_still_rejected() -> None:
    """planning_artifact owning kitty-specs + src/ is NOT exempted (FR-004, INV-4)."""
    meta = _planning_meta(
        [f"kitty-specs/{MISSION_SLUG}/x.md", "src/foo.py"],
    )
    invalid = seam._invalid_mission_specs_owned_files({"WP01": meta})
    assert invalid == [{"wp_id": "WP01", "path": f"kitty-specs/{MISSION_SLUG}/x.md"}]


def test_confinement_non_code_non_planning_prefix_still_rejected() -> None:
    """planning_artifact owning kitty-specs + scripts/ is still rejected.

    Proves confinement excludes ANY non-``_PLANNING_PREFIXES`` path, not only
    ``src/``/``tests/`` (decision-table row 4)."""
    meta = _planning_meta(
        [f"kitty-specs/{MISSION_SLUG}/x.md", "scripts/verify.py"],
    )
    invalid = seam._invalid_mission_specs_owned_files({"WP01": meta})
    assert invalid == [{"wp_id": "WP01", "path": f"kitty-specs/{MISSION_SLUG}/x.md"}]


def test_confinement_normalizes_dot_slash_planning_entry_is_exempt() -> None:
    """A ``./kitty-specs/...`` entry is normalized before the prefix check, so a
    confined planning WP spelled with ``./`` is still exempted (pedro Q5).

    This fixture fails if the confinement guard uses a raw ``startswith`` — the
    ban predicate matches the normalized path, so confinement must too."""
    meta = _planning_meta([f"./kitty-specs/{MISSION_SLUG}/x.md"])
    assert seam._is_confined_planning_wp(meta) is True
    assert seam._invalid_mission_specs_owned_files({"WP01": meta}) == []


def test_paired_mode_discrimination_planning_accept_code_reject(tmp_path: Path) -> None:
    """SC-004 / FR-006: one shared fixture flipped by ``execution_mode`` — the
    ``planning_artifact`` case finalizes (exit 0) while the ``code_change`` case
    is rejected with ``INVALID_WP_OWNED_FILES_KITTY_SPECS``. The near-identical
    pair is what proves mode-discrimination end-to-end."""
    owned = [f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md"]
    surface = f"kitty-specs/{MISSION_SLUG}/"

    # ACCEPT arm — planning_artifact.
    accept_dir = _build_planning_wp(
        tmp_path / "accept",
        owned_files=owned,
        execution_mode="planning_artifact",
        authoritative_surface=surface,
        create_intent=owned,
    )
    accept_result, _ = _invoke_finalize(tmp_path / "accept", accept_dir, ["--validate-only"])
    assert accept_result.exit_code == 0, accept_result.stdout

    # REJECT arm — same declaration, flipped to code_change.
    reject_dir = _build_planning_wp(
        tmp_path / "reject",
        owned_files=owned,
        execution_mode="code_change",
        authoritative_surface=surface,
        create_intent=owned,
    )
    reject_result, reject_commit = _invoke_finalize(tmp_path / "reject", reject_dir, ["--validate-only"])
    assert reject_result.exit_code == 1
    reject_commit.assert_not_called()
    payload = _json_payload(reject_result.stdout)
    assert payload["error_code"] == INVALID_WP_OWNED_FILES_KITTY_SPECS
    assert payload["invalid_owned_files"] == [{"wp_id": "WP01", "path": owned[0]}]


def test_fr005_out_of_planning_paths_warning_preserved() -> None:
    """FR-005: a planning_artifact WP owning a ``scripts/`` path still yields the
    soft "owns files outside planning paths" warning (not a hard error) from
    ``validate_execution_mode_consistency`` — untouched by the exemption.

    Asserted as a direct unit test of that validator: it runs at finalize after
    the ban, so end-to-end it is only reachable for a WP owning no kitty-specs
    path — the unit test is the crisp home."""
    manifest = OwnershipManifest(
        execution_mode=ExecutionMode.PLANNING_ARTIFACT,
        owned_files=("scripts/verify.py",),
        authoritative_surface="scripts/",
    )
    warnings = validate_execution_mode_consistency(manifest)
    assert warnings, warnings
    assert any("outside planning paths" in w for w in warnings)


# ---------------------------------------------------------------------------
# T004 — Inference → ban ordering (findings A-2 / D-3)
# ---------------------------------------------------------------------------


def test_inference_accept_unset_mode_planning_body_is_exempt() -> None:
    """A WP with unset execution_mode whose body carries only planning signals
    infers ``planning_artifact`` and its kitty-specs ownership is exempt (A-2)."""
    raw = (
        "---\nwork_package_id: WP01\ntitle: Decision checkpoint\n---\n"
        f"# WP01\nProduce the disposition matrix under kitty-specs/{MISSION_SLUG}/"
        "disposition-matrix.md. A planning decision checkpoint; see docs/ for context.\n"
    )
    manifest, _warnings = infer_ownership(raw, MISSION_SLUG)
    assert str(manifest.execution_mode) == ExecutionMode.PLANNING_ARTIFACT.value

    # The exemption applies to the resolved-planning WP owning kitty-specs.
    exempt_meta = _planning_meta([f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md"])
    assert seam._invalid_mission_specs_owned_files({"WP01": exempt_meta}) == []


def test_inference_reject_unset_mode_code_signal_stays_fail_closed(tmp_path: Path) -> None:
    """A WP with unset execution_mode whose body carries a code signal infers
    ``code_change`` and its kitty-specs ownership is rejected fail-closed (D-3).

    The resolved ``code_change`` mode is asserted BEFORE the rejection, so a naive
    kitty-specs-owning WP that would infer planning cannot pass as a false negative."""
    body = (
        "# WP01\nImplement the change in src/specify_cli/foo.py and cover it in "
        "tests/test_foo.py.\n"
    )
    owned = [f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md"]

    # (a) resolved mode is code_change (read-back via the inference seam).
    raw = (
        "---\nwork_package_id: WP01\ntitle: Mislabeled\ndependencies: []\n"
        "requirement_refs: [FR-001]\nowned_files:\n"
        f"  - {owned[0]}\nauthoritative_surface: kitty-specs/{MISSION_SLUG}/\n---\n" + body
    )
    manifest, _warnings = infer_ownership(raw, MISSION_SLUG)
    assert str(manifest.execution_mode) == ExecutionMode.CODE_CHANGE.value

    # (b) end-to-end: finalize rejects the inferred-code_change WP fail-closed.
    feature_dir = _build_planning_wp(
        tmp_path,
        owned_files=owned,
        execution_mode=None,  # unset → inferred
        authoritative_surface=f"kitty-specs/{MISSION_SLUG}/",
        create_intent=owned,
        body=body,
    )
    result, commit_for_mission = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])
    assert result.exit_code == 1
    commit_for_mission.assert_not_called()
    payload = _json_payload(result.stdout)
    assert payload["error_code"] == INVALID_WP_OWNED_FILES_KITTY_SPECS


# ---------------------------------------------------------------------------
# T005 — Negative-overlap floor (finding A-1)
# ---------------------------------------------------------------------------


def test_overlapping_planning_wps_still_rejected_by_no_overlap() -> None:
    """Two planning_artifact WPs owning overlapping kitty-specs scopes with no
    dependency edge are still rejected by ``validate_no_overlap`` — the exemption
    is not a blanket kitty-specs bless (A-1)."""
    shared = f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md"
    manifests = {
        "WP01": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=(shared,),
            authoritative_surface=f"kitty-specs/{MISSION_SLUG}/",
        ),
        "WP02": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=(shared,),
            authoritative_surface=f"kitty-specs/{MISSION_SLUG}/",
        ),
    }
    errors = validate_no_overlap(manifests, dependencies={"WP01": [], "WP02": []})
    assert errors, errors
    assert any("Overlap" in e for e in errors)


# ---------------------------------------------------------------------------
# T007 — Seam-bound regression guards (findings D-2 / D-4 / C-003)
# ---------------------------------------------------------------------------


def test_authoritative_surface_inference_covers_kitty_specs_owned_file() -> None:
    """A kitty-specs owned file yields a compatible authoritative_surface — no
    surface hard-error for the accepted case (D-4)."""
    owned = [f"kitty-specs/{MISSION_SLUG}/**"]
    surface = infer_authoritative_surface(owned)
    assert surface == f"kitty-specs/{MISSION_SLUG}/"
    manifest = OwnershipManifest(
        execution_mode=ExecutionMode.PLANNING_ARTIFACT,
        owned_files=tuple(owned),
        authoritative_surface=surface,
    )
    assert validate_authoritative_surface(manifest) == []


def test_deliverable_durability_is_filename_scoped() -> None:
    """C-003 durability is filename-scoped (D-2): a non-managed filename survives
    auto_rebase (``kind is None``); ``analysis-report.md`` and ``tasks/WP*.md`` are
    managed kinds and are therefore reconciled ("take theirs").

    Asserts against the real authorities — ``kind_for_mission_file`` and the
    ``_AUTO_REBASE_MANAGED_LAYOUT_KINDS`` frozenset — not a re-derived set."""
    # The managed frozenset is exactly the reconciled kinds.
    expected_managed = frozenset(
        {
            MissionArtifactKind.LANE_STATE,
            MissionArtifactKind.WORK_PACKAGE_TASK,
            MissionArtifactKind.ANALYSIS_REPORT,
        }
    )
    assert expected_managed == _AUTO_REBASE_MANAGED_LAYOUT_KINDS

    # Durable: a non-managed planning deliverable.
    assert kind_for_mission_file(f"kitty-specs/{MISSION_SLUG}/disposition-matrix.md") is None

    # Negative carve-out: managed kinds are clobbered by take-theirs.
    analysis_kind = kind_for_mission_file(f"kitty-specs/{MISSION_SLUG}/analysis-report.md")
    assert analysis_kind == MissionArtifactKind.ANALYSIS_REPORT
    assert analysis_kind in _AUTO_REBASE_MANAGED_LAYOUT_KINDS

    wp_task_kind = kind_for_mission_file(f"kitty-specs/{MISSION_SLUG}/tasks/WP01-x.md")
    assert wp_task_kind == MissionArtifactKind.WORK_PACKAGE_TASK
    assert wp_task_kind in _AUTO_REBASE_MANAGED_LAYOUT_KINDS
