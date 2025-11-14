"""Dashboard command implementation."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional

import typer

from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.dashboard import ensure_dashboard_running, stop_dashboard


def dashboard(
    port: Optional[int] = typer.Option(
        None,
        "--port",
        help="Preferred port for the dashboard (falls back to the first available port).",
    ),
    kill: bool = typer.Option(
        False,
        "--kill",
        help="Stop the running dashboard for this project and clear its metadata.",
    ),
) -> None:
    """Open or stop the Spec Kitty dashboard."""
    project_root = get_project_root_or_exit()

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

    try:
        dashboard_url, active_port, started = ensure_dashboard_running(project_root, preferred_port=port)
    except Exception as exc:  # pragma: no cover
        # Before reporting error, verify dashboard isn't actually running
        # (handles race condition where dashboard starts but health check times out)
        import httpx
        from specify_cli.dashboard.server import find_free_port

        # Try checking a few common ports
        found_port = None
        found_url = None
        for check_port in range(port or 9280, (port or 9280) + 10):
            try:
                test_url = f"http://127.0.0.1:{check_port}/api/health"
                response = httpx.get(test_url, timeout=1.0)
                if response.status_code == 200:
                    data = response.json()
                    if str(Path(data.get("project_path", "")).resolve()) == str(project_root.resolve()):
                        # Found our dashboard!
                        found_port = check_port
                        found_url = f"http://127.0.0.1:{check_port}"
                        break
            except:
                continue

        if found_url and found_port:
            # Dashboard IS running, just health check timed out
            dashboard_url = found_url
            active_port = found_port
            started = True
            console.print(f"[yellow]⚠️  Dashboard health check timed out but server is running[/yellow]")
            console.print()
        else:
            # Dashboard truly failed
            console.print("[red]❌ Unable to start or locate the dashboard[/red]")
            console.print(f"   {exc}")
            console.print()
            console.print("[yellow]💡 Try running:[/yellow]")
            console.print(f"  [cyan]cd {project_root}[/cyan]")
            console.print("  [cyan]spec-kitty init .[/cyan]")
            console.print()
            raise typer.Exit(1)

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

    try:
        webbrowser.open(dashboard_url)
        console.print("[green]✅ Opening dashboard in your browser...[/green]")
        console.print()
    except Exception:
        console.print("[yellow]⚠️  Could not automatically open browser[/yellow]")
        console.print(f"   Please open this URL manually: [cyan]{dashboard_url}[/cyan]")
        console.print()


__all__ = ["dashboard"]
