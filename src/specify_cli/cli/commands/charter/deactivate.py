"""spec-kitty charter deactivate — deactivate a doctrine artifact.

FR-005 (direct deactivation), FR-015/FR-016 (shared-reference-safe cascade),
FR-035 (fail-closed on invalid pack config).

Wiring (Contracts C3.3/C3.4, C1.5)
----------------------------------
The live caller for the WP10 plan/commit engine and the WP11 shared-reference-
safe cascade engine on the removal side:

* ``--cascade`` is parsed through :meth:`charter.cascade.CascadeScope.parse`
  (WP11) into a real scope value object — never collapsed to a bool (C3.3).
* Cascade removal goes through :func:`charter.cascade.deactivation_plan`, which
  removes only *exclusive* referenced artifacts and **never** removes a shared
  one (Contract C3.4); shared skips are reported with the still-referencing
  active source named.
* :class:`charter.activation_engine.NoActivationRestrictionsError` (raised by
  the WP10 engine for a None-state kind) is caught and surfaced as a clean
  exit-1 with the upgrade guidance.
* :class:`charter.pack_context.CharterPackConfigError` is caught and surfaced as
  fail-closed guidance before any mutation (FR-035, C1.5).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from charter.activation_engine import NoActivationRestrictionsError
from charter.cascade import CascadeScope, deactivation_plan
from charter.catalog import resolve_doctrine_root
from charter.invocation_context import ProjectContext
from charter.kind_vocabulary import (
    UnknownArtifactIdError,
    resolve_artifact_urn,
    resolve_config_id,
)
from charter.pack_context import CharterPackConfigError
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager
from charter.kind_vocabulary import ArtifactKind, MissionTypeNotAnArtifactKind

from specify_cli.cli.commands.charter.activate import (
    render_pack_config_error,
    validate_pack_config,
)
from specify_cli.cli.commands.charter._layer_roots import resolve_layer_roots

__all__ = ["deactivate_cmd"]

console = Console()


def _source_urn(
    kind: str,
    artifact_id: str,
    layer_roots: dict[str, Path] | None,
) -> str | None:
    """Resolve the DRG source URN for ``(kind, config-stem artifact_id)`` or ``None``."""
    try:
        kind_enum = ArtifactKind.from_operator_token(kind)
    except MissionTypeNotAnArtifactKind:
        return None
    try:
        return resolve_artifact_urn(
            kind_enum,
            artifact_id,
            doctrine_root=resolve_doctrine_root(),
            layer_roots=layer_roots,
        )
    except UnknownArtifactIdError:
        return None


def _active_urns(
    manager: CharterPackManager,
    ctx_project: ProjectContext,
    layer_roots: dict[str, Path] | None,
) -> set[str]:
    """Return the set of currently-activated artifact URNs across all kinds.

    Resolves each activated config-stem ID back to its DRG URN. IDs with no
    resolvable DRG node (or mission-type, which is not an artifact kind) are
    skipped — they cannot participate in DRG reachability anyway.
    """
    doctrine_root = resolve_doctrine_root()
    urns: set[str] = set()
    for kind_token, ids in manager.list_activated(ctx_project).items():
        if ids is None:
            continue
        try:
            kind_enum = ArtifactKind.from_operator_token(kind_token)
        except MissionTypeNotAnArtifactKind:
            continue
        for config_id in ids:
            try:
                urns.add(
                    resolve_artifact_urn(
                        kind_enum,
                        config_id,
                        doctrine_root=doctrine_root,
                        layer_roots=layer_roots,
                    )
                )
            except UnknownArtifactIdError:
                continue
    return urns


def _render_cascade_deactivation(
    manager: CharterPackManager,
    ctx_project: ProjectContext,
    target_urn: str,
    scope: CascadeScope,
    repo_root: Path,
    layer_roots: dict[str, Path] | None,
) -> None:
    """Cascade-deactivate exclusive referenced artifacts; keep shared ones (FR-015/016).

    Uses the WP11 :func:`charter.cascade.deactivation_plan` over the merged DRG.
    Exclusive candidates are removed through the same activation seam; shared
    candidates are reported (never removed — Contract C3.4) with the still-
    referencing active source named.
    """
    from charter._drg_helpers import load_validated_graph  # noqa: PLC0415

    graph = load_validated_graph(repo_root)
    active = _active_urns(manager, ctx_project, layer_roots)
    plan = deactivation_plan(graph, target_urn, scope, active_urns=active)
    doctrine_root = resolve_doctrine_root()

    for urn in plan.deactivate:
        kind_value, _, _ = urn.partition(":")
        kind_token = ArtifactKind(kind_value).operator_token
        try:
            config_id = resolve_config_id(
                urn, doctrine_root=doctrine_root, layer_roots=layer_roots
            )
        except (UnknownArtifactIdError, ValueError):
            config_id = urn.partition(":")[2]
        try:
            manager.deactivate(
                ctx_project,
                kind_token,
                config_id,
                cascade=False,
                layer_roots=layer_roots,
            )
        except (ValueError, NoActivationRestrictionsError) as exc:
            console.print(
                f"[yellow]Warning[/yellow]: could not cascade-deactivate "
                f"{kind_token}/{config_id}: {exc}"
            )
            continue
        console.print(f"[cyan]Cascade-deactivated[/cyan]: {kind_token}/{config_id}")

    for skip in plan.skipped_shared:
        console.print(
            f"[yellow]Skipped (shared artifact)[/yellow]: {skip.urn} "
            f"(still referenced by {skip.referencing_active_urn})"
        )


def deactivate_cmd(
    ctx: typer.Context,
    kind: str | None = typer.Argument(None, help="Activation kind (e.g. directive, agent-profile)."),
    artifact_id: str | None = typer.Argument(None, help="Artifact ID to deactivate."),
    cascade: str | None = typer.Option(
        None,
        "--cascade",
        help=(
            "Cascade deactivation scope: 'all' for every exclusively-referenced "
            "kind, or a comma-separated kind list. Shared artifacts are never "
            "removed. Omit to deactivate only the named artifact."
        ),
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Deactivate a doctrine artifact by kind and ID (FR-005), with optional cascade."""
    if ctx.invoked_subcommand is not None:
        return
    if kind is None or artifact_id is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)
    if kind not in YAML_KEY_MAP:
        console.print(f"[red]Error:[/red] Unknown kind '{kind}'. Valid kinds: {', '.join(sorted(YAML_KEY_MAP))}.")
        raise typer.Exit(1)

    # FR-015/016: parse the scope value object — never collapsed to a bool (C3.3).
    try:
        scope = CascadeScope.parse(cascade)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # FR-035 fail-closed: reject invalid pack config before any mutation (C1.5).
    try:
        validate_pack_config(repo_root)
    except CharterPackConfigError as exc:
        render_pack_config_error(exc, console)
        raise typer.Exit(1) from exc

    ctx_project = ProjectContext(repo_root=repo_root)
    layer_roots = resolve_layer_roots(repo_root)
    manager = CharterPackManager()

    try:
        result = manager.deactivate(
            ctx_project,
            kind,
            artifact_id,
            cascade=scope is not None,
            layer_roots=layer_roots,
        )
    except NoActivationRestrictionsError as exc:
        # WP10 engine raises this for a None-state kind; surface the upgrade
        # guidance carried in the error and exit non-zero (no mutation).
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    for msg in result.deactivated:
        console.print(f"[green]Deactivated[/green]: {msg}")
    for warn in result.warnings:
        console.print(f"[yellow]Warning[/yellow]: {warn}")

    # FR-015/016: shared-reference-safe cascade deactivation via the WP11 engine.
    # Only runs when a scope was supplied and the direct deactivation actually
    # removed the target (so we never cascade off a no-op removal).
    if scope is None or not result.deactivated:
        return
    target_urn = _source_urn(kind, artifact_id, layer_roots)
    if target_urn is None:
        return
    _render_cascade_deactivation(
        manager, ctx_project, target_urn, scope, repo_root, layer_roots
    )
