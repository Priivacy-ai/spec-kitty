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
    acceptance_lane_derivations,
    choose_mode,
    collect_feature_summary,
    perform_acceptance,
    resolve_acceptance_actor,
)
from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.cli.helpers import console, show_banner
from specify_cli.git.commit_helpers import assert_not_protected_branch
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


def _spec_artifact_dirty_paths(repo_root: Path, feature_slug: str) -> list[str]:
    """Return tracked-but-uncommitted spec/meta artifacts under the mission dir.

    The acceptance pipeline materializes derived artifacts (e.g.
    ``acceptance-matrix.json`` and status views) while running readiness checks
    *before* the acceptance commit is created. Those writes happen after the
    git-cleanliness snapshot is taken, so the acceptance commit only captures
    ``meta.json`` and leaves the materialized artifacts modified-unstaged. This
    helper finds exactly those leftover tracked modifications so the command can
    fold them into the acceptance state and leave a clean working tree.

    Untracked files (``??``) are deliberately excluded so the cleanup commit
    never sweeps in unrelated, unmanaged files the operator may have created.
    """
    prefix = f"kitty-specs/{feature_slug}/"
    dirty: list[str] = []
    for line in git_status_lines(repo_root):
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


def _commit_residual_acceptance_artifacts(repo_root: Path, feature_slug: str) -> bool:
    """Stage and commit any leftover acceptance artifacts so the tree is clean.

    Returns True when a follow-up commit was created. This preserves the
    recorded ``accept_commit`` SHA (it still points at the real acceptance
    commit) while guaranteeing a successful ``accept`` leaves no
    staged-but-uncommitted or modified-unstaged spec/meta artifacts behind.
    """
    dirty = _spec_artifact_dirty_paths(repo_root, feature_slug)
    if not dirty:
        return False

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
        ["commit", "-m", f"Finalize acceptance artifacts for {feature_slug}", "--", *dirty],
        cwd=repo_root,
        check=True,
    )
    return True


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

    if summary.recommended_fix_order:
        console.print("\n[bold]Recommended fix order[/bold]")
        for idx, item in enumerate(summary.recommended_fix_order, start=1):
            console.print(f"  {idx}. {item}")


def _summary_payload(summary: AcceptanceSummary) -> dict[str, object]:
    payload = summary.to_dict()
    payload.update(acceptance_lane_derivations(summary))
    return payload


def accept(
    mission: str | None = typer.Option(
        None,
        "--mission",
        help="Mission slug to accept",
    ),
    feature: str | None = typer.Option(
        None,
        "--feature",
        hidden=True,
        help="(deprecated) Use --mission",
    ),
    mode: str = typer.Option("auto", "--mode", case_sensitive=False, help="Acceptance mode: auto, pr, local, or checklist"),
    actor: str | None = typer.Option(None, "--actor", help="Name to record as the acceptance actor"),
    test: list[str] = typer.Option([], "--test", help="Validation command executed (repeatable)", show_default=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of formatted text"),
    lenient: bool = typer.Option(False, "--lenient", help="Skip strict metadata validation"),
    no_commit: bool = typer.Option(False, "--no-commit", help="Report acceptance readiness without writing metadata or status changes"),
    diagnose: bool = typer.Option(False, "--diagnose", help="Diagnose acceptance blockers without writing metadata or matrix artifacts"),
    allow_fail: bool = typer.Option(False, "--allow-fail", help="Return checklist even when issues remain"),
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
    raw_handle = mission or feature
    if raw_handle is None:
        _safe_emit_error_logged("No mission handle provided")
        if json_output:
            print(json.dumps({"error": "--mission <slug> is required"}))
        else:
            tracker.error("detect", "--mission <slug> is required")
            console.print(tracker.render())
            console.print("[red]Error:[/red] --mission <slug> is required")
        raise typer.Exit(1)

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
        summary = collect_feature_summary(
            repo_root,
            mission_slug,
            strict_metadata=not lenient,
            mutate_matrix=not diagnose,
        )
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

    if commit_required:
        try:
            assert_not_protected_branch(repo_root, operation="record acceptance")
        except Exception as exc:
            _safe_emit_error_logged(str(exc))
            if json_output:
                print(json.dumps({"error": str(exc)}))
            else:
                console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)

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
        if commit_required:
            # The acceptance commit (inside perform_acceptance) only captures
            # meta.json. Derived artifacts materialized during readiness checks
            # (e.g. acceptance-matrix.json, status views) are written after the
            # git-cleanliness snapshot and would otherwise be left dirty. Fold
            # them into a follow-up commit so a successful accept leaves a clean
            # working tree on every path (including accept_commit == None).
            _commit_residual_acceptance_artifacts(repo_root, mission_slug)
        if commit_required and not json_output:
            detail = "commit created" if result.commit_created else "no changes"
            tracker.complete("commit", detail)
    except AcceptanceError as exc:
        _safe_emit_error_logged(str(exc))
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            if commit_required:
                tracker.error("commit", str(exc))
                console.print(tracker.render())
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
        return

    tracker.start("guide")
    tracker.complete("guide", "instructions ready")
    console.print(tracker.render())

    _print_acceptance_summary(result.summary)
    _print_acceptance_result(result)


__all__ = ["accept"]
