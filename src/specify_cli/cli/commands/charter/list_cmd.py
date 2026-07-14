"""spec-kitty charter list — show activated doctrine artifacts per kind."""

from __future__ import annotations

from pathlib import Path

import typer
from specify_cli.cli.console import CliConsole
from specify_cli.cli.console import console
from rich.table import Table

from charter.invocation_context import ProjectContext
from charter.kind_vocabulary import CHARTER_KIND_TOKENS
from charter.pack_manager import AvailableArtifact, CharterPackManager
from charter.resolution import ResolutionTier
from charter.template_catalog import TemplateRef, TierRoot, discover_templates

from specify_cli.cli.commands.charter._layer_roots import resolve_layer_roots

__all__ = ["charter_list_app"]

charter_list_app = typer.Typer(
    name="list",
    help="List activated doctrine artifacts by kind.",
    no_args_is_help=False,
    invoke_without_command=True,
)

#: Display order for the charter kinds. Derived from the canonical charter kind
#: universe (:data:`doctrine.artifact_kinds.CHARTER_KIND_TOKENS`, WP01) so this
#: surface never re-declares the kind set (R-009 / CC-4). The ``template`` kind
#: (FR-025) is *not* in ``CHARTER_KIND_TOKENS`` — it is resolved specially
#: (mission-qualified IDs, WP18) and appended to the ``--all`` listing below.
_KIND_ORDER: list[str] = list(CHARTER_KIND_TOKENS)

#: Pseudo-kind label for the template row in the ``--all`` listing. Templates
#: are not a charter activation kind (no ``config.yaml`` activation list); they
#: are surfaced here as an availability-only row (FR-025).
_TEMPLATE_KIND = "template"


def _template_tier_roots(repo_root: Path, layer_roots: dict[str, Path]) -> list[TierRoot]:
    """Build template-discovery tier roots (C-008) in precedence order.

    Templates live mission-scoped under ``<missions_root>/<mission>/templates``
    and ``.../command-templates`` (WP18). The package missions root ships with
    the ``doctrine`` package; the org / project layers (when present) carry
    their own missions trees under ``<doctrine-root>/doctrine/missions``.

    Roots are returned override → package so :func:`discover_templates`
    deduplicates same ``<mission>/<name>`` IDs to the highest-precedence tier.
    """
    from doctrine.missions.repository import MissionTemplateRepository  # noqa: PLC0415  # boundary: lazy import intentionally not facaded (PLC0415; boundary-invisible)

    tier_roots: list[TierRoot] = []

    # Project (override-tier) missions, if a project doctrine layer exists.
    project_root = layer_roots.get("project")
    if project_root is not None:
        missions = project_root / "doctrine" / "missions"
        if missions.is_dir():
            tier_roots.append(
                TierRoot(
                    tier=ResolutionTier.OVERRIDE,
                    missions_root=missions,
                    project_dir=repo_root,
                )
            )

    # Org (global-mission-tier) missions, if an org doctrine layer exists.
    org_root = layer_roots.get("org")
    if org_root is not None:
        missions = org_root / "doctrine" / "missions"
        if missions.is_dir():
            tier_roots.append(
                TierRoot(
                    tier=ResolutionTier.GLOBAL_MISSION,
                    missions_root=missions,
                )
            )

    # Built-in (package-default-tier) missions: always present.
    tier_roots.append(
        TierRoot(
            tier=ResolutionTier.PACKAGE_DEFAULT,
            missions_root=MissionTemplateRepository.default_missions_root(),
        )
    )

    return tier_roots


def _layer_label(layer: str) -> str:
    """Return a short, readable layer tag for table rendering."""
    return {"built-in": "built-in", "org": "org", "project": "project"}.get(layer, layer)


def _render_available(entries: list[AvailableArtifact], activated: frozenset[str]) -> str:
    """Render available-but-not-activated artifacts annotated by source layer.

    Each entry is shown as ``<id> [<layer>]``. Artifacts already activated are
    dropped (an activated ID is no longer "available but not activated"). The
    output is sorted by ``(id, layer)`` for determinism.
    """
    not_activated = sorted(
        ((e.artifact_id, e.layer) for e in entries if e.artifact_id not in activated),
        key=lambda pair: (pair[0], pair[1]),
    )
    if not not_activated:
        return "[dim]—[/dim]"
    return ", ".join(f"{aid} [dim]({_layer_label(layer)})[/dim]" for aid, layer in not_activated)


def _render_templates(refs: list[TemplateRef]) -> str:
    """Render discovered templates with mission-qualified IDs and source tier."""
    if not refs:
        return "[dim]—[/dim]"
    return ", ".join(
        f"{ref.template_id} [dim]({ref.tier.value})[/dim]" for ref in refs
    )


@charter_list_app.callback()
def list_cmd(
    show_available: bool = typer.Option(
        False,
        "--show-available",
        help="Also show available-but-not-activated artifacts.",
    ),
    all_layers: bool = typer.Option(
        False,
        "--all",
        help=(
            "Show every available artifact per kind across the built-in, org, "
            "and project layers (annotated by source layer), including the "
            "template kind. Supersedes --show-available."
        ),
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """List activated doctrine artifacts for each charter kind.

    With ``--all`` the listing additionally surfaces every *available* artifact
    across the built-in, org, and project layers — each annotated by its source
    layer — and appends the mission-scoped ``template`` kind (FR-025). Org and
    project doctrine roots are resolved here (in ``specify_cli``) and passed to
    the lower layers as data (C-008).
    """
    # --all implies and supersedes --show-available (it is a richer, layer-aware
    # availability view).
    if all_layers:
        show_available = True

    ctx = ProjectContext.from_repo(repo_root)
    manager = CharterPackManager()
    activated_map = manager.list_activated(ctx)

    # Resolve org/project roots once when we need the layer-aware view (C-008).
    layer_roots = resolve_layer_roots(repo_root) if all_layers else None

    table = Table(title="Charter Activation State", show_lines=True)
    table.add_column("Kind", style="bold cyan", no_wrap=True)
    table.add_column("Activated", style="white")
    if show_available:
        header = "Available (all layers)" if all_layers else "Available (not activated)"
        table.add_column(header, style="dim")

    for kind in _KIND_ORDER:
        value = activated_map.get(kind)
        if value is None:
            activated_str = "[dim](All built-ins — no explicit activation)[/dim]"
        elif len(value) == 0:
            activated_str = "[yellow](Nothing activated — explicit restriction)[/yellow]"
        else:
            activated_str = ", ".join(sorted(value))

        if show_available:
            activated_set = value or frozenset()
            if all_layers:
                entries = manager.list_available_detailed(
                    ctx, kind, layer_roots=layer_roots
                )
                available_str = _render_available(entries, activated_set)
            else:
                available = manager.list_available(ctx, kind)
                not_activated = sorted(available - activated_set) if available else []
                available_str = (
                    ", ".join(not_activated) if not_activated else "[dim]—[/dim]"
                )
            table.add_row(kind, activated_str, available_str)
        else:
            table.add_row(kind, activated_str)

    # FR-025: the template kind is mission-scoped and has no activation list, so
    # it only appears in the layer-aware (--all) availability view.
    if all_layers:
        tier_roots = _template_tier_roots(repo_root, layer_roots or {})
        template_refs = discover_templates(tier_roots=tier_roots)
        table.add_row(
            _TEMPLATE_KIND,
            "[dim](mission-scoped — not separately activated)[/dim]",
            _render_templates(template_refs),
        )

    # The layer-aware view is intentionally wide (IDs + per-layer tags); render
    # it at a generous fixed width so artifact IDs are never word-wrapped into
    # unreadable fragments on narrow / non-tty terminals.
    if all_layers:
        CliConsole(width=200).print(table)
    else:
        console.print(table)
