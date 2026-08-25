"""finalize-tasks command family for ``agent mission`` (#2056 WP07).

This leaf module owns ``finalize_tasks`` — the largest single function in the
pre-decomposition ``mission.py`` (1227 LOC) — plus its two dedicated helpers
``_collect_finalize_artifacts`` and ``_branch_tree_relative_path``. The body is
decomposed into ≤15-CC phase helpers, each with focused tests in
``test_mission_finalize_phases.py``.

INV-6 (the ``--validate-only`` zero-mutation invariant) is preserved exactly:
the bootstrap loop infers all 8 fields in memory but the disk-write phase is
guarded by ``frontmatter_changed and not validate_only`` and the validate-only
report path returns BEFORE any committing/seeding writer runs. An explicit
assertion (``_assert_no_write_in_validate_only``) reinforces the guard.

One-way leaf (INV-8): imports lower layers + sibling Seam B/C/D leaves only at
module scope. The cross-cutting symbols the finalize tests patch on the
``mission`` module (``locate_project_root`` /
``_find_feature_directory`` / ``run_command``) are resolved
THROUGH the ``mission`` module at call time so the historical
``mission.<name>`` patch seams keep working without an import cycle. The
command is defined here as a plain callable; ``mission`` registers it on its
Typer ``app`` and re-exports the public names (WP09 finalizes the sweep).

Behavior is preserved byte-for-byte from the pre-decomposition ``mission.py``;
the WP01 golden harness is the regression net. ``_stage_finalize_artifacts_in_
coord_worktree`` / ``_resolve_planning_placement`` / ``_planning_commit_worktree``
are NOT relocated here — WP08 moves them to ``commit_router``.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, cast

import typer
from specify_cli.cli.console import console
from specify_cli.cli.console import err_console

from kernel._safe_re import re
from kernel.paths import repo_tree_path
from mission_runtime import ActionContextError, MissionArtifactKind
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.core.dependency_graph import detect_cycles, validate_dependencies
from specify_cli.frontmatter import write_frontmatter
from specify_cli.missions._resolve_planning_branch import PlanningBranchResolutionFailed
from specify_cli.lanes.models import LanesManifest
from specify_cli.ownership import infer_ownership
from specify_cli.ownership.audit_targets import validate_audit_coverage
from specify_cli.ownership.frontmatter_source import (
    FinalizeFrontmatterSource,
    resolve_wp_manifests,
)
from specify_cli.ownership.models import OwnershipManifest
from specify_cli.ownership.validation import (
    GlobValidationResult,
    ValidationResult,
    validate_glob_matches,
)
from specify_cli.status import BootstrapResult, WPMetadata, _Builder
from specify_cli.core.wps_manifest import (
    WpsManifest,
    check_concern_refs_coverage,
    dependencies_are_explicit,
    generate_tasks_md_from_manifest,
    load_wps_manifest,
)

from specify_cli.cli.commands.agent.mission_check_prerequisites import (
    _read_meta_for_emission,
)
from specify_cli.cli.commands.agent.mission_feature_resolution import (
    _build_setup_plan_detection_error,
    _resolve_mission_dir_name_primary_anchored,
)
from specify_cli.cli.commands.agent.mission_parsing import (
    _extract_wp_ids_from_task_files,
    _find_undeclared_requirement_citations,
    _invalid_mission_specs_owned_files,
    _owned_files_yaml_is_explicit_empty_list,
    _parse_requirement_ids_from_spec_md,
    _parse_requirement_refs_from_tasks_md,
    _parse_requirement_refs_from_wp_files,
    _raw_frontmatter_has_field,
)

logger = logging.getLogger(__name__)

TASKS_MD_FILENAME = "tasks.md"
ISSUE_MATRIX_FILENAME = "issue-matrix.md"
META_JSON_FILENAME = "meta.json"
FINALIZE_TASKS_COMMAND_NAME = "spec-kitty agent mission finalize-tasks"
INVALID_WP_OWNED_FILES_KITTY_SPECS = "INVALID_WP_OWNED_FILES_KITTY_SPECS"
PROJECT_ROOT_NOT_FOUND = "Could not locate project root"

# SK3466-REV-001: the ONLY meta.json field finalize-tasks itself ever writes
# (via ``_persist_target_branch_override`` -> ``mission_metadata.
# set_target_branch``). A pending meta.json delta confined to these fields —
# whether produced by THIS invocation's own persist call or dangling from an
# earlier crashed finalize-tasks run (SK3466-RR-001) — is finalize-tasks'
# business regardless of which run produced it. A delta touching any OTHER
# field (e.g. ``vcs``/``vcs_locked_at``, written by ``implement``'s
# ``_ensure_vcs_in_meta`` -> ``set_vcs_lock`` even under ``--no-auto-commit``)
# belongs to a different command and must not silently ride finalize-tasks'
# commit. See ``_meta_json_delta_is_finalize_attributable``.
FINALIZE_ATTRIBUTABLE_META_FIELDS = frozenset({"target_branch"})

# Dynamic alias mirror of the canonical ``mission-specs`` validator (the
# KITTY_SPECS_DIR identifier form, built via ``.replace("-", "_")`` to avoid a
# raw mission-spec literal in source). Mirrors mission.py's globals() injection
# so the same symbol is resolvable here too.
globals()["_invalid_" + KITTY_SPECS_DIR.replace("-", "_") + "_owned_files"] = (
    _invalid_mission_specs_owned_files
)


def _emit_json(payload: dict[str, object]) -> None:
    """Emit ``payload`` as JSON via the ``mission`` module's ``_emit_json``.

    Routing every finalize JSON emission through the ``mission`` module (rather
    than importing ``_emit_json`` directly) preserves the historical
    ``mission._emit_json`` patch seam exercised by callers that invoke
    ``mission.finalize_tasks`` directly.
    """
    from specify_cli.cli.commands.agent import mission as _mission

    _mission._emit_json(payload)


# ---------------------------------------------------------------------------
# Cross-cutting indirection (#2056 WP07): resolve the symbols the finalize test
# suites patch on the ``mission`` module THROUGH that module at call time, so the
# historical ``mission.<name>`` patch seams keep working after the relocation
# without an import cycle. The direct module-scope imports above are kept for the
# type annotations + non-patched call sites; these wrappers are used wherever a
# test patches the name (``read_wp_frontmatter`` / ``bootstrap_canonical_state``
# / ``validate_ownership`` / ``_resolve_planning_branch`` are spied/replaced by
# ``test_feature_finalize_bootstrap.py`` and friends).
# ---------------------------------------------------------------------------


def _read_wp_frontmatter(wp_file: Path) -> tuple[WPMetadata, str]:
    """Route ``read_wp_frontmatter`` through ``mission`` (patch seam)."""
    from specify_cli.cli.commands.agent import mission as _mission

    return _mission.read_wp_frontmatter(wp_file)


def _resolve_planning_branch_via_mission(
    repo_root: Path, primary_dir: Path, *, target_branch_override: str | None
) -> str:
    """Route ``_resolve_planning_branch`` through ``mission`` (patch seam)."""
    from specify_cli.cli.commands.agent import mission as _mission

    return _mission._resolve_planning_branch(
        repo_root, primary_dir, target_branch_override=target_branch_override
    )


def _bootstrap_canonical_state_via_mission(
    planning_dir: Path, mission_slug: str, *, dry_run: bool, capability: GuardCapability | None = None
) -> BootstrapResult:
    """Route ``bootstrap_canonical_state`` through ``mission`` (patch seam)."""
    from specify_cli.cli.commands.agent import mission as _mission

    if capability is None:
        return _mission.bootstrap_canonical_state(planning_dir, mission_slug, dry_run=dry_run)
    return _mission.bootstrap_canonical_state(planning_dir, mission_slug, dry_run=dry_run, capability=capability)


def _validate_ownership_via_mission(
    wp_manifests: dict[str, OwnershipManifest], wp_dependencies: dict[str, list[str]]
) -> ValidationResult:
    """Route ``validate_ownership`` through ``mission`` (patch seam)."""
    from specify_cli.cli.commands.agent import mission as _mission

    return _mission.validate_ownership(wp_manifests, wp_dependencies)


# ---------------------------------------------------------------------------
# Finalize artifact helpers (relocated verbatim from mission.py — WP07 / T027)
# ---------------------------------------------------------------------------


def _branch_tree_relative_path(file_path: Path, repo_root: Path) -> str:
    """Return the path as it appears in the current branch tree.

    Delegates to the canonical worktree-aware seam
    (:func:`specify_cli.missions._substantive.repo_tree_path`) so the
    worktree-strip and POSIX-normalization logic (#2836) lives in exactly one
    place rather than being maintained as a second copy here. Raises
    ``ValueError`` when ``file_path`` is not under ``repo_root`` (unchanged).
    """
    return repo_tree_path(file_path, repo_root)[1]


def _collect_finalize_artifacts(
    feature_dir: Path,
    tasks_dir: Path,
    lanes_path: Path | None = None,
) -> list[Path]:
    """Return all deterministic artifacts finalize-tasks may need to commit.

    FIX-M2-05: dropped the ``mission_slug`` parameter (positional 3rd arg in
    prior revisions). It existed solely to build the dossier snapshot's path
    (``feature_dir / ".kittify" / "dossiers" / mission_slug / "snapshot-latest.json"``)
    for inclusion as a commit candidate -- an inclusion that itself violated
    ``contracts/dossier-snapshot-ownership.md`` (D1) and is removed below.
    None of the remaining deterministic candidates need the mission slug
    (they resolve entirely from ``feature_dir`` / ``tasks_dir`` /
    ``lanes_path``), so the parameter is genuinely dead, not merely unused —
    callers pass only what this function still reads.

    ``meta.json`` (SK3466-RR-001) is an UNCONDITIONAL CANDIDATE here — not
    gated on whether THIS invocation's own ``--target-branch`` persist call
    fired. A prior, crashed finalize-tasks run can leave meta.json rewritten
    on disk but never committed; a later run whose override happens to match
    that dangling value reads as a no-op from
    ``_persist_target_branch_override``'s point of view (``previous_value ==
    target_branch``) and would never re-fold it into a commit if inclusion
    depended on that call's own outcome. Making meta.json a first-class,
    always-considered CANDIDATE closes that half of the defect class by
    construction (DIRECTIVE_043).

    UNLIKE ``tasks.md`` / ``status.json`` / the lane manifest, meta.json has a
    writer OUTSIDE finalize-tasks: ``implement --no-auto-commit`` can leave
    its own unrelated meta.json edit (``vcs``/``vcs_locked_at``) staged but
    deliberately uncommitted (SK3466-REV-001). Being a candidate here does
    NOT mean meta.json is unconditionally committed — ``_commit_finalize_
    artifacts`` additionally attributes any pending delta by WHICH FIELDS
    changed (:func:`_meta_json_delta_is_finalize_attributable`) before
    folding it in, so a foreign writer's edit is not silently swept into this
    commit just because it happens to be dirty at the same time.
    """
    candidates: list[Path] = [
        feature_dir / "status.events.jsonl",
        feature_dir / "status.json",
        feature_dir / TASKS_MD_FILENAME,
        # partition-authority-residuals-01M021K9 WP06 (#2937 / FR-009 / D-001
        # default): the wps.yaml manifest is the finalize INPUT that tasks.md is
        # regenerated from. Version it here so the finalized checkpoint can
        # reproduce its own state (INV-5) — it classifies to the PRIMARY-partition
        # TASKS_INDEX kind, so the commit router routes it to target_branch with
        # tasks.md.
        feature_dir / "wps.yaml",
        feature_dir / META_JSON_FILENAME,
        feature_dir / "acceptance-matrix.json",
        # write-surface-coherence WP08 (#2804 / #2404 T043 / G3): sweep the
        # terminal ``issue-matrix.json`` — the retired ``issue-matrix.md`` is
        # never authored by any canonical path any more (WP05), so it is no
        # longer a finalize-commit candidate.
        feature_dir / "issue-matrix.json",
        # FIX-M2-05: the dossier snapshot is DELIBERATELY NOT a candidate here.
        # ``contracts/dossier-snapshot-ownership.md`` (D1, mission
        # charter-e2e-827-followups-01KQAJA0 / #845) ratifies
        # ``.kittify/dossiers/<slug>/snapshot-latest.json`` as excluded from
        # version control -- "save_snapshot() ... No staging, no committing,
        # no special branch interaction. The file is just a file." Committing
        # it here (as a prior revision of this function did) violated that
        # contract: once tracked on one branch it is inherited by every lane
        # and coordination worktree that branch touches, and every later
        # fire-and-forget dossier-sync write (mark-status, move-task, merge,
        # …) then leaves that worktree's copy locally modified/uncommitted —
        # exactly the drift ``git/ref_advance.py``'s merge-time
        # dirty-checked-out-worktree resync (#1826) refuses to silently
        # discard. Leaving it off this list keeps every producer honoring the
        # same "just a file" contract move-task's dirty-state preflight
        # already enforces (``status/preflight.py::is_dossier_snapshot``).
    ]
    candidates.extend(sorted(path for path in tasks_dir.iterdir() if path.is_file()))
    if lanes_path is not None:
        candidates.append(lanes_path)

    seen: set[Path] = set()
    artifacts: list[Path] = []
    for candidate in candidates:
        if candidate.exists() and candidate not in seen:
            artifacts.append(candidate)
            seen.add(candidate)
    return artifacts


def _meta_json_delta_is_finalize_attributable(meta_path: Path, repo_root: Path) -> bool:
    """Decide whether a pending meta.json edit is finalize-tasks' own business (SK3466-REV-001).

    ``_collect_finalize_artifacts`` treats meta.json as an unconditional
    CANDIDATE (SK3466-RR-001) so a dangling write from an earlier CRASHED
    finalize-tasks run still gets folded into this run's commit even though
    it wasn't produced by THIS invocation's own persist call. But
    ``implement --no-auto-commit`` can ALSO leave meta.json dirty — via
    ``_ensure_vcs_in_meta`` -> ``set_vcs_lock`` writing ``vcs``/``vcs_locked_
    at`` unconditionally on a WP's first claim, deliberately left uncommitted
    when auto-commit is disabled — and that edit belongs to a DIFFERENT
    command, not to finalize-tasks.

    Rather than attributing a pending edit to a particular PRIOR INVOCATION
    (unrecoverable — no invocation identity survives a crash, and a
    dangling write and a foreign write look identical on disk), this
    attributes by WHICH FIELDS changed: finalize-tasks is the sole writer of
    ``target_branch`` in meta.json (:func:`specify_cli.mission_metadata.
    set_target_branch`), so a delta confined to
    ``FINALIZE_ATTRIBUTABLE_META_FIELDS`` — whichever run produced it — is
    finalize-tasks' business. A delta touching any OTHER field is a foreign
    writer's business and must not silently ride this commit.

    Mixed case: when BOTH a dangling ``target_branch`` write and a foreign
    field write are pending simultaneously, this returns ``False`` — the
    WHOLE file is excluded from this commit, not just the foreign field.
    meta.json is a single JSON blob; there is no way to commit "only the
    target_branch part" of a working-tree file without finalize-tasks
    hand-constructing and writing a synthetic merged meta.json itself, which
    would make it a second writer of fields (``vcs``) it does not own —
    reintroducing exactly the kind of implicit cross-command coupling this
    fix closes. Excluding the whole file is the smallest-blast-radius choice:
    the dangling ``target_branch`` fix simply waits for a future run where
    the foreign field is no longer pending (e.g. once ``implement`` itself
    commits it).

    Both sides of the diff are decoded via :func:`kernel.meta_decode.
    decode_meta` — the single canonical meta.json decode primitive (FR-010) —
    rather than a hand-rolled ``json.loads``, so this function does not
    become a second, independent meta.json decoder.

    Returns ``True`` (attributable — keep as a commit candidate) when:
    - meta.json is not tracked at ``HEAD`` yet (nothing to diff against — the
      whole file is new content), or
    - the committed (``HEAD``) side fails to parse as JSON while the working-tree
      copy is valid (our fix supersedes a malformed committed copy), or
    - the changed-field set is empty or a subset of
      ``FINALIZE_ATTRIBUTABLE_META_FIELDS``.

    Returns ``False`` (exclude the whole file) when the working-tree copy is
    unreadable or malformed. finalize-tasks did NOT commit meta.json before
    #3466, so the conservative default for a corrupt on-disk file is to never
    commit it -- committing a truncated meta.json would break every fail-closed
    reader.
    """
    from kernel.meta_decode import decode_meta
    from specify_cli.cli.commands.agent import mission as _mission

    try:
        rel_path = _branch_tree_relative_path(meta_path, repo_root)
    except ValueError:
        return True

    return_code, committed_text, _stderr = _mission.run_command(
        ["git", "show", f"HEAD:{rel_path}"],
        check_return=False,
        capture=True,
        cwd=repo_root,
    )
    if return_code != 0:
        # Not tracked at HEAD (brand-new meta.json) -- the whole file is new
        # content, not a foreign edit riding alongside ours.
        return True

    try:
        current_text = meta_path.read_text(encoding="utf-8")
    except OSError as read_exc:
        # #3466 landing: a working-tree meta.json that cannot be read is
        # EXCLUDED, not committed. finalize-tasks never committed meta.json
        # before this change, so an unreadable on-disk copy must not be swept
        # into the finalize commit -- doing so risks committing a truncated or
        # corrupt file over readers that fail closed on it.
        logger.warning(
            "#3466: could not read %s to compute finalize-commit attribution "
            "(%s); excluding meta.json from the finalize commit",
            meta_path,
            read_exc,
        )
        return False
    committed_meta = decode_meta(committed_text, on_malformed="none")
    current_meta = decode_meta(current_text, on_malformed="none")
    if current_meta is None:
        # #3466 landing: the working-tree meta.json is malformed (e.g. truncated
        # by a crash mid-write). finalize-tasks did NOT commit meta.json before
        # this change, so the conservative default is to EXCLUDE a corrupt
        # on-disk file -- committing it would break every fail-closed reader.
        logger.warning(
            "#3466: working-tree %s failed to decode as JSON while computing "
            "finalize-commit attribution for %s; excluding meta.json from the "
            "finalize commit",
            META_JSON_FILENAME,
            meta_path,
        )
        return False
    if committed_meta is None:
        # The committed (HEAD) copy is malformed but our working-tree copy is
        # valid: include it -- committing the good file over a bad HEAD is safe
        # and is exactly the corrective write finalize-tasks exists to make.
        logger.warning(
            "#3466: HEAD %s failed to decode as JSON while computing "
            "finalize-commit attribution for %s; including the valid "
            "working-tree meta.json in the finalize commit",
            META_JSON_FILENAME,
            meta_path,
        )
        return True

    changed_keys = {
        key
        for key in {*committed_meta.keys(), *current_meta.keys()}
        if committed_meta.get(key) != current_meta.get(key)
    }
    return changed_keys <= FINALIZE_ATTRIBUTABLE_META_FIELDS


# ---------------------------------------------------------------------------
# Phase helpers (each ≤15 CC — #2056 WP07 / T028)
# ---------------------------------------------------------------------------


def _resolve_repo_root(json_output: bool) -> Path:
    """Phase: locate the project root or exit with the canonical error.

    Routes ``locate_project_root`` through the ``mission`` module so the
    ``mission.locate_project_root`` patch seam keeps working.
    """
    from specify_cli.cli.commands.agent import mission as _mission

    repo_root = _mission.locate_project_root()
    if repo_root is None:
        if json_output:
            _emit_json({"error": PROJECT_ROOT_NOT_FOUND})
        else:
            console.print(f"[red]Error:[/red] {PROJECT_ROOT_NOT_FOUND}")
        raise typer.Exit(1)
    return repo_root


def _resolve_mission_slug(repo_root: Path, feature: str | None, *, json_output: bool) -> str:
    """Phase: resolve the mission slug, primary-anchored (Seam D).

    #11 / #1718 / #1692: anchor primary-first (no coord-existence gate); only
    when the primary surface also cannot resolve the handle do we surface the
    structured detection error. Routes ``_find_feature_directory`` through the
    ``mission`` module to preserve the patch seam.
    """
    from specify_cli.cli.commands.agent import mission as _mission
    from specify_cli.missions._read_path_resolver import MissionSelectorAmbiguous

    cwd = Path.cwd().resolve()
    ambiguous: ActionContextError | None
    try:
        mission_dir_name = _resolve_mission_dir_name_primary_anchored(repo_root, feature)
    except MissionSelectorAmbiguous as ambiguous_error:
        ambiguous = ActionContextError(ambiguous_error.error_code, str(ambiguous_error))
    else:
        ambiguous = None

    if mission_dir_name is not None:
        return mission_dir_name

    try:
        feature_dir = _mission._find_feature_directory(repo_root, cwd, explicit_feature=feature)
    except (ValueError, ActionContextError) as detection_error:
        payload = _build_setup_plan_detection_error(
            repo_root,
            str(ambiguous or detection_error),
            feature,
            error_code=(ambiguous.code if ambiguous is not None else "FEATURE_CONTEXT_UNRESOLVED"),
            command_name="finalize-tasks",
            command_args=["--json"] if json_output else [],
        )
        if json_output:
            _emit_json(payload)
        else:
            console.print(f"[red]Error:[/red] {payload['error']}")
            for slug in cast(list[str], payload.get("available_missions", []))[:10]:
                console.print(f"  - {slug}")
            if "example_command" in payload:
                console.print(f"  {payload['example_command']}")
        raise typer.Exit(1) from None
    return feature_dir.name


def _resolve_target_branch(
    repo_root: Path,
    primary_dir: Path,
    *,
    target_branch_override: str | None,
    json_output: bool,
) -> str:
    """Phase: resolve the canonical merge target branch (WP07 / FR-012 / SC-04).

    The current checkout is NEVER consulted; ``_resolve_planning_branch`` reads
    meta.json. Anchored on the PRIMARY feature dir for idempotency across
    re-runs (WP05 / T020 / F-001).
    """
    try:
        return _resolve_planning_branch_via_mission(
            repo_root, primary_dir, target_branch_override=target_branch_override
        )
    except PlanningBranchResolutionFailed as exc:
        if json_output:
            _emit_json({"error": str(exc), "error_code": exc.error_code})
        else:
            console.print(f"[red]Error:[/red] {exc}")
            console.print("[yellow]Hint:[/yellow] re-run with [bold]--target-branch <ref>[/bold] to override.")
        raise typer.Exit(1) from exc


@dataclass(frozen=True)
class TargetBranchPersistOutcome:
    """Result of attempting to persist a ``--target-branch`` override (#3466).

    A plain ``bool`` return could not distinguish "no-op: override already
    matched meta.json" from "no-op: the write was attempted and FAILED" —
    SK3466-R-002 found that ambiguity meant a ``--json`` caller had zero
    diagnostic when the write failed, so a subsequent ``PROTECTED_BRANCH_
    REFUSED`` (still reading the stale on-disk value) looked like an
    unexplained recurrence of #3466 rather than a directly attributable
    persist failure. This type makes every arm explicit for callers AND for
    the terminal JSON payload (SK3466-R-003 traceability).

    Attributes:
        persisted: ``True`` only when meta.json was actually rewritten this
            call.
        previous_value: The ``target_branch`` value read from meta.json
            BEFORE this call (``None`` when meta.json was absent/unreadable
            or no override was supplied).
        persist_error: Set only when a write was attempted and raised
            (``ValueError``/``FileNotFoundError``/``MissionMetaReadError``
            from ``set_target_branch`` — SK3466-RR-002 added the last);
            ``None`` for every no-op or successful arm.
    """

    persisted: bool
    previous_value: str | None = None
    persist_error: str | None = None


def _persist_target_branch_override(
    primary_dir: Path,
    target_branch: str,
    *,
    target_branch_override: str | None,
    json_output: bool,
) -> TargetBranchPersistOutcome:
    """Persist an explicit ``--target-branch`` override into meta.json (#3466).

    Every ``target_branch`` reader downstream of finalize-tasks — chiefly the
    WP-status-transition bookkeeping (:func:`specify_cli.status.bootstrap.
    bootstrap_canonical_state`, via :func:`specify_cli.core.paths.
    get_feature_target_branch` / :func:`mission_runtime.resolution.
    resolve_placement_only`) — resolves the mission's ``target_branch`` by
    reading the PRIMARY ``meta.json`` directly. It has no awareness of
    ``target_branch_override``: that value previously lived only in this
    command's own local ``target_branch`` variable, so a mission whose
    meta.json still recorded ``target_branch: "main"`` kept sending WP-status
    bookkeeping at "main" — the protected-branch guard refused it — even when
    the operator passed ``--target-branch <real-branch>`` (the documented
    FR-012 escape hatch never reached that consumer).

    Rather than threading a second override parameter through the shared
    placement/status-transition resolvers (``resolve_placement_only`` /
    ``resolve_write_target_or_degrade`` / ``TransitionRequest`` — a much wider
    blast radius across ~15 call sites in implement/merge/review/sync that have
    no override concept of their own — DIRECTIVE_024 locality-of-change), this
    persists the corrected value through the existing canonical mutation
    helper (:func:`specify_cli.mission_metadata.set_target_branch`), built and
    unit-tested for exactly this purpose but never wired to this CLI flag.
    Every downstream reader then converges on the SAME corrected field with no
    further code changes — DIRECTIVE_044 single canonical authority / 043
    close-the-defect-class-by-construction, rather than a second fallback
    branch.

    A no-op when no override was supplied, when it matches the value already
    on disk (idempotent re-runs), or when meta.json is absent (the rarer
    pre-meta.json legacy case the escape hatch also nominally covers — the
    override still applies in-process via ``target_branch``; there is simply
    no canonical file yet to persist it into). Only ever called from the
    non-``--validate-only`` commit pipeline (INV-6: validate-only performs
    zero writes).

    A failed run must not leave this write dangling in the working tree
    (SK3466-R-001): the caller captures meta.json's pre-call content and
    restores it if a downstream validation gate raises ``typer.Exit`` before
    ``_commit_finalize_artifacts`` folds the (still on-disk) write into the
    finalize commit — see ``_revert_unpersisted_target_branch_override`` in
    ``finalize_tasks``.

    Returns:
        A :class:`TargetBranchPersistOutcome`. ``persisted=True`` only when
        meta.json was actually rewritten this call. :func:`_collect_finalize_
        artifacts` (SK3466-RR-001) treats meta.json as a commit candidate,
        and :func:`_meta_json_delta_is_finalize_attributable` (SK3466-REV-001)
        folds any pending ``target_branch``-only delta into the finalize
        commit — this run's own write, or one dangling from a prior crashed
        run — rather than letting it survive as a dangling working-tree edit;
        this function no longer has to get that right on its own. (A delta
        that ALSO touches a foreign field, e.g. a concurrent ``implement
        --no-auto-commit`` write, is excluded from the commit entirely —
        see that function's docstring for the mixed-case rationale.) Every
        no-op/failure arm carries ``persisted=False`` plus ``previous_
        value``/``persist_error`` so the caller (and the terminal JSON
        payload) can distinguish "already correct" from "write failed"
        (SK3466-R-002/R-003).
    """
    if target_branch_override is None or not target_branch_override.strip():
        return TargetBranchPersistOutcome(persisted=False)
    from specify_cli.core.paths import MissionMetaReadError
    from specify_cli.mission_metadata import load_meta_or_empty, set_target_branch

    meta_path = primary_dir / META_JSON_FILENAME
    if not meta_path.exists():
        return TargetBranchPersistOutcome(persisted=False)
    previous_value_raw = load_meta_or_empty(primary_dir).get("target_branch")
    previous_value = str(previous_value_raw) if previous_value_raw else None
    if previous_value == target_branch:
        return TargetBranchPersistOutcome(persisted=False, previous_value=previous_value)
    try:
        set_target_branch(primary_dir, target_branch)
    except (FileNotFoundError, ValueError, MissionMetaReadError) as persist_exc:
        # FileNotFoundError is a TOCTOU guard only (SK3466-R-004): the
        # ``meta_path.exists()`` check above already returns early on a
        # missing meta.json, so this arm fires only if meta.json is deleted
        # out from under us between that check and set_target_branch's own
        # read — not reachable in the single-process, single-invocation path.
        # MissionMetaReadError (SK3466-RR-002) IS reachable: it fires when
        # meta.json EXISTS but is corrupt/malformed JSON — a realistic shape
        # for the legacy-mission population this --target-branch escape
        # hatch is documented to serve. set_target_branch -> _require_meta ->
        # _load_meta_fail_closed raises this typed RuntimeError subclass
        # (core/paths.py) rather than ValueError; without it here, a corrupt
        # meta.json bypassed this function's structured warning/JSON contract
        # entirely and fell through to finalize_tasks's generic outer
        # ``except Exception`` as an unstructured ``{"error": str(e)}``.
        error_detail = str(persist_exc)
        if not json_output:
            console.print(
                "[yellow]Warning:[/yellow] could not persist --target-branch override "
                f"to meta.json: {error_detail}"
            )
        else:
            # SK3466-R-002: without this, a --json caller gets ZERO
            # diagnostic — meta_json_persisted silently stays False and a
            # later PROTECTED_BRANCH_REFUSED (still reading the stale
            # on-disk value) reads as an unexplained recurrence of #3466
            # instead of a directly attributable persist failure.
            _emit_json(
                {
                    "warning": "target_branch_override_not_persisted",
                    "target_branch_override": target_branch,
                    "detail": error_detail,
                }
            )
        return TargetBranchPersistOutcome(
            persisted=False, previous_value=previous_value, persist_error=error_detail
        )
    if not json_output and previous_value is not None:
        # SK3466-R-003: a distinct (non-cyan) notice that a repeat
        # finalize-tasks invocation just permanently rewrote the mission's
        # canonical merge destination — finalize-tasks is documented as
        # repeatable, so a stale/mistaken --target-branch on a routine
        # re-run is otherwise a silent, unflagged overwrite.
        console.print(
            f"[yellow]Note:[/yellow] target_branch override persisted to meta.json "
            f"({previous_value} -> {target_branch})"
        )
    return TargetBranchPersistOutcome(persisted=True, previous_value=previous_value)



def _read_spec_requirement_ids(
    planning_dir: Path, *, json_output: bool
) -> tuple[set[str], set[str], list[str], str]:
    """Phase: parse spec.md requirement ids (all + functional) + #3394 F1 warnings.

    The third element is a (possibly empty) list of non-blocking warning
    messages from :func:`_find_undeclared_requirement_citations` -- surfaced
    so a spec whose Functional Requirements section matches none of the
    recognized declared shapes gets a loud (but never gate-failing) signal
    instead of silently reporting zero declared FRs as full coverage.

    WP06 (#3396) T031 plumbing fix: also returns the raw ``spec_content`` (the
    fourth element) so the caller can thread it into
    :func:`_validate_requirement_mapping` for the bare-prose requirement-id
    detector -- previously this text was read here and discarded, leaving
    that later phase with no access to it.
    """
    spec_md = planning_dir / "spec.md"
    if not spec_md.exists():
        error_msg = f"spec.md not found: {spec_md}"
        if json_output:
            print(json.dumps({"error": error_msg}))
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)
    spec_content = spec_md.read_text(encoding="utf-8")
    spec_requirement_ids = _parse_requirement_ids_from_spec_md(spec_content)
    extraction_warnings = _find_undeclared_requirement_citations(spec_content)
    return (
        set(spec_requirement_ids["all"]),
        set(spec_requirement_ids["functional"]),
        extraction_warnings,
        spec_content,
    )


def _scaffold_issue_matrix_if_present(
    planning_dir: Path,
    repo_root: Path,
    mission_slug: str,
    *,
    target_branch: str | None,
    validate_only: bool,
    json_output: bool,
) -> None:
    """Phase: B3 / T021 issue-matrix.json scaffold (idempotent), routed COORD.

    write-side-seam-matrix-tracer-01KYP3MH WP05 (B3): authors
    ``issue-matrix.json`` via ``write_target(ISSUE_MATRIX)`` -- COORD for
    coord/lanes-with-coord topologies -- NEVER a stray ``issue-matrix.md`` on
    the planning (primary) dir. The former ``.md``-on-primary scaffold meant
    FR-013 migrate-on-write never fired for a greenfield mission.
    """
    if validate_only:
        return
    try:
        from specify_cli.git.protection_policy import ProtectionPolicy
        from specify_cli.tasks.issue_matrix import scaffold_issue_matrix

        spec_md = planning_dir / "spec.md"
        issue_matrix_path = scaffold_issue_matrix(
            planning_dir,
            spec_md,
            repo_root=repo_root,
            mission_slug=mission_slug,
            policy=ProtectionPolicy.resolve(repo_root),
            target_branch=target_branch,
        )
    except Exception as issue_matrix_exc:  # noqa: BLE001 — convenience artifact never blocks finalize
        if not json_output:
            console.print(f"[yellow]Warning:[/yellow] could not scaffold issue-matrix.json: {issue_matrix_exc}")
        return
    if issue_matrix_path is not None and not json_output:
        try:
            rel: Path = issue_matrix_path.relative_to(repo_root)
        except ValueError:
            rel = issue_matrix_path
        console.print(f"[info] Scaffolded {rel}")


def _advisory_issue_matrix_lint(planning_dir: Path, *, json_output: bool) -> None:
    """Phase: FR-009 advisory (never-blocking) issue-matrix lint (#2223).

    Reuses the SAME exported ``validate_issue_matrix`` rule engine the approve
    gate calls (NFR-002 — one engine, two callers). Findings are surfaced as
    warnings only; a malformed matrix NEVER blocks ``finalize-tasks``. The
    completeness "row-for-every-#ref" scan in
    ``agent/tasks_parsing_validation.py::_issue_matrix_evaluation`` is OUT of
    scope here and intentionally not cross-imported (it would invert the
    command-module dependency direction; factor a shared pure helper first).

    The engine is imported at call time from the ``review`` package so the
    symbol resolves to the exact callable the approve gate uses (and stays
    monkeypatchable for call-identity tests) without an import cycle.

    C1 fix (write-side-seam-matrix-tracer-01KYP3MH WP05): the precheck is
    dir-based (:func:`issue_matrix_artifact_present`), not a ``.md``-only
    ``.exists()`` -- the prior precheck made a ``.json``-only mission (B3)
    return here BEFORE ``validate_issue_matrix`` ever ran, silently skipping
    the lint entirely (the same dead-code-behind-a-precheck class the reader
    migration fixes elsewhere).
    """
    from specify_cli.tasks.issue_matrix import ISSUE_MATRIX_JSON_FILENAME
    from specify_cli.tasks.issue_matrix_migration import issue_matrix_artifact_present

    if not issue_matrix_artifact_present(planning_dir):
        return
    json_path = planning_dir / ISSUE_MATRIX_JSON_FILENAME
    matrix_path = json_path if json_path.exists() else planning_dir / ISSUE_MATRIX_FILENAME
    try:
        from specify_cli.cli.commands.review import validate_issue_matrix

        result = validate_issue_matrix(matrix_path)
    except Exception as lint_exc:  # noqa: BLE001 — advisory lint never blocks finalize
        if not json_output:
            console.print(
                f"[yellow]Warning:[/yellow] could not lint {ISSUE_MATRIX_FILENAME}: {lint_exc}"
            )
        return
    if result.passed or json_output:
        return
    console.print(
        f"[yellow]Advisory:[/yellow] {ISSUE_MATRIX_FILENAME} has lint finding(s) "
        "(non-blocking — does not affect finalize):"
    )
    for diagnostic in result.diagnostics:
        console.print(f"  - {diagnostic['diagnostic_code']}: {diagnostic['message']}")


def _load_manifest(planning_dir: Path, *, json_output: bool) -> WpsManifest | None:
    """Phase: TIER 0 — load the wps.yaml manifest (or None)."""
    try:
        return load_wps_manifest(planning_dir)
    except typer.Exit:
        raise
    except Exception as exc:
        error_msg = f"wps.yaml is present but could not be loaded: {exc}"
        if json_output:
            _emit_json({"error": error_msg})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1) from exc


@dataclass
class _DependencyResolution:
    """Outcome of the 3-tier dependency + requirement-ref resolution phase."""

    wp_dependencies: dict[str, list[str]] = field(default_factory=dict)
    tasks_md_dependencies: dict[str, list[str]] = field(default_factory=dict)
    wp_requirement_refs: dict[str, list[str]] = field(default_factory=dict)


def _resolve_dependencies_and_refs(
    planning_dir: Path,
    wps_manifest: WpsManifest | None,
    wp_files: list[Path],
    expected_wp_ids: list[str],
    *,
    json_output: bool,
) -> _DependencyResolution:
    """Phase: TIER 1+ — 3-tier dependency + requirement-ref resolution.

    1. wps.yaml manifest when present
    2. explicit WP frontmatter dependencies (including explicit [])
    3. tasks.md text parsing as a legacy fallback only when frontmatter lacks
       the dependencies field entirely
    """
    tasks_md = planning_dir / TASKS_MD_FILENAME
    res = _DependencyResolution()

    if wps_manifest is not None:
        for entry in wps_manifest.work_packages:
            res.wp_dependencies[entry.id] = list(entry.dependencies) if dependencies_are_explicit(entry) else []

    # PRIMARY: WP frontmatter (map-requirements writes here directly)
    res.wp_requirement_refs = _parse_requirement_refs_from_wp_files(wp_files)

    if wps_manifest is None and tasks_md.exists():
        tasks_content = tasks_md.read_text(encoding="utf-8")
        from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md as _shared_parse_deps

        res.tasks_md_dependencies = _shared_parse_deps(tasks_content)
        _validate_tasks_md_coverage(res.tasks_md_dependencies, expected_wp_ids, json_output=json_output)

        # FALLBACK: tasks.md text (backward compat for pre-API projects)
        for wp_id, refs in _parse_requirement_refs_from_tasks_md(tasks_content).items():
            if refs and not res.wp_requirement_refs.get(wp_id):
                res.wp_requirement_refs[wp_id] = refs

        for wp_file in wp_files:
            wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
            if not wp_id_match:
                continue
            wp_id = wp_id_match.group(1)
            raw_content = wp_file.read_text(encoding="utf-8")
            wp_meta, _ = _read_wp_frontmatter(wp_file)
            if _raw_frontmatter_has_field(raw_content, "dependencies"):
                res.wp_dependencies[wp_id] = list(wp_meta.dependencies)
            else:
                res.wp_dependencies[wp_id] = list(res.tasks_md_dependencies.get(wp_id, []))
    return res


def _validate_occurrence_map_ready(planning_dir: Path, *, json_output: bool) -> None:
    """Phase: bulk-edit occurrence-map gate (reuses the implement-time check).

    Reuses ``ensure_occurrence_classification_ready`` unchanged (C-001, FR-002):
    for non-bulk-edit missions it self-conditions to a no-op; for bulk-edit
    missions it blocks finalize-tasks when ``occurrence_map.yaml`` is missing,
    schema-invalid, or inadmissible, so the failure surfaces here instead of
    at the first ``implement WP##`` (FR-001). Read-only — preserves the
    ``--validate-only`` zero-mutation invariant (C-004).
    """
    from specify_cli.bulk_edit.gate import (
        ensure_occurrence_classification_ready,
        finalize_tasks_gate_error_payload,
        render_gate_failure,
    )

    result = ensure_occurrence_classification_ready(planning_dir)
    if result.passed:
        return
    if json_output:
        _emit_json(finalize_tasks_gate_error_payload(result))
    else:
        render_gate_failure(result, console)
    raise typer.Exit(1)


def _validate_tasks_md_coverage(
    tasks_md_dependencies: dict[str, list[str]], expected_wp_ids: list[str], *, json_output: bool
) -> None:
    """Phase: verify every WP file matches a parsed tasks.md section."""
    missing_wp_sections = [wp_id for wp_id in expected_wp_ids if wp_id not in tasks_md_dependencies]
    extra_wp_sections = sorted(set(tasks_md_dependencies) - set(expected_wp_ids))
    if not (missing_wp_sections or extra_wp_sections):
        return
    error_msg = (
        "tasks.md work package coverage is incomplete. "
        "finalize-tasks could not match all WP files to parsed sections, "
        "so dependency lanes would be unreliable."
    )
    payload: dict[str, object] = {
        "error": error_msg,
        "missing_wp_sections": missing_wp_sections,
        "extra_wp_sections": extra_wp_sections,
        "hint": "Use supported section headers such as '## WP01', '## Work Package WP01', or '## Work Package 1 — Title'.",
    }
    if json_output:
        _emit_json(payload)
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
        if missing_wp_sections:
            console.print(f"  Missing WP sections: {', '.join(missing_wp_sections)}")
        if extra_wp_sections:
            console.print(f"  Extra WP sections: {', '.join(extra_wp_sections)}")
        console.print(f"  {payload['hint']}")
    raise typer.Exit(1)


def _validate_dependency_graph(wp_dependencies: dict[str, list[str]], *, json_output: bool) -> None:
    """Phase: detect cycles + invalid references in the dependency graph."""
    if not wp_dependencies:
        return
    cycles = detect_cycles(wp_dependencies)
    if cycles:
        error_msg = f"Circular dependencies detected: {cycles}"
        if json_output:
            _emit_json({"error": error_msg, "cycles": cycles})
        else:
            console.print("[red]Error:[/red] Circular dependencies detected:")
            for cycle in cycles:
                console.print(f"  {' → '.join(cycle)}")
        raise typer.Exit(1)

    for wp_id, deps in wp_dependencies.items():
        is_valid, errors = validate_dependencies(wp_id, deps, wp_dependencies)
        if not is_valid:
            error_msg = f"Invalid dependencies for {wp_id}: {errors}"
            if json_output:
                _emit_json({"error": error_msg, "wp_id": wp_id, "errors": errors})
            else:
                console.print(f"[red]Error:[/red] Invalid dependencies for {wp_id}:")
                for err in errors:
                    console.print(f"  - {err}")
            raise typer.Exit(1)


def _classify_wp_requirement_refs(
    wp_ids: list[str],
    wp_requirement_refs: dict[str, list[str]],
    all_spec_requirement_ids: set[str],
) -> tuple[list[str], dict[str, list[str]], set[str]]:
    """Bucket each WP's requirement refs into missing/unknown/mapped."""
    missing_requirement_refs_wps: list[str] = []
    unknown_requirement_refs: dict[str, list[str]] = {}
    mapped_requirement_ids: set[str] = set()

    for wp_id in sorted(set(wp_ids)):
        refs = wp_requirement_refs.get(wp_id, [])
        if not refs:
            missing_requirement_refs_wps.append(wp_id)
            continue
        unknown_refs = sorted(ref for ref in refs if ref not in all_spec_requirement_ids)
        if unknown_refs:
            unknown_requirement_refs[wp_id] = unknown_refs
        else:
            mapped_requirement_ids.update(refs)

    return missing_requirement_refs_wps, unknown_requirement_refs, mapped_requirement_ids


def _detect_bare_prose_requirement_ids_fail_loud(spec_content: str) -> list[str]:
    """WP06 (#3396) T031/IC-04: fail-loud bare-prose requirement-id detection
    for ``finalize-tasks``'s requirement-mapping gate.

    ``find_bare_prose_requirement_ids`` catches a requirement id (e.g.
    ``FR-001``) written as bare, unbulleted, unbolded prose in a
    "Functional Requirements"-named section -- a gap the existing
    missing/unknown/unmapped buckets cannot see, since a bare-prose id was
    never counted as mapped OR as a declared functional requirement in the
    first place (Story 1 AC1/AC2).

    Deliberately NOT routed through ``_find_undeclared_requirement_citations``
    / its swallow-and-log advisory contract (that helper's "never fail the
    gate" intent is the opposite of this one) -- this is a textually separate
    wrapper: any classification exception is caught ONCE and converted into
    an explicit, non-empty failure entry (mirroring WP05/T023's
    ``BareProseRequirementFacts.classification_error`` contract) so the
    caller's blocking check below can never be silently satisfied by a
    swallowed "0 uncounted" (NFR-002).
    """
    try:
        from specify_cli.requirement_mapping import find_bare_prose_requirement_ids

        candidates = find_bare_prose_requirement_ids(spec_content)
        return sorted({req_id for candidate in candidates for req_id in candidate.ids})
    except Exception as exc:  # noqa: BLE001 -- fail-loud: converted below into an explicit, non-empty failure, never swallowed
        return [
            f"<bare-prose-detection-error: {exc!r} -- treating as blocking, never silently clean (NFR-002)>"
        ]


def _emit_requirement_mapping_report(
    *,
    json_output: bool,
    missing_requirement_refs_wps: list[str],
    unknown_requirement_refs: dict[str, list[str]],
    unmapped_functional_requirements: list[str],
    bare_prose_requirement_ids: list[str],
    wp_dependencies: dict[str, list[str]],
    wp_requirement_refs: dict[str, list[str]],
) -> None:
    """Phase: emit the requirement-mapping validation failure (JSON or console)."""
    error_msg = "Requirement mapping validation failed"
    if json_output:
        payload = {
            "error": error_msg,
            "missing_requirement_refs_wps": missing_requirement_refs_wps,
            "unknown_requirement_refs": unknown_requirement_refs,
            "unmapped_functional_requirements": unmapped_functional_requirements,
            "bare_prose_requirement_ids": bare_prose_requirement_ids,
            "dependencies_parsed": wp_dependencies,
            "requirement_refs_parsed": wp_requirement_refs,
        }
        print(json.dumps(payload))
        return
    console.print(f"[red]Error:[/red] {error_msg}")
    if missing_requirement_refs_wps:
        console.print("[red]Missing requirement refs:[/red]")
        for wp_id in missing_requirement_refs_wps:
            console.print(f"  - {wp_id}")
    if unknown_requirement_refs:
        console.print("[red]Unknown requirement refs:[/red]")
        for wp_id, refs in unknown_requirement_refs.items():
            console.print(f"  - {wp_id}: {', '.join(refs)}")
    if unmapped_functional_requirements:
        console.print("[red]Unmapped functional requirements:[/red]")
        for req_id in unmapped_functional_requirements:
            console.print(f"  - {req_id}")
    if bare_prose_requirement_ids:
        console.print("[red]Bare-prose requirement id(s) found, uncounted:[/red]")
        for req_id in bare_prose_requirement_ids:
            console.print(f"  - {req_id}")


def _validate_requirement_mapping(
    wp_ids: list[str],
    wp_requirement_refs: dict[str, list[str]],
    all_spec_requirement_ids: set[str],
    functional_spec_requirement_ids: set[str],
    wp_dependencies: dict[str, list[str]],
    spec_content: str = "",
    *,
    json_output: bool,
) -> None:
    """Phase: validate every WP maps to known requirement ids (FR coverage).

    WP06 (#3396) T031: additionally surfaces ``bare_prose_requirement_ids`` --
    requirement ids written as bare, unbulleted, unbolded prose in spec.md's
    "Functional Requirements"-named section(s) -- as a distinct,
    separately-labeled failure alongside missing/unknown/unmapped. Never
    merged into ``unmapped_functional_requirements``: "declared but not yet
    mapped to a WP" and "never declared at all" are different remediation
    stories for an operator.
    """
    missing_requirement_refs_wps, unknown_requirement_refs, mapped_requirement_ids = (
        _classify_wp_requirement_refs(wp_ids, wp_requirement_refs, all_spec_requirement_ids)
    )

    unmapped_functional_requirements = sorted(functional_spec_requirement_ids - mapped_requirement_ids)
    bare_prose_requirement_ids = _detect_bare_prose_requirement_ids_fail_loud(spec_content)
    if not (
        missing_requirement_refs_wps
        or unknown_requirement_refs
        or unmapped_functional_requirements
        or bare_prose_requirement_ids
    ):
        return

    _emit_requirement_mapping_report(
        json_output=json_output,
        missing_requirement_refs_wps=missing_requirement_refs_wps,
        unknown_requirement_refs=unknown_requirement_refs,
        unmapped_functional_requirements=unmapped_functional_requirements,
        bare_prose_requirement_ids=bare_prose_requirement_ids,
        wp_dependencies=wp_dependencies,
        wp_requirement_refs=wp_requirement_refs,
    )
    raise typer.Exit(1)


def _detect_dependency_conflicts(
    wp_files: list[Path], wp_dependencies: dict[str, list[str]], *, json_output: bool
) -> None:
    """Phase: T004 disagree-loud — frontmatter vs parsed deps conflict gate."""
    existing_frontmatter: dict[str, WPMetadata] = {}
    for wp_file in wp_files:
        wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
        if not wp_id_match:
            continue
        wp_id = wp_id_match.group(1)
        try:
            wp_meta, _ = _read_wp_frontmatter(wp_file)
            existing_frontmatter[wp_id] = wp_meta
        except Exception:  # noqa: BLE001 — unreadable frontmatter degrades to a stub
            existing_frontmatter[wp_id] = WPMetadata(work_package_id=wp_id, title=wp_id)

    dep_conflict_errors: list[str] = []
    for wp_id_chk, parsed_deps in wp_dependencies.items():
        existing_meta = existing_frontmatter.get(wp_id_chk)
        existing_deps: list[str] = list(existing_meta.dependencies) if existing_meta else []
        if existing_deps and parsed_deps and set(existing_deps) != set(parsed_deps):
            dep_conflict_errors.append(
                f"{wp_id_chk}: frontmatter has {sorted(existing_deps)}, "
                f"tasks.md parsed {sorted(parsed_deps)}. "
                f"Resolve the disagreement in tasks.md or WP frontmatter before finalizing."
            )
    if dep_conflict_errors:
        error_msg = "Dependency disagreement detected:\n" + "\n".join(dep_conflict_errors)
        if json_output:
            _emit_json({"error": error_msg, "dependency_conflicts": dep_conflict_errors})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)


def _enforce_charter_activation_gate(wp_meta: WPMetadata, wp_id: str, repo_root: Path) -> None:
    """Phase: T044 / FR-017 charter activation gate (fires before any write)."""
    profile = wp_meta.agent_profile
    if not profile:
        return
    from charter.exceptions import CharterActivationError
    from charter.invocation_context import ProjectContext

    pack_ctx = ProjectContext.from_repo(repo_root).require_pack_context()
    activated_profiles = pack_ctx.activated_agent_profiles
    if activated_profiles is not None and profile not in activated_profiles:
        activated_list = ", ".join(sorted(activated_profiles)) or "(none)"
        resolution_cmd = f"spec-kitty charter activate agent-profile {profile}"
        console.print(
            f"[red]✗ Charter activation gate FAILED[/red]\n"
            f"  WP {wp_id} assigns profile: [bold]{profile}[/bold]\n"
            f"  '{profile}' is not in the activated agent-profile set.\n"
            f"  Currently activated: {activated_list}\n"
            f"  Resolution: {resolution_cmd}"
        )
        raise CharterActivationError(f"artifact={profile!r}, activated={activated_list!r}, resolution={resolution_cmd!r}")


@dataclass
class _BootstrapState:
    """Accumulated in-memory state from the 8-field bootstrap-mutation loop."""

    updated_count: int = 0
    work_packages: list[dict[str, object]] = field(default_factory=list)
    modified_wps: list[str] = field(default_factory=list)
    unchanged_wps: list[str] = field(default_factory=list)
    preserved_wps: list[str] = field(default_factory=list)
    would_modify: list[dict[str, object]] = field(default_factory=list)
    inmemory_frontmatter: dict[str, WPMetadata] = field(default_factory=dict)
    inmemory_bodies: dict[str, str] = field(default_factory=dict)
    pending_writes: list[tuple[Path, WPMetadata, str]] = field(default_factory=list)
    ownership_warnings: list[str] = field(default_factory=list)
    #: #3394 review F1 -- non-blocking signal, kept distinct from
    #: ``ownership_warnings`` so the JSON payload names the concern precisely
    #: (raw requirement tokens that matched no declared shape) rather than
    #: folding it into an unrelated bucket.
    requirement_extraction_warnings: list[str] = field(default_factory=list)


def _branch_strategy_text(target_branch: str) -> str:
    """Compute the long-form branch-strategy frontmatter value."""
    return (
        f"Planning artifacts for this mission were generated on {target_branch}. "
        f"During /spec-kitty.implement this WP may branch from a dependency-specific base, "
        f"but completed changes must merge back into {target_branch} unless the human explicitly redirects the landing branch."
    )


def _apply_bootstrap_fields(
    bld: _Builder,
    wp_meta: WPMetadata,
    *,
    deps: list[str],
    has_dependencies_line: bool,
    requirement_refs: list[str],
    has_requirement_refs_line: bool,
    target_branch: str,
) -> tuple[bool, dict[str, object]]:
    """Apply the 4 always-evaluated bootstrap fields, returning (changed, fields).

    Covers dependencies, planning_base_branch, merge_target_branch,
    branch_strategy, requirement_refs. Ownership fields are applied separately.
    """
    branch_strategy = _branch_strategy_text(target_branch)
    changed_fields: dict[str, object] = {}
    frontmatter_changed = False

    if not has_dependencies_line or list(wp_meta.dependencies) != deps:
        changed_fields["dependencies"] = deps
        bld.set(dependencies=deps)
        frontmatter_changed = True
    if wp_meta.planning_base_branch != target_branch:
        changed_fields["planning_base_branch"] = target_branch
        bld.set(planning_base_branch=target_branch)
        frontmatter_changed = True
    if wp_meta.merge_target_branch != target_branch:
        changed_fields["merge_target_branch"] = target_branch
        bld.set(merge_target_branch=target_branch)
        frontmatter_changed = True
    if wp_meta.branch_strategy != branch_strategy:
        changed_fields["branch_strategy"] = branch_strategy
        bld.set(branch_strategy=branch_strategy)
        frontmatter_changed = True
    if not has_requirement_refs_line or list(wp_meta.requirement_refs) != requirement_refs:
        changed_fields["requirement_refs"] = requirement_refs
        bld.set(requirement_refs=requirement_refs)
        frontmatter_changed = True
    return frontmatter_changed, changed_fields


def _apply_ownership_inference(
    bld: _Builder,
    wp_meta: WPMetadata,
    wp_raw_content: str,
    mission_slug: str,
    changed_fields: dict[str, object],
) -> tuple[bool, list[str]]:
    """Apply inferred ownership fields, returning (changed, infer_warnings).

    Respects an explicit ``owned_files: []`` (planning-artifact WPs).
    """
    owned_files_explicitly_empty = _owned_files_yaml_is_explicit_empty_list(wp_raw_content)
    need_execution_mode = not wp_meta.execution_mode
    need_owned_files = not wp_meta.owned_files and not owned_files_explicitly_empty
    if not (need_execution_mode or need_owned_files):
        return False, []

    ownership, infer_warnings = infer_ownership(wp_raw_content, mission_slug)
    changed = False
    if need_execution_mode:
        changed_fields["execution_mode"] = str(ownership.execution_mode)
        bld.set(execution_mode=str(ownership.execution_mode))
        changed = True
    if need_owned_files:
        changed_fields["owned_files"] = list(ownership.owned_files)
        bld.set(owned_files=list(ownership.owned_files))
        changed = True
    if not wp_meta.authoritative_surface:
        changed_fields["authoritative_surface"] = ownership.authoritative_surface
        bld.set(authoritative_surface=ownership.authoritative_surface)
        changed = True
    return changed, infer_warnings


def _run_bootstrap_loop(
    wp_files: list[Path],
    dep_resolution: _DependencyResolution,
    wps_manifest: WpsManifest | None,
    mission_slug: str,
    repo_root: Path,
    target_branch: str,
    concern_coverage_warnings: list[str],
    requirement_extraction_warnings: list[str],
    *,
    validate_only: bool,
    json_output: bool,
) -> _BootstrapState:
    """Phase: the 8-field bootstrap-mutation loop (INV-6 write-guarded).

    Infers all 8 fields in memory for every WP so downstream validation runs
    against post-bootstrap state; disk writes are deferred to
    ``pending_writes`` and only flushed when ``not validate_only``.
    """
    state = _BootstrapState(
        ownership_warnings=list(concern_coverage_warnings),
        requirement_extraction_warnings=list(requirement_extraction_warnings),
    )
    wp_dependencies = dep_resolution.wp_dependencies
    wp_requirement_refs = dep_resolution.wp_requirement_refs

    for wp_file in wp_files:
        wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
        if not wp_id_match:
            continue
        wp_id = wp_id_match.group(1)

        raw_content = wp_file.read_text(encoding="utf-8")
        has_dependencies_line = _raw_frontmatter_has_field(raw_content, "dependencies")
        has_requirement_refs_line = _raw_frontmatter_has_field(raw_content, "requirement_refs")
        try:
            wp_meta, body = _read_wp_frontmatter(wp_file)
        except Exception as e:  # noqa: BLE001 — surface but skip unreadable WPs
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Could not read {wp_file.name}: {e}")
            continue

        _enforce_charter_activation_gate(wp_meta, wp_id, repo_root)

        parsed_deps = wp_dependencies.get(wp_id, [])
        existing_deps = list(wp_meta.dependencies)
        if wps_manifest is None and not parsed_deps and existing_deps:
            deps = existing_deps
            state.preserved_wps.append(wp_id)
        else:
            deps = parsed_deps

        requirement_refs = wp_requirement_refs.get(wp_id, [])
        state.work_packages.append(
            {"id": wp_id, "title": wp_meta.display_title, "dependencies": deps, "requirement_refs": requirement_refs}
        )

        bld = wp_meta.builder()
        frontmatter_changed, changed_fields = _apply_bootstrap_fields(
            bld,
            wp_meta,
            deps=deps,
            has_dependencies_line=has_dependencies_line,
            requirement_refs=requirement_refs,
            has_requirement_refs_line=has_requirement_refs_line,
            target_branch=target_branch,
        )
        own_changed, infer_warnings = _apply_ownership_inference(
            bld, wp_meta, wp_file.read_text(encoding="utf-8"), mission_slug, changed_fields
        )
        state.ownership_warnings.extend(infer_warnings)
        frontmatter_changed = frontmatter_changed or own_changed

        updated_meta = bld.build() if frontmatter_changed else wp_meta
        state.inmemory_frontmatter[wp_id] = updated_meta
        state.inmemory_bodies[wp_id] = body

        if frontmatter_changed:
            if not validate_only:
                state.pending_writes.append((wp_file, updated_meta, body))
            else:
                state.would_modify.append({"wp_id": wp_id, "changes": changed_fields})
            state.updated_count += 1
            if wp_id not in state.preserved_wps:
                state.modified_wps.append(wp_id)
        elif wp_id not in state.preserved_wps:
            state.unchanged_wps.append(wp_id)
    return state


def _assert_no_write_in_validate_only(state: _BootstrapState, *, validate_only: bool) -> None:
    """INV-6 reinforcement: in validate-only mode the write queue MUST be empty.

    The bootstrap loop never appends to ``pending_writes`` under
    ``validate_only`` — this assertion makes the zero-mutation invariant
    explicit (#2056 WP07 / T029).
    """
    if validate_only:
        assert not state.pending_writes, "INV-6 violated: pending frontmatter writes in --validate-only mode"


def _validate_owned_files_not_in_mission_specs(
    inmemory_frontmatter: dict[str, WPMetadata], *, json_output: bool
) -> None:
    """Phase: reject owned_files paths under the mission-specs dir."""
    invalid_owned_files = _invalid_mission_specs_owned_files(inmemory_frontmatter)
    if not invalid_owned_files:
        return
    error_msg = "WP owned_files cannot include paths under kitty-specs/"
    payload: dict[str, object] = {
        "error": error_msg,
        "error_code": INVALID_WP_OWNED_FILES_KITTY_SPECS,
        "invalid_owned_files": invalid_owned_files,
    }
    if json_output:
        _emit_json(payload)
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
        for invalid in invalid_owned_files:
            console.print(f"  - {invalid['wp_id']}: {invalid['path']}")
    raise typer.Exit(1) from None


def _flush_frontmatter_writes(state: _BootstrapState, *, validate_only: bool) -> None:
    """Phase: write pending frontmatter to disk (gated on not validate_only)."""
    if validate_only:
        return
    for wp_file, updated_meta, body in state.pending_writes:
        write_frontmatter(wp_file, updated_meta.model_dump(exclude_none=True, mode="json"), body)


def _gather_validation_frontmatter(
    wp_files: list[Path], state: _BootstrapState
) -> tuple[dict[str, WPMetadata], dict[str, str]]:
    """Phase: prefer-in-memory-then-disk frontmatter acquisition (FR-031)."""
    wp_frontmatters: dict[str, WPMetadata] = {}
    wp_bodies: dict[str, str] = {}
    for wp_file in wp_files:
        wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
        if not wp_id_match:
            continue
        wp_id = wp_id_match.group(1)
        with contextlib.suppress(Exception):
            if wp_id in state.inmemory_frontmatter:
                fm_meta = state.inmemory_frontmatter[wp_id]
                wp_body = state.inmemory_bodies[wp_id]
            else:
                fm_meta, wp_body = _read_wp_frontmatter(wp_file)
            wp_bodies[wp_id] = wp_body
            wp_frontmatters[wp_id] = fm_meta
    return wp_frontmatters, wp_bodies


def _validate_ownership_manifests(
    wp_manifests: dict[str, OwnershipManifest],
    wp_frontmatters: dict[str, WPMetadata],
    repo_root: Path,
    state: _BootstrapState,
    *,
    json_output: bool,
) -> None:
    """Phase: ownership overlap + glob-match + audit-coverage validation."""
    if not wp_manifests:
        return
    wp_dependencies = {
        wp_id: list(fm.dependencies) for wp_id, fm in wp_frontmatters.items() if getattr(fm, "dependencies", None)
    }
    ownership_result = _validate_ownership_via_mission(wp_manifests, wp_dependencies)
    for warning in ownership_result.warnings:
        if not json_output:
            console.print(f"[yellow]Ownership warning:[/yellow] {warning}")
    if not ownership_result.passed:
        error_msg = "Ownership validation failed"
        if json_output:
            _emit_json({"error": error_msg, "ownership_errors": ownership_result.errors})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
            for err in ownership_result.errors:
                console.print(f"  - {err}")
        raise typer.Exit(1) from None

    create_intent = {wp_id: list(fm.create_intent) for wp_id, fm in wp_frontmatters.items() if fm.create_intent}
    glob_result = validate_glob_matches(wp_manifests, repo_root, create_intent=create_intent)
    _record_ownership_glob_diagnostics(glob_result, state, json_output=json_output)
    if not glob_result.passed:
        error_msg = "Ownership validation failed: literal-path owned_files entries match zero files. Fix the paths or add them to 'create_intent'."
        if json_output:
            _emit_json({"error": error_msg, "ownership_literal_path_errors": glob_result.errors})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1) from None

    codebase_wide = [list(m.owned_files) for m in wp_manifests.values() if m.is_codebase_wide]
    audit_warnings = validate_audit_coverage(codebase_wide, repo_root)
    state.ownership_warnings.extend(audit_warnings)
    if not json_output:
        for warning in audit_warnings:
            console.print(f"[yellow]Audit coverage warning:[/yellow] {warning}")


def _record_ownership_glob_diagnostics(
    glob_result: GlobValidationResult,
    state: _BootstrapState,
    *,
    json_output: bool,
) -> None:
    """Record glob diagnostics, rendering them only for human output."""
    state.ownership_warnings.extend(glob_result.warnings)
    if json_output:
        return
    stderr_console = err_console
    for note in glob_result.info:
        stderr_console.print(f"[blue]INFO:[/blue] {note}")
    for warning in glob_result.warnings:
        stderr_console.print(f"[yellow]WARNING:[/yellow] Ownership: {warning}")
    if not glob_result.passed:
        for err in glob_result.errors:
            stderr_console.print(f"[red]ERROR:[/red] Ownership: {err}")


def _emit_validate_only_report(
    planning_dir: Path,
    mission_slug: str,
    meta: dict[str, object] | None,
    state: _BootstrapState,
    wp_manifests: dict[str, OwnershipManifest],
    wp_dependencies: dict[str, list[str]],
    wp_bodies: dict[str, str],
    target_branch: str,
    *,
    json_output: bool,
) -> None:
    """Phase: emit the --validate-only report (INV-6: zero mutation).

    Runs bootstrap + lane computation in dry-run mode only.
    """
    bootstrap_result = _bootstrap_canonical_state_via_mission(planning_dir, mission_slug, dry_run=True)
    bootstrap_stats = {
        "total_wps": bootstrap_result.total_wps,
        "newly_seeded": bootstrap_result.newly_seeded,
        "already_initialized": bootstrap_result.already_initialized,
    }

    lanes_stats: dict[str, object] = {"computed": False}
    if wp_manifests and wp_dependencies:
        from specify_cli.lanes.compute import compute_lanes as _compute_lanes_validate

        raw_mission_id = meta.get("mission_id") if meta else None
        mission_id = raw_mission_id if isinstance(raw_mission_id, str) else None
        lanes_manifest_dry = _compute_lanes_validate(
            dependency_graph=wp_dependencies,
            ownership_manifests=wp_manifests,
            mission_slug=mission_slug,
            target_branch=target_branch,
            wp_bodies=wp_bodies,
            mission_id=mission_id,
        )
        cr_dry = lanes_manifest_dry.collapse_report
        lanes_stats = {
            "computed": True,
            "count": len(lanes_manifest_dry.lanes),
            "lane_ids": [lane.lane_id for lane in lanes_manifest_dry.lanes],
            "planning_artifact_wps": lanes_manifest_dry.planning_artifact_wps,
            "collapse_report": cr_dry.to_dict() if cr_dry else None,
        }

    if json_output:
        _emit_json(
            {
                "result": "validation_passed",
                "mission_slug": mission_slug,
                "wp_count": len(state.work_packages),
                "validate_only": True,
                "would_modify": state.would_modify,
                "would_preserve": state.preserved_wps,
                "unchanged": state.unchanged_wps,
                "updated_wp_count": state.updated_count,
                "ownership_warnings": state.ownership_warnings,
                "requirement_extraction_warnings": state.requirement_extraction_warnings,
                "validation": {"bootstrap_preview": bootstrap_stats, "lanes_preview": lanes_stats},
                "message": "All validations passed. Run without --validate-only to commit.",
            }
        )
        return
    console.print("[green]✓[/green] All validations passed (--validate-only mode, no commit)")
    console.print(f"  Mission: {mission_slug}")
    console.print(f"  WPs validated: {len(state.work_packages)}")
    console.print(
        f"  Would modify: {len(state.would_modify)} WP(s), preserve: {len(state.preserved_wps)}, unchanged: {len(state.unchanged_wps)}"
    )
    console.print(
        f"  Bootstrap: {bootstrap_result.newly_seeded} WPs would be seeded, {bootstrap_result.already_initialized} already initialized"
    )
    if lanes_stats.get("computed"):
        console.print(f"  Lanes: {lanes_stats['count']} lane(s) would be computed")
        cr_info = lanes_stats.get("collapse_report")
        collapse_report = cr_info if isinstance(cr_info, dict) else {}
        if collapse_report.get("independent_wps_collapsed", 0) > 0:
            console.print(
                f"[yellow]⚠[/yellow] {collapse_report['independent_wps_collapsed']} independent WP pair(s) "
                f"collapsed into same lane. Run with --json to see details."
            )


def _emit_local_canonical_events(
    planning_dir: Path,
    mission_slug: str,
    repo_root: Path,
    work_packages: list[dict[str, object]],
    *,
    json_output: bool,
) -> None:
    """Phase: persist local WPCreated + TasksCompleted before bootstrap seeding."""
    try:
        from specify_cli.status import TASKS_COMPLETED, emit_artifact_phase, emit_wp_created_local

        for wp in work_packages:
            wp_id = str(wp["id"])
            wp_path: str | None = None
            try:
                candidate = next(iter(sorted((planning_dir / "tasks").glob(f"{wp_id}*.md"))), None)
                if candidate is not None:
                    wp_path = str(candidate.relative_to(repo_root))
            except Exception:  # noqa: BLE001 — best-effort path resolution
                wp_path = None
            emit_wp_created_local(
                planning_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                wp_title=str(wp.get("title") or wp_id),
                wp_path=wp_path,
                depends_on=list(cast(list[str], wp.get("dependencies") or [])),
                actor=FINALIZE_TASKS_COMMAND_NAME,
            )

        tasks_artifact = planning_dir / TASKS_MD_FILENAME
        tasks_artifact_rel: str | None = None
        if tasks_artifact.exists():
            try:
                tasks_artifact_rel = str(tasks_artifact.relative_to(repo_root))
            except ValueError:
                tasks_artifact_rel = str(tasks_artifact)
        emit_artifact_phase(
            planning_dir,
            event_type=TASKS_COMPLETED,
            mission_slug=mission_slug,
            actor=FINALIZE_TASKS_COMMAND_NAME,
            artifact_path=tasks_artifact_rel or TASKS_MD_FILENAME,
            wp_count=len(work_packages),
        )
    except Exception as local_wp_exc:  # noqa: BLE001 — non-blocking emission
        if not json_output:
            console.print(f"[yellow]Warning:[/yellow] Local canonical WPCreated/TasksCompleted persistence failed: {local_wp_exc}")


def _capture_target_branch_tip(repo_root: Path, target_branch: str) -> str | None:
    """Capture ``target_branch``'s current tip SHA — the FR-009 recorded planning SHA.

    ADR ``2026-07-29-1`` (WP01, out-of-map producer edit — justified: T002 requires
    the recorded SHA to exist in ``lanes.json`` at finalize time, and this is the
    single write authority for that file; ``lanes/worktree_allocator.py`` alone
    cannot manufacture a value nobody ever persisted). By the time
    ``_compute_and_write_lanes`` runs, every earlier planning-artifact commit
    (spec-commit, setup-plan, tasks-commit) has already landed on ``target_branch``
    (ADR ``2026-06-24-1``: PRIMARY-partition kinds commit there for every topology),
    so this snapshot is, by construction, the recorded planning-artifact tip — never
    re-read live at lane-allocation time (the moving-tip trap the ADR closes).

    Returns ``None`` (never raises) on any git failure — a capture failure degrades
    gracefully to the allocator's pre-WP01 fallback rather than blocking finalize.
    """
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--verify", target_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _execution_has_begun(repo_root: Path, mission_slug: str) -> bool:
    """#3311 T014: read-only "has execution begun" signal for the finalize gate.

    MANDATORY reader recipe: resolve the coord-aware status read dir via
    :func:`resolve_status_surface_with_anchor` (the same authority
    ``implement.py`` uses, ``implement.py:1668-1680``), then read lanes
    read-only through :func:`get_all_wp_lanes`. **Never calls
    ``reducer.materialize()``** — that WRITES ``status.json`` to disk, which a
    "read" helper for a gate check must never do (C-005 / the
    read-does-not-write invariant this WP is guarded against).

    ``has_event_log`` gates first: an absent event log means the mission has
    never been finalized/bootstrapped, so execution categorically has not
    begun (a fresh mission, or the very first finalize run).

    Returns:
        ``True`` iff any WP's current lane is something other than
        ``planned`` (claimed, in_progress, for_review, ..., done, blocked,
        canceled). ``False`` when the event log is absent, empty, every
        seeded WP is still ``planned``, or the surface/event log cannot be
        read at all (degrades gracefully like this module's sibling
        ``_capture_target_branch_tip`` — a signal-computation helper must
        never crash the whole ``finalize-tasks`` command over an unreadable
        read-only surface; a corrupted event log is a pre-existing store
        problem `status doctor` surfaces separately, not something this gate
        should newly turn into a hard finalize failure).
    """
    from specify_cli.coordination.surface_resolver import (
        CoordinationBranchDeleted,
        StatusReadPathNotFound,
        resolve_status_surface_with_anchor,
    )
    from specify_cli.status import Lane, StoreError, get_all_wp_lanes, has_event_log

    try:
        read_dir = resolve_status_surface_with_anchor(repo_root, mission_slug).read_dir
    except (FileNotFoundError, ValueError, StatusReadPathNotFound, CoordinationBranchDeleted):
        # Surface resolution failed closed (no meta.json / malformed meta / an
        # unresolvable coord surface). No event log can be read from an
        # unresolvable surface either, so this degrades to the same
        # "not begun" answer ``has_event_log``'s absence produces below.
        return False
    if not has_event_log(read_dir):
        return False
    try:
        lanes = get_all_wp_lanes(read_dir)
    except StoreError:
        # Corrupted/malformed event log content. Degrade to "not begun"
        # rather than raise — see the docstring's graceful-degradation note.
        return False
    return any(lane != Lane.PLANNED for lane in lanes.values())


def _preserve_or_capture_planning_commit_sha(
    planning_dir: Path,
    repo_root: Path,
    mission_slug: str,
    target_branch: str,
    *,
    json_output: bool,
) -> str | None:
    """#3311 T015: gate the ``planning_commit_sha`` capture on execution-begun.

    ADR ``2026-07-29-1`` / FR-009 freezes the recorded planning-artifact SHA
    into the SAME write ``_compute_and_write_lanes`` performs — no second
    commit, no re-read at lane-allocation time. #3311: once execution has
    begun (:func:`_execution_has_begun` — any WP past ``planned``), a
    re-finalize triggered by an ownership-only amendment must PRESERVE that
    frozen SHA instead of silently re-capturing the CURRENT branch tip, which
    would clobber the established planning provenance a lane worktree may
    already carry a merge-base against. Before execution begins, the
    historical recompute + re-capture behavior is unchanged — every
    pre-execution re-finalize keeps regenerating freely (C-005).

    Preserve is the default resolution. Refuse (raise ``typer.Exit(1)`` before
    writing any bytes) only in the one case preservation cannot be done
    safely: execution has begun yet no on-disk ``lanes.json`` exists to read
    the recorded SHA from — an inconsistent state finalize should never
    reach, since bootstrapping the event log itself requires a prior
    successful finalize run that already wrote ``lanes.json``.
    """
    if not _execution_has_begun(repo_root, mission_slug):
        return _capture_target_branch_tip(repo_root, target_branch)

    from specify_cli.lanes.persistence import read_lanes_json

    existing: LanesManifest | None = read_lanes_json(planning_dir)
    if existing is None:
        error_msg = (
            f"Cannot re-finalize mission {mission_slug!r}: execution has begun "
            "(a WP is past 'planned') but no lanes.json exists on disk to "
            "preserve planning provenance from. Refusing to write a new "
            "lanes.json rather than guess a planning_commit_sha."
        )
        if json_output:
            _emit_json({"error": error_msg})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)
    # Suppression rationale (not a real type error): this module's
    # [[tool.mypy.overrides]] sets ``follow_imports = "skip"`` for all
    # ``specify_cli.*`` modules (to avoid walking the CLI bootstrap graph), so
    # a single-file mypy invocation loses ``LanesManifest``'s real field types
    # across that import boundary and reports a spurious no-any-return here —
    # the SAME pre-existing pattern already present at 6 other return sites in
    # this file (e.g. lines 136, 145). ``planning_commit_sha`` is genuinely
    # ``str | None`` (specify_cli/lanes/models.py); `mypy
    # src/specify_cli/lanes/models.py src/specify_cli/lanes/persistence.py` in
    # isolation reports zero issues.
    return existing.planning_commit_sha  # type: ignore[no-any-return]


def _compute_and_write_lanes(
    planning_dir: Path,
    repo_root: Path,
    mission_slug: str,
    wp_manifests: dict[str, OwnershipManifest],
    wp_dependencies: dict[str, list[str]],
    wp_frontmatters: dict[str, WPMetadata],
    wp_bodies: dict[str, str],
    meta: dict[str, object] | None,
    target_branch: str,
    *,
    json_output: bool,
) -> tuple[Path | None, LanesManifest | None]:
    """Phase: compute execution lanes + write lanes.json + risk report."""
    if not (wp_manifests and wp_dependencies):
        return None, None
    from specify_cli.lanes.compute import compute_lanes
    from specify_cli.lanes.persistence import write_lanes_json

    create_intent = {wp_id: list(fm.create_intent) for wp_id, fm in wp_frontmatters.items() if fm.create_intent}
    glob_result = validate_glob_matches(wp_manifests, repo_root, create_intent=create_intent)
    if not glob_result.passed:
        if not json_output:
            lane_stderr = err_console
            for err in glob_result.errors:
                lane_stderr.print(f"[red]ERROR:[/red] Lane-compute re-validation: {err}")
        error_msg = "Lane computation aborted: literal-path owned_files entries match zero files. Fix the paths before lanes.json is written."
        if json_output:
            _emit_json({"error": error_msg, "ownership_literal_path_errors": glob_result.errors})
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1) from None

    raw_mission_id = meta.get("mission_id") if meta else None
    mission_id = raw_mission_id if isinstance(raw_mission_id, str) else None
    lanes_manifest = compute_lanes(
        dependency_graph=wp_dependencies,
        ownership_manifests=wp_manifests,
        mission_slug=mission_slug,
        target_branch=target_branch,
        wp_bodies=wp_bodies,
        mission_id=mission_id,
    )
    # FR-009 / ADR 2026-07-29-1 (T002): freeze the recorded planning-artifact SHA
    # into the SAME write as the rest of lanes.json — no second commit, no
    # chicken-and-egg with this invocation's own finalize commit hash.
    # #3311 T015: once execution has begun, PRESERVE the previously-recorded
    # SHA instead of re-capturing the current branch tip (see
    # ``_preserve_or_capture_planning_commit_sha``).
    lanes_manifest.planning_commit_sha = _preserve_or_capture_planning_commit_sha(
        planning_dir, repo_root, mission_slug, target_branch, json_output=json_output
    )
    lanes_path = write_lanes_json(planning_dir, lanes_manifest)
    if not json_output:
        console.print(f"[green]✓[/green] Computed {len(lanes_manifest.lanes)} execution lane(s)")
        if lanes_manifest.collapse_report and lanes_manifest.collapse_report.independent_wps_collapsed > 0:
            console.print(
                f"[yellow]⚠[/yellow] {lanes_manifest.collapse_report.independent_wps_collapsed} "
                f"independent WP pair(s) collapsed into same lane. Run with --json to see details."
            )
    _report_parallelization_risk(repo_root, lanes_manifest, wp_bodies, json_output=json_output)
    return lanes_path, lanes_manifest


def _report_parallelization_risk(
    repo_root: Path, lanes_manifest: LanesManifest, wp_bodies: dict[str, str], *, json_output: bool
) -> None:
    """Phase: compute + (optionally block on) the parallelization risk report."""
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.risk_scorer import compute_risk_report

    policy = load_policy_config(repo_root)
    risk_report = compute_risk_report(lanes_manifest, wp_bodies=wp_bodies, policy=policy.risk)
    if risk_report.overall_score > 0 and not json_output:
        console.print(
            f"[yellow]⚠[/yellow] Parallelization risk: {risk_report.overall_score:.2f} (threshold: {risk_report.threshold:.2f})"
        )
        for pr in risk_report.lane_pair_risks:
            if pr.score > 0:
                console.print(f"  {pr.lane_a} ↔ {pr.lane_b}: {pr.score:.2f}")
                for d in pr.shared_parent_dirs[:3]:
                    console.print(f"    shared dir: {d}")
                for c in pr.import_coupling[:3]:
                    console.print(f"    coupling: {c}")
    if risk_report.exceeds_threshold and policy.risk.mode == "block":
        error_msg = (
            f"Parallelization risk {risk_report.overall_score:.2f} exceeds threshold "
            f"{risk_report.threshold:.2f}. Adjust the risk policy to proceed."
        )
        if json_output:
            _emit_json(
                {
                    "error": error_msg,
                    "risk_report": {"overall_score": risk_report.overall_score, "threshold": risk_report.threshold},
                }
            )
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)


def _resolve_acceptance_matrix_home(repo_root: Path, planning_dir: Path) -> Path:
    """Resolve the acceptance matrix's declared home dir (FR-010 / C8 single-home).

    Reuses the gate's canonical read-dir resolver so the scaffolder's single-home
    check consults exactly where the accept gate will read the matrix from. A
    ``DELETED`` coordination branch (fail-loud) has no readable home, so we fall
    back to the primary ``planning_dir`` — the scaffold is a convenience artifact
    and must never fail finalize.
    """
    from specify_cli.acceptance.gates_core import _acceptance_matrix_read_dir
    from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

    try:
        return _acceptance_matrix_read_dir(repo_root, planning_dir)
    except CoordinationBranchDeleted:
        return planning_dir


def _scaffold_acceptance_matrix_if_lane_based(
    planning_dir: Path,
    repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest | None,
    functional_spec_requirement_ids: set[str],
    *,
    validate_only: bool,
    json_output: bool,
) -> None:
    """Phase: Finding 6 — scaffold acceptance-matrix.json for lane-based missions."""
    if lanes_manifest is None or validate_only:
        return
    try:
        from specify_cli.acceptance.matrix import scaffold_acceptance_matrix
        from specify_cli.git.protection_policy import ProtectionPolicy

        # FR-010 / C8: resolve the matrix's DECLARED HOME through the same surface
        # resolver the accept gate reads from, so the scaffolder's idempotency check
        # sees an existing coord-homed matrix and never authors a divergent second
        # primary copy (#2882). A deleted coord branch (fail-loud) falls back to the
        # primary planning dir — the scaffold is a convenience artifact, never a gate.
        home_dir = _resolve_acceptance_matrix_home(repo_root, planning_dir)
        # write-surface-coherence WP08 (#2804 / #2404 T040/T041): thread
        # ``repo_root`` so the WRITE (not just the idempotency check) routes
        # through the coord-aware write-seam — never a stray PRIMARY husk
        # under coord topology, mirroring the sibling issue-matrix scaffold.
        acceptance_matrix_path = scaffold_acceptance_matrix(
            planning_dir,
            mission_slug,
            requirement_ids=sorted(functional_spec_requirement_ids),
            home_dir=home_dir,
            repo_root=repo_root,
            policy=ProtectionPolicy.resolve(repo_root),
        )
    except Exception as acc_matrix_exc:  # noqa: BLE001 — convenience artifact never blocks finalize
        if not json_output:
            console.print(f"[yellow]Warning:[/yellow] could not scaffold acceptance-matrix.json: {acc_matrix_exc}")
            console.print(
                f"[yellow]Hint:[/yellow] create it manually before acceptance:\n  spec-kitty agent mission finalize-tasks --mission {mission_slug}"
            )
        return
    if acceptance_matrix_path is not None and not json_output:
        try:
            rel: Path = acceptance_matrix_path.relative_to(repo_root)
        except ValueError:
            rel = acceptance_matrix_path
        console.print(f"[info] Scaffolded {rel}")


@dataclass
class _CommitOutcome:
    """Outcome of the finalize commit phase.

    ``commit_hash`` remains the historical single-value projection (the
    feature-branch commit for the common case) for backward compatibility.
    ``commit_hashes`` (#2549 facet B) additionally carries the FULL per-branch
    commit set the router actually issued — under coord topology this includes
    BOTH the feature-branch commit (primary-partition artifacts: tasks.md,
    lanes.json, tasks/WP*) AND the coordination-branch commit (placement-
    partition artifacts: status.events.jsonl, status.json, acceptance-
    matrix.json, issue-matrix.md), which ``commit_hash`` alone cannot express.
    """

    commit_created: bool = False
    commit_hash: str | None = None
    commit_hashes: list[dict[str, str]] = field(default_factory=list)
    files_committed: list[str] = field(default_factory=list)


def _commit_finalize_artifacts(
    planning_dir: Path,
    tasks_dir: Path,
    repo_root: Path,
    mission_slug: str,
    target_branch: str,
    lanes_path: Path | None,
    preexisting_primary_files: set[Path],
    *,
    json_output: bool,
    updated_count: int,
) -> _CommitOutcome:
    """Phase: commit finalize artifacts through commit_for_mission.

    Routes ``run_command`` through the ``mission`` module to preserve the
    ``mission.run_command`` patch seam. T027 / WP02: collapsed to the
    ``commit_for_mission`` entry point (TASKS_INDEX → primary target branch for
    every topology).

    meta.json (#3466 / SK3466-RR-001) needs no special-cased ``extra_paths``
    threading here: :func:`_collect_finalize_artifacts` already includes it as
    a candidate, so a ``--target-branch`` correction rides the same ``git
    status --porcelain`` gate below as every other tracked artifact. But
    unlike those other artifacts, meta.json can ALSO carry a pending edit
    finalize-tasks did not make (SK3466-REV-001, e.g. ``implement
    --no-auto-commit``'s ``vcs``/``vcs_locked_at`` write) — so, before
    computing the commit set, a meta.json candidate is additionally checked
    with :func:`_meta_json_delta_is_finalize_attributable` and dropped
    entirely when the pending delta is not confined to the fields
    finalize-tasks itself owns.
    """
    from specify_cli.cli.commands.agent import mission as _mission

    outcome = _CommitOutcome()
    try:
        files_to_commit = _collect_finalize_artifacts(planning_dir, tasks_dir, lanes_path=lanes_path)
        meta_json_path = planning_dir / META_JSON_FILENAME
        if meta_json_path in files_to_commit and not _meta_json_delta_is_finalize_attributable(
            meta_json_path, repo_root
        ):
            files_to_commit = [path for path in files_to_commit if path != meta_json_path]
        files_to_commit_rel = [str(path.relative_to(repo_root)) for path in files_to_commit]
        # partition-authority-residuals-01M021K9 WP06 (#2937 / FR-009): report the
        # TRUE committed set — ``files_committed`` is populated ONLY once the router
        # actually lands a commit (below), never up front. Reporting the full
        # candidate set here regardless of outcome misled automated callers on the
        # no-change / "unchanged" paths (nothing was committed, yet every candidate
        # was named as committed).

        has_relevant_changes = False
        if files_to_commit_rel:
            _rc, status_out, _status_err = _mission.run_command(
                ["git", "status", "--porcelain", "--", *files_to_commit_rel],
                check_return=True,
                capture=True,
                cwd=repo_root,
            )
            has_relevant_changes = bool(status_out.strip())

        if not has_relevant_changes:
            if not json_output:
                console.print("[dim]Tasks unchanged, no commit needed[/dim]")
            return outcome

        from specify_cli.coordination.commit_router import commit_for_mission
        from specify_cli.git.protection_policy import ProtectionPolicy

        tasks_policy = ProtectionPolicy.resolve(repo_root)
        primary_created = frozenset(path for path in files_to_commit if path not in preexisting_primary_files)
        router_result = commit_for_mission(
            repo_root=repo_root,
            mission_slug=mission_slug,
            files=tuple(files_to_commit),
            message=f"Add tasks for feature {mission_slug}",
            policy=tasks_policy,
            kind=MissionArtifactKind.TASKS_INDEX,
            primary_paths_created_this_invocation=primary_created,
            target_branch=target_branch,
        )

        if router_result.status == "committed":
            outcome.commit_hash = router_result.commit_hash
            outcome.commit_created = True
            # WP06 (#2937 / FR-009): only now is the committed set real.
            outcome.files_committed = list(files_to_commit_rel)
            outcome.commit_hashes = [
                {"branch": ref, "hash": commit_hash} for ref, commit_hash in router_result.commit_hashes
            ]
            if not json_output:
                console.print(f"[green]✓[/green] Tasks committed to {router_result.placement_ref}")
                if outcome.commit_hash:
                    console.print(f"[dim]Commit: {outcome.commit_hash[:7]}[/dim]")
                console.print(f"[dim]Updated {updated_count} WP files with dependencies[/dim]")
        elif router_result.status == "unchanged":
            outcome.commit_created = False
            if not json_output:
                console.print("[dim]Tasks unchanged, no commit needed[/dim]")
        else:
            error_output = router_result.diagnostic or "Failed to commit tasks updates"
            if json_output:
                print(json.dumps({"error": f"Git commit failed: {error_output}"}))
            else:
                console.print(f"[red]Error:[/red] Git commit failed: {error_output}")
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    return outcome


def _emit_success_report(
    tasks_dir: Path,
    state: _BootstrapState,
    commit_outcome: _CommitOutcome,
    dep_resolution: _DependencyResolution,
    bootstrap_result: BootstrapResult,
    lanes_manifest: LanesManifest | None,
    *,
    target_branch_override: str | None = None,
    target_branch_persist: TargetBranchPersistOutcome | None = None,
    meta_committed_this_run: bool = False,
) -> None:
    """Phase: emit the terminal JSON success report.

    ``target_branch_override`` / ``target_branch_persist`` (SK3466-R-003):
    a ``--target-branch`` override durably rewrites meta.json's canonical
    merge destination, but the payload previously carried no signal that a
    mutation occurred or what the previous value was — the only observable
    trace for a ``--json`` caller was "meta.json" appearing in
    ``files_committed``, indistinguishable from any other artifact commit.
    ``target_branch_override`` is only non-``None`` when the flag was
    actually supplied this run.

    ``meta_committed_this_run`` (SK3466-REV2-002): ``persist.persisted=True``
    only means meta.json was rewritten to disk this call — it says nothing
    about whether that write survived ``_commit_finalize_artifacts``'s
    attribution check (``_meta_json_delta_is_finalize_attributable`` excludes
    meta.json entirely when a foreign field is pending alongside our
    ``target_branch`` write). A ``--json`` caller checking ``persisted``
    alone — its documented use — could not tell "durably committed" from
    "written but left dangling because it was excluded from this commit".
    Computed once by ``_run_commit_pipeline`` from ``commit_outcome.
    files_committed`` (the same value that already gates the revert-safety
    marker for SK3466-REV2-001) and passed through here rather than
    re-derived, so both corrections share one source of truth.
    """
    persist = target_branch_persist or TargetBranchPersistOutcome(persisted=False)
    _emit_json(
        {
            "result": "success",
            "wp_count": len(state.work_packages),
            "updated_wp_count": state.updated_count,
            "modified_wps": state.modified_wps,
            "unchanged_wps": state.unchanged_wps,
            "preserved_wps": state.preserved_wps,
            "tasks_dir": str(tasks_dir),
            "commit_created": commit_outcome.commit_created,
            "commit_hash": commit_outcome.commit_hash,
            "commit_hashes": commit_outcome.commit_hashes,
            "files_committed": commit_outcome.files_committed,
            "dependencies_parsed": dep_resolution.wp_dependencies,
            "requirement_refs_parsed": dep_resolution.wp_requirement_refs,
            "bootstrap": {
                "total_wps": bootstrap_result.total_wps,
                "newly_seeded": bootstrap_result.newly_seeded,
                "already_initialized": bootstrap_result.already_initialized,
            },
            "lanes": {
                "computed": lanes_manifest is not None,
                "count": len(lanes_manifest.lanes) if lanes_manifest else 0,
                "lane_ids": [lane.lane_id for lane in lanes_manifest.lanes] if lanes_manifest else [],
                "planning_artifact_wps": lanes_manifest.planning_artifact_wps if lanes_manifest else [],
                "collapse_report": (
                    lanes_manifest.collapse_report.to_dict()
                    if lanes_manifest and lanes_manifest.collapse_report
                    else None
                ),
            },
            "ownership_warnings": state.ownership_warnings,
            "requirement_extraction_warnings": state.requirement_extraction_warnings,
            "target_branch_override": {
                "requested": target_branch_override,
                "persisted": persist.persisted,
                # SK3466-REV2-002: distinct from ``persisted`` -- ``True``
                # only when meta.json's delta actually rode this commit.
                # ``persisted and not committed`` means the override is
                # written to disk but excluded from this run's commit and
                # left dangling in the working tree (mixed with a foreign
                # meta.json field also pending).
                "committed": persist.persisted and meta_committed_this_run,
                "previous_value": persist.previous_value,
                "persist_error": persist.persist_error,
            },
        }
    )


def _warn_missing_meta(
    planning_dir: Path, meta: dict[str, object] | None, *, json_output: bool
) -> None:
    """Phase: warn (non-blocking) when meta.json is missing/malformed."""
    if meta is not None or json_output:
        return
    if (planning_dir / META_JSON_FILENAME).exists():
        console.print(
            "[yellow]Warning:[/yellow] Failed to read meta.json for event "
            "emission (missing or malformed); skipping MissionCreated emission"
        )
    else:
        console.print("[yellow]Warning:[/yellow] meta.json missing; skipping MissionCreated emission")


def _emit_tasks_started(
    planning_dir: Path, mission_slug: str, state: _BootstrapState, *, validate_only: bool
) -> None:
    """Phase: local canonical TasksStarted (idempotent; skipped in validate-only)."""
    if validate_only:
        return
    try:
        from specify_cli.status import TASKS_STARTED, emit_artifact_phase

        emit_artifact_phase(
            planning_dir,
            event_type=TASKS_STARTED,
            mission_slug=mission_slug,
            actor=FINALIZE_TASKS_COMMAND_NAME,
            wp_count=len(state.work_packages),
        )
    except Exception as tasks_started_exc:  # noqa: BLE001 — non-blocking
        logger.debug("TasksStarted emission skipped: %s", tasks_started_exc)


def _run_commit_pipeline(
    planning_dir: Path,
    tasks_dir: Path,
    repo_root: Path,
    mission_slug: str,
    target_branch: str,
    state: _BootstrapState,
    dep_resolution: _DependencyResolution,
    wp_manifests: dict[str, OwnershipManifest],
    wp_frontmatters: dict[str, WPMetadata],
    wp_bodies: dict[str, str],
    meta: dict[str, object] | None,
    functional_spec_requirement_ids: set[str],
    preexisting_primary_files: set[Path],
    *,
    validate_only: bool,
    json_output: bool,
    target_branch_override: str | None = None,
    target_branch_persist: TargetBranchPersistOutcome | None = None,
    meta_commit_progress: _MetaBranchOverrideProgress | None = None,
) -> None:
    """Phase: the post-validate-only commit pipeline.

    Seeds canonical state, computes lanes, scaffolds acceptance-matrix, syncs the
    dossier, commits artifacts, emits SaaS WPCreated, and reports success. Only
    ever reached when ``not validate_only`` (INV-6).

    A ``--target-branch`` override that just rewrote meta.json
    (:func:`_persist_target_branch_override`) — or one dangling from a prior
    crashed run (SK3466-RR-001) — is folded into the SAME finalize commit as
    tasks.md / WP files below, because :func:`_collect_finalize_artifacts`
    treats meta.json as a commit candidate and :func:`_commit_finalize_
    artifacts` attributes any pending delta by field
    (SK3466-REV-001: a delta confined to ``target_branch`` rides this commit
    regardless of which run produced it; a delta ALSO touching a foreign
    field, e.g. a concurrent ``implement --no-auto-commit`` write, is
    excluded from this commit entirely). Nothing in this phase needs to know
    whether THIS invocation's own persist call fired.

    ``target_branch_override`` / ``target_branch_persist`` are threaded
    through only to ``_emit_success_report`` (SK3466-R-003 JSON traceability)
    and do not affect this phase's own behavior.

    ``meta_commit_progress`` (SK3466-R-001, corrected SK3466-REV2-001): once
    ``_commit_finalize_artifacts`` below returns, flipped to
    ``committed=True`` only when meta.json's own relative path actually
    appears in ``commit_outcome.files_committed`` -- NOT unconditionally.
    ``_meta_json_delta_is_finalize_attributable`` can exclude meta.json from
    this commit entirely (a foreign field, e.g. ``implement
    --no-auto-commit``'s ``vcs``/``vcs_locked_at`` write, is pending
    alongside our ``target_branch`` write); an unconditional flip in that
    case fooled ``_revert_unpersisted_target_branch_override``'s ``not
    meta_commit_progress.committed`` guard into skipping a real revert when a
    LATER step in this function (SaaS emission, the JSON report) goes on to
    raise, leaving a permanently dangling meta.json write. Reading
    ``commit_outcome.files_committed`` -- a value ``_commit_finalize_
    artifacts`` already computes -- needs no new state to close this.
    """
    _emit_local_canonical_events(
        planning_dir, mission_slug, repo_root, state.work_packages, json_output=json_output
    )

    bootstrap_result = _bootstrap_canonical_state_via_mission(
        planning_dir, mission_slug, dry_run=False, capability=GuardCapability.STANDARD
    )
    if not json_output and bootstrap_result.newly_seeded:
        console.print(f"[green]✓[/green] Bootstrapped canonical status: {bootstrap_result.newly_seeded} WPs seeded")

    lanes_path, lanes_manifest = _compute_and_write_lanes(
        planning_dir,
        repo_root,
        mission_slug,
        wp_manifests,
        dep_resolution.wp_dependencies,
        wp_frontmatters,
        wp_bodies,
        meta,
        target_branch,
        json_output=json_output,
    )

    _scaffold_acceptance_matrix_if_lane_based(
        planning_dir,
        repo_root,
        mission_slug,
        lanes_manifest,
        functional_spec_requirement_ids,
        validate_only=validate_only,
        json_output=json_output,
    )

    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        trigger_feature_dossier_sync_if_enabled(planning_dir, mission_slug, repo_root)

    commit_outcome = _commit_finalize_artifacts(
        planning_dir,
        tasks_dir,
        repo_root,
        mission_slug,
        target_branch,
        lanes_path,
        preexisting_primary_files,
        json_output=json_output,
        updated_count=state.updated_count,
    )
    # SK3466-REV2-001/002: whether meta.json's own delta actually rode this
    # commit -- NOT "the phase returned without raising". Computed once here
    # (the exact same relative-path form _commit_finalize_artifacts used to
    # build ``commit_outcome.files_committed``) and reused below for both the
    # revert-safety marker and the terminal report, so the two call sites
    # this Op's round 3 left behind learn about the same third outcome state
    # from a single source rather than two independent guesses.
    meta_json_rel = str((planning_dir / META_JSON_FILENAME).relative_to(repo_root))
    meta_committed_this_run = meta_json_rel in commit_outcome.files_committed
    if meta_commit_progress is not None:
        # SK3466-R-001, corrected SK3466-REV2-001: only durable once
        # meta.json's delta actually folded into this commit -- an
        # unconditional flip here fooled the revert guard below
        # (``not meta_commit_progress.committed``) into skipping a real
        # revert when ``_meta_json_delta_is_finalize_attributable`` excluded
        # meta.json for being mixed with a foreign field.
        meta_commit_progress.committed = meta_committed_this_run
    if (
        not json_output
        and target_branch_persist is not None
        and target_branch_persist.persisted
        and not meta_committed_this_run
    ):
        # SK3466-REV2-002: the "persisted to meta.json" note already printed
        # by ``_persist_target_branch_override`` ran before this commit's
        # attribution decision was known, so a mixed-delta exclusion left no
        # console trace distinguishing "committed" from "written but still
        # dangling". This corrective note fires only in that gap.
        console.print(
            "[yellow]Note:[/yellow] the --target-branch override written to meta.json "
            "was excluded from this commit (a foreign meta.json edit is pending "
            "alongside it) and remains an uncommitted working-tree change."
        )

    if json_output:
        _emit_success_report(
            tasks_dir,
            state,
            commit_outcome,
            dep_resolution,
            bootstrap_result,
            lanes_manifest,
            target_branch_override=target_branch_override,
            target_branch_persist=target_branch_persist,
            meta_committed_this_run=meta_committed_this_run,
        )


@dataclass
class _MetaBranchOverrideProgress:
    """Mutable revert-safety marker for a persisted ``--target-branch`` write (SK3466-R-001).

    Mutated in place from inside ``_run_commit_pipeline`` (not communicated
    via a return value) so its state survives even when a LATER, unrelated
    phase raises AFTER the meta.json write has already been folded into the
    finalize commit. A return value alone cannot do this: if
    ``_emit_success_report`` raised after
    ``_commit_finalize_artifacts`` had already committed successfully, but
    before ``_run_commit_pipeline`` returned, the caller would never observe
    an "already committed" return and would incorrectly revert meta.json —
    reintroducing a fresh, uncommitted diff on top of an already-green
    commit. Mutating this shared object instead means the caller's
    ``except`` handler still sees ``committed=True`` no matter where past
    that point the exception originated.
    """

    committed: bool = False


def _revert_unpersisted_target_branch_override(
    meta_path: Path | None,
    original_text: str | None,
    *,
    meta_json_persisted: bool,
    meta_commit_progress: _MetaBranchOverrideProgress,
) -> str | None:
    """Undo an applied-but-uncommitted ``--target-branch`` meta.json write (SK3466-R-001).

    ``_persist_target_branch_override`` writes meta.json to disk as soon as
    the override differs from the on-disk value — well before roughly eight
    downstream validation gates (missing ``tasks_dir``, dependency-cycle,
    requirement-mapping, ownership, ...) that can still raise
    ``typer.Exit(1)``. Without this guard, a run that failed one of those
    gates left meta.json mutated and uncommitted in the working tree,
    contradicting the invariant :func:`_collect_finalize_artifacts` exists to
    uphold: a persisted override lands in the SAME commit as tasks.md / the
    WP files, or not at all — never as a dangling, uncommitted edit.

    A no-op unless the write actually happened this run (``meta_json_
    persisted``) AND it was never folded into the finalize commit
    (``not meta_commit_progress.committed``) AND the pre-write content was
    captured.

    Returns:
        ``None`` on success or on a no-op. A non-``None`` string
        (SK3466-RR-003) describes the revert WRITE's OWN failure — e.g. a
        permission change, a full disk, or the same TOCTOU class this
        function's caller already reasons about (meta.json deleted/replaced
        between the persist and this revert attempt). Without this, a
        SECOND, unrelated exception raised from inside ``mission_metadata.
        restore_meta_text``'s own write would propagate out of one of
        ``finalize_tasks``'s ``except`` handlers uncaught — replacing the
        graceful ``{"error": str(e)}``
        JSON-output contract the rest of this fix guarantees with an
        unhandled Python traceback for a ``--json`` caller. Callers report
        the ORIGINAL exception regardless; this is a best-effort ADDITIONAL
        note.
    """
    if not (
        meta_json_persisted
        and not meta_commit_progress.committed
        and original_text is not None
        and meta_path is not None
    ):
        return None
    from specify_cli.mission_metadata import restore_meta_text

    try:
        # Routed through mission_metadata.py's byte-exact rollback primitive
        # (T025 single-writer gate) rather than a direct ``meta_path.
        # write_text`` here -- this module must not become a second writer of
        # meta.json, the very defect class this fix's history (SK3466-R-001)
        # exists to close. ``restore_meta_text`` guarantees the SAME
        # byte-exact restore this call site always relied on; see its
        # docstring for why ``write_meta`` (re-serialize from a parsed dict)
        # cannot make that guarantee.
        restore_meta_text(meta_path.parent, original_text)
    except OSError as revert_exc:
        logger.warning(
            "SK3466-RR-003: failed to revert unpersisted target_branch override in %s: %s",
            meta_path,
            revert_exc,
        )
        return str(revert_exc)
    return None


def _report_target_branch_revert_failure(revert_error: str | None, *, json_output: bool) -> None:
    """Phase: best-effort surfacing of a failed meta.json revert (SK3466-RR-003).

    A no-op unless the revert write itself failed. Used from ``finalize_
    tasks``'s ``except typer.Exit`` handler, where the ORIGINAL error already
    emitted its own diagnostic before raising — this is purely an additional
    note, never a substitute for it.
    """
    if not revert_error:
        return
    if json_output:
        _emit_json({"warning": "target_branch_override_revert_failed", "detail": revert_error})
    else:
        console.print(
            "[yellow]Warning:[/yellow] failed to revert unpersisted "
            f"--target-branch override in meta.json: {revert_error}"
        )


def _emit_finalize_error_with_revert_note(
    error: Exception, revert_error: str | None, *, json_output: bool
) -> None:
    """Phase: emit finalize_tasks's terminal error, folding in a revert-failure note (SK3466-RR-003).

    Preserves the existing ``{"error": str(e)}`` / ``[red]Error:[/red]``
    diagnostic contract for the ORIGINAL exception unconditionally; the
    meta.json-revert failure (if any) is added as a SECOND, clearly-labelled
    field/line rather than replacing it.
    """
    if json_output:
        error_payload: dict[str, object] = {"error": str(error)}
        if revert_error:
            error_payload["target_branch_override_revert_error"] = revert_error
        _emit_json(error_payload)
        return
    console.print(f"[red]Error:[/red] {error}")
    if revert_error:
        console.print(
            "[yellow]Warning:[/yellow] failed to revert unpersisted "
            f"--target-branch override in meta.json: {revert_error}"
        )


def finalize_tasks(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    validate_only: Annotated[
        bool, typer.Option("--validate-only", help="Run all validations without committing. Reports issues that would block finalization.")
    ] = False,
    target_branch_override: Annotated[
        str | None,
        typer.Option(
            "--target-branch",
            help=(
                "Override the canonical merge target branch read from meta.json. "
                "Use this for legacy missions created before WP07 persisted "
                "target_branch in meta.json, or to correct a mission whose "
                "target_branch is stale (FR-012 escape hatch). The override is "
                "persisted into the primary meta.json as part of this run, so "
                "every other target_branch consumer converges on it too (#3466)."
            ),
        ),
    ] = None,
) -> None:
    """Parse dependencies from tasks.md and update WP frontmatter, then commit to target branch.

    This command is designed to be called after LLM generates WP files via /spec-kitty.tasks.
    It post-processes the generated files to add dependency information and commits everything.

    Use --validate-only to check for issues (missing requirement mappings, ownership overlaps,
    dependency cycles) without making any changes or committing.

    Bootstrap Mutation Surface (FR-003 / SC-002)
    =============================================
    The 8 frontmatter fields below may be written or overwritten by this command.
    When ``--validate-only`` is active, ALL writes are skipped — the
    ``frontmatter_changed and not validate_only`` guard ensures zero bytes of
    mutation on disk (INV-6). In validate-only mode the bootstrap loop still
    infers all 8 fields in memory so downstream validation operates against the
    post-bootstrap state — not the stale on-disk frontmatter.

    See also: ``tasks.py:finalize-tasks()`` which writes ``dependencies`` via
    ``build_document() + write_text()`` — guarded the same way (T002).

    Examples:
        spec-kitty agent mission finalize-tasks --mission 020-my-feature --json
        spec-kitty agent mission finalize-tasks --mission 020-my-feature --validate-only --json
    """
    # SK3466-R-001: tracked across the whole try body (not just the persist
    # call site) so the except blocks below can undo an already-applied
    # meta.json write if any later validation gate bails with typer.Exit
    # before the finalize commit actually lands it. Declared before ``try``
    # so a failure BEFORE the persist call (nothing written yet) still leaves
    # these names bound.
    meta_json_persisted = False
    meta_commit_progress = _MetaBranchOverrideProgress()
    meta_path_for_revert: Path | None = None
    meta_original_text: str | None = None
    try:
        repo_root = _resolve_repo_root(json_output)
        mission_slug = _resolve_mission_slug(repo_root, feature, json_output=json_output)

        from mission_runtime import placement_seam

        # WP05/FR-005: _resolve_mission_slug may return a raw operator-supplied
        # handle (the raw_handle fast-path in _resolve_mission_dir_name_primary_anchored
        # at line 258). The seam folds every handle form to the composed primary
        # dir internally (WP08 T036: the caller no longer pre-canonicalizes with
        # _canonicalize_primary_read_handle — redundant with that internal fold).
        # read-side-seam-primary-primitive-closure-01KYKMMT WP06 (T029): routed off
        # the retiring ``primary_feature_dir_for_mission`` wrapper onto the seam
        # directly — WORK_PACKAGE_TASK, since this finalize-tasks flow reads/writes
        # the ``tasks/`` WP files, ``wps.yaml``, and ``tasks.md`` under this dir.
        primary_dir = placement_seam(repo_root, mission_slug).read_dir(
            MissionArtifactKind.WORK_PACKAGE_TASK
        )
        planning_dir = primary_dir

        # Bulk edit occurrence-map gate (FR-001/002/003/004): fail-fast, before
        # the (potentially expensive) requirement-mapping/dependency-graph
        # validators, and before the `if validate_only:` split so it fires in
        # both normal and --validate-only modes (C-005/IC-01).
        _validate_occurrence_map_ready(planning_dir, json_output=json_output)

        target_branch = _resolve_target_branch(
            repo_root, primary_dir, target_branch_override=target_branch_override, json_output=json_output
        )
        if not json_output:
            console.print(f"[bold cyan]Branch:[/bold cyan] {target_branch} (target for this mission)")
        target_branch_persist = TargetBranchPersistOutcome(persisted=False)
        if not validate_only:
            meta_path_for_revert = primary_dir / META_JSON_FILENAME
            meta_original_text = (
                meta_path_for_revert.read_text(encoding="utf-8") if meta_path_for_revert.exists() else None
            )
            target_branch_persist = _persist_target_branch_override(
                primary_dir,
                target_branch,
                target_branch_override=target_branch_override,
                json_output=json_output,
            )
        meta_json_persisted = target_branch_persist.persisted

        tasks_dir = planning_dir / "tasks"
        if not tasks_dir.exists():
            error_msg = f"Tasks directory not found: {tasks_dir}"
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
        wp_files = list(tasks_dir.glob("WP*.md"))
        expected_wp_ids = _extract_wp_ids_from_task_files(wp_files)

        (
            all_spec_requirement_ids,
            functional_spec_requirement_ids,
            requirement_extraction_warnings,
            spec_content,
        ) = _read_spec_requirement_ids(planning_dir, json_output=json_output)

        # Snapshot pre-existing primary-side files BEFORE any finalize writer runs
        # (WP02 / FR-006 / A-r1 — residue cleanup scoping, research R6).
        preexisting_primary_files: set[Path] = {p for p in planning_dir.rglob("*") if p.is_file()}

        _scaffold_issue_matrix_if_present(
            planning_dir,
            repo_root,
            mission_slug,
            target_branch=target_branch,
            validate_only=validate_only,
            json_output=json_output,
        )
        _advisory_issue_matrix_lint(planning_dir, json_output=json_output)

        wps_manifest = _load_manifest(planning_dir, json_output=json_output)
        concern_coverage_warnings = check_concern_refs_coverage(wps_manifest) if wps_manifest is not None else []

        dep_resolution = _resolve_dependencies_and_refs(
            planning_dir, wps_manifest, wp_files, expected_wp_ids, json_output=json_output
        )
        _validate_dependency_graph(dep_resolution.wp_dependencies, json_output=json_output)

        wp_files = list(tasks_dir.glob("WP*.md"))
        wp_ids = _extract_wp_ids_from_task_files(wp_files)
        _validate_requirement_mapping(
            wp_ids,
            dep_resolution.wp_requirement_refs,
            all_spec_requirement_ids,
            functional_spec_requirement_ids,
            dep_resolution.wp_dependencies,
            spec_content,
            json_output=json_output,
        )

        _detect_dependency_conflicts(wp_files, dep_resolution.wp_dependencies, json_output=json_output)

        if concern_coverage_warnings and not json_output:
            for warning in concern_coverage_warnings:
                console.print(f"[yellow]Warning:[/yellow] {warning}")

        if requirement_extraction_warnings and not json_output:
            for warning in requirement_extraction_warnings:
                console.print(f"[yellow]Warning:[/yellow] {warning}")

        state = _run_bootstrap_loop(
            wp_files,
            dep_resolution,
            wps_manifest,
            mission_slug,
            repo_root,
            target_branch,
            concern_coverage_warnings,
            requirement_extraction_warnings,
            validate_only=validate_only,
            json_output=json_output,
        )
        _assert_no_write_in_validate_only(state, validate_only=validate_only)

        _validate_owned_files_not_in_mission_specs(state.inmemory_frontmatter, json_output=json_output)
        _flush_frontmatter_writes(state, validate_only=validate_only)

        # T017: Regenerate tasks.md from wps.yaml manifest (FR-008, FR-011)
        tasks_md = planning_dir / TASKS_MD_FILENAME
        if wps_manifest is not None:
            tasks_md.write_text(generate_tasks_md_from_manifest(wps_manifest, mission_slug), encoding="utf-8")
            if not json_output:
                console.print(
                    f"[green]Regenerated[/green] tasks.md from wps.yaml ({len(wps_manifest.work_packages)} WPs)"
                )

        wp_frontmatters, wp_bodies = _gather_validation_frontmatter(wp_files, state)
        ownership_source = FinalizeFrontmatterSource(wp_files=list(wp_files), inmemory=state.inmemory_frontmatter)
        wp_manifests = resolve_wp_manifests(ownership_source)
        _validate_ownership_manifests(
            wp_manifests, wp_frontmatters, repo_root, state, json_output=json_output
        )

        mission_slug = planning_dir.name
        meta = _read_meta_for_emission(planning_dir)
        _warn_missing_meta(planning_dir, meta, json_output=json_output)
        _emit_tasks_started(planning_dir, mission_slug, state, validate_only=validate_only)

        if validate_only:
            _emit_validate_only_report(
                planning_dir,
                mission_slug,
                meta,
                state,
                wp_manifests,
                dep_resolution.wp_dependencies,
                wp_bodies,
                target_branch,
                json_output=json_output,
            )
            return

        _run_commit_pipeline(
            planning_dir,
            tasks_dir,
            repo_root,
            mission_slug,
            target_branch,
            state,
            dep_resolution,
            wp_manifests,
            wp_frontmatters,
            wp_bodies,
            meta,
            functional_spec_requirement_ids,
            preexisting_primary_files,
            validate_only=validate_only,
            json_output=json_output,
            target_branch_override=target_branch_override,
            target_branch_persist=target_branch_persist,
            meta_commit_progress=meta_commit_progress,
        )

    except typer.Exit:
        revert_error = _revert_unpersisted_target_branch_override(
            meta_path_for_revert,
            meta_original_text,
            meta_json_persisted=meta_json_persisted,
            meta_commit_progress=meta_commit_progress,
        )
        # SK3466-RR-003: the ORIGINAL error already emitted its own
        # diagnostic before raising typer.Exit above; this is a best-effort,
        # ADDITIONAL note if the meta.json revert itself also failed.
        _report_target_branch_revert_failure(revert_error, json_output=json_output)
        raise
    except Exception as e:
        revert_error = _revert_unpersisted_target_branch_override(
            meta_path_for_revert,
            meta_original_text,
            meta_json_persisted=meta_json_persisted,
            meta_commit_progress=meta_commit_progress,
        )
        _emit_finalize_error_with_revert_note(e, revert_error, json_output=json_output)
        raise typer.Exit(1) from None
