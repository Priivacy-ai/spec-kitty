"""TeamSpace mission-state migration prompt and connection gate helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel


@dataclass(frozen=True)
class TeamspaceMissionStateReadiness:
    """Readiness summary for TeamSpace historical mission-state import."""

    repo_root: Path
    total_missions: int = 0
    blocker_count: int = 0
    missions_with_blockers: int = 0
    blocker_codes: tuple[str, ...] = ()
    audit_error: str | None = None

    @property
    def migration_pending(self) -> bool:
        return self.blocker_count > 0

    @property
    def blocked(self) -> bool:
        return self.migration_pending or self.audit_error is not None


def check_teamspace_mission_state_readiness(repo_root: Path) -> TeamspaceMissionStateReadiness:
    """Return mission-state readiness for TeamSpace connect/import paths."""
    repo_root = repo_root.resolve()
    if not (repo_root / "kitty-specs").is_dir():
        return TeamspaceMissionStateReadiness(repo_root=repo_root)

    try:
        from specify_cli.audit import AuditOptions, run_audit
        from specify_cli.audit.models import is_teamspace_blocker

        report = run_audit(AuditOptions(repo_root=repo_root))
    except Exception as exc:  # noqa: BLE001 - connection paths fail closed on unknown readiness
        return TeamspaceMissionStateReadiness(
            repo_root=repo_root,
            audit_error=str(exc),
        )

    blocker_codes: set[str] = set()
    blocker_count = 0
    missions_with_blockers = 0
    for mission in report.missions:
        mission_has_blocker = False
        for finding in mission.findings:
            if not is_teamspace_blocker(finding):
                continue
            blocker_count += 1
            blocker_codes.add(finding.code)
            mission_has_blocker = True
        if mission_has_blocker:
            missions_with_blockers += 1

    return TeamspaceMissionStateReadiness(
        repo_root=repo_root,
        total_missions=int(report.repo_summary.get("total_missions", len(report.missions))),
        blocker_count=blocker_count,
        missions_with_blockers=missions_with_blockers,
        blocker_codes=tuple(sorted(blocker_codes)),
    )


def _guidance_lines(readiness: TeamspaceMissionStateReadiness) -> list[str]:
    if readiness.audit_error:
        return [
            "Spec Kitty could not verify local mission-state readiness.",
            f"Audit error: {readiness.audit_error}",
            "",
            "Run the audit before connecting to TeamSpace:",
            "  spec-kitty doctor mission-state --audit --fail-on teamspace-blocker",
        ]

    codes = ", ".join(readiness.blocker_codes) if readiness.blocker_codes else "unknown"
    return [
        "TeamSpace mission-state migration is required before connecting.",
        (
            f"Found {readiness.blocker_count} TeamSpace blocker(s) "
            f"across {readiness.missions_with_blockers} mission(s)."
        ),
        f"Finding codes: {codes}",
        "",
        "Recommended sequence:",
        "  spec-kitty doctor mission-state --audit --fail-on teamspace-blocker",
        "  spec-kitty doctor mission-state --fix",
        "  spec-kitty doctor mission-state --teamspace-dry-run",
    ]


def _print_notice(
    readiness: TeamspaceMissionStateReadiness,
    *,
    console: Console,
    title: str,
    border_style: str,
) -> None:
    console.print(
        Panel(
            "\n".join(_guidance_lines(readiness)),
            title=title,
            border_style=border_style,
            expand=False,
        )
    )


def enforce_teamspace_mission_state_ready(*, console: Console, command_name: str) -> None:
    """Block TeamSpace connect/sync commands until local mission-state is ready."""
    try:
        from specify_cli.core.paths import locate_project_root

        repo_root = locate_project_root()
    except Exception:  # noqa: BLE001 - outside a project is not a project migration problem
        repo_root = None

    if repo_root is None:
        return

    readiness = check_teamspace_mission_state_readiness(repo_root)
    if not readiness.blocked:
        return

    _print_notice(
        readiness,
        console=console,
        title="TeamSpace Migration Required",
        border_style="red",
    )
    console.print(f"[red]Blocked:[/red] `{command_name}` will not connect until this migration is complete.")
    raise typer.Exit(1)


def offer_teamspace_mission_state_migration(
    project_path: Path,
    *,
    console: Console,
    dry_run: bool,
    assume_yes: bool,
) -> tuple[bool, bool]:
    """Surface and optionally run the TeamSpace mission-state migration.

    Returns ``(migration_was_pending, repair_ran)``.
    """
    readiness = check_teamspace_mission_state_readiness(project_path)
    if not readiness.blocked:
        return False, False

    _print_notice(
        readiness,
        console=console,
        title="TeamSpace Mission-State Migration",
        border_style="yellow",
    )

    if readiness.audit_error:
        return True, False

    if dry_run:
        console.print("[dim]Dry run: mission-state repair was not run.[/dim]")
        return True, False

    should_run = assume_yes or typer.confirm(
        "Run `spec-kitty doctor mission-state --fix` now?",
        default=True,
    )
    if not should_run:
        console.print("[yellow]Skipped TeamSpace mission-state repair.[/yellow]")
        return True, False

    from specify_cli.migration.mission_state import MissionStateRepairError, repair_repo

    try:
        report = repair_repo(project_path)
    except MissionStateRepairError as exc:
        console.print(f"[red]Mission-state repair failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Mission-state repair encountered an unexpected error:[/red] {exc}")
        raise typer.Exit(1) from exc

    summary = report.to_dict()["summary"]
    if not isinstance(summary, dict):
        raise MissionStateRepairError(f"Unexpected repair report summary type: {type(summary)!r}")
    console.print(
        "[green]Mission-state repair complete[/green] "
        f"(updated={summary['missions_updated']}, "
        f"unchanged={summary['missions_unchanged']}, "
        f"errors={summary['missions_error']})."
    )
    console.print(f"Manifest: {report.manifest_path}")

    post_repair = check_teamspace_mission_state_readiness(project_path)
    if post_repair.blocked:
        _print_notice(
            post_repair,
            console=console,
            title="TeamSpace Migration Still Blocked",
            border_style="red",
        )
        raise typer.Exit(1)

    console.print("[green]TeamSpace mission-state blockers cleared.[/green]")
    return True, True
