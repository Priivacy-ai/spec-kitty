"""Tracker commands for provider bindings, mappings, and sync operations.

Dispatches to SaaS-backed providers (linear, jira, github, gitlab) via the
Spec Kitty SaaS control plane, or to local providers (beads, fp) via
direct connectors.  Provider credentials are never accepted for SaaS-backed
providers -- authentication flows through ``spec-kitty auth login``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.tracker.config import (
    LOCAL_PROVIDERS,
    REMOVED_PROVIDERS,
    SAAS_PROVIDERS,
    TrackerProjectConfig,
    load_tracker_config,
    require_repo_root,
)
from specify_cli.sync.project_identity import ensure_identity
from specify_cli.tracker.discovery import BindResult, ResolutionResult
from specify_cli.tracker.factory import normalize_provider
from specify_cli.saas.readiness import evaluate_readiness
from specify_cli.saas.rollout import is_saas_sync_enabled, saas_sync_disabled_message
from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig
from specify_cli.tracker.service import TrackerService, TrackerServiceError, parse_kv_pairs

app = typer.Typer(
    help=(
        "Task tracker integration commands.\n\n"
        "SaaS-backed providers (linear, jira, github, gitlab) route through "
        "the Spec Kitty SaaS control plane.  Local providers (beads, fp) use "
        "direct connectors."
    )
)
map_app = typer.Typer(help="Work-package mapping commands")
sync_app = typer.Typer(help="Tracker synchronization commands")
app.add_typer(map_app, name="map")
app.add_typer(sync_app, name="sync")

# ---------------------------------------------------------------------------
# Stable wording constants (asserted byte-for-byte by tests)
# ---------------------------------------------------------------------------

_MANUAL_MODE_MESSAGE = (
    'Background sync is in manual mode (`[sync].background_daemon = "manual"`).\n'
    "Run `spec-kitty sync run` to perform a one-shot remote sync."
)

_MANUAL_MODE_SYNC_RUN_MESSAGE = (
    "Background sync is in manual mode. Running a one-shot remote sync now."
)


def _print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _resolve_active_feature_slug(repo_root: Path) -> str | None:
    """Return the active feature slug from .kittify/meta.json, or None.

    Used by _check_readiness to supply a feature_slug when
    require_mission_binding=True.  A missing or unreadable meta.json is
    treated as "no active feature" — the readiness evaluator handles
    MISSING_MISSION_BINDING gracefully in that case.
    """
    try:
        meta_path = repo_root / ".kittify" / "meta.json"
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        slug = data.get("feature_slug") or data.get("slug")
        return str(slug) if slug else None
    except Exception:  # noqa: BLE001
        return None


def _check_readiness(
    *,
    require_mission_binding: bool,
    probe_reachability: bool,
) -> None:
    """Check hosted readiness; raise typer.Exit(1) with actionable message on failure.

    Calls evaluate_readiness with the supplied flags and the current repo root.
    On non-READY results, prints message + next_action to stderr and exits 1.
    """
    try:
        repo_root = require_repo_root()
    except Exception as exc:  # noqa: BLE001
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    feature_slug = _resolve_active_feature_slug(repo_root)
    result = evaluate_readiness(
        repo_root=repo_root,
        feature_slug=feature_slug,
        require_mission_binding=require_mission_binding,
        probe_reachability=probe_reachability,
    )
    if not result.is_ready:
        typer.secho(result.message, fg=typer.colors.RED, err=True)
        if result.next_action:
            typer.echo(result.next_action, err=True)
        raise typer.Exit(1)


def _check_daemon_policy(*, is_sync_run: bool = False) -> None:
    """Pre-flight: handle manual daemon policy for sync sub-commands.

    For sync pull/push/publish: prints the manual-mode message and exits 0.
    For sync run (is_sync_run=True): prints the one-shot message and returns
    (does NOT exit — sync run proceeds as a foreground one-shot).

    **Only applies to SaaS-backed bindings.**  Callers that may hit a local
    provider should invoke :func:`_check_sync_readiness` or manually gate on
    :func:`_is_local_binding` before calling this helper.  The background
    daemon belongs to the SaaS sync path; local providers use direct
    connectors and are unaffected by the policy.
    """
    cfg = SyncConfig()
    if cfg.get_background_daemon() == BackgroundDaemonPolicy.MANUAL:
        if is_sync_run:
            typer.echo(_MANUAL_MODE_SYNC_RUN_MESSAGE)
            # Do NOT exit — sync run is the explicit one-shot.
        else:
            typer.echo(_MANUAL_MODE_MESSAGE)
            raise typer.Exit(0)


def _is_local_binding() -> bool:
    """Return True iff the current repo has a bound *local* tracker provider.

    Used to short-circuit readiness and daemon-policy checks for commands
    whose local-provider code path does not touch the SaaS surface.  Returns
    ``False`` when no binding is configured, when the binding is SaaS-backed,
    or when config loading fails for any reason — in all those cases callers
    fall through to the full SaaS readiness chain, which is the safer default.
    """
    try:
        config = load_tracker_config(require_repo_root())
        if config.provider and normalize_provider(config.provider) in LOCAL_PROVIDERS:
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _check_sync_readiness(*, is_sync_run: bool = False) -> None:
    """Provider-aware readiness gate for sync subcommands.

    Local providers (beads, fp) reach the sync command without going through
    the SaaS surface at all: no auth token, no ``SPEC_KITTY_SAAS_URL``, no
    reachability probe, no background daemon.  Their direct connectors handle
    connectivity errors on their own.  For those bindings this helper is a
    no-op — the rollout gate is already enforced by :func:`tracker_callback`
    and the binding itself is the proof that setup is complete.

    SaaS-backed (or unknown/unconfigured) bindings get the full readiness
    chain plus the manual-mode daemon-policy check.
    """
    if _is_local_binding():
        return
    _check_readiness(require_mission_binding=True, probe_reachability=True)
    _check_daemon_policy(is_sync_run=is_sync_run)


def _check_binding_readiness(*, probe_reachability: bool = False) -> None:
    """Provider-aware readiness gate for non-sync commands that act on a binding.

    Mirrors :func:`_check_sync_readiness` without the daemon-policy step: used
    by ``status``, ``map add``, ``map list``, and ``unbind`` which require a
    binding to operate on but do not interact with the background sync daemon.
    """
    if _is_local_binding():
        return
    _check_readiness(require_mission_binding=True, probe_reachability=probe_reachability)


def _service() -> TrackerService:
    repo_root = require_repo_root()
    return TrackerService(repo_root)


def _doctrine_modes() -> tuple[str, ...]:
    return (
        "external_authoritative",
        "spec_kitty_authoritative",
        "split_ownership",
    )


def _run_or_exit(fn):  # type: ignore[no-untyped-def]
    try:
        return fn()
    except (RuntimeError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.callback()
def tracker_callback() -> None:
    """Defense-in-depth rollout gate for tracker commands.

    The conditional registration in cli/commands/__init__.py already hides
    this group entirely when the flag is off.  This callback is a
    defense-in-depth check in case the env-var state drifts between import
    time and invocation time.  Per-command readiness checks handle all
    prerequisite validation beyond the rollout gate.
    """
    if not is_saas_sync_enabled():
        typer.secho(saas_sync_disabled_message(), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# providers
# ---------------------------------------------------------------------------


@app.command("providers")
def providers_command(
    as_json: bool = typer.Option(False, "--json", help="Render provider list as JSON"),
) -> None:
    """List supported tracker providers, categorized by backend type.

    SaaS-backed providers authenticate through ``spec-kitty auth login`` and
    route sync operations through the Spec Kitty SaaS control plane.

    Local providers use direct connectors with locally stored credentials.

    This command is purely informational and prints the hard-coded provider
    categories.  It does **not** consult hosted readiness — the rollout gate
    itself is enforced by ``tracker_callback`` (and by the conditional
    registration in ``cli/commands/__init__.py``), which is all the gating
    this static output needs.
    """

    def _run() -> None:
        saas = sorted(SAAS_PROVIDERS)
        local = sorted(LOCAL_PROVIDERS)

        if as_json:
            _print_json({"saas": saas, "local": local})
            return

        typer.echo("Supported providers:")
        typer.echo("")
        typer.echo("  SaaS-backed (authenticate via spec-kitty auth login):")
        for p in saas:
            typer.echo(f"    - {p}")
        typer.echo("")
        typer.echo("  Local (direct connectors, credentials stored locally):")
        for p in local:
            typer.echo(f"    - {p}")

    _run_or_exit(_run)


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------


@app.command("discover")
def discover_command(
    provider: str = typer.Option(..., "--provider", help="Provider name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Discover bindable tracker resources under your installation.

    Lists all resources (projects, teams, boards) available for binding
    with the specified provider.  Each row is numbered 1-indexed to align
    with ``tracker bind --select N``.

    ``discover`` is explicitly the *pre-binding* command — it is how users
    find something to bind to — so it MUST NOT require an existing mission
    binding.  Requiring a binding here would make fresh bind flows
    impossible.
    """
    _check_readiness(require_mission_binding=False, probe_reachability=False)
    normalized = normalize_provider(provider)

    try:
        resources = _service().discover(provider=normalized)
    except TrackerServiceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    if not resources:
        typer.echo(f"No bindable resources found for provider '{normalized}'.")
        typer.echo("Verify the tracker is connected in the SaaS dashboard.")
        raise typer.Exit(0)

    if json_output:
        # Full payload, no truncation — all BindableResource fields included
        output = [
            {
                "number": idx + 1,
                "candidate_token": r.candidate_token,
                "display_label": r.display_label,
                "provider": r.provider,
                "provider_context": r.provider_context,
                "binding_ref": r.binding_ref,
                "bound_project_slug": r.bound_project_slug,
                "bound_at": r.bound_at,
                "is_bound": r.is_bound,
            }
            for idx, r in enumerate(resources)
        ]
        typer.echo(json.dumps(output, indent=2, default=str))
        return

    # Rich table output — numbered rows for alignment with --select N.
    # Numbering is 1-indexed: discover row N corresponds to --select N
    # because discover lists resources in host-returned order and
    # --select N maps to the Nth item (1-based).
    console = Console()
    table = Table(title="Bindable Resources")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Resource", style="bold")
    table.add_column("Provider")
    table.add_column("Workspace")
    table.add_column("Status")

    for idx, r in enumerate(resources):
        status = "bound" if r.is_bound else "available"
        table.add_row(
            str(idx + 1),
            r.display_label,
            r.provider,
            r.provider_context.get("workspace_name", ""),
            status,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


@app.command("bind")
def bind_command(
    provider: str = typer.Option(
        ...,
        "--provider",
        help="Provider name (linear, jira, github, gitlab, beads, fp)",
    ),
    bind_ref: str | None = typer.Option(
        None,
        "--bind-ref",
        help="Binding reference for CI/automation (validates against host)",
    ),
    select: int | None = typer.Option(
        None,
        "--select",
        help="Auto-select candidate by number (non-interactive)",
    ),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        help="Provider workspace/team/project identifier (local providers only)",
    ),
    doctrine_mode: str = typer.Option(
        "external_authoritative",
        "--doctrine-mode",
        help="Doctrine mode: external_authoritative | spec_kitty_authoritative | split_ownership",
    ),
    field_owners: list[str] = typer.Option(
        [],
        "--field-owner",
        help="Split ownership mapping: field=owner (local providers only)",
    ),
    credentials: list[str] = typer.Option(
        [],
        "--credential",
        help="Provider credential key/value: key=value (local providers only)",
    ),
) -> None:
    """Bind the current project to an issue tracker.

    For SaaS-backed providers (linear, jira, github, gitlab):
      Uses discovery to find bindable resources automatically.
      Use --bind-ref for CI/automation, --select N for non-interactive.
      Authentication via ``spec-kitty auth login``.

    For local providers (beads, fp):
      Requires --provider, --workspace, and --credential flags.
    """
    _check_readiness(require_mission_binding=False, probe_reachability=False)

    def _run() -> None:
        provider_normalized = normalize_provider(provider)

        # FR-013: Removed providers
        if provider_normalized in REMOVED_PROVIDERS:
            typer.secho(
                f"Error: Provider '{provider_normalized}' is no longer supported.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # SaaS-backed providers
        if provider_normalized in SAAS_PROVIDERS:
            # FR-010: Hard-fail --credential for SaaS
            if credentials:
                typer.secho(
                    f"Error: Direct provider credentials are no longer supported for {provider_normalized}.\n"
                    "Run `spec-kitty auth login` to authenticate.\n"
                    "Then connect your provider in the Spec Kitty dashboard.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)

            cancelled = _bind_saas(provider_normalized, bind_ref=bind_ref, select_n=select)
            if cancelled:
                typer.echo("Bind cancelled.")
            return

        # Local providers
        if provider_normalized in LOCAL_PROVIDERS:
            if not workspace:
                typer.secho(
                    "Error: --workspace is required for local providers.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)

            mode = doctrine_mode.strip().lower()
            if mode not in set(_doctrine_modes()):
                raise TrackerServiceError(
                    f"Invalid doctrine mode '{doctrine_mode}'. "
                    f"Expected one of: {', '.join(_doctrine_modes())}"
                )

            parsed_field_owners = parse_kv_pairs(field_owners)
            parsed_credentials = parse_kv_pairs(credentials)

            config = _service().bind(
                provider=provider_normalized,
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
            return

        # Unknown provider
        raise TrackerServiceError(
            f"Unknown provider '{provider_normalized}'. "
            f"Supported: {', '.join(sorted(SAAS_PROVIDERS | LOCAL_PROVIDERS))}"
        )

    _run_or_exit(_run)


def _bind_saas(
    provider: str,
    *,
    bind_ref: str | None,
    select_n: int | None,
) -> bool:
    """Execute the SaaS discovery-bind flow.

    Handles: re-bind confirmation, project identity derivation,
    interactive candidate selection, --bind-ref validation, and
    --select N auto-selection.

    Returns ``True`` if the user cancelled re-bind, ``False`` otherwise.
    Raises ``TrackerServiceError`` on failures (caught by ``_run_or_exit``).
    Raises ``typer.Exit(1)`` for user input errors.
    """
    console = Console()
    repo_root = require_repo_root()

    # Re-bind confirmation (skip for non-interactive modes)
    if bind_ref is None and select_n is None:
        existing = load_tracker_config(repo_root)
        if existing.is_configured and existing.provider in SAAS_PROVIDERS:
            label = existing.display_label or existing.binding_ref or existing.project_slug
            console.print(f"[yellow]Warning:[/yellow] Existing binding: {label}")
            confirm = input("Replace existing binding? (y/N): ")
            if confirm.strip().lower() != "y":
                return True

    # Derive project identity
    identity = ensure_identity(repo_root)
    project_identity = {
        "uuid": str(identity.project_uuid),
        "slug": identity.project_slug,
        "node_id": identity.node_id,
        "repo_slug": identity.repo_slug,
        "build_id": identity.build_id,
    }

    # Dispatch to facade (TrackerServiceError propagates to _run_or_exit)
    result = _service().bind(
        provider=provider,
        project_identity=project_identity,
        bind_ref=bind_ref,
        select_n=select_n,
    )

    # Handle bind success (auto-bind, --bind-ref, or --select N)
    if isinstance(result, BindResult | TrackerProjectConfig):
        _display_bind_success(result, provider)
        return False

    # Handle ResolutionResult with candidates (interactive selection needed)
    if isinstance(result, ResolutionResult) and result.candidates:
        _handle_candidate_selection(console, result, provider, project_identity)
        return False

    # No candidates (should not reach here -- service raises on no-match)
    raise TrackerServiceError(
        f"No bindable resources found for provider '{provider}'."
    )


def _display_bind_success(
    result: BindResult | TrackerProjectConfig,
    provider: str,
) -> None:
    """Display success output after binding."""
    provider_name = result.provider or provider
    binding_ref = result.binding_ref or result.project_slug or "unknown"
    display_label = result.display_label or result.project_slug or binding_ref

    typer.echo("Tracker binding saved")
    typer.echo(f"- provider: {provider_name}")
    typer.echo(f"- binding_ref: {binding_ref}")
    typer.echo(f"- display_label: {display_label}")


def _handle_candidate_selection(
    console: Console,
    resolution: ResolutionResult,
    provider: str,
    project_identity: dict[str, Any],
) -> None:
    """Display candidates and get interactive user selection."""
    console.print(f"\nMultiple resources found for provider '{provider}':\n")
    for candidate in resolution.candidates:
        num = candidate.sort_position + 1
        console.print(f"  {num}. {candidate.display_label} ({candidate.confidence} confidence)")
        console.print(f"     Reason: {candidate.match_reason}")

    console.print()
    choice = input(f"Select resource (1-{len(resolution.candidates)}): ")
    try:
        select_n = int(choice.strip())
    except ValueError:
        raise TrackerServiceError("Invalid selection.") from None

    # Call bind again with the selected candidate
    final = _service().bind(
        provider=provider,
        project_identity=project_identity,
        select_n=select_n,
    )

    if isinstance(final, BindResult):
        _display_bind_success(final, provider)
    else:
        raise TrackerServiceError("Unexpected result from bind operation.")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command("status")
def status_command(
    all_installations: bool = typer.Option(
        False, "--all", help="Show installation-wide status (SaaS providers only)"
    ),
    as_json: bool = typer.Option(False, "--json", help="Render status as JSON"),
) -> None:
    """Show tracker binding and sync status.

    For SaaS-backed providers: displays identity path, sync state, and
    provider info from the SaaS control plane.

    For local providers: displays local cache statistics and configuration.

    With --all: shows installation-wide summary across all bindings
    (SaaS providers only).
    """
    _check_binding_readiness(probe_reachability=False)

    def _run() -> None:
        payload = _service().status(all=all_installations)

        if as_json:
            _print_json(payload)
            return

        # Installation-wide output uses Rich for distinct formatting
        if all_installations:
            _print_installation_wide_status(payload)
            return

        if not payload.get("configured"):
            typer.echo("Tracker is not configured")
            return

        typer.echo("Tracker status")
        typer.echo(f"- provider: {payload.get('provider')}")

        # SaaS-specific fields
        if payload.get("identity_path"):
            ip = payload["identity_path"]
            typer.echo(f"- type: {ip.get('type', 'unknown')}")
            typer.echo(f"- sync_state: {payload.get('sync_state', 'unknown')}")
        # Local-specific fields
        else:
            typer.echo(f"- workspace: {payload.get('workspace')}")
            typer.echo(f"- doctrine_mode: {payload.get('doctrine_mode')}")
            typer.echo(f"- db_path: {payload.get('db_path')}")
            typer.echo(f"- issue_count: {payload.get('issue_count')}")
            typer.echo(f"- mapping_count: {payload.get('mapping_count')}")
            typer.echo(f"- credentials_present: {'yes' if payload.get('credentials_present') else 'no'}")

    _run_or_exit(_run)


def _print_installation_wide_status(payload: dict) -> None:
    """Render installation-wide tracker status using Rich for visual distinction."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    provider = payload.get("provider", "unknown")
    connected = payload.get("connected", payload.get("status", "unknown"))
    bindings = payload.get("bindings")

    if isinstance(bindings, list):
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Project", style="bold")
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Bound At")

        if bindings:
            for binding in bindings:
                if isinstance(binding, dict):
                    table.add_row(
                        _binding_project_label(binding),
                        str(binding.get("provider") or provider),
                        _binding_status_label(binding),
                        str(binding.get("bound_at") or "-"),
                    )
                else:
                    table.add_row(str(binding), str(provider), "unknown", "-")
        else:
            table.add_row("No bindings", str(provider), str(connected), "-")

        if "resource_count" in payload:
            table.caption = (
                f"Connected: {connected} | Resources: {payload['resource_count']}"
            )

        panel = Panel(table, title="Installation-wide tracker status", border_style="green")
        console.print(panel)
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Provider", str(provider))
    table.add_row("Connected", str(connected))

    # Show binding/resource counts if present
    if "bindings" in payload and isinstance(bindings, int):
        table.add_row("Bindings", str(bindings))

    if "resource_count" in payload:
        table.add_row("Resources", str(payload["resource_count"]))

    # Include any additional top-level keys that aren't already covered
    _skip = {"provider", "connected", "status", "bindings", "resource_count"}
    for key, value in sorted(payload.items()):
        if key not in _skip:
            table.add_row(key, str(value))

    panel = Panel(table, title="Installation-wide tracker status", border_style="green")
    console.print(panel)


def _binding_project_label(binding: dict[str, Any]) -> str:
    """Return the most useful project identifier from a binding payload."""
    return str(
        binding.get("project_name")
        or binding.get("project_slug")
        or binding.get("project")
        or binding.get("slug")
        or binding.get("name")
        or binding.get("display_label")
        or "unknown"
    )


def _binding_status_label(binding: dict[str, Any]) -> str:
    """Return a normalized status label for installation-wide bindings."""
    return str(
        binding.get("status")
        or binding.get("sync_state")
        or ("bound" if binding.get("binding_ref") or binding.get("bound_at") else "unknown")
    )


# ---------------------------------------------------------------------------
# map add
# ---------------------------------------------------------------------------


@map_app.command("add")
def map_add_command(
    wp_id: str = typer.Option(..., "--wp-id", help="Work package ID (e.g., WP01)"),
    external_id: str = typer.Option(..., "--external-id", help="External issue ID"),
    external_key: str | None = typer.Option(None, "--external-key", help="External issue key"),
    external_url: str | None = typer.Option(None, "--external-url", help="External issue URL"),
) -> None:
    """Add or update a WP-to-external issue mapping.

    For local providers: stores the mapping in the local SQLite database.

    For SaaS-backed providers: this command is not available.  Manage
    mappings in the Spec Kitty dashboard instead.
    """
    _check_binding_readiness(probe_reachability=False)

    def _run() -> None:
        _service().map_add(
            wp_id=wp_id,
            external_id=external_id,
            external_key=external_key,
            external_url=external_url,
        )
        typer.echo(f"Mapping saved: {wp_id} -> {external_id}")

    _run_or_exit(_run)


# ---------------------------------------------------------------------------
# map list
# ---------------------------------------------------------------------------


@map_app.command("list")
def map_list_command(
    as_json: bool = typer.Option(False, "--json", help="Render mappings as JSON"),
) -> None:
    """List tracker mappings.

    For local providers: shows mappings from the local SQLite database.

    For SaaS-backed providers: shows SaaS-authoritative mappings from the
    control plane.
    """
    _check_binding_readiness(probe_reachability=False)

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


# ---------------------------------------------------------------------------
# sync pull
# ---------------------------------------------------------------------------


@sync_app.command("pull")
def sync_pull_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Pull tracker updates into the local cache.

    For SaaS-backed providers: pulls items via the SaaS control plane.
    The response includes an identity_path and summary envelope.

    For local providers: pulls directly from the tracker API.
    """
    _check_sync_readiness()

    def _run() -> None:
        payload = _service().sync_pull(limit=limit)
        if as_json:
            _print_json(payload)
            return

        # SaaS envelope format
        if "summary" in payload:
            summary = payload.get("summary", {})
            typer.echo(f"Pull {payload.get('status', 'complete')}")
            if payload.get("identity_path"):
                ip = payload["identity_path"]
                typer.echo(f"- provider: {ip.get('provider', 'unknown')}")
                typer.echo(f"- type: {ip.get('type', 'unknown')}")
            typer.echo(f"- total: {summary.get('total', 0)}")
            typer.echo(f"- succeeded: {summary.get('succeeded', 0)}")
            typer.echo(f"- failed: {summary.get('failed', 0)}")
            typer.echo(f"- skipped: {summary.get('skipped', 0)}")
            if payload.get("has_more"):
                typer.echo(f"- has_more: yes (next_cursor: {payload.get('next_cursor', 'N/A')})")
        # Local format
        else:
            stats = payload.get("stats", {})
            typer.echo(f"Pulled from {payload.get('provider')}")
            typer.echo(f"- created: {stats.get('pulled_created', 0)}")
            typer.echo(f"- updated: {stats.get('pulled_updated', 0)}")
            typer.echo(f"- skipped: {stats.get('skipped', 0)}")
            typer.echo(f"- conflicts: {len(payload.get('conflicts', []))}")
            typer.echo(f"- errors: {len(payload.get('errors', []))}")

    _run_or_exit(_run)


# ---------------------------------------------------------------------------
# sync push
# ---------------------------------------------------------------------------


@sync_app.command("push")
def sync_push_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000, help="Max items (local providers only)"),
    items_json: str | None = typer.Option(
        None, "--items-json",
        help="Path to JSON file with PushItem[] array (SaaS providers). Use '-' for stdin.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Push explicit mutations to the upstream provider.

    For SaaS-backed providers: requires --items-json with a JSON array of
    PushItem objects per the PRI-12 TrackerPushRequest contract.  Each item
    must have ``ref``, ``action``, and optionally ``patch`` / ``target_status``.

    For full bidirectional sync, use ``tracker sync run`` instead.

    For local providers: pushes directly to the tracker API using --limit.
    """
    _check_sync_readiness()
    import sys as _sys

    def _run() -> None:
        service = _service()
        config = load_tracker_config(require_repo_root())

        if config.provider and config.provider in SAAS_PROVIDERS:
            # --- SaaS path: explicit items required ---
            if items_json is None:
                typer.secho(
                    "Error: --items-json is required for SaaS-backed providers.\n"
                    "Provide a JSON file with PushItem[] mutations, or use '-' for stdin.\n"
                    "For full bidirectional sync, use: tracker sync run",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)

            if items_json == "-":
                raw = _sys.stdin.read()
            else:
                from pathlib import Path as _Path  # noqa: PLC0415

                raw = _Path(items_json).read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                typer.secho(
                    "Error: --items-json must contain a JSON array of "
                    "PushItem objects.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)

            payload = service.sync_push(items=parsed)
        else:
            # --- Local path: push via direct connector ---
            payload = service.sync_push(limit=limit)

        if as_json:
            _print_json(payload)
            return

        # SaaS envelope format
        if "summary" in payload:
            summary = payload.get("summary", {})
            typer.echo(f"Push {payload.get('status', 'complete')}")
            typer.echo(f"- total: {summary.get('total', 0)}")
            typer.echo(f"- succeeded: {summary.get('succeeded', 0)}")
            typer.echo(f"- failed: {summary.get('failed', 0)}")
            typer.echo(f"- skipped: {summary.get('skipped', 0)}")
        # Local format
        else:
            stats = payload.get("stats", {})
            typer.echo(f"Pushed to {payload.get('provider')}")
            typer.echo(f"- created: {stats.get('pushed_created', 0)}")
            typer.echo(f"- updated: {stats.get('pushed_updated', 0)}")
            typer.echo(f"- skipped: {stats.get('skipped', 0)}")
            typer.echo(f"- conflicts: {len(payload.get('conflicts', []))}")
            typer.echo(f"- errors: {len(payload.get('errors', []))}")

    _run_or_exit(_run)


# ---------------------------------------------------------------------------
# sync run
# ---------------------------------------------------------------------------


@sync_app.command("run")
def sync_run_command(
    limit: int = typer.Option(100, "--limit", min=1, max=10000),
    as_json: bool = typer.Option(False, "--json", help="Render sync result as JSON"),
) -> None:
    """Run pull+push synchronization in one operation.

    For SaaS-backed providers: executes a full sync cycle via the SaaS
    control plane.

    For local providers: runs pull then push using direct connectors.
    """
    _check_sync_readiness(is_sync_run=True)

    def _run() -> None:
        payload = _service().sync_run(limit=limit)
        if as_json:
            _print_json(payload)
            return

        # SaaS envelope format
        if "summary" in payload:
            summary = payload.get("summary", {})
            typer.echo(f"Sync run {payload.get('status', 'complete')}")
            typer.echo(f"- total: {summary.get('total', 0)}")
            typer.echo(f"- succeeded: {summary.get('succeeded', 0)}")
            typer.echo(f"- failed: {summary.get('failed', 0)}")
            typer.echo(f"- skipped: {summary.get('skipped', 0)}")
        # Local format
        else:
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


# ---------------------------------------------------------------------------
# sync publish
# ---------------------------------------------------------------------------


@sync_app.command("publish")
def sync_publish_command(
    as_json: bool = typer.Option(False, "--json", help="Render publish result as JSON"),
) -> None:
    """Publish local tracker snapshot.

    This command is not supported for SaaS-backed providers.  Use
    ``spec-kitty tracker sync push`` instead.

    For local providers: the facade will raise an error if this operation
    is not supported by the bound provider.
    """
    _check_sync_readiness()

    def _run() -> None:
        payload = _service().sync_publish()
        if as_json:
            _print_json(payload)
            return

        typer.echo("Snapshot publish complete")
        typer.echo(f"- endpoint: {payload.get('endpoint')}")
        typer.echo(f"- status_code: {payload.get('status_code')}")
        typer.echo(f"- ok: {'yes' if payload.get('ok') else 'no'}")

    _run_or_exit(_run)


# ---------------------------------------------------------------------------
# unbind
# ---------------------------------------------------------------------------


@app.command("unbind")
def unbind_command() -> None:
    """Remove tracker binding for this project.

    For SaaS-backed providers this clears only local project configuration.
    Provider unlinking remains a SaaS dashboard action.
    """
    _check_binding_readiness(probe_reachability=False)

    def _run() -> None:
        _service().unbind()
        typer.echo("Tracker binding removed")

    _run_or_exit(_run)
