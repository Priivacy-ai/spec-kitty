"""Accept command implementation."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceResult,
    AcceptanceSummary,
    ArtifactEncodingError,
    acceptance_lane_derivations,
    choose_mode,
    collect_feature_summary,
    normalize_feature_encoding,
    perform_acceptance,
    resolve_acceptance_actor,
)
from specify_cli.upgrade.pre30_guard import Pre30LayoutError
from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.cli.helpers import console, show_banner
from specify_cli.task_utils import (
    LANES,
    TaskCliError,
    find_repo_root,
    git_status_lines,
    run_git,
)


def _safe_emit_error_logged(message: str) -> None:
    try:
        from specify_cli.sync.events import emit_error_logged

        emit_error_logged(error_type="runtime", error_message=message)
    except Exception:
        # Non-blocking: never fail the command on emission errors
        pass


def _dirty_paths_with_prefix(status_lines: list[str], prefix: str) -> list[str]:
    """Filter ``git status --porcelain`` lines to tracked-modified paths under ``prefix``.

    Shared by the primary and coordination-worktree scans (T008) so both
    surfaces apply the identical filtering rule: rename entries resolve to
    their destination path, and untracked files (``??``) are deliberately
    excluded so the cleanup commit never sweeps in unrelated, unmanaged files
    the operator may have created.
    """
    dirty: list[str] = []
    for line in status_lines:
        # Porcelain format: two status chars, a space, then the path.
        status_code = line[:2]
        path = line[3:].strip()
        # Rename entries look like "old -> new"; keep the destination path.
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if status_code == "??":
            continue
        if path.startswith(prefix):
            dirty.append(path)
    return dirty


def _primary_dirty_paths(repo_root: Path, mission_slug: str) -> list[str]:
    """Return tracked-but-uncommitted spec/meta artifacts in the PRIMARY checkout."""
    prefix = f"kitty-specs/{mission_slug}/"
    return _dirty_paths_with_prefix(git_status_lines(repo_root), prefix)


def _coord_worktree_root(repo_root: Path, mission_slug: str) -> Path | None:
    """Resolve the mission's materialised coordination worktree root, if any.

    Returns ``None`` when the mission's stored topology does not route
    through coordination, or the coordination worktree has not been
    materialised on disk yet — there is nothing to reconcile before that
    (mirrors the leniency ``_status_read_feature_dir`` already applies).
    Never creates the worktree (a dirty-tree scan must not have side effects).
    """
    from mission_runtime import (
        MissionArtifactKind,
        placement_seam,
        resolve_topology,
        routes_through_coordination,
    )

    topology = resolve_topology(repo_root, mission_slug)
    if not routes_through_coordination(topology):
        return None

    coord_feature_dir = placement_seam(repo_root, mission_slug).read_dir(
        MissionArtifactKind.ACCEPTANCE_MATRIX
    )
    if not coord_feature_dir.exists():
        return None

    try:
        worktree_root = Path(
            run_git(
                ["rev-parse", "--show-toplevel"], cwd=coord_feature_dir, check=True
            ).stdout.strip()
        )
    except TaskCliError:
        return None

    if worktree_root.resolve() == repo_root.resolve():
        return None
    return worktree_root


def _coord_dirty_paths(repo_root: Path, mission_slug: str) -> list[str]:
    """Return tracked-but-uncommitted acceptance artifacts in the COORD worktree.

    M2 (#read-surface-ssot-closeout FR-008): ``write_acceptance_matrix`` writes
    ``acceptance-matrix.json`` (and the sibling issue-matrix/status views) to
    the coordination worktree's ``feature_dir`` under coordination topology
    (:func:`~specify_cli.acceptance.resolve_feature_dir_for_mission` /
    :func:`~mission_runtime.placement_seam`). A primary-only
    ``git_status_lines(repo_root)`` scan can never see that dirt — it lives in
    a completely separate git worktree. This mirrors :func:`_primary_dirty_paths`
    against that surface instead.
    """
    worktree_root = _coord_worktree_root(repo_root, mission_slug)
    if worktree_root is None:
        return []
    prefix = f"kitty-specs/{mission_slug}/"
    return _dirty_paths_with_prefix(git_status_lines(worktree_root), prefix)


def _spec_artifact_dirty_paths(repo_root: Path, mission_slug: str) -> list[str]:
    """Return tracked-but-uncommitted spec/meta artifacts under the mission dir.

    The acceptance pipeline materializes derived artifacts (e.g.
    ``acceptance-matrix.json`` and status views) while running readiness checks
    *before* the acceptance commit is created. Those writes happen after the
    git-cleanliness snapshot is taken, so the acceptance commit only captures
    ``meta.json`` and leaves the materialized artifacts modified-unstaged. This
    helper finds exactly those leftover tracked modifications so the command can
    fold them into the acceptance state and leave a clean working tree.

    M2 (T008): under coordination topology the acceptance-matrix write lands in
    the coordination worktree, not the primary checkout, so the scan also
    consults that surface (:func:`_coord_dirty_paths`) and unions the result —
    a flattened/non-coord mission is unaffected (that scan returns ``[]``).
    """
    dirty = _primary_dirty_paths(repo_root, mission_slug)
    for path in _coord_dirty_paths(repo_root, mission_slug):
        if path not in dirty:
            dirty.append(path)
    return dirty


def _commit_primary_residuals(repo_root: Path, mission_slug: str, dirty: list[str]) -> bool:
    """Stage and commit leftover PRIMARY-checkout acceptance artifacts.

    Byte-identical to the pre-WP02 direct-commit behaviour (DoD: "keep
    PRIMARY-kind residuals working") — these files already live in ``repo_root``,
    so a raw scoped commit on the current branch is safe regardless of the
    mission's declared ``target_branch`` (unlike ``commit_for_mission``, which
    resolves a kind-aware placement that may differ from HEAD, see
    ``_commit_coord_residuals``).
    """
    for path in dirty:
        run_git(["add", path], cwd=repo_root, check=True)

    # Scope the staged-check and the commit to the mission's dirty artifacts
    # only. A bare ``git commit`` would sweep in any files the operator had
    # pre-staged outside the mission dir; the explicit ``-- <paths>`` pathspec
    # commits exactly these spec/meta artifacts and leaves unrelated staged work
    # untouched.
    staged = run_git(
        ["diff", "--cached", "--name-only", "--", *dirty],
        cwd=repo_root,
        check=True,
    )
    staged_files = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    if not staged_files:
        return False

    run_git(
        ["commit", "-m", f"Finalize acceptance artifacts for {mission_slug}", "--", *dirty],
        cwd=repo_root,
        check=True,
    )
    return True


def _commit_coord_residuals(repo_root: Path, mission_slug: str, dirty: list[str]) -> bool:
    """Route coordination-partition residuals through the partition-aware seam.

    T007: these files physically live in the coordination worktree (M2), which
    a primary-rooted raw ``git commit`` structurally cannot reach. Routes
    through :func:`~specify_cli.coordination.commit_router.commit_for_mission`
    instead — the SAME single canonical commit entry point ``spec_commit_cmd.py``
    / ``mission_finalize.py`` use. Files are NOT hand-classified here: the
    router's own ``kind_for_mission_file`` classification (contracts/partition-
    aware-commit-seam.md) resolves each file's placement and materialises the
    coordination worktree on demand; ``ACCEPTANCE_MATRIX`` only seeds the
    fallback for an unrecognised path and which group's outcome is reported.
    """
    from mission_runtime import MissionArtifactKind
    from specify_cli.coordination.commit_router import CommitRouterResult, commit_for_mission
    from specify_cli.git.protection_policy import ProtectionPolicy

    policy = ProtectionPolicy.resolve(repo_root)
    files = tuple(repo_root / path for path in dirty)
    # Explicit annotation: under the project's ``follow_imports = "skip"`` mypy
    # config the cross-module ``commit_for_mission`` return is seen as ``Any``;
    # the annotation re-narrows it (matching the ``_planning_read_dir`` /
    # ``spec_commit_cmd.py`` chokepoint pattern) so ``.status`` comparisons below
    # type-check as ``bool``, not ``Any``.
    result: CommitRouterResult = commit_for_mission(
        repo_root=repo_root,
        mission_slug=mission_slug,
        files=files,
        message=f"Finalize acceptance artifacts for {mission_slug}",
        policy=policy,
        kind=MissionArtifactKind.ACCEPTANCE_MATRIX,
    )

    if result.status == "error":
        raise TaskCliError(
            f"Residual coordination artifact commit failed for {mission_slug} "
            f"({result.placement_ref}): {result.diagnostic or 'unknown error'}"
        )
    return bool(result.status == "committed")


def _commit_residual_acceptance_artifacts(repo_root: Path, mission_slug: str) -> bool:
    """Stage and commit any leftover acceptance artifacts so the tree is clean.

    Returns True when a follow-up commit was created. This preserves the
    recorded ``accept_commit`` SHA (it still points at the real acceptance
    commit) while guaranteeing a successful ``accept`` leaves no
    staged-but-uncommitted or modified-unstaged spec/meta artifacts behind.

    T007/T008: dirt is now detected on BOTH the primary checkout and (under
    coordination topology) the coordination worktree, and each surface commits
    through the mechanism that can actually reach it — coordination residuals
    via the partition-aware ``commit_for_mission`` seam, primary residuals via
    the historical direct commit. A batch mixing both commits to each surface
    independently (never a single cross-worktree commit, which git cannot do).
    """
    coord_dirty = _coord_dirty_paths(repo_root, mission_slug)
    primary_dirty = _primary_dirty_paths(repo_root, mission_slug)
    if not coord_dirty and not primary_dirty:
        return False

    committed = False
    if coord_dirty:
        committed = _commit_coord_residuals(repo_root, mission_slug, coord_dirty) or committed
    if primary_dirty:
        committed = _commit_primary_residuals(repo_root, mission_slug, primary_dirty) or committed
    return committed


def _print_acceptance_warnings(summary: AcceptanceSummary) -> None:
    """Render non-blocking ``summary.warnings`` in the human console.

    The ``--json`` output already carries ``warnings``, but the human-readable
    paths did not surface them, so a ``--lenient`` operator (issue #1892) got no
    signal about what was downgraded from blocking to advisory. Shown only when
    non-empty so a clean summary prints no spurious section.
    """
    if not summary.warnings:
        return
    console.print("\n[bold yellow]Warnings[/bold yellow]")
    for warning in summary.warnings:
        console.print(f"[yellow]- {warning}[/yellow]")


def _print_acceptance_summary(summary: AcceptanceSummary) -> None:
    table = Table(title="Work Packages by Lane", header_style="cyan")
    table.add_column("Lane")
    table.add_column("Count", justify="right")
    table.add_column("Work Packages", justify="left")
    for lane in LANES:
        items = summary.lanes.get(lane, [])
        display = ", ".join(items) if items else "-"
        table.add_row(lane, str(len(items)), display)
    console.print(table)

    outstanding = summary.outstanding()
    if outstanding:
        console.print("\n[bold red]Outstanding items[/bold red]")
        for key, values in outstanding.items():
            console.print(f"[red]- {key}[/red]")
            for value in values:
                console.print(f"    • {value}")
    else:
        console.print("\n[green]No outstanding acceptance issues detected.[/green]")

    _print_acceptance_warnings(summary)

    if summary.optional_missing:
        console.print(
            "\n[yellow]Optional artifacts missing:[/yellow] "
            + ", ".join(summary.optional_missing)
        )
        console.print()


def _print_acceptance_result(result: AcceptanceResult) -> None:
    console.print(
        "\n[bold]Acceptance metadata[/bold]\n"
        f"• Mission: {result.summary.feature}\n"
        f"• Accepted at: {result.accepted_at}\n"
        f"• Accepted by: {result.accepted_by}"
    )
    if result.accept_commit:
        console.print(f"• Acceptance commit: {result.accept_commit}")
    if result.parent_commit:
        console.print(f"• Parent commit: {result.parent_commit}")
    if not result.commit_created:
        console.print("• Commit status: no changes were committed (dry-run)")
    if result.accepted_wps:
        console.print(f"• Accepted WPs: {', '.join(result.accepted_wps)}")
    if result.merge_pending_wps:
        console.print(f"• Merge-pending WPs: {', '.join(result.merge_pending_wps)}")
    if result.done_wps:
        console.print(f"• Already merged WPs: {', '.join(result.done_wps)}")

    if result.instructions:
        console.print("\n[bold]Next steps[/bold]")
        for idx, instruction in enumerate(result.instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.cleanup_instructions:
        console.print("\n[bold]Cleanup[/bold]")
        for idx, instruction in enumerate(result.cleanup_instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.notes:
        console.print("\n[bold]Notes[/bold]")
        for note in result.notes:
            console.print(f"  - {note}")


def _print_acceptance_diagnosis(summary: AcceptanceSummary) -> None:
    failed_checks = summary.failed_checks()
    if failed_checks:
        console.print("\n[bold red]Failed checks[/bold red]")
        for item in failed_checks:
            console.print(f"[red]- {item.check}[/red]: {item.detail}")
    else:
        console.print("\n[green]No failed acceptance checks detected.[/green]")

    if summary.skipped_checks:
        console.print("\n[bold yellow]Skipped checks[/bold yellow]")
        for item in summary.skipped_checks:
            console.print(f"[yellow]- {item.check}[/yellow]: {item.detail}")

    if summary.blocked_checks:
        console.print("\n[bold yellow]Blocked checks[/bold yellow]")
        for item in summary.blocked_checks:
            console.print(f"[yellow]- {item.check}[/yellow]: {item.detail}")

    _print_acceptance_warnings(summary)

    if summary.recommended_fix_order:
        console.print("\n[bold]Recommended fix order[/bold]")
        for idx, fix in enumerate(summary.recommended_fix_order, start=1):
            console.print(f"  {idx}. {fix}")


def _summary_payload(summary: AcceptanceSummary) -> dict[str, object]:
    payload: dict[str, object] = summary.to_dict()
    payload.update(acceptance_lane_derivations(summary))
    return payload


def _report_encoding_repair(repo_root: Path, repaired: list[Path]) -> None:
    """Surface which acceptance artifacts the encoding repair rewrote.

    Mirrors the command's existing ``console`` reporting idiom. Paths are shown
    relative to ``repo_root`` when possible so the operator sees mission-relative
    artifact names rather than absolute temp paths.
    """
    if not repaired:
        console.print(
            "[yellow]--normalize-encoding enabled but no artifacts required updates.[/yellow]"
        )
        return
    console.print("[yellow]Normalized acceptance-artifact encoding for:[/yellow]")
    for path in repaired:
        try:
            display = path.relative_to(repo_root)
        except ValueError:
            display = path
        console.print(f"  - {display}")


def _collect_summary_with_optional_repair(
    repo_root: Path,
    mission_slug: str,
    *,
    strict_metadata: bool,
    mutate_matrix: bool,
    normalize_encoding: bool,
) -> AcceptanceSummary:
    """Collect the acceptance summary, optionally repairing artifact encoding.

    FR-005 / C-003: when ``normalize_encoding`` is True and the strict UTF-8 read
    raises ``ArtifactEncodingError``, delegate to the **canonical**
    ``acceptance.normalize_feature_encoding`` (no standalone logic is copied),
    report the repaired paths, and re-collect exactly once. Any second failure
    propagates to the caller's ``except AcceptanceError`` handler (exit 1). When
    the flag is off, the error propagates unchanged so the pre-existing default
    error path is preserved untouched.
    """
    try:
        return collect_feature_summary(
            repo_root,
            mission_slug,
            strict_metadata=strict_metadata,
            mutate_matrix=mutate_matrix,
        )
    except ArtifactEncodingError:
        if not normalize_encoding:
            raise
        repaired = normalize_feature_encoding(repo_root, mission_slug)
        _report_encoding_repair(repo_root, repaired)
        # Re-collect exactly once; a second encoding (or other acceptance)
        # failure propagates rather than looping.
        return collect_feature_summary(
            repo_root,
            mission_slug,
            strict_metadata=strict_metadata,
            mutate_matrix=mutate_matrix,
        )


def accept(
    mission: str | None = typer.Option(
        None,
        "--mission",
        help="Mission slug to accept",
    ),
    mode: str = typer.Option("auto", "--mode", case_sensitive=False, help="Acceptance mode: auto, pr, local, or checklist"),
    actor: str | None = typer.Option(None, "--actor", help="Name to record as the acceptance actor"),
    test: list[str] = typer.Option([], "--test", help="Validation command executed (repeatable)", show_default=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of formatted text"),
    lenient: bool = typer.Option(False, "--lenient", help="Skip strict metadata validation"),
    no_commit: bool = typer.Option(False, "--no-commit", help="Report acceptance readiness without writing metadata or status changes"),
    diagnose: bool = typer.Option(False, "--diagnose", help="Diagnose acceptance blockers without writing metadata or matrix artifacts"),
    allow_fail: bool = typer.Option(False, "--allow-fail", help="Return checklist even when issues remain"),
    normalize_encoding: bool = typer.Option(
        False,
        "--normalize-encoding/--no-normalize-encoding",
        help="Repair acceptance-artifact encoding (Windows-1252/Latin-1 -> UTF-8) before validating.",
    ),
) -> None:
    """Validate mission readiness before merging to main."""

    if not json_output:
        show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    tracker = StepTracker("Mission Acceptance")
    if not json_output:
        tracker.add("detect", "Identify mission slug")
        tracker.add("verify", "Run readiness checks")
        console.print()
        tracker.start("detect")

    # Resolve mission handle — supports slug, numeric prefix, mid8, or full ULID.
    # resolve_mission_handle() handles AmbiguousHandleError / MissionNotFoundError
    # and calls sys.exit(2) on failure; no try/except needed.
    raw_handle = mission
    if raw_handle is None:
        _safe_emit_error_logged("No mission handle provided")
        if json_output:
            print(json.dumps({"error": "--mission <slug> is required"}))
        else:
            tracker.error("detect", "--mission <slug> is required")
            console.print(tracker.render())
            console.print("[red]Error:[/red] --mission <slug> is required")
        raise typer.Exit(2)

    resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
    mission_slug = resolved.mission_slug

    if not json_output:
        tracker.complete("detect", mission_slug)

    requested_mode = (mode or "auto").lower()
    actual_mode = choose_mode(requested_mode, repo_root)
    commit_required = actual_mode != "checklist" and not no_commit and not diagnose
    if commit_required and not json_output:
        tracker.add("commit", "Record acceptance metadata")
    if not json_output:
        tracker.add("guide", "Share next steps" if not diagnose else "Report diagnostics")

    if not json_output:
        tracker.start("verify")
    try:
        summary = _collect_summary_with_optional_repair(
            repo_root,
            mission_slug,
            strict_metadata=not lenient,
            # --no-commit must still resolve the acceptance matrix (run negative
            # invariants, refresh verdict); otherwise the verdict stays 'pending'
            # and the gate can never pass in --no-commit mode. The matrix write
            # is accept-owned and excluded from the dirty-tree gate (#1883), so
            # mutating without committing is safe and converges. Only diagnose
            # (read-only) leaves the matrix untouched.
            mutate_matrix=not diagnose,
            # FR-005: opt-in repair of mojibake acceptance artifacts via the
            # canonical normalize_feature_encoding before validating (default off).
            normalize_encoding=normalize_encoding,
        )
    except Pre30LayoutError as exc:
        # #1057 / squad Blocker 1: a pre-3.0 lane-directory mission must hard-reject
        # with the `spec-kitty upgrade` instruction and write NOTHING — never fall
        # through to a vacuous all-done summary that auto-commits an unmigrated
        # mission.
        _safe_emit_error_logged(str(exc))
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            tracker.error("verify", str(exc))
            console.print(tracker.render())
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    except AcceptanceError as exc:
        _safe_emit_error_logged(str(exc))
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            tracker.error("verify", str(exc))
            console.print(tracker.render())
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    if not json_output:
        tracker.complete("verify", "ready" if summary.ok else "issues found")

    if diagnose:
        if json_output:
            payload = _summary_payload(summary)
            payload["diagnose"] = True
            print(json.dumps(payload, indent=2))
        else:
            tracker.start("guide")
            tracker.complete("guide", "diagnostics ready")
            console.print(tracker.render())
            _print_acceptance_diagnosis(summary)
        raise typer.Exit(0)

    if actual_mode == "checklist":
        if json_output:
            print(
                json.dumps(
                    _summary_payload(summary),
                    indent=2,
                )
            )
        else:
            _print_acceptance_summary(summary)
        raise typer.Exit(0 if summary.ok else 1)

    if not summary.ok:
        if json_output:
            print(json.dumps(summary.to_dict(), indent=2))
        else:
            _print_acceptance_summary(summary)
        if not allow_fail:
            _safe_emit_error_logged("Outstanding acceptance issues detected")
            if not json_output:
                console.print(
                    "\n[red]Outstanding acceptance issues detected. Resolve them before merging or rerun with --allow-fail for a checklist-only report.[/red]"
                )
            raise typer.Exit(1)
        raise typer.Exit(1)

    acceptance_tests = list(test)
    actor_name = resolve_acceptance_actor(actor)

    # T015 / WP04 / FR-001: the protected-primary guard is no longer a hard
    # reject here.  ``_commit_acceptance_meta`` routes every commit through
    # ``commit_for_mission``, which materialises the coordination worktree on
    # demand when the primary is protected (C-001 / FR-003).  A pre-flight
    # raise-and-exit deadlock is therefore unnecessary and has been removed.

    result: AcceptanceResult | None = None
    _accept_exc: AcceptanceError | None = None
    _residue_exc: Exception | None = None
    try:
        if commit_required and not json_output:
            tracker.start("commit")
        if no_commit:
            result = perform_acceptance(
                summary,
                mode=actual_mode,
                actor=actor_name,
                tests=acceptance_tests,
                auto_commit=False,
            )
        else:
            result = perform_acceptance(
                summary,
                mode=actual_mode,
                actor=actor_name,
                tests=acceptance_tests,
                auto_commit=commit_required,
            )
        if commit_required and not json_output:
            detail = "commit created" if result.commit_created else "no changes"
            tracker.complete("commit", detail)
    except AcceptanceError as exc:
        _accept_exc = exc
        _safe_emit_error_logged(str(exc))
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            if commit_required:
                tracker.error("commit", str(exc))
                console.print(tracker.render())
            console.print(f"[red]Error:[/red] {exc}")
    finally:
        if commit_required:
            # The acceptance commit (inside perform_acceptance) only captures
            # meta.json. Derived artifacts materialized during readiness checks
            # (e.g. acceptance-matrix.json, status views) are written after the
            # git-cleanliness snapshot and would otherwise be left dirty. Fold
            # them into a follow-up commit so all writing exit paths (including
            # error paths and accept_commit == None) leave a clean working tree.
            try:
                _commit_residual_acceptance_artifacts(repo_root, mission_slug)
            except Exception as residue_exc:
                _residue_exc = residue_exc
                _safe_emit_error_logged(f"Residual artifact commit failed: {residue_exc}")
    if _accept_exc is not None:
        raise typer.Exit(1)
    if _residue_exc is not None:
        error_msg = f"Residual artifact commit failed: {_residue_exc}"
        if json_output:
            print(json.dumps({"error": error_msg}))
        else:
            if commit_required:
                tracker.error("commit", error_msg)
                console.print(tracker.render())
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)

    assert result is not None  # guaranteed: _accept_exc is None means perform_acceptance succeeded

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
        return

    tracker.start("guide")
    tracker.complete("guide", "instructions ready")
    console.print(tracker.render())

    _print_acceptance_summary(result.summary)
    _print_acceptance_result(result)


__all__ = ["accept"]
