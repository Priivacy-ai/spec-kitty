"""setup-plan command family for ``agent mission`` (#2056 WP06).

Hosts the ``setup-plan`` command, decomposed from its pre-decomposition 507-LOC
monolith into ≤15-CC phase helpers (SaaS/auth preflight → git preflight →
feature-dir resolution → spec gate → plan scaffold → lifecycle emit → plan
commit → documentation wiring → result emit), plus the planning-commit helpers
it owns: ``_commit_to_branch`` + ``CommitToBranchResult``, ``_kind_for_artifact``
(and its ``_ARTIFACT_TYPE_TO_KIND`` table), ``_artifact_has_no_git_changes``,
``_artifact_absent_at_placement``, ``_print_artifact_unchanged``,
``_warn_commit_failed``. The heavyweight ``commit_for_mission`` import stays
function-local (A-3 / NFR-005).

The command is defined here as a plain callable; ``mission`` registers it on its
Typer ``app`` and re-exports ``setup_plan`` / ``_commit_to_branch`` /
``CommitToBranchResult`` / ``_kind_for_artifact`` (imported by tests and by
``lifecycle.py``). The relocated body resolves test-patched cross-cutting symbols
(``locate_project_root`` / ``_enforce_git_preflight`` / ``_find_feature_directory``
/ ``_show_branch_context`` / ``get_current_branch`` / ``resolve_template`` /
``_commit_to_branch``) through the ``mission`` module at call time so the
historical ``mission.<name>`` patch seams keep working without an import cycle.

One-way leaf (INV-8): imports lower layers + sibling Seam B/C/D leaves only at
module scope; the ``mission`` lookup inside the command is a deferred call-time
import. Behavior is preserved byte-for-byte from the pre-decomposition
``mission.py``; the WP01 golden harness is the regression net.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Annotated, Literal, cast

from rich.console import Console
import typer

from mission_runtime import MissionArtifactKind
from specify_cli.core.constants import MISSION_TYPE_DOCUMENTATION
from specify_cli.doc_analysis.doc_state import GeneratorConfig
from specify_cli.mission import get_mission_type

from specify_cli.cli.commands.agent.mission_branch_context import (
    _inject_branch_contract,
)
from specify_cli.cli.commands.agent.mission_feature_resolution import (
    _ARTIFACT_TYPE_TO_KIND as _ARTIFACT_TYPE_TO_KIND,
    _build_setup_plan_detection_error,
    _kind_for_artifact as _kind_for_artifact,
    _sole_mission_slug_or_none,
)

console = Console()


def _emit_json(payload: dict[str, object]) -> None:
    """Emit ``payload`` as JSON via the ``mission`` module's ``_emit_json``.

    Routing every setup-plan JSON emission through the ``mission`` module (rather
    than importing ``_emit_json`` directly) preserves the historical
    ``mission._emit_json`` patch seam exercised by callers that invoke
    ``mission.setup_plan`` directly (e.g. ``test_mission_planning_entry``).
    """
    from specify_cli.cli.commands.agent import mission as _mission

    _mission._emit_json(payload)
logger = logging.getLogger(__name__)

SETUP_PLAN_COMMAND_NAME = "spec-kitty agent mission setup-plan"
PROJECT_ROOT_NOT_FOUND = "Could not locate project root"
PROJECT_ROOT_NOT_FOUND_MESSAGE = f"{PROJECT_ROOT_NOT_FOUND}. Run from within spec-kitty repository."
TASKS_MD_FILENAME = "tasks.md"


# ---------------------------------------------------------------------------
# Planning-commit helpers (relocated from mission.py — WP06 / T023)
# ---------------------------------------------------------------------------


def _artifact_has_no_git_changes(repo_root: Path, file_path: Path) -> bool:
    candidate = file_path
    if candidate.is_absolute():
        with contextlib.suppress(ValueError):
            candidate = candidate.relative_to(repo_root)

    status = subprocess.run(
        ["git", "status", "--porcelain", "--", str(candidate)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return status.returncode == 0 and not status.stdout.strip()


def _artifact_absent_at_placement(
    worktree_root: Path, commit_paths: tuple[Path, ...], file_path: Path
) -> bool:
    """Return True iff the artifact is NOT present at the resolved placement.

    FR-006 / D-5: a commit that would run against a worktree where the artifact
    does not exist is a no-op-against-the-wrong-surface (vs. a genuine
    benign-unchanged where the artifact IS present and already committed). When
    ``_planning_commit_worktree`` produced committable paths, each must exist on
    disk; when it produced none, the original ``file_path`` is checked against
    the worktree. An empty changeset where the artifact IS present is a genuine
    no-op (returns False here), handled by the caller.
    """
    if commit_paths:
        return any(not path.exists() for path in commit_paths)
    # No committable paths: check the artifact at the worktree-relative location.
    return not _artifact_has_no_git_changes(worktree_root, file_path) and not file_path.exists()


def _print_artifact_unchanged(artifact_type: str, json_output: bool) -> None:
    if not json_output:
        console.print(f"[dim]{artifact_type.capitalize()} unchanged, no commit needed[/dim]")


def _warn_commit_failed(artifact_type: str, file_path: Path, exc: BaseException, json_output: bool) -> None:
    if not json_output:
        console.print(f"[yellow]Warning:[/yellow] Failed to commit {artifact_type}: {exc}")
        console.print(f"[yellow]You may need to commit manually:[/yellow] git add {file_path} && git commit")


@dataclass(frozen=True)
class CommitToBranchResult:
    """Typed outcome of :func:`_commit_to_branch` (FR-006 / D-5).

    Replaces the old ``-> None`` contract so the planning caller can surface the
    real commit hash on success and a typed diagnostic for a no-op against the
    wrong surface, instead of an opaque silent ``commit_created: None``.

    ``status`` is one of:

    * ``"committed"`` — ``safe_commit`` landed a real commit; ``commit_hash`` is
      the resolved SHA.
    * ``"unchanged"`` — genuine benign no-op: the artifact IS present at the
      resolved placement and already committed there (nothing to commit).
    * ``"no_op_wrong_surface"`` — the artifact is NOT present at the resolved
      placement (the commit would no-op against the wrong worktree/surface);
      ``diagnostic`` names the missing artifact + placement.
    """

    status: Literal["committed", "unchanged", "no_op_wrong_surface"]
    placement_ref: str
    commit_hash: str | None = None
    diagnostic: str | None = None


# write-surface-coherence WP02 (T007): the ``artifact_type`` → canonical
# :class:`~mission_runtime.MissionArtifactKind` map and its ``_kind_for_artifact``
# lookup were RELOCATED to ``mission_feature_resolution`` (the INV-8 one-way leaf)
# by #2113 / gate-read-surface-completion so the shared ``_planning_read_dir``
# chokepoint can name its kind without an import cycle. They are re-exported above
# (``_ARTIFACT_TYPE_TO_KIND`` / ``_kind_for_artifact``) to keep this module's public
# surface — consumed by ``_commit_to_branch`` below, ``lifecycle.py``, the
# ``mission`` shim, and the unit tests — unchanged.


def _commit_to_branch(
    file_path: Path,
    mission_slug: str,
    artifact_type: str,
    repo_root: Path,
    _target_branch: str,
    json_output: bool = False,
) -> CommitToBranchResult:
    """Commit a planning artifact to its single resolved placement.

    WP02 / T027 / IC-02 (#2056): now delegates to
    :func:`~specify_cli.coordination.commit_router.commit_for_mission`
    — the canonical single entry point for all planning-phase commits.
    This eliminates the final direct safe-commit call in this module and
    closes the C-001 "no duplicate" requirement.

    WP05 / FR-003 / C-GUARD-3a (#1784 catch-22 fix): the commit destination is
    the resolved placement :class:`CommitTarget` (``resolve_placement_only``
    → the SAME authority the full resolver computes), NOT ``git HEAD`` /
    ``current_branch``.

    WP03 / FR-006 / D-5: returns a typed :class:`CommitToBranchResult` so the
    caller surfaces the real commit hash on success and a typed diagnostic for a
    no-op-against-the-wrong-surface (artifact absent at the resolved placement).

    Args:
        file_path: Path to file being committed
        mission_slug: Feature slug (e.g., "001-my-feature")
        artifact_type: Type of artifact ("spec", "plan", "tasks")
        repo_root: Repository root path (ensures commits go to planning repo, not worktree)
        _target_branch: Branch the mission targets; passed to commit_for_mission
            for the post-commit ff-advance (WP09 / FR-010 / #1878).
        json_output: If True, suppress Rich console output

    Returns:
        CommitToBranchResult: the typed commit outcome (see the class docstring).
    """
    from specify_cli.core.git_ops import get_current_branch

    if get_current_branch(repo_root) is None:
        raise RuntimeError("Not in a git repository")

    from specify_cli.coordination.commit_router import commit_for_mission
    from specify_cli.git.protection_policy import ProtectionPolicy

    commit_msg = f"Add {artifact_type} for feature {mission_slug}"
    policy = ProtectionPolicy.resolve(repo_root)
    router_result = commit_for_mission(
        repo_root=repo_root,
        mission_slug=mission_slug,
        files=(file_path,),
        message=commit_msg,
        policy=policy,
        kind=_kind_for_artifact(artifact_type),
        target_branch=_target_branch,
    )

    if router_result.status == "committed":
        if not json_output:
            console.print(f"[green]✓[/green] {artifact_type.capitalize()} committed to {router_result.placement_ref}")
            if router_result.commit_hash:
                console.print(f"[dim]Commit: {router_result.commit_hash[:7]}[/dim]")
        return CommitToBranchResult(
            status="committed",
            placement_ref=router_result.placement_ref,
            commit_hash=router_result.commit_hash,
        )
    elif router_result.status == "unchanged":
        _print_artifact_unchanged(artifact_type, json_output)
        return CommitToBranchResult(status="unchanged", placement_ref=router_result.placement_ref)
    elif router_result.status == "no_op_wrong_surface":
        if not json_output:
            console.print(f"[yellow]Warning:[/yellow] {router_result.diagnostic}")
        return CommitToBranchResult(
            status="no_op_wrong_surface",
            placement_ref=router_result.placement_ref,
            diagnostic=router_result.diagnostic,
        )
    else:
        # "error" status — surface via warn helper and re-raise as RuntimeError
        # so callers that catch RuntimeError still get the failure.
        _warn_commit_failed(artifact_type, file_path, RuntimeError(router_result.diagnostic or "commit failed"), json_output)
        raise RuntimeError(router_result.diagnostic or f"commit_for_mission failed for {artifact_type}")


# ---------------------------------------------------------------------------
# setup-plan phase helpers (WP06 / T022)
# ---------------------------------------------------------------------------


def _enforce_saas_sync_boundary_preflight(repo_root: Path) -> None:
    """FR-002 / FR-009 read-only boundary preflight (WP04).

    Guarded by ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` and run AFTER project-root
    resolution and the FR-011 auth refusal (:func:`_enforce_saas_sync_auth_refusal`).
    Exits 2 on any structural incoherence (owner mismatch, orphan record, legacy
    rows in scope, missing hosted auth). No-op when SaaS sync is disabled.
    """
    if os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") != "1":
        return

    from specify_cli.sync.preflight import run_preflight

    _boundary_result = run_preflight(repo_root=repo_root, require_auth=True)
    if not _boundary_result.ok:
        console.print(f"[red]Refusing `{SETUP_PLAN_COMMAND_NAME}`.[/red]")
        _boundary_result.render(console)
        raise typer.Exit(code=2)


def _resolve_setup_plan_feature_dir(repo_root: Path, feature: str | None, *, json_output: bool) -> Path:
    """Resolve the feature directory for setup-plan; exit 1 with a detection payload on failure.

    FR-004 / #4: when no ``--mission`` was given and exactly one substantive
    mission is resolvable, auto-select it before the shared
    ``_find_feature_directory`` call (which otherwise hard-requires an explicit
    handle). Zero or >1 missions → structured detection error (no silent fallback).
    """
    from specify_cli.cli.commands.agent import mission as _mission

    cwd = Path.cwd().resolve()
    resolved_feature = feature
    if resolved_feature is None:
        resolved_feature = _sole_mission_slug_or_none(repo_root)
    try:
        from mission_runtime import ActionContextError

        return _mission._find_feature_directory(repo_root, cwd, explicit_feature=resolved_feature)
    except (ValueError, ActionContextError) as detection_error:
        payload = _build_setup_plan_detection_error(repo_root, str(detection_error), feature)
        if json_output:
            _emit_json(payload)
        else:
            console.print(f"[red]Error:[/red] {payload['error']}")
            for slug in cast(list[str], payload.get("available_missions", []))[:10]:
                console.print(f"  - {slug}")
            if "example_command" in payload:
                console.print(f"  {payload['example_command']}")
        raise typer.Exit(1) from None


def _emit_spec_missing(spec_file: Path, feature_dir: Path, mission_slug: str, *, json_output: bool) -> None:
    """Emit the SPEC_FILE_MISSING payload and exit 1."""
    payload: dict[str, object] = {
        "error_code": "SPEC_FILE_MISSING",
        "error": f"Required spec not found for mission '{mission_slug}': {spec_file.resolve()}",
        "mission_slug": mission_slug,
        "feature_dir": str(feature_dir.resolve()),
        "spec_file": str(spec_file.resolve()),
        "remediation": [
            f"Restore the missing spec file at {spec_file.resolve()}",
            f"Or select another mission explicitly: {SETUP_PLAN_COMMAND_NAME} --mission <mission-slug> --json",
        ],
    }
    if json_output:
        _emit_json(payload)
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        for step in cast(list[str], payload["remediation"]):
            console.print(f"  - {step}")
    raise typer.Exit(1)


def _enforce_spec_gate(
    spec_file: Path,
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
    *,
    target_branch: str,
    current_branch: str,
    json_output: bool,
) -> bool:
    """Issue #846 entry gate: spec must exist + be committed + substantive.

    Returns ``True`` when the gate blocks (the caller must return early); emits
    the blocked payload as a side effect. Returns ``False`` when the spec passes.
    Raises ``typer.Exit(1)`` when the spec file is entirely missing.
    """
    if not spec_file.exists():
        _emit_spec_missing(spec_file, feature_dir, mission_slug, json_output=json_output)

    # FR-011: single read-surface commit check. ``spec_file`` is the
    # READ-resolved surface — since gate-read-surface-completion WP02 it is
    # resolved via the kind-aware chokepoint ``_planning_read_dir`` (SPEC is a
    # PRIMARY-partition kind → the primary ``target_branch`` dir for ALL
    # topologies), so ``is_committed`` checks ``spec_file`` against ``HEAD`` of
    # the primary surface it physically lives on. The #1848 coord-deleted case
    # never reaches here: ``_find_feature_directory`` raises
    # ``CoordinationBranchDeleted`` (a ``StatusReadPathNotFound``) above,
    # caught as ``ActionContextError`` → ``Exit(1)``.
    from specify_cli.missions._substantive import is_committed, is_substantive

    _commit_diagnostics: list[str] = []
    spec_is_committed = is_committed(spec_file, repo_root, diagnostics=_commit_diagnostics)
    spec_is_substantive = is_substantive(spec_file, "spec")
    if spec_is_committed and spec_is_substantive:
        return False

    blocked_reason = (
        "spec.md must be committed AND substantive before setup-plan can run. "
        "Populate the Functional Requirements (at least one FR-### row with "
        "real description content), commit spec.md, then re-run setup-plan."
    )
    payload = {
        "result": "blocked",
        "phase_complete": False,
        "blocked_reason": blocked_reason,
        "error_code": "SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED",
        "mission_slug": mission_slug,
        "feature_dir": str(feature_dir.resolve()),
        "spec_file": str(spec_file.resolve()),
        "spec_committed": spec_is_committed,
        "spec_substantive": spec_is_substantive,
        "spec_commit_surfaces_checked": _commit_diagnostics,
    }
    if json_output:
        _emit_json(_inject_branch_contract(payload, target_branch=target_branch, current_branch=current_branch))
    else:
        console.print(f"[yellow]Blocked:[/yellow] {blocked_reason}")
    return True


def _scaffold_plan_template(plan_file: Path, repo_root: Path) -> None:
    """Copy the plan template into ``plan_file`` when it does not yet exist (C-007).

    Routes ``resolve_template`` through the ``mission`` module so the
    ``mission.resolve_template`` patch seam keeps working.
    """
    if plan_file.exists():
        return
    from specify_cli.cli.commands.agent import mission as _mission

    try:
        plan_template = _mission.resolve_template("plan-template.md", repo_root, mission="software-dev")
    except FileNotFoundError as exc:
        raise FileNotFoundError("Plan template not found in repository or package") from exc
    shutil.copy2(plan_template.path, plan_file)


def _emit_spec_plan_phase_events(feature_dir: Path, mission_slug: str, spec_file: Path, repo_root: Path) -> None:
    """Record SpecifyCompleted + PlanStarted lifecycle markers (issue #1067)."""
    from specify_cli.cli.commands.agent import mission as _mission

    try:
        from specify_cli.status import (
            emit_artifact_phase,
            SPECIFY_COMPLETED,
            PLAN_STARTED,
        )

        emit_artifact_phase(
            feature_dir,
            event_type=SPECIFY_COMPLETED,
            mission_slug=mission_slug,
            actor=SETUP_PLAN_COMMAND_NAME,
            artifact_path=_mission._branch_tree_relative_path(spec_file, repo_root),
        )
        emit_artifact_phase(
            feature_dir,
            event_type=PLAN_STARTED,
            mission_slug=mission_slug,
            actor=SETUP_PLAN_COMMAND_NAME,
        )
    except Exception as _phase_exc:  # noqa: BLE001
        logger.debug("Lifecycle phase emission skipped: %s", _phase_exc)


def _commit_plan_if_substantive(
    plan_file: Path,
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
    *,
    target_branch: str,
    json_output: bool,
) -> tuple[CommitToBranchResult | None, str | None]:
    """Commit plan.md when substantive; otherwise build the blocked reason.

    Returns ``(commit_result, blocked_reason)``. Routes ``_commit_to_branch``
    through the ``mission`` module so the ``mission._commit_to_branch`` patch
    seam keeps working.
    """
    from specify_cli.cli.commands.agent import mission as _mission
    from specify_cli.missions._substantive import is_substantive

    if is_substantive(plan_file, "plan"):
        commit_result = _mission._commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)
        try:
            from specify_cli.status import emit_artifact_phase, PLAN_COMPLETED

            emit_artifact_phase(
                feature_dir,
                event_type=PLAN_COMPLETED,
                mission_slug=mission_slug,
                actor=SETUP_PLAN_COMMAND_NAME,
                artifact_path=_mission._branch_tree_relative_path(plan_file, repo_root),
            )
        except Exception as _plan_exc:  # noqa: BLE001
            logger.debug("PlanCompleted emission skipped: %s", _plan_exc)
        return commit_result, None

    # FR-013 (#1896): name the offending Technical Context format.
    from specify_cli.missions._substantive import describe_technical_context_gap

    _plan_gap = describe_technical_context_gap(plan_file.read_text(encoding="utf-8"))
    blocked_reason = (
        "plan.md content is not substantive yet; populate Technical Context with real "
        "values (Language/Version plus at least one peer field, such as Primary "
        "Dependencies) — not template placeholders — and re-run setup-plan to commit."
    )
    if _plan_gap is not None:
        blocked_reason = f"{blocked_reason} Detail: {_plan_gap}"
    if not json_output:
        console.print(f"[yellow]Plan not committed:[/yellow] {blocked_reason}")
    return None, blocked_reason


def _run_documentation_gap_analysis(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
    meta_file: Path,
    *,
    target_branch: str,
    json_output: bool,
) -> str | None:
    """Run gap analysis for gap_filling/feature_specific doc missions; return its path or None."""
    from specify_cli.doc_analysis.doc_state import read_documentation_state, set_audit_metadata
    from specify_cli.doc_analysis.gap_analysis import generate_gap_analysis_report

    if not meta_file.exists():
        return None
    doc_state = read_documentation_state(meta_file)
    iteration_mode = doc_state.get("iteration_mode", "initial") if doc_state else "initial"
    if iteration_mode not in ("gap_filling", "feature_specific"):
        return None

    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        if not json_output:
            console.print("[yellow]Warning:[/yellow] No docs/ directory found, skipping gap analysis")
        return None

    gap_analysis_output = feature_dir / "gap-analysis.md"
    try:
        analysis = generate_gap_analysis_report(docs_dir, gap_analysis_output, project_root=repo_root)
        set_audit_metadata(
            meta_file,
            last_audit_date=analysis.analysis_date,
            coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
        )
        with contextlib.suppress(Exception):  # Non-fatal: agent can commit separately
            from specify_cli.coordination.commit_router import commit_for_mission
            from specify_cli.git.protection_policy import ProtectionPolicy

            _gap_policy = ProtectionPolicy.resolve(repo_root)
            commit_for_mission(
                repo_root=repo_root,
                mission_slug=mission_slug,
                files=(gap_analysis_output, meta_file),
                message=f"Add gap analysis for feature {mission_slug}",
                policy=_gap_policy,
                kind=MissionArtifactKind.PRIMARY_METADATA,
                target_branch=target_branch,
            )
        if not json_output:
            coverage_pct = analysis.coverage_matrix.get_coverage_percentage() * 100
            console.print(f"[cyan]→ Gap analysis generated: {gap_analysis_output.name} (coverage: {coverage_pct:.1f}%)[/cyan]")
        return str(gap_analysis_output)
    except Exception as gap_err:
        if not json_output:
            console.print(f"[yellow]Warning:[/yellow] Gap analysis failed: {gap_err}")
        return None


def _detect_and_configure_generators(
    mission_slug: str,
    repo_root: Path,
    meta_file: Path,
    *,
    target_branch: str,
    json_output: bool,
) -> list[GeneratorConfig]:
    """Detect documentation generators, persist config to meta.json, return detected list."""
    from specify_cli.doc_analysis.doc_state import set_generators_configured
    from specify_cli.doc_analysis.doc_generators import (
        DocGenerator,
        JSDocGenerator,
        SphinxGenerator,
        RustdocGenerator,
    )

    generators_detected: list[GeneratorConfig] = []
    all_generators: list[DocGenerator] = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
    for gen in all_generators:
        with contextlib.suppress(Exception):  # Skip generators that fail detection
            if gen.detect(repo_root):
                generator_name = cast(Literal["sphinx", "jsdoc", "rustdoc"], gen.name)
                generators_detected.append({"name": generator_name, "language": gen.languages[0], "config_path": ""})
                if not json_output:
                    console.print(f"[cyan]→ Detected {gen.name} generator (languages: {', '.join(gen.languages)})[/cyan]")

    if generators_detected and meta_file.exists():
        try:
            set_generators_configured(meta_file, generators_detected)
            with contextlib.suppress(Exception):  # Non-fatal
                from specify_cli.coordination.commit_router import commit_for_mission
                from specify_cli.git.protection_policy import ProtectionPolicy

                _gen_policy = ProtectionPolicy.resolve(repo_root)
                commit_for_mission(
                    repo_root=repo_root,
                    mission_slug=mission_slug,
                    files=(meta_file,),
                    message=f"Update generator config for feature {mission_slug}",
                    policy=_gen_policy,
                    kind=MissionArtifactKind.PRIMARY_METADATA,
                    target_branch=target_branch,
                )
        except Exception as gen_err:
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Failed to save generator config: {gen_err}")
    return generators_detected


def _run_documentation_wiring(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
    *,
    target_branch: str,
    json_output: bool,
) -> tuple[str | None, list[GeneratorConfig]]:
    """Documentation-mission plan wiring (T014 + T016): gap analysis + generator detection.

    No-op (returns ``(None, [])``) for non-documentation missions.
    """
    if get_mission_type(feature_dir) != MISSION_TYPE_DOCUMENTATION:
        return None, []
    meta_file = feature_dir / "meta.json"
    gap_analysis_path = _run_documentation_gap_analysis(
        feature_dir, mission_slug, repo_root, meta_file, target_branch=target_branch, json_output=json_output
    )
    generators_detected = _detect_and_configure_generators(
        mission_slug, repo_root, meta_file, target_branch=target_branch, json_output=json_output
    )
    return gap_analysis_path, generators_detected


def _trigger_dossier_sync(feature_dir: Path, mission_slug: str, repo_root: Path) -> None:
    """Fire-and-forget dossier sync."""
    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        trigger_feature_dossier_sync_if_enabled(feature_dir, mission_slug, repo_root)


def _emit_setup_plan_result(
    *,
    plan_file: Path,
    spec_file: Path,
    feature_dir: Path,
    mission_slug: str,
    plan_is_substantive: bool,
    plan_blocked_reason: str | None,
    plan_commit_result: CommitToBranchResult | None,
    gap_analysis_path: str | None,
    generators_detected: list[GeneratorConfig],
    target_branch: str,
    current_branch: str,
    json_output: bool,
) -> None:
    """Emit the setup-plan result in JSON or human form."""
    if not json_output:
        console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")
        return

    result: dict[str, object] = {
        "result": "success" if plan_is_substantive else "blocked",
        "phase_complete": plan_is_substantive,
        "mission_slug": mission_slug,
        "plan_file": str(plan_file),
        "feature_dir": str(feature_dir),
        "spec_file": str(spec_file),
        "plan_substantive": plan_is_substantive,
    }
    if plan_blocked_reason is not None:
        result["blocked_reason"] = plan_blocked_reason
    # FR-006 / D-5: surface the real commit hash and the typed no-op
    # classification instead of an opaque ``commit_created: None``.
    if isinstance(plan_commit_result, CommitToBranchResult):
        result["commit_created"] = plan_commit_result.status == "committed"
        result["commit_hash"] = plan_commit_result.commit_hash
        result["commit_status"] = plan_commit_result.status
        if plan_commit_result.diagnostic is not None:
            result["commit_diagnostic"] = plan_commit_result.diagnostic
    if gap_analysis_path:
        result["gap_analysis"] = gap_analysis_path
    if generators_detected:
        result["generators_detected"] = generators_detected
    _emit_json(_inject_branch_contract(result, target_branch=target_branch, current_branch=current_branch))


def setup_plan(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Scaffold implementation plan template in the project root checkout.

    This command is designed for AI agents to call programmatically.
    Creates plan.md and commits to target branch.

    Examples:
        spec-kitty agent mission setup-plan --json
        spec-kitty agent mission setup-plan --mission 020-my-feature --json

    ------------------------------------------------------------------
    WP04 / FR-011 + FR-012 audit (2026-05-17)
    ------------------------------------------------------------------
    This command's full call graph was audited to confirm every body
    upload / queue write goes through ``default_queue_db_path()`` and
    that no setup-plan path opens the legacy home-scoped queue database
    directly. The audit covered:

      * ``trigger_feature_dossier_sync_if_enabled()`` (this function
        constructs ``OfflineBodyUploadQueue()`` which delegates to
        ``default_queue_db_path()`` — FR-012 lock).
      * ``OfflineBodyUploadQueue.__init__`` (``sync.body_queue``) —
        falls back to ``default_queue_db_path()`` when ``db_path`` is
        ``None``.
      * ``emit_artifact_phase()`` / ``SPECIFY_COMPLETED`` /
        ``PLAN_STARTED`` / ``PLAN_COMPLETED`` — writes to local
        lifecycle JSONL only, no queue DB.
      * ``commit_for_mission()`` / underlying safe-commit — local git only, no queue DB.

    No direct ``_legacy_queue_db_path()`` call sites exist in the
    setup-plan call graph as of 2026-05-17. The FR-011 refuse-loudly
    guard (now in :func:`_enforce_saas_sync_auth_refusal`) is the
    load-bearing gate that ensures we never silently fall back to the
    legacy queue when SaaS sync is enabled but the foreground is
    unauthenticated.

    ------------------------------------------------------------------
    WP04 (mission ``mvp-cli-sync-boundary-completion-01KRX11M``)
    boundary preflight integration — 2026-05-18
    ------------------------------------------------------------------
    Immediately after the FR-011 hosted-auth refusal above (and only
    when ``SPEC_KITTY_ENABLE_SAAS_SYNC=1``, matching the existing FR-011
    gate), setup-plan invokes
    :func:`specify_cli.sync.preflight.run_preflight` with
    ``require_auth=True`` to enforce FR-002 / FR-009 (now in
    :func:`_enforce_saas_sync_boundary_preflight`). The boundary preflight
    refuses (``typer.Exit(2)``) on:

      * any of the six canonical daemon-owner / foreground mismatch
        fields (D-3 canon);
      * any orphan daemon owner record on disk;
      * any legacy queue rows belonging to the active scope; or
      * missing hosted auth when SaaS sync is required.

    The preflight is read-only — no DB writes, no SaaS round-trip — so
    placing it AFTER the FR-011 auth guard and BEFORE any
    ``emit_artifact_phase`` / ``trigger_feature_dossier_sync`` /
    ``emit_wp_created`` call ensures every SaaS-producing code path
    downstream of this function has passed the gate. The same gate is
    applied in ``sync now`` (WP03); the two surfaces share
    :func:`specify_cli.sync.preflight.build_boundary_failure_set` as
    their single source of truth.

    Cross-reference: WP04 of mission
    ``mvp-sync-boundary-cli-01KRVCQS``; regression tests in
    ``tests/runtime/test_setup_plan_sync_evidence.py``.
    ------------------------------------------------------------------
    """
    # Deferred import keeps this leaf free of an import cycle while honoring the
    # historical ``mission.<name>`` patch seams (``locate_project_root`` /
    # ``_enforce_git_preflight`` / ``_show_branch_context`` / ``get_current_branch`` /
    # ``_find_feature_directory`` / ``resolve_template`` / ``_commit_to_branch``).
    from specify_cli.cli.commands.agent import mission as _mission

    try:
        _enforce_saas_sync_auth_refusal(json_output=json_output)

        repo_root = _mission.locate_project_root()
        if repo_root is None:
            error_msg = PROJECT_ROOT_NOT_FOUND_MESSAGE
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        _enforce_saas_sync_boundary_preflight(repo_root)

        _mission._enforce_git_preflight(
            repo_root,
            json_output=json_output,
            command_name=SETUP_PLAN_COMMAND_NAME,
        )

        feature_dir = _resolve_setup_plan_feature_dir(repo_root, feature, json_output=json_output)
        mission_slug = feature_dir.name
        _, target_branch = _mission._show_branch_context(repo_root, mission_slug, json_output)
        current_branch = _mission.get_current_branch(repo_root) or target_branch

        # gate-read-surface-completion WP02 / FR-001 / #2107 (out-of-map edit —
        # WP01 owns ``mission.py``; rationale: re-point ``setup_plan``'s PLANNING
        # reads onto WP01's ``_planning_read_dir`` chokepoint). RESTORED after the
        # lane-d integration merge (32eb6df89) silently dropped the approved WP02
        # diff, reverting these joins to the coord-aware ``feature_dir`` — the
        # ratchet (FR-010) caught the regression. The driver bug: ``feature_dir``
        # comes from the coord-aware ``_find_feature_directory`` (→
        # ``resolve_handle_to_read_path`` → the coord worktree dir under a
        # materialized coordination topology). Since #2106 the planning artifacts
        # (spec.md, plan.md) live on the PRIMARY ``target_branch`` dir, so reading
        # them off ``feature_dir`` resolves to the coord husk and blocks with
        # ``SPEC_FILE_MISSING``. ``_planning_read_dir`` resolves SPEC / plan
        # (PRIMARY-partition kinds) to the primary dir for ALL topologies, so the
        # reads converge on the real artifact. Only the PLANNING reads move
        # (C-002): ``feature_dir`` stays the surface for STATUS/lifecycle emission
        # (``emit_artifact_phase``) and mission-type / dossier lookups below.
        # Routed through the ``mission`` shim (``_mission`` deferred-imported at the
        # top of this body) so the historical ``mission._planning_read_dir`` patch
        # seam — exercised by ``test_setup_plan_read_surface`` — reaches this caller.
        spec_read_dir = _mission._planning_read_dir(repo_root, mission_slug, artifact_type="spec")
        spec_file = spec_read_dir / "spec.md"
        plan_read_dir = _mission._planning_read_dir(repo_root, mission_slug, artifact_type="plan")
        plan_file = plan_read_dir / "plan.md"

        if _enforce_spec_gate(
            spec_file,
            feature_dir,
            mission_slug,
            repo_root,
            target_branch=target_branch,
            current_branch=current_branch,
            json_output=json_output,
        ):
            return

        _scaffold_plan_template(plan_file, repo_root)
        _emit_spec_plan_phase_events(feature_dir, mission_slug, spec_file, repo_root)

        from specify_cli.missions._substantive import is_substantive

        plan_is_substantive = is_substantive(plan_file, "plan")
        plan_commit_result, plan_blocked_reason = _commit_plan_if_substantive(
            plan_file,
            feature_dir,
            mission_slug,
            repo_root,
            target_branch=target_branch,
            json_output=json_output,
        )

        gap_analysis_path, generators_detected = _run_documentation_wiring(
            feature_dir, mission_slug, repo_root, target_branch=target_branch, json_output=json_output
        )

        _trigger_dossier_sync(feature_dir, mission_slug, repo_root)

        _emit_setup_plan_result(
            plan_file=plan_file,
            spec_file=spec_file,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            plan_is_substantive=plan_is_substantive,
            plan_blocked_reason=plan_blocked_reason,
            plan_commit_result=plan_commit_result,
            gap_analysis_path=gap_analysis_path,
            generators_detected=generators_detected,
            target_branch=target_branch,
            current_branch=current_branch,
            json_output=json_output,
        )

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


def _enforce_saas_sync_auth_refusal(*, json_output: bool) -> None:
    """FR-011 auth refusal that must run BEFORE project-root resolution.

    The original ``setup_plan`` ran the FR-011 ``read_queue_scope`` refusal at
    the very top (before ``locate_project_root``), so an unauthenticated
    SaaS-enabled invocation refuses even outside a repo. This phase preserves
    that ordering; the repo-scoped boundary preflight runs later in
    :func:`_enforce_saas_sync_preflight`.
    """
    if os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") != "1":
        return
    from specify_cli.sync.queue import (
        read_queue_scope_from_credentials,
        read_queue_scope_from_session,
    )

    _scope = read_queue_scope_from_session() or read_queue_scope_from_credentials()
    if _scope:
        return
    error_msg = "SaaS sync cannot be guaranteed: no authenticated session/credentials found."
    remediation = "Run `spec-kitty auth login` or unset SPEC_KITTY_ENABLE_SAAS_SYNC before running setup-plan."
    if json_output:
        _emit_json(
            {
                "error_code": "SAAS_SYNC_UNAUTHENTICATED",
                "error": error_msg,
                "remediation": [remediation],
            }
        )
    else:
        console.print(f"[red]Error[/red]: {error_msg}")
        console.print(remediation)
    raise typer.Exit(code=2)
