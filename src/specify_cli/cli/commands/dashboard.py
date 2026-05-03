"""Dashboard command implementation."""

from __future__ import annotations

import json
import webbrowser
from typing import TYPE_CHECKING, Any

import typer

from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.dashboard import ensure_dashboard_running, stop_dashboard

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from dashboard.services.registry import MissionRecord


def _mission_record_to_cli_dict(record: "MissionRecord") -> dict[str, Any]:
    """Map a MissionRecord to the legacy ``build_mission_registry`` dict shape.

    Mirrors the wire shape produced by
    ``specify_cli.dashboard.scanner.build_mission_registry`` so existing
    consumers of ``spec-kitty dashboard --json`` see byte-identical output
    after the registry migration. The legacy shape has these keys:

    - ``mission_id``: str — ULID or pseudo-key (legacy:/orphan:)
    - ``mission_slug``: str — directory name
    - ``display_number``: int | None — numeric prefix for display sort
    - ``mid8``: str | None — first 8 chars of mission_id (None for pseudo-keys)
    - ``feature_dir``: str — absolute path as string

    The registry uses an empty string ``""`` for ``mid8`` on legacy/orphan
    records; the legacy CLI shape uses ``None`` for the same case, so we
    coerce ``""`` → ``None`` here. ``mission_id`` for legacy missions is
    already prefixed with ``legacy:`` in both layers.
    """
    is_pseudo = record.mission_id.startswith(("legacy:", "orphan:"))
    return {
        "mission_id": record.mission_id,
        "mission_slug": record.mission_slug,
        "display_number": record.display_number,
        "mid8": None if (is_pseudo or not record.mid8) else record.mid8,
        "feature_dir": str(record.feature_dir),
    }


def _collect_missions_with_worktrees(
    project_root: "Path",
) -> "tuple[list[MissionRecord], dict[str, MissionRecord]]":
    """Aggregate missions from the main repo + every worktree in display order.

    The legacy ``build_mission_registry`` walked both ``kitty-specs/`` and
    every ``.worktrees/<wt>/kitty-specs/`` to surface missions that exist
    only in a worktree (e.g., a freshly-created spec on a feature branch).
    The canonical ``MissionRegistry`` is intentionally scoped to one
    project root per instance — its contract is that
    ``list_missions()`` returns missions under that project's ``kitty-specs/``.

    To preserve the ``spec-kitty dashboard --json`` parity contract, this
    helper instantiates one registry per worktree and merges the results
    with the main-repo registry. Dedup follows the legacy
    ``gather_feature_paths`` rule: **dedup by mission directory name**
    (``mission_slug``), with the main repo winning over worktree copies
    (since worktree ``meta.json`` may carry a stale ``mission_id`` from
    when the worktree branched off — a mismatch that would otherwise
    surface a same-slug mission twice under different ULIDs).

    Returns a (display_order, registry_dict) pair. The registry_dict maps
    the legacy registry-key shape (``mission_id`` / ``legacy:<slug>`` /
    ``orphan:<slug>``) to the ``MissionRecord`` instance the legacy CLI
    would have surfaced.
    """
    from dashboard.services.registry import MissionRegistry

    # Dedup by mission_slug (dir name) — matches legacy gather_feature_paths.
    by_slug: dict[str, "MissionRecord"] = {}

    # Worktrees first (lower priority) so main-repo records overwrite.
    worktrees_root = project_root / ".worktrees"
    if worktrees_root.exists():
        for worktree_dir in sorted(worktrees_root.iterdir()):
            if not worktree_dir.is_dir():
                continue
            wt_specs = worktree_dir / "kitty-specs"
            if not wt_specs.exists():
                continue
            try:
                wt_reg = MissionRegistry(project_dir=worktree_dir)
                for record in wt_reg.list_missions():
                    by_slug[record.mission_slug] = record
            except Exception:  # pragma: no cover - defensive parity branch
                continue

    # Main repo last (higher priority); overwrites any worktree duplicates.
    main_reg = MissionRegistry(project_dir=project_root)
    main_records = main_reg.list_missions()
    main_slugs: set[str] = set()
    for record in main_records:
        by_slug[record.mission_slug] = record
        main_slugs.add(record.mission_slug)

    # Build the ordered list: main repo first (in registry display order),
    # then worktree-only entries appended in display_number+slug order so
    # the result is deterministic. This mirrors the legacy CLI output
    # (which sorted purely by display_number then slug).
    ordered_main = [by_slug[r.mission_slug] for r in main_records]
    worktree_only = sorted(
        (rec for slug, rec in by_slug.items() if slug not in main_slugs),
        key=lambda r: (
            r.display_number if r.display_number is not None else 10**9,
            r.mission_slug,
        ),
    )
    ordered = ordered_main + worktree_only

    # Build the keyed dict using the legacy registry-key contract:
    # - mission_id (ULID) when present
    # - "legacy:<slug>" when meta.json has mission_number but no mission_id
    # - "orphan:<slug>" when neither is present
    by_key: dict[str, "MissionRecord"] = {}
    for record in ordered:
        by_key[record.mission_id] = record
    return ordered, by_key


def dashboard(
    port: int | None = typer.Option(
        None,
        "--port",
        help="Preferred port for the dashboard (falls back to the first available port).",
    ),
    kill: bool = typer.Option(
        False,
        "--kill",
        help="Stop the running dashboard for this project and clear its metadata.",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Open dashboard URL in your default browser (disabled by default).",
    ),
    emit_json: bool = typer.Option(
        False,
        "--json",
        help=(
            "Print the mission registry as JSON (keyed by mission_id) and exit. "
            "Does not start the dashboard server."
        ),
    ),
    transport: str | None = typer.Option(
        None,
        "--transport",
        help=(
            "Dashboard transport stack: 'legacy' (BaseHTTPServer) or 'fastapi'. "
            "Overrides the dashboard.transport value in .kittify/config.yaml. "
            "Default (when neither flag nor config is set) is 'fastapi'."
        ),
    ),
    bench_exit_after_first_byte: bool = typer.Option(
        False,
        "--bench-exit-after-first-byte",
        hidden=True,
        help="Exit immediately after the first byte is served (used by scripts/bench_dashboard_startup.py).",
    ),
) -> None:
    """Open or stop the Spec Kitty dashboard."""
    project_root = get_project_root_or_exit()

    # --json: emit mission registry keyed by mission_id and exit early.
    if emit_json:
        # Per DIRECTIVE_API_DEPENDENCY_DIRECTION (mission
        # mission-registry-and-api-boundary-doctrine-01KQPDBB), the CLI
        # consumes mission data via the canonical MissionRegistry rather
        # than importing the scanner directly. The architectural test in
        # tests/architectural/test_transport_does_not_import_scanner.py
        # (WP05) will enforce that this module has no scanner imports.
        ordered_missions, _ = _collect_missions_with_worktrees(project_root)
        registry_dict = {m.mission_id: _mission_record_to_cli_dict(m) for m in ordered_missions}
        display_order = [m.mission_id for m in ordered_missions]
        payload = {
            "missions": registry_dict,
            "display_order": display_order,
        }
        console.print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    console.print()

    if kill:
        stopped, message = stop_dashboard(project_root)
        console.print(f"[green]✅ {message}[/green]" if stopped else f"[yellow]⚠️  {message}[/yellow]")
        console.print()
        return

    if port is not None and not (1 <= port <= 65535):
        console.print("[red]❌ Invalid port specified. Use a value between 1 and 65535.[/red]")
        console.print()
        raise typer.Exit(1)

    if transport is not None and transport not in ("legacy", "fastapi"):
        console.print(
            f"[red]❌ Unknown --transport value: {transport!r}. Use 'legacy' or 'fastapi'.[/red]"
        )
        raise typer.Exit(1)

    try:
        dashboard_url, active_port, started = ensure_dashboard_running(
            project_root, preferred_port=port, transport=transport,
        )
    except FileNotFoundError as exc:  # Missing .kittify directory
        console.print("[red]❌ Dashboard metadata not found[/red]")
        console.print(f"   {exc}")
        console.print()
        console.print("[yellow]💡 Initialize this project first:[/yellow]")
        console.print(f"  [cyan]cd {project_root}[/cyan]")
        console.print("  [cyan]spec-kitty init .[/cyan]")
        console.print()
        raise typer.Exit(1) from exc
    except OSError as exc:  # Port conflict or permission error
        error_msg = str(exc).lower()
        if "address already in use" in error_msg or "port" in error_msg:
            console.print("[red]❌ Port conflict detected[/red]")
            console.print(f"   {exc}")
            console.print()
            console.print("[yellow]💡 Try these steps:[/yellow]")
            if port:
                console.print(f"  1. Use a different port: [cyan]spec-kitty dashboard --port {port + 1}[/cyan]")
            else:
                console.print("  1. Use a specific port: [cyan]spec-kitty dashboard --port 9238[/cyan]")
            console.print("  2. Or kill existing dashboard: [cyan]spec-kitty dashboard --kill[/cyan]")
            console.print()
        else:
            console.print("[red]❌ Unable to start dashboard[/red]")
            console.print(f"   {exc}")
            console.print()
        raise typer.Exit(1) from exc
    except Exception as exc:  # pragma: no cover
        console.print("[red]❌ Unable to start or locate the dashboard[/red]")
        console.print(f"   {exc}")
        console.print()
        console.print("[yellow]💡 Try running:[/yellow]")
        console.print(f"  [cyan]cd {project_root}[/cyan]")
        console.print("  [cyan]spec-kitty init .[/cyan]")
        console.print()
        raise typer.Exit(1) from exc

    console.print("[bold green]Spec Kitty Dashboard[/bold green]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]")
    console.print()
    console.print(f"  [bold cyan]Project Root:[/bold cyan] {project_root}")
    console.print(f"  [bold cyan]URL:[/bold cyan] {dashboard_url}")
    console.print(f"  [bold cyan]Port:[/bold cyan] {active_port}")
    if port is not None and port != active_port:
        console.print(f"  [yellow]⚠️ Requested port {port} was unavailable; using {active_port} instead.[/yellow]")
    console.print()

    status_msg = (
        f"  [green]✅ Status:[/green] Started new dashboard instance on port {active_port}"
        if started
        else f"  [green]✅ Status:[/green] Dashboard already running on port {active_port}"
    )
    console.print(status_msg)
    console.print()
    console.print("[cyan]" + "=" * 60 + "[/cyan]")
    console.print()

    if open_browser:
        try:
            webbrowser.open(dashboard_url)
            console.print("[green]✅ Opening dashboard in your browser...[/green]")
            console.print()
        except Exception:
            console.print("[yellow]⚠️  Could not automatically open browser[/yellow]")
            console.print(f"   Please open this URL manually: [cyan]{dashboard_url}[/cyan]")
            console.print()
    else:
        console.print("[dim]Browser auto-open is disabled by default.[/dim]")
        console.print(f"[dim]Open manually: [cyan]{dashboard_url}[/cyan] (or use --open)[/dim]")
        console.print()


__all__ = ["dashboard"]
