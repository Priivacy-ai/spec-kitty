"""Record-analysis command seam for ``agent mission`` (#2056 Seam A).

The lowest-risk command slice: the ``record-analysis`` command and its two
dedicated helpers, plus the small ``_git_dirty_paths`` git helper they depend
on. A one-way leaf that imports the Seam C/D surfaces (mission_parsing,
mission_feature_resolution) and lower layers only — never back into
``mission`` (INV-8). Heavyweight commit/SaaS imports stay function-local to
avoid import cycles (NFR-005).

The command function is defined here as a plain callable; ``mission.py``
registers it on its Typer ``app`` (``app.command(...)(record_analysis)``) so the
CLI surface is unchanged (WP01 golden harness is the regression net). Behavior
is preserved byte-for-byte from the pre-decomposition ``mission.py``.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
import subprocess
import sys
from typing import Annotated

from rich.console import Console
import typer

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    MissionArtifactKind,
    is_coordination_artifact_residue_path,
    is_self_bookkeeping_path,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.core.git_ops import is_git_repo
from specify_cli.core.paths import (
    get_feature_target_branch,
    get_main_repo_root,
    locate_project_root,
)

from specify_cli.cli.commands.agent.mission_feature_resolution import (
    _build_setup_plan_detection_error,
    _find_feature_directory,
)
from specify_cli.cli.commands.agent.mission_parsing import _emit_json

console = Console()

PROJECT_ROOT_NOT_FOUND = "Could not locate project root"
# WP03 / S1192: the rich-markup error prefix and the ``success``/``error``
# JSON payload keys, each repeated >=3x in this module -- hoisted to named
# constants rather than restated at every call site.
_RED_ERROR_PREFIX = "[red]Error:[/red] "
_PAYLOAD_KEY_SUCCESS = "success"
_PAYLOAD_KEY_ERROR = "error"




def _git_dirty_paths(repo_root: Path) -> list[str]:
    """Return dirty paths from `git status --porcelain`, or an empty list outside git."""
    if not is_git_repo(repo_root):
        return []
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "git status failed").strip())
    dirty: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        dirty.append(line[3:].strip() if len(line) > 3 else line.strip())
    return dirty


def _resolve_record_analysis_placement_ref(repo_root: Path, feature_dir: Path) -> CommitTarget | None:
    """Resolve the ANALYSIS_REPORT write placement ref for ``record-analysis``.

    Routes through ``placement_seam(...).write_target(ANALYSIS_REPORT)`` — the
    single kind-aware write authority (C-PLACE-1). ``ANALYSIS_REPORT`` is a
    coordination-partition kind, so the seam resolves its canonical
    :class:`CommitTarget` directly; ``resolve_action_context`` is NOT on this
    path. The mission slug is the resolved mission directory name (already
    CWD-invariant via the read primitive).
    Returns ``None`` on any resolution failure — the low-level resolver stays
    a plain ``Optional`` producer (unchanged contract); the caller now fails
    closed on ``None`` (D11 — see :func:`_require_record_analysis_placement`)
    instead of silently degrading to a conservative preflight.
    """
    from mission_runtime import ActionContextError as _ActionContextError, placement_seam

    try:
        return placement_seam(repo_root, feature_dir.name).write_target(
            MissionArtifactKind.ANALYSIS_REPORT
        )
    except _ActionContextError:
        return None


def _require_record_analysis_placement(
    placement_ref: CommitTarget | None, *, mission_slug: str
) -> CommitTarget:
    """Fail closed when record-analysis cannot resolve canonical placement (T013 / D11).

    A small, pure extraction (Sonar-testable) consumed by :func:`record_analysis`
    right after :func:`_resolve_record_analysis_placement_ref`. Replaces the
    silent "conservative legacy preflight" degradation the None-fallback used
    to produce: a genuine resolution failure now raises
    :class:`PlacementResolutionRequired` (naming the mission) instead of
    letting the dirty-tree preflight run with an un-filtered, potentially
    misleading dirty set.
    """
    if placement_ref is None:
        raise PlacementResolutionRequired(
            f"Could not resolve the canonical write placement for mission "
            f"'{mission_slug}'. This usually means the mission's stored "
            f"topology could not be resolved (e.g. a coordination branch "
            f"declared in meta.json is missing/torn down in git). Run "
            f"`spec-kitty doctor workspaces --fix`, or flatten the mission by "
            f"removing `coordination_branch` from meta.json if the "
            f"coordination topology was never used, then retry "
            f"`record-analysis`."
        )
    return placement_ref


def _enforce_analysis_report_write_preflight(
    repo_root: Path,
    *,
    json_output: bool,
    placement_ref: CommitTarget | None = None,
    mission_slug: str | None = None,
) -> None:
    """Fail before `record-analysis` mutates a mission artifact in unsafe git state.

    The dirty-tree check is context-aware. Under coordination topology,
    finalized planning/status artifacts are owned by the coordination branch; the
    primary checkout may legitimately carry stale copies. When ``placement_ref``
    resolves to a coordination target, drop only artifact-home residue from the
    dirty set so the preflight still gates on genuine uncommitted edits.
    """
    if not is_git_repo(repo_root):
        return

    dirty_paths = _git_dirty_paths(repo_root)
    # FR-003 (#2102): drop spec-kitty's OWN bookkeeping churn unconditionally —
    # ``meta.json`` + ``.kittify/encoding-provenance/global.jsonl`` are allowlisted
    # via the self-bookkeeping authority (DISJOINT from the coord-residue partition).
    # This runs regardless of topology because these files are spec-kitty's own
    # metadata, not coordination residue. The G-5 invariant holds: a stale primary
    # ``spec.md`` is NOT in the allowlist, so it survives this filter as "real dirt".
    dirty_paths = [path for path in dirty_paths if not is_self_bookkeeping_path(path)]
    # FR-005 / FR-001b: drop coord-owned residue only under a coordination
    # topology, read from the WP02 STORED topology via the ONE canonical predicate
    # (never a per-ref ``.kind``). ``mission_slug`` is required to resolve the
    # stored topology; absent it, the residue filter is skipped (no slug ⇒ no
    # mission topology to route on) and the preflight gates on the full dirty set.
    if (
        placement_ref is not None
        and mission_slug is not None
        and routes_through_coordination(resolve_topology(repo_root, mission_slug))
    ):
        dirty_paths = [
            path
            for path in dirty_paths
            if not is_coordination_artifact_residue_path(path, mission_slug=mission_slug)
        ]
    if dirty_paths:
        payload = {
            _PAYLOAD_KEY_SUCCESS: False,
            "error_code": "DIRTY_WORKTREE",
            _PAYLOAD_KEY_ERROR: "Refusing to record analysis report with pre-existing dirty working tree.",
            "dirty_paths": dirty_paths,
            "remediation": ["Commit or stash existing changes, then rerun /spec-kitty.analyze."],
        }
        if json_output:
            _emit_json(payload)
        else:
            console.print(f"{_RED_ERROR_PREFIX}{payload[_PAYLOAD_KEY_ERROR]}")
            for path in dirty_paths:
                console.print(f"  - {path}")
        raise typer.Exit(1)

    # T014 / WP02 / FR-001: protected-branch check removed here.
    # The analysis report write path now routes through commit_for_mission
    # (materialize-then-retry) so the report commit lands on the coordination
    # branch when the primary checkout is protected.  The write itself is safe
    # because write_analysis_report targets the primary checkout's kitty-specs
    # dir (primary_feature_dir_for_mission), which is not a git operation;
    # the subsequent commit_for_mission call stages the written artifact on
    # the coordination worktree before committing.


def record_analysis(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    input_file: Annotated[
        str,
        typer.Option("--input-file", help="Markdown report path, or '-' to read report from stdin"),
    ] = "-",
    analyzer_agent: Annotated[
        str | None,
        typer.Option("--agent", help="Agent name that produced the analysis report"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Persist `/spec-kitty.analyze` output as `analysis-report.md`."""
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = PROJECT_ROOT_NOT_FOUND
            if json_output:
                _emit_json({_PAYLOAD_KEY_ERROR: error_msg, _PAYLOAD_KEY_SUCCESS: False})
            else:
                console.print(f"{_RED_ERROR_PREFIX}{error_msg}")
            raise typer.Exit(1)
        cwd_repo_root = repo_root  # preserve CWD root for branch-protection check
        repo_root = get_main_repo_root(repo_root)

        # WP06 / T020 (#1814): resolve the mission read/write surface FIRST (via
        # the consolidated read primitive — no silent fallback) so the dirty-tree
        # preflight can key off the context's placement ref and not deadlock on
        # coord-residue in the primary checkout.
        try:
            feature_dir = _find_feature_directory(
                repo_root,
                Path.cwd().resolve(),
                explicit_feature=feature,
            )
        except (ValueError, ActionContextError) as detection_error:
            payload = _build_setup_plan_detection_error(
                repo_root,
                str(detection_error),
                feature,
                error_code="FEATURE_CONTEXT_UNRESOLVED",
                command_name="record-analysis",
                command_args=["--json"] if json_output else [],
            )
            if json_output:
                _emit_json(payload)
            else:
                console.print(f"{_RED_ERROR_PREFIX}{payload['error']}")
            raise typer.Exit(1) from None

        # C-PLACE-1: the placement ref is the ONE CommitTarget that planning
        # artifacts (incl. analysis-report) AND status events resolve to. The
        # dirty-tree preflight uses it to ignore coord-owned residue (#1814).
        # T013 / D11: a genuine resolution failure fails closed here instead of
        # silently letting the preflight run with a conservative, un-filtered
        # dirty set (see ``_require_record_analysis_placement``).
        placement_ref = _resolve_record_analysis_placement_ref(repo_root, feature_dir)
        placement_ref = _require_record_analysis_placement(
            placement_ref, mission_slug=feature_dir.name
        )
        _enforce_analysis_report_write_preflight(
            cwd_repo_root,
            json_output=json_output,
            placement_ref=placement_ref,
            mission_slug=feature_dir.name,
        )

        body = sys.stdin.read() if input_file == "-" else Path(input_file).read_text(encoding="utf-8")
        if not body.strip():
            error_msg = "Analysis report body is empty"
            if json_output:
                _emit_json({_PAYLOAD_KEY_ERROR: error_msg, _PAYLOAD_KEY_SUCCESS: False})
            else:
                console.print(f"{_RED_ERROR_PREFIX}{error_msg}")
            raise typer.Exit(1)

        from specify_cli.analysis_report import write_analysis_report

        # #1989: the write destination must be the PRIMARY-checkout mission dir,
        # not the coord-aware ``feature_dir`` from ``_find_feature_directory``
        # (which resolves to the coordination worktree once one exists — and that
        # worktree lacks ``spec.md``, so ``write_analysis_report`` would fail with
        # "Required artifact missing"). The coord-aware ``feature_dir`` still drives
        # the placement-ref and dirty-tree preflight above.
        #
        # #2102 / FR-009 (gate-read-surface-completion WP04): collapse the manual
        # coord-then-primary double-resolution onto the single kind-aware seam. The
        # planning-read leg here resolves the dir that must hold ``spec.md`` (a SPEC
        # kind — PRIMARY-partition) before the report is written; route it through
        # WP01's kind-aware read seam (``resolve_planning_read_dir``, the same single
        # authority ``tasks.py`` and ``_commit_to_branch`` route every planning
        # read/write onto) keyed by ``_kind_for_artifact("spec")``, instead of a
        # bespoke ``primary_feature_dir_for_mission`` call. SPEC is primary-partition,
        # so the seam resolves to the SAME topology-blind primary dir — a
        # behavior-NEUTRAL dedup (no observable delta), removing the parallel
        # resolution. The analysis-report WRITE target stays primary (data-model.md
        # KEEP); the dirty-tree allowlist / ANALYSIS_REPORT placement is WP05's
        # concern and is untouched here.
        from specify_cli.cli.commands.agent.mission_feature_resolution import _kind_for_artifact
        from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

        write_feature_dir = resolve_planning_read_dir(
            repo_root, feature_dir.name, kind=_kind_for_artifact("spec")
        )

        result = write_analysis_report(
            feature_dir=write_feature_dir,
            repo_root=repo_root,
            body=body,
            analyzer_agent=analyzer_agent,
        )

        # T014 / WP02 / FR-001: commit the analysis report via the canonical
        # commit router (materialize-then-retry). On a protected primary this
        # routes the commit to the coordination worktree, materialising it on
        # demand if needed. On an unprotected or flattened primary the commit
        # is direct. Best-effort: a commit failure does not abort the write
        # (the report is already on disk; the operator can commit separately).
        with contextlib.suppress(Exception):
            from specify_cli.coordination.commit_router import commit_for_mission
            from specify_cli.git.protection_policy import ProtectionPolicy

            _analysis_policy = ProtectionPolicy.resolve(repo_root)
            _analysis_mission_slug = feature_dir.name
            commit_for_mission(
                repo_root=repo_root,
                mission_slug=_analysis_mission_slug,
                files=(result.path,),
                message=f"Add analysis report for mission {_analysis_mission_slug}",
                policy=_analysis_policy,
                # ANALYSIS_REPORT is a COORD kind (write-surface-coherence WP02 /
                # T008): the analysis report STAYS on the coordination branch under
                # coord topology (C-001) — the explicit COORD caller proving the
                # bifurcation. It must NOT be re-kinded to a primary kind.
                kind=MissionArtifactKind.ANALYSIS_REPORT,
                target_branch=get_feature_target_branch(repo_root, _analysis_mission_slug),
            )

        with contextlib.suppress(Exception):
            from specify_cli.sync.dossier_pipeline import (
                trigger_feature_dossier_sync_if_enabled,
            )

            trigger_feature_dossier_sync_if_enabled(
                write_feature_dir,
                result.mission_slug,
                repo_root,
            )

        payload = {_PAYLOAD_KEY_SUCCESS: True, "result": "success", **result.to_dict()}
        if json_output:
            _emit_json(payload)
        else:
            rel = result.path.relative_to(repo_root) if result.path.is_relative_to(repo_root) else result.path
            console.print(f"[green]✓[/green] Analysis report persisted: {rel}")

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({_PAYLOAD_KEY_ERROR: str(e), _PAYLOAD_KEY_SUCCESS: False})
        else:
            console.print(f"{_RED_ERROR_PREFIX}{e}")
        raise typer.Exit(1) from None
