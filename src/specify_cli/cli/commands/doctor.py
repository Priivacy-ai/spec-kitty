"""Top-level doctor command group for project health diagnostics.

This module is the ``add_typer`` ORCHESTRATION SHIM for the ``doctor`` command
group: it owns the ``app`` object + the 16 thin ``@app.command`` shells, and
re-exports the test-facing private symbols. Every subcommand's logic lives in a
dedicated ``_*_doctor`` / ``_*`` sibling (shared infra in ``_doctor_shared``).
"""

# ⚠️ ORCHESTRATION SHIM (#2059 de-godding complete — do NOT add new responsibilities here).
# The former ~3300 LOC god module was decomposed into cohesive sibling modules
# (WP02–WP10). New subcommand logic belongs in a sibling, not here; this file
# stays a thin shim of command shells + the re-export block.
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2059
# (prior partial FR-012 extraction landed in closed #1623.)

from __future__ import annotations

import json
import logging
import sys  # noqa: F401 — re-exported patch target: tests monkeypatch ``doctor.sys.stdin`` (#2059)
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.paths import locate_project_root
from specify_cli.paths import get_runtime_root, render_runtime_path
from specify_cli.runtime.home import get_kittify_home

# WP02 (#2059): the shared ``doctor`` infrastructure — the single ``console``
# singleton, the ``--json`` guards, and the module constants — lives in
# ``_doctor_shared`` (the canonical home, H1/I-3). Every sibling imports from
# there so exactly one ``Console()`` backs the whole surface. The redundant
# aliases mark these as intentional re-exports kept importable from ``doctor``.
from ._doctor_shared import (
    _CI_ENV_VARS as _CI_ENV_VARS,
    _NOT_IN_PROJECT_MESSAGE as _NOT_IN_PROJECT_MESSAGE,
    _STARTED_AT_COLUMN as _STARTED_AT_COLUMN,
    _is_interactive_environment as _is_interactive_environment,
    _json_error as _json_error,
    _json_output_guard as _json_output_guard,
    console as console,
)

if TYPE_CHECKING:
    from specify_cli.compat.doctor import ShimRegistryReport

    from ._doctrine_health import DoctrineHealthReport

app = typer.Typer(name="doctor", help="Project health diagnostics")
# WP08 (#1623): the doctrine/profile health *render* helpers were extracted to
# ``_profile_health_render`` (which instantiates the single ``console``
# re-exported via ``_doctor_shared``).  ``doctor.py`` re-imports them so the
# public (test-facing) names remain importable from ``doctor``.
from ._profile_health_render import (  # noqa: E402 — must follow `app`/imports above
    _emit_doctrine_human,
    _emit_doctrine_json,
    _emit_doctrine_no_packs,
)

# Re-export the render-only helpers so the existing test surface
# (``from specify_cli.cli.commands.doctor import _render_doctrine_pack`` etc.)
# keeps resolving after the WP08 extraction.  The redundant-alias form marks
# these as intentional re-exports (they are consumed by the moved emit helpers,
# not by ``doctor.py`` directly).
from ._profile_health_render import (  # noqa: E402
    _render_doctrine_pack as _render_doctrine_pack,
    _render_org_layer_section as _render_org_layer_section,
    _render_pack_invalid_profiles as _render_pack_invalid_profiles,
    _render_selection_block_lines as _render_selection_block_lines,
)

# WP03 (#2059): the doctrine-health DATA COLLECTORS (Cluster J) were extracted
# to ``_doctrine_collect``, completing the MODEL/RENDER/COLLECT triad #1623 left
# unfinished. The ``doctrine`` command body calls them from there; the redundant
# aliases keep the test-facing collector symbols importable from ``doctor``.
from ._doctrine_collect import (  # noqa: E402
    _attach_pack_health,
    _build_selection_block,
    _collect_doctrine_collisions,
)
from ._doctrine_collect import (  # noqa: E402
    _build_pack_entries as _build_pack_entries,
    _collect_org_layer_data as _collect_org_layer_data,
    _collect_profile_health as _collect_profile_health,
    _count_pack_artifacts as _count_pack_artifacts,
    _resolve_pack_version as _resolve_pack_version,
)

# WP04 (#2059): the identity + topology audit cluster (D) was extracted to
# ``_identity_audit`` and the ``identity`` command body decomposed into
# <=15-CC helpers. The ``@app.command`` shells below delegate to these
# entry points (behavior-preserving).
from ._identity_audit import (  # noqa: E402
    run_identity_audit,
    run_topology_audit,
)

# WP05 (#2059): the tool-surface + command-skill + slash-command cluster (A) was
# extracted to ``_command_surface_doctor`` and the ``skills`` /
# ``_repair_command_skill_state`` bodies decomposed into <=15-CC helpers. The
# @app.command shells below delegate to the entry points (behavior-preserving).
# The frozen subcommand names are owned by the shells, so the compat safety
# predicates + argv fast-paths (I-7) are unaffected. The redundant aliases keep
# the test-facing symbols (SlashCommandGap + the two slash-state helpers)
# importable from ``doctor`` (FR-006).
from ._command_surface_doctor import (  # noqa: E402
    run_command_files,
    run_skills_audit,
    run_tool_surfaces_audit,
)
from ._command_surface_doctor import (  # noqa: E402
    SlashCommandGap as SlashCommandGap,
    _load_slash_command_state as _load_slash_command_state,
    _repair_slash_command_state as _repair_slash_command_state,
)

# WP06 (#2059): the mission-state audit/repair/teamspace-dry-run cluster (H) was
# extracted to ``_mission_state_doctor``. The ``mission-state`` @app.command
# shell delegates to ``run_mission_state``; the previous C901 complexity
# suppression on the command is dropped (the dispatched helpers moved out).
from ._mission_state_doctor import run_mission_state  # noqa: E402

# WP07 (#2059): the coordination + git-health cluster (K) was extracted to
# ``_coordination_doctor`` and ``_check_lane_sparse_checkout_drift`` decomposed.
# The ``coordination`` @app.command shell delegates to ``run_coordination_health``.
# H2/I-6: the ``merge.path_is_under_worktrees`` import stays function-local in the
# sibling to avoid a doctor <-> merge module-load cycle. The redundant aliases
# keep the test-facing coordination symbols importable from ``doctor`` (FR-006).
from ._coordination_doctor import run_coordination_health  # noqa: E402
from ._coordination_doctor import (  # noqa: E402
    DoctorFinding as DoctorFinding,
    _check_coordination_worktree_health as _check_coordination_worktree_health,
    _check_git_version as _check_git_version,
    _check_lane_sparse_checkout_drift as _check_lane_sparse_checkout_drift,
)

# WP08 (#2059): the legacy sparse-checkout detection + remediation cluster (E)
# was extracted to ``_sparse_checkout_doctor`` and the ``sparse-checkout`` command
# (CC19) decomposed into <=15-CC helpers. The @app.command shell delegates to
# ``run_sparse_checkout``; the subcommand name is byte-preserved (I-7).
from ._sparse_checkout_doctor import run_sparse_checkout  # noqa: E402

# WP09 (#2059): the workspace-husk cluster (C) was extracted to a standalone
# ``_workspace_husk_doctor``. The ``workspaces`` @app.command shell resolves
# repo_root (patchable seam) and delegates to ``run_workspaces``.
from ._workspace_husk_doctor import run_workspaces  # noqa: E402

# WP10 (#2059): the daemon cluster (I) — orphan-daemons + restart-daemon — was
# extracted to a standalone ``_daemon_doctor``. The @app.command shells delegate
# to the entrypoints; the ``restart-daemon`` name is byte-preserved (I-7: the
# ``__init__`` argv fast-path keys on it).
from ._daemon_doctor import run_orphan_daemons, run_restart_daemon  # noqa: E402

logger = logging.getLogger(__name__)


@app.command(name="command-files")
def command_files(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check all agent command files for correctness.

    Verifies that every configured agent has the correct command files:
    - Full rendered prompts for prompt-driven commands (specify, plan, tasks, ...)
    - Thin shims for CLI-driven commands (implement, review, merge, ...)
    - Current version markers on all files

    Examples:
        spec-kitty doctor command-files
        spec-kitty doctor command-files --json
    """
    run_command_files(json_output)


@app.command(name="skills")
def skills(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Repair missing command-skill files"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check command-skill manifest drift for Codex, Vibe, Pi, and Letta."""
    try:
        project_path = locate_project_root()
    except Exception as exc:
        if json_output:
            console.print_json(
                json.dumps(_json_error("not_in_project", _NOT_IN_PROJECT_MESSAGE), indent=2)
            )
            raise typer.Exit(2) from exc
        console.print(f"[red]Error:[/red] {_NOT_IN_PROJECT_MESSAGE}")
        raise typer.Exit(2) from exc
    run_skills_audit(fix, json_output, project_path)


@app.command(name="tool-surfaces")
def tool_surfaces(
    kind: Annotated[
        list[str] | None,
        typer.Option("--kind", help="Filter to surface kind(s), e.g. command-skill"),
    ] = None,
    tool: Annotated[
        str | None,
        typer.Option("--tool", help="Filter to a single configured tool key"),
    ] = None,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Repair missing or stale surfaces"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Audit (and optionally repair) every configured tool surface.

    Examples:
        spec-kitty doctor tool-surfaces --json
        spec-kitty doctor tool-surfaces --kind command-skill --json
        spec-kitty doctor tool-surfaces --tool codex --fix
    """
    run_tool_surfaces_audit(kind, tool, fix, json_output)



def _print_state_roots_table(report: object) -> None:
    """Print the resolved state-roots existence table (human output)."""
    console.print("\n[bold]State Roots[/bold]")
    for root_info in report.roots:  # type: ignore[attr-defined]
        status = "[green]exists[/green]" if root_info.exists else "[dim]absent[/dim]"
        console.print(f"  {root_info.name:<20} {root_info.resolved_path}  {status}")


def _print_state_surfaces(report: object) -> None:
    """Print the per-root surface classification tables (human output)."""
    from specify_cli.state.contract import StateRoot

    console.print()
    root_order = [
        StateRoot.PROJECT,
        StateRoot.FEATURE,
        StateRoot.GLOBAL_RUNTIME,
        StateRoot.GLOBAL_SYNC,
        StateRoot.GIT_INTERNAL,
    ]
    root_labels = {
        StateRoot.PROJECT: "Project Surfaces (.kittify/)",
        StateRoot.FEATURE: "Feature Surfaces (kitty-specs/)",
        StateRoot.GLOBAL_RUNTIME: f"Global Runtime ({render_runtime_path(get_kittify_home())})",
        StateRoot.GLOBAL_SYNC: f"Global Sync ({render_runtime_path(get_runtime_root().base)})",
        StateRoot.GIT_INTERNAL: "Git-Internal (.git/spec-kitty/)",
    }

    for root in root_order:
        root_surfaces = [s for s in report.surfaces if s.surface.root == root]  # type: ignore[attr-defined]
        if not root_surfaces:
            continue

        console.print(f"[bold]{root_labels.get(root, root.value)}[/bold]")
        table = Table(box=None, padding=(0, 2), show_edge=False)
        table.add_column("Name", style="cyan", min_width=28)
        table.add_column("Authority", min_width=16)
        table.add_column("Git Policy", min_width=22)
        table.add_column("Present", justify="center", min_width=8)

        for check in root_surfaces:
            present_icon = "[green]Y[/green]" if check.present else "[dim]N[/dim]"
            authority = check.surface.authority.value
            git_class = check.surface.git_class.value
            if check.warning:
                authority = f"[yellow]{authority}[/yellow]"
                git_class = f"[yellow]{git_class}[/yellow]"
            table.add_row(check.surface.name, authority, git_class, present_icon)

        console.print(table)
        console.print()


def _print_state_warnings(report: object) -> None:
    """Print the runtime-surface gitignore-coverage warnings section."""
    if report.warnings:  # type: ignore[attr-defined]
        console.print("[bold yellow]Warnings[/bold yellow]")
        for w in report.warnings:  # type: ignore[attr-defined]
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print(
            "[green]No warnings -- all runtime surfaces are properly covered.[/green]"
        )
    console.print()


@app.command(name="state-roots")
def state_roots(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Show state roots, surface classification, and safety warnings.

    Displays the three state roots with resolved paths, all registered
    state surfaces grouped by root with authority and Git classification,
    and warnings for any runtime surfaces not covered by .gitignore.

    Examples:
        spec-kitty doctor state-roots
        spec-kitty doctor state-roots --json
    """
    from specify_cli.state.doctor import check_state_roots

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = check_state_roots(repo_root)

    if json_output:
        console.print_json(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(0 if report.healthy else 1)

    _print_state_roots_table(report)
    _print_state_surfaces(report)
    _print_state_warnings(report)
    raise typer.Exit(0 if report.healthy else 1)


@app.command(name="workspaces")
def workspaces(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Remove husks that are NOT registered in `git worktree list` (registered worktrees are never removed)"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Report .worktrees/ husk directories (entries lacking a .git entry).

    A husk is not a usable git worktree: git commands run inside it fall
    through to the primary repository (#1833). Workspace resolution refuses
    husks with a structured error; this check is the recovery path.

    Examples:
        spec-kitty doctor workspaces
        spec-kitty doctor workspaces --fix
        spec-kitty doctor workspaces --json
    """
    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    run_workspaces(repo_root, fix, json_output)


@app.command(name="identity")
def identity(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit structured JSON output (suitable for CI)"),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Scope report to a single mission slug"),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option(
            "--fail-on",
            help=(
                "Exit non-zero if any mission is in the given state(s). "
                "Comma-separated list of: assigned, pending, legacy, orphan."
            ),
        ),
    ] = None,
) -> None:
    """Report mission-identity health across kitty-specs/.

    Classifies every mission into one of four states (FR-045):

    \\b
    - assigned: mission_id present AND mission_number non-null (fully migrated)
    - pending:  mission_id present AND mission_number null (pre-merge)
    - legacy:   mission_id missing AND mission_number present (needs backfill)
    - orphan:   both fields missing or meta.json unreadable (needs triage)

    Also reports duplicate numeric prefixes (FR-011) and ambiguous selectors
    that would resolve to multiple missions (FR-012).

    Examples:
        spec-kitty doctor identity
        spec-kitty doctor identity --json
        spec-kitty doctor identity --mission 083-foo
        spec-kitty doctor identity --fail-on legacy,orphan
    """
    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)
    run_identity_audit(repo_root, json_output, mission, fail_on)


@app.command(name="topology")
def topology(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit structured JSON output (suitable for CI)"),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Scope report to a single mission slug"),
    ] = None,
) -> None:
    """Report each mission's STORED topology across kitty-specs/.

    Reads the authoritative ``topology`` value persisted in ``meta.json`` WITHOUT
    re-inferring from disk/git. Missions not yet backfilled surface
    ``topology: null`` — run ``spec-kitty migrate backfill-topology`` to persist
    the computed value.

    Examples:
        spec-kitty doctor topology
        spec-kitty doctor topology --json
        spec-kitty doctor topology --mission 083-foo
    """
    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)
    run_topology_audit(repo_root, json_output, mission)


@app.command(name="sparse-checkout")
def sparse_checkout(
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Apply remediation (disable sparse-checkout on primary + worktrees).",
        ),
    ] = False,
) -> None:
    """Detect and optionally remediate legacy sparse-checkout state.

    Without ``--fix``: scans the repo and prints a warning finding
    describing any active sparse-checkout state (primary + lane
    worktrees). Exits 0 when clean, 1 when state is present.

    With ``--fix``: in an interactive TTY, prints a step-by-step plan,
    prompts once for consent, and calls WP03's ``remediate()``. In
    non-interactive / CI environments, prints a remediation pointer and
    exits non-zero without mutating state (FR-023).

    Examples:
        spec-kitty doctor sparse-checkout
        spec-kitty doctor sparse-checkout --fix
    """
    run_sparse_checkout(fix)


def _print_overdue_details(report: ShimRegistryReport, console: Console) -> None:
    console.print()
    console.print("[bold red]Overdue shims must be resolved before release:[/bold red]")
    for e in report.entries:
        if e.status.value == "overdue":
            canonical = (
                ", ".join(e.entry.canonical_import)
                if isinstance(e.entry.canonical_import, list)
                else e.entry.canonical_import
            )
            console.print(f"\n  [red]{e.entry.legacy_path}[/red]")
            console.print(f"    Canonical import : {canonical}")
            console.print(f"    Removal target   : {e.entry.removal_target_release}")
            console.print(f"    Tracker          : {e.entry.tracker_issue}")
            console.print("    Remediation:")
            console.print(
                f"      Option A: Delete src/specify_cli/{e.entry.legacy_path.replace('.', '/')}.py"
                " (or __init__.py)"
            )
            console.print(
                "      Option B: Extend removal_target_release in"
                " docs/migrations/shim-registry.yaml with extension_rationale"
            )


@app.command(name="shim-registry")
def shim_registry(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check for overdue compatibility shims in the shim registry.

    Reads docs/migrations/shim-registry.yaml and compares each entry's
    removal_target_release against the current project version. Fails with
    exit code 1 if any shim is overdue (removal release has shipped but
    shim file still exists on disk).

    Exit codes:
      0  All entries are pending, removed, or grandfathered.
      1  At least one entry is overdue — shim must be deleted or window extended.
      2  Configuration error (registry file or pyproject.toml missing/invalid).

    Examples:
        spec-kitty doctor shim-registry
        spec-kitty doctor shim-registry --json
    """
    from collections import Counter

    from specify_cli.compat import (
        RegistrySchemaError,
        ShimStatus,
        check_shim_registry,
    )

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(2)

    try:
        report = check_shim_registry(repo_root)
    except FileNotFoundError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    except RegistrySchemaError as exc:
        console.print("[red]Registry schema error:[/red]")
        for err in exc.errors:
            console.print(f"  {err}")
        raise typer.Exit(2) from exc
    except KeyError as exc:
        console.print(f"[red]Configuration error:[/red] missing key {exc} in pyproject.toml")
        raise typer.Exit(2) from exc

    if json_output:
        output = {
            "project_version": report.project_version,
            "registry_path": str(report.registry_path),
            "entries": [
                {
                    "legacy_path": e.entry.legacy_path,
                    "canonical_import": e.entry.canonical_import,
                    "removal_target_release": e.entry.removal_target_release,
                    "grandfathered": e.entry.grandfathered,
                    "tracker_issue": e.entry.tracker_issue,
                    "status": e.status.value,
                    "shim_exists": e.shim_exists,
                }
                for e in report.entries
            ],
            "has_overdue": report.has_overdue,
            "exit_code": report.recommended_exit_code,
        }
        console.print_json(json.dumps(output, indent=2))
        raise typer.Exit(report.recommended_exit_code)

    if not report.entries:
        console.print("[green]Shim Registry[/green]: registry is empty — no shims to check.")
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Shim Registry[/bold] — {len(report.entries)} entry/entries"
        f" (project version: {report.project_version})\n"
    )

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Legacy Path", style="cyan", min_width=24)
    table.add_column("Canonical Import", min_width=20)
    table.add_column("Removal Target", min_width=14)
    table.add_column("Status", min_width=12)

    _status_styles: dict[ShimStatus, str] = {
        ShimStatus.PENDING: "[cyan]pending[/cyan]",
        ShimStatus.OVERDUE: "[bold red]OVERDUE[/bold red]",
        ShimStatus.GRANDFATHERED: "[yellow]grandfathered[/yellow]",
        ShimStatus.REMOVED: "[dim]removed[/dim]",
    }

    for e in report.entries:
        canonical = (
            ", ".join(e.entry.canonical_import)
            if isinstance(e.entry.canonical_import, list)
            else e.entry.canonical_import
        )
        table.add_row(
            e.entry.legacy_path,
            canonical,
            e.entry.removal_target_release,
            _status_styles[e.status],
        )

    console.print(table)
    console.print()

    counts = Counter(e.status.value for e in report.entries)
    parts = [f"{v} {k}" for k, v in sorted(counts.items())]
    console.print(f"Summary: {', '.join(parts)}")

    if report.has_overdue:
        _print_overdue_details(report, console)

    console.print()
    raise typer.Exit(report.recommended_exit_code)


@app.command(name="contracts")
def contracts(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Validate the Contract Registry for well-formedness.

    Reads docs/contracts/contract-registry.yaml and validates every record
    against the schema: required fields present, kind/status/enforcement in
    range, semver + tracker refs well-formed, anchors resolve, and — the DIR-041
    self-consistency gate (NFR-003) — NO positional file:line anchoring anywhere.
    Structural validation is the only enforcing gate in v1; the retirement
    absence-sweep is advisory.

    Exit codes:
      0  Registry is well-formed (or empty).
      2  Configuration error (registry file missing) or a schema violation.

    Examples:
        spec-kitty doctor contracts
        spec-kitty doctor contracts --json
    """
    from specify_cli.contracts.registry import (
        ContractRegistrySchemaError,
        check_contract_registry,
    )

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(2)

    try:
        report = check_contract_registry(repo_root)
    except FileNotFoundError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    except ContractRegistrySchemaError as exc:
        console.print("[red]Contract registry schema error:[/red]")
        for err in exc.errors:
            console.print(f"  {err}")
        raise typer.Exit(2) from exc

    if json_output:
        output = {
            "registry_path": str(report.registry_path),
            "record_count": report.record_count,
            "advisory_count": report.advisory_count,
            "enforcing_count": report.enforcing_count,
            "records": [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "status": r.status,
                    "owner": r.owner,
                    "replaced_by": r.replaced_by,
                    "enforcement": r.verification.enforcement,
                    "scan_roots": list(r.consumers.scan_roots),
                }
                for r in report.records
            ],
            "exit_code": 0,
        }
        console.print_json(json.dumps(output, indent=2))
        raise typer.Exit(0)

    if not report.records:
        console.print(
            "[green]Contract Registry[/green]: registry is empty — nothing to validate."
        )
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Contract Registry[/bold] — {report.record_count} record(s)"
        f" ({report.advisory_count} advisory, {report.enforcing_count} enforcing)\n"
    )

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("ID", style="cyan", min_width=24)
    table.add_column("Kind", min_width=14)
    table.add_column("Status", min_width=10)
    table.add_column("Enforcement", min_width=12)
    table.add_column("Owner", min_width=8)
    for r in report.records:
        table.add_row(r.id, r.kind, r.status, r.verification.enforcement, r.owner)

    console.print(table)
    console.print()
    console.print("[green]Contract Registry[/green]: all records are well-formed.")
    console.print()
    raise typer.Exit(0)


@app.command(name="invocation-pairing")
def invocation_pairing(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """List orphan profile-invocation lifecycle records.

    WP05 (#843) wiring: scans
    ``.kittify/events/profile-invocation-lifecycle.jsonl`` for ``started``
    records with no paired ``completed`` or ``failed`` partner. Mid-cycle
    agent crashes show up here. The check observes; it does not remediate.

    Exit codes:
      0  No orphans observed.
      1  At least one orphan found.

    Examples:
        spec-kitty doctor invocation-pairing
        spec-kitty doctor invocation-pairing --json
    """
    from specify_cli.invocation.lifecycle import doctor_orphan_report

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = doctor_orphan_report(repo_root)
    orphan_count_raw = report.get("orphan_count", 0)
    orphan_count = orphan_count_raw if isinstance(orphan_count_raw, int) else 0
    pairing_rate_raw = report.get("pairing_rate", 1.0)
    pairing_rate = pairing_rate_raw if isinstance(pairing_rate_raw, (int, float)) else 1.0
    total_groups_raw = report.get("total_groups", 0)
    total_groups = total_groups_raw if isinstance(total_groups_raw, int) else 0
    orphans_raw = report.get("orphans", [])
    orphans_list: list[dict[str, object]] = (
        [o for o in orphans_raw if isinstance(o, dict)] if isinstance(orphans_raw, list) else []
    )

    if json_output:
        console.print_json(json.dumps(report, indent=2, sort_keys=True))
        raise typer.Exit(1 if orphan_count else 0)

    if orphan_count == 0:
        console.print(
            "[green]Invocation Pairing[/green]: no orphan started records "
            f"(pairing rate: {pairing_rate:.0%}, "
            f"groups: {total_groups})."
        )
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Invocation Pairing[/bold] — {orphan_count} orphan "
        f"started record(s)\n"
    )
    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Canonical Action ID", style="cyan", min_width=24)
    table.add_column("Agent", min_width=10)
    table.add_column("Mission ID", min_width=10)
    table.add_column("WP", min_width=6)
    table.add_column(_STARTED_AT_COLUMN, min_width=20)
    for entry in orphans_list:
        table.add_row(
            str(entry.get("canonical_action_id", "")),
            str(entry.get("agent", "")),
            str(entry.get("mission_id", "")),
            str(entry.get("wp_id") or "-"),
            str(entry.get("started_at", "")),
        )
    console.print(table)
    console.print(
        f"\nPairing rate: {pairing_rate:.0%} "
        f"across {total_groups} group(s)."
    )
    console.print()
    raise typer.Exit(1)


def _run_ops_sweep(repo_root: Path, *, threshold_hours: float, json_output: bool) -> None:
    """Run the stale sweep and exit per contracts/doctor-ops-close-stale.md."""
    import datetime as _dt

    from specify_cli.doctor.ops import close_stale_ops

    report = close_stale_ops(
        repo_root,
        threshold_hours=threshold_hours,
        now=_dt.datetime.now(_dt.UTC),
    )
    # Exit 1 on per-op write/IO errors or when open-but-fresh Ops remain after
    # the sweep (consistent with report mode); already_closed is not a failure.
    exit_code = 1 if (report.has_errors or report.skipped_fresh > 0) else 0

    if json_output:
        console.print_json(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(exit_code)

    console.print(
        f"\n[bold]Ops sweep[/bold] — threshold {report.threshold_hours}h: "
        f"{report.swept} closed as abandoned, {report.skipped_fresh} fresh (skipped)\n"
    )
    if report.open_ops:
        table = Table(box=None, padding=(0, 2), show_edge=False)
        table.add_column("Invocation ID", style="cyan", min_width=26)
        table.add_column("Profile", min_width=10)
        table.add_column(_STARTED_AT_COLUMN, min_width=20)
        table.add_column("Age (h)", justify="right", min_width=8)
        table.add_column("Action", min_width=16)
        for entry in report.open_ops:
            age_text = f"{entry.age_hours:.1f}" if entry.age_hours is not None else "?"
            action_text = entry.action_taken if entry.error is None else f"error: {entry.error}"
            table.add_row(
                entry.invocation_id,
                entry.profile_id,
                entry.started_at,
                age_text,
                action_text,
            )
        console.print(table)
    if report.skipped_fresh:
        console.print(
            "\nFresh open Ops remain — close them with "
            "spec-kitty profile-invocation complete, or re-run with --threshold 0."
        )
    console.print()
    raise typer.Exit(exit_code)


@app.command(name="ops")
def ops(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
    close_stale: Annotated[
        bool,
        typer.Option(
            "--close-stale",
            help="Close open Ops older than --threshold as abandoned (closed_by=doctor_sweep)",
        ),
    ] = False,
    threshold: Annotated[
        float | None,
        typer.Option(
            "--threshold",
            help="Staleness threshold in hours (default 24; 0 closes all). Requires --close-stale.",
        ),
    ] = None,
) -> None:
    """List orphan Op records; --close-stale sweeps stale ones closed as abandoned."""
    from specify_cli.doctor.ops import list_orphan_ops

    if threshold is not None and not close_stale:
        raise typer.BadParameter("--threshold requires --close-stale")

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    if close_stale:
        _run_ops_sweep(
            repo_root,
            threshold_hours=threshold if threshold is not None else 24.0,
            json_output=json_output,
        )

    orphans = list_orphan_ops(repo_root)
    if json_output:
        payload = [{"path": str(path.relative_to(repo_root))} for path in orphans]
        console.print_json(json.dumps(payload, indent=2))
        raise typer.Exit(1 if orphans else 0)

    if not orphans:
        console.print("[green]Ops[/green]: no orphan op records found.")
        raise typer.Exit(0)

    console.print(f"\n[bold]Ops[/bold] — {len(orphans)} orphan op record(s)\n")
    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Path", style="cyan")
    for path in orphans:
        table.add_row(str(path.relative_to(repo_root)))
    console.print(table)
    console.print(
        "\nThese op records were started but never completed. "
        "Run spec-kitty doctor ops --json for machine-readable output."
    )
    console.print()
    raise typer.Exit(1)


@app.command(name="orphan-daemons")
def orphan_daemons(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """List orphan daemon owner records and emit retirement hints.

    Implements FR-010 of the identity-boundary mission: an orphan
    daemon owner record is one whose recorded PID is dead OR whose
    recorded executable path no longer exists on disk. Each orphan
    is printed with a copy-pasteable retirement command that removes
    the on-disk ``owner.json`` so the next ``sync status --check``
    returns clean.

    Exit codes:
      0  No orphan records.
      1  At least one orphan record found.

    Examples:
        spec-kitty doctor orphan-daemons
        spec-kitty doctor orphan-daemons --json
    """
    run_orphan_daemons(json_output)


@app.command(name="restart-daemon")
def restart_daemon_cmd(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit a single JSON object instead of human-readable text.",
        ),
    ] = False,
) -> None:
    """Stop the registered sync daemon and respawn it at the foreground.

    Composes the existing daemon stop + launch primitives so the operator
    has a one-shot remedy when the foreground process and the registered
    daemon disagree on any of the six canonical D-3 fields (version,
    executable, source, server URL, team/user, or queue DB path).

    Exit codes:
      0  Daemon restarted (or stale owner record cleaned and respawned).
      1  No registered daemon — run ``spec-kitty sync now`` to launch one.
      2  Daemon stop succeeded but respawn failed; system is stopped.
      3  Daemon stop failed (unresponsive); owner record left intact.

    Examples:
        spec-kitty doctor restart-daemon
        spec-kitty doctor restart-daemon --json
    """
    run_restart_daemon(json_output)


@app.command(name="mission-state")
def mission_state(
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Run mission-state audit (required to proceed)"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Repair mission-state artifacts in place and write a migration manifest"),
    ] = False,
    teamspace_dry_run: Annotated[
        bool,
        typer.Option(
            "--teamspace-dry-run",
            help="Synthesize canonical TeamSpace envelopes from local state and validate them",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON report to stdout"),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Scope to a single mission handle"),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option(
            "--fail-on",
            help=(
                "Exit 1 if findings meet a gate "
                "(error|warning|info|teamspace-blocker)"
            ),
        ),
    ] = None,
    fixture_dir: Annotated[
        Path | None,
        typer.Option("--fixture-dir", help="Override scan root (for testing)"),
    ] = None,
    include_fixtures: Annotated[
        bool,
        typer.Option(
            "--include-fixtures",
            help="Audit the bundled mission-state survey fixtures",
        ),
    ] = False,
    manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest-path", help="Path for --fix migration manifest"),
    ] = None,
    allow_dirty: Annotated[
        bool,
        typer.Option("--allow-dirty", help="Allow --fix when relevant git paths are already dirty"),
    ] = False,
) -> None:
    """Audit, repair, or TeamSpace-validate mission-state shapes."""
    # Resolve the project root HERE, through the shim's ``locate_project_root``
    # binding — the patchable seam (#2059, mirrors the ``workspaces`` shell). A
    # ``None`` root is valid for a fixtures-only run, so it is forwarded as-is;
    # the sibling reconciles ``None`` against ``--fixture-dir`` / fixtures.
    try:
        resolved_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    run_mission_state(
        audit=audit,
        fix=fix,
        teamspace_dry_run=teamspace_dry_run,
        json_output=json_output,
        mission=mission,
        fail_on=fail_on,
        fixture_dir=fixture_dir,
        include_fixtures=include_fixtures,
        manifest_path=manifest_path,
        allow_dirty=allow_dirty,
        repo_root=resolved_root,
    )


# ---------------------------------------------------------------------------
# WP07 T035 + T048: `spec-kitty doctor doctrine` — org-layer snapshot health.
# ---------------------------------------------------------------------------


@app.command(name="doctrine")
def doctrine_check(
    json_output: Annotated[
        bool, typer.Option("--json", help="Machine-readable JSON output")
    ] = False,
) -> None:
    """Check org doctrine snapshot status and list installed pack artifacts.

    Exit code reflects health (WP01, operator directive: loud over hidden): the
    command exits **1 when the report is unhealthy** and 0 only when healthy
    (``report.healthy`` drives the code on every output path). A clear RC=1 with
    a surfaced error is preferred over an RC=0 that hides a defect.  It
    enumerates each configured org pack (from ``.kittify/config.yaml``), prints
    its on-disk version (``git describe`` for git-managed packs, otherwise the
    ``pack-manifest.yaml`` ``pack_version``), per-artifact YAML counts, and
    ``org-charter.yaml`` policy status when present.

    Override governance (FR-010 / FR-012): when org packs are configured, any
    ``org:``-provenance override of a built-in DRG node that is NOT sanctioned
    by ``.kittify/doctrine/replaceable-builtins.yaml`` is reported as an
    ``unsanctioned_overrides`` finding and flips the report unhealthy (RC=1).
    Project-tier (``.kittify/doctrine/``) overrides of built-ins are
    intentionally **ungoverned** — project doctrine is the trusted operator tier
    and is not gated by the consumer-facing allowlist; only org-tier overrides
    are adjudicated.

    Examples:
        spec-kitty doctor doctrine
        spec-kitty doctor doctrine --json
    """
    from specify_cli.doctrine.config import load_pack_registry

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    registry = load_pack_registry(repo_root)

    # WP08: build the doctrine health report ONCE (single DoctrineService /
    # org-DRG load).  Both the human and JSON surfaces are passthroughs of this
    # report — there is no parallel assembly (R-011-C / NFR-001).
    report = _collect_profile_health(repo_root)

    # WP09 T050 / FR-018: the Selections diagnostic is independent of whether
    # org packs are configured, so build it for both branches.
    selection_block = _build_selection_block(repo_root)

    # WP01 (C5, operator directive): loud RC=1 over hidden RC=0. The honest
    # ``report.healthy`` flag drives the exit code on every output path.
    exit_code = 0 if report.healthy else 1

    if not registry.packs:
        _emit_doctrine_no_packs(report, selection_block, json_output=json_output)
        raise typer.Exit(exit_code)

    pack_entries = _build_pack_entries(registry, repo_root)

    # FR-010: annotate present packs with derived profile health so the human
    # renderer greens/yellows from health, not snapshot presence.
    _attach_pack_health(pack_entries, report)

    # Detect override collisions across the full resolved doctrine surface
    # (FR-003 wording + ADR 2026-05-16-1).
    collision_summaries = _collect_doctrine_collisions(repo_root)

    if json_output:
        _emit_doctrine_json(
            report,
            org_configured=True,
            pack_entries=pack_entries,
            collision_summaries=collision_summaries,
            selection_block=selection_block,
        )
        raise typer.Exit(exit_code)

    _emit_doctrine_human(
        pack_entries,
        collision_summaries,
        selection_block,
        repo_root,
    )
    # WP08 (FR-010): surface unsanctioned built-in overrides loudly (the JSON
    # surface already carries them via the ``org_drg`` passthrough).
    _render_unsanctioned_override_findings(report)
    raise typer.Exit(exit_code)


def _render_unsanctioned_override_findings(report: DoctrineHealthReport) -> None:
    """Render the loud ``unsanctioned built-in override`` block (FR-010 / FR-012).

    Reads the dedicated ``org_drg['unsanctioned_overrides']`` key (assembled in
    ``_doctrine_collect``) — narrowed with ``isinstance`` so no ``# type: ignore``
    is needed — rather than re-deriving the merged blob in ``org_drg['errors']``.
    A no-op when there are no findings (e.g. no org packs configured).
    """
    org_drg = report.org_drg
    findings = org_drg.get("unsanctioned_overrides") if isinstance(org_drg, dict) else None
    if not isinstance(findings, list) or not findings:
        return
    console.print(
        f"\n[bold red]Unsanctioned built-in override(s)[/bold red] — "
        f"{len(findings)} not allowlisted\n"
    )
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        console.print(
            f"  • [red]{finding.get('urn')}[/red] "
            f"({finding.get('kind')}): {finding.get('why')}"
        )
    console.print(
        "  [dim]Add the URN to .kittify/doctrine/replaceable-builtins.yaml "
        "(with a reason for directives) or remove the org override.[/dim]"
    )
    console.print(
        "  [dim]Only org-tier overrides are adjudicated; project-tier "
        "(.kittify/doctrine/) overrides are intentionally ungoverned (FR-012).[/dim]"
    )


# ---------------------------------------------------------------------------
# #1348 (WP04): coordination workspace + lane sparse-checkout health
# ---------------------------------------------------------------------------


@app.command(name="coordination")
def coordination_health(
    json_output: Annotated[
        bool, typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Run the WP04 #1348 coordination + sparse-checkout health checks.

    Iterates over every mission under ``kitty-specs/`` whose ``meta.json``
    declares a ``coordination_branch`` field, runs the coord-worktree
    and lane-sparse-checkout health checks, and prints findings.

    Also runs the minimum git-version (RR-01) check.

    Exits with code 1 if any ``error`` finding is emitted; ``warning``
    findings exit 0 but are still printed.
    """
    run_coordination_health(json_output)
