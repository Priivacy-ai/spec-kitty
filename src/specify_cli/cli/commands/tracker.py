"""Tracker commands for provider bindings, mappings, and sync operations."""

from __future__ import annotations

import json
import os
from typing import Any

import typer

from specify_cli.tracker.config import require_repo_root
from specify_cli.tracker.feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from specify_cli.tracker.service import TrackerService, TrackerServiceError, parse_kv_pairs

app = typer.Typer(help="Task tracker integration commands")
map_app = typer.Typer(help="Work-package mapping commands")
sync_app = typer.Typer(help="Tracker synchronization commands")
app.add_typer(map_app, name="map")
app.add_typer(sync_app, name="sync")


def _print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _require_enabled() -> None:
    if is_saas_sync_enabled():
        return
    typer.secho(saas_sync_disabled_message(), fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


def _service() -> TrackerService:
    repo_root = require_repo_root()
    return TrackerService(repo_root)


def _doctrine_modes() -> tuple[str, ...]:
    return (
        "external_authoritative",
        "spec_kitty_authoritative",
        "split_ownership",
    )


def _run_or_exit(fn):
    try:
        return fn()
    except (RuntimeError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.callback()
def tracker_callback() -> None:
    """Guard tracker commands behind the SaaS sync feature flag."""
    _require_enabled()


@app.command("providers")
def providers_command(as_json: bool = typer.Option(False, "--json", help="Render provider list as JSON")) -> None:
    """List supported tracker providers."""

    def _run() -> None:
        providers = list(TrackerService.supported_providers())
        if as_json:
            _print_json({"providers": providers})
            return

        typer.echo("Supported providers:")
        for provider in providers:
            typer.echo(f"- {provider}")

    _run_or_exit(_run)


@app.command("bind")
def bind_command(
    provider: str = typer.Option(..., "--provider", help="Provider name (jira, linear, azure_devops, github, gitlab, beads, fp)"),
    workspace: str = typer.Option(..., "--workspace", help="Provider workspace/team/project identifier"),
    doctrine_mode: str = typer.Option(
        "external_authoritative",
        "--doctrine-mode",
        help="Doctrine mode: external_authoritative | spec_kitty_authoritative | split_ownership",
    ),
    field_owners: list[str] = typer.Option([], "--field-owner", help="Split ownership mapping: field=owner"),
    credentials: list[str] = typer.Option([], "--credential", help="Provider credential key/value: key=value"),
) -> None:
    """Bind the current project to an issue tracker workspace."""

    def _run() -> None:
        mode = doctrine_mode.strip().lower()
        if mode not in set(_doctrine_modes()):
            raise TrackerServiceError(
                f"Invalid doctrine mode '{doctrine_mode}'. Expected one of: {', '.join(_doctrine_modes())}"
            )

        parsed_field_owners = parse_kv_pairs(field_owners)
        parsed_credentials = parse_kv_pairs(credentials)

        config = _service().bind(
            provider=provider,
            workspace=workspace,
            doctrine_mode=mode,
            doctrine_field_owners=parsed_field_owners,
            credentials=parsed_credentials,
        )

        typer.echo("Tracker binding saved")
        typer.echo(f"- provider: {config.provider}")
        typer.echo(f"- workspace: {config.workspace}")
        typer.echo(f"- doctrine_mode: {config.doctrine_mode}")
        typer.echo(f"- field_owners: {len(config.doctrine_field_owners)}")
        typer.echo(f"- credentials_saved: {'yes' if bool(parsed_credentials) else 'no'}")

    _run_or_exit(_run)


@app.command("status")
def status_command(as_json: bool = typer.Option(False, "--json", help="Render status as JSON")) -> None:
    """Show tracker binding and local cache status."""

    def _run() -> None:
        payload = _service().status()

        if as_json:
            _print_json(payload)
            return

        if not payload.get("configured"):
            typer.echo("Tracker is not configured")
            return

        typer.echo("Tracker status")
        typer.echo(f"- provider: {payload.get('provider')}")
        typer.echo(f"- workspace: {payload.get('workspace')}")
        typer.echo(f"- doctrine_mode: {payload.get('doctrine_mode')}")
        typer.echo(f"- db_path: {payload.get('db_path')}")
        typer.echo(f"- issue_count: {payload.get('issue_count')}")
        typer.echo(f"- mapping_count: {payload.get('mapping_count')}")
        typer.echo(f"- credentials_present: {'yes' if payload.get('credentials_present') else 'no'}")

    _run_or_exit(_run)


@map_app.command("add")
def map_add_command(
    wp_id: str = typer.Option(..., "--wp-id", help="Work package ID (e.g., WP01)"),
    external_id: str = typer.Option(..., "--external-id", help="External issue ID"),
    external_key: str | None = typer.Option(None, "--external-key", help="External issue key"),
    external_url: str | None = typer.Option(None, "--external-url", help="External issue URL"),
) -> None:
    """Add or update a local WP-to-external issue mapping."""

    def _run() -> None:
        _service().map_add(
            wp_id=wp_id,
            external_id=external_id,
            external_key=external_key,
            external_url=external_url,
        )
        typer.echo(f"Mapping saved: {wp_id} -> {external_id}")

    _run_or_exit(_run)


@map_app.command("list")
def map_list_command(as_json: bool = typer.Option(False, "--json", help="Render mappings as JSON")) -> None:
    """List local tracker mappings."""

    def _run() -> None:
        mappings = _service().map_list()
        if as_json:
            _print_json({"mappings": mappings})
            return

        if not mappings:
            typer.echo("No mappings found")
            return

        typer.echo("Mappings")
        for row in mappings:
            key = row.get("external_key") or row.get("external_id")
            typer.echo(f"- {row.get('wp_id')}: {row.get('system')}:{key}")

    _run_or_exit(_run)


@sync_app.command("pull")
def sync_pull_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Pull tracker updates into the local cache."""

    def _run() -> None:
        payload = _service().sync_pull(limit=limit)
        if as_json:
            _print_json(payload)
            return

        stats = payload.get("stats", {})
        typer.echo(f"Pulled from {payload.get('provider')}")
        typer.echo(f"- created: {stats.get('pulled_created', 0)}")
        typer.echo(f"- updated: {stats.get('pulled_updated', 0)}")
        typer.echo(f"- skipped: {stats.get('skipped', 0)}")
        typer.echo(f"- conflicts: {len(payload.get('conflicts', []))}")
        typer.echo(f"- errors: {len(payload.get('errors', []))}")

    _run_or_exit(_run)


@sync_app.command("push")
def sync_push_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Push local tracker changes to the upstream provider."""

    def _run() -> None:
        payload = _service().sync_push(limit=limit)
        if as_json:
            _print_json(payload)
            return

        stats = payload.get("stats", {})
        typer.echo(f"Pushed to {payload.get('provider')}")
        typer.echo(f"- created: {stats.get('pushed_created', 0)}")
        typer.echo(f"- updated: {stats.get('pushed_updated', 0)}")
        typer.echo(f"- skipped: {stats.get('skipped', 0)}")
        typer.echo(f"- conflicts: {len(payload.get('conflicts', []))}")
        typer.echo(f"- errors: {len(payload.get('errors', []))}")

    _run_or_exit(_run)


@sync_app.command("run")
def sync_run_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Run pull+push synchronization in one operation."""

    def _run() -> None:
        payload = _service().sync_run(limit=limit)
        if as_json:
            _print_json(payload)
            return

        stats = payload.get("stats", {})
        typer.echo(f"Sync run completed ({payload.get('provider')})")
        typer.echo(f"- pulled_created: {stats.get('pulled_created', 0)}")
        typer.echo(f"- pulled_updated: {stats.get('pulled_updated', 0)}")
        typer.echo(f"- pushed_created: {stats.get('pushed_created', 0)}")
        typer.echo(f"- pushed_updated: {stats.get('pushed_updated', 0)}")
        typer.echo(f"- skipped: {stats.get('skipped', 0)}")
        typer.echo(f"- conflicts: {len(payload.get('conflicts', []))}")
        typer.echo(f"- errors: {len(payload.get('errors', []))}")

    _run_or_exit(_run)


@sync_app.command("publish")
def sync_publish_command(
    server_url: str = typer.Option(
        os.getenv("SAAS_API_URL", ""),
        "--server-url",
        help="Spec Kitty SaaS base URL",
    ),
    auth_token: str | None = typer.Option(
        os.getenv("SAAS_AUTH_TOKEN") or None,
        "--auth-token",
        help="Bearer token for SaaS API authentication",
    ),
    timeout_seconds: float = typer.Option(10.0, "--timeout-seconds", min=1.0, max=120.0),
    as_json: bool = typer.Option(False, "--json", help="Render publish result as JSON"),
) -> None:
    """Publish local tracker snapshot to Spec Kitty SaaS."""

    def _run() -> None:
        if not server_url.strip():
            raise TrackerServiceError("Missing --server-url (or SAAS_API_URL)")

        payload = _service().sync_publish(
            server_url=server_url,
            auth_token=auth_token,
            timeout_seconds=timeout_seconds,
        )

        if as_json:
            _print_json(payload)
            return

        typer.echo("Snapshot publish complete")
        typer.echo(f"- endpoint: {payload.get('endpoint')}")
        typer.echo(f"- status_code: {payload.get('status_code')}")
        typer.echo(f"- ok: {'yes' if payload.get('ok') else 'no'}")
        typer.echo(f"- idempotency_key: {payload.get('idempotency_key')}")

    _run_or_exit(_run)


@app.command("unbind")
def unbind_command() -> None:
    """Remove tracker binding and provider credentials for this project."""

    def _run() -> None:
        _service().unbind()
        typer.echo("Tracker binding removed")

    _run_or_exit(_run)
