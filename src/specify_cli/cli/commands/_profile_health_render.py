"""Doctrine/profile health *render* helpers for ``spec-kitty doctor doctrine``.

Pure extraction (mission ``tooling-stability-guard-coherence-01KTRC04`` WP08,
issue #1623 / DIRECTIVE_013 / adversarial finding I-10): the doctrine- and
profile-health *rendering* helpers that grew on ``doctor.py`` during mission
``org-doctrine-profile-integrity-activation-closure-01KT1TV1`` belong beside the
single-source health model in :mod:`._doctrine_health`.  These helpers turn a
:class:`._doctrine_health.DoctrineHealthReport` (plus the registry pack entries
and selection block assembled by ``doctor.py``'s collectors) into operator
output — human Rich console lines and the ``--json`` payload.

This is a **pure move**: the bodies are verbatim relocations of the helpers that
previously lived in ``doctor.py`` (only the module docstring and the imports
differ).  The data *collectors* (``_collect_profile_health``,
``_attach_pack_health``, ``_build_pack_entries``, ``_collect_org_layer_data``,
``_collect_doctrine_collisions``, ``_build_selection_block``) and the
``doctrine`` command itself stay in ``doctor.py``; only the render-only surface
moved here.

The module-level :data:`console` is the shared singleton: ``doctor.py`` imports
it from here so the whole ``doctor`` command surface and these renderers write
through one :class:`rich.console.Console` instance.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    from ._doctrine_health import DoctrineHealthReport

__all__ = [
    "console",
    "_SELECTION_KIND_PLURALS",
    "_render_pack_invalid_profiles",
    "_render_doctrine_pack",
    "_emit_doctrine_human",
    "_emit_doctrine_json",
    "_emit_doctrine_no_packs",
    "_render_org_layer_section",
    "_render_selection_block_lines",
]

#: Shared Rich console singleton for the ``doctor`` command surface.  ``doctor.py``
#: re-imports this name so both modules emit through the same instance.
console = Console()

#: Canonical artifact-kind plurals as surfaced by ``doctor doctrine`` in the
#: Selections section.  Ordering is the operator-facing reading order from
#: the WP09 plan (directives first, agent_profiles last so the audit ends
#: on the "who can drive" surface).
_SELECTION_KIND_PLURALS: tuple[str, ...] = (
    "directives",
    "tactics",
    "paradigms",
    "styleguides",
    "toolguides",
    "procedures",
    "mission_step_contracts",
    "agent_profiles",
)


def _render_pack_invalid_profiles(pack_health: object) -> None:
    """Render per-layer invalid-profile diagnostics for a pack (FR-008/009)."""
    if not isinstance(pack_health, dict):
        return
    invalid = pack_health.get("invalid_profiles") or []
    if not (isinstance(invalid, list) and invalid):
        return
    console.print(f"  [yellow]invalid profiles:[/yellow] {len(invalid)} skipped")
    for entry in invalid:
        if not isinstance(entry, dict):
            continue
        layer = entry.get("layer", "?")
        path = entry.get("path", "?")
        error = entry.get("error_summary", "")
        # Render dynamic values without Rich markup so a path/error containing
        # square brackets is never mis-parsed as a style tag.
        console.print(
            f"    • ({layer}) {path}: {error}",
            markup=False,
        )


def _render_doctrine_pack(pack_entry: dict[str, object], pack_index: int) -> None:
    """Render one pack entry to the Rich console (human output for ``doctor doctrine``).

    FR-010: the pack header is colored from derived profile health
    (``pack_health.healthy``), not from snapshot presence.  A snapshot that is
    present but whose agent profiles failed to load renders *degraded* (yellow),
    and the per-layer invalid profiles are listed.
    """
    name = pack_entry.get("name") or f"pack#{pack_index}"
    local_path = pack_entry.get("local_path")
    if not pack_entry.get("snapshot_present"):
        console.print(
            f"[yellow]Pack:[/yellow] {name}  (snapshot missing at {local_path})"
        )
        return

    version = pack_entry.get("pack_version", "unknown")
    is_git = pack_entry.get("is_git_pack", False)
    counts = pack_entry.get("artifact_counts") or {}
    summary_parts = [f"git {version}" if is_git else f"v{version}"]
    if isinstance(counts, dict):
        for artifact_type, count in counts.items():
            summary_parts.append(f"{count} {artifact_type}")

    # FR-010: derive the header color from profile health, never snapshot
    # presence.  ``pack_health`` is the report's PackHealth.to_dict() for the
    # matching layer (attached by the report builder), or ``None`` if no
    # agent-profile surface was discovered for this pack.
    pack_health = pack_entry.get("pack_health")
    # WP01: default to degraded, not green. A present pack with no/partial
    # ``pack_health`` must render degraded (loud-over-hidden) rather than
    # silently green — only an explicit ``healthy: true`` greens the header.
    healthy = False
    if isinstance(pack_health, dict):
        healthy = bool(pack_health.get("healthy", False))
    color = "green" if healthy else "yellow"
    status_suffix = "" if healthy else "  [yellow](degraded)[/yellow]"
    console.print(
        f"[{color}]Pack:[/{color}] {name}  ({', '.join(summary_parts)}){status_suffix}"
    )
    _render_pack_invalid_profiles(pack_health)
    _render_org_charter_line(pack_entry.get("org_charter"))


def _render_org_charter_line(charter: object) -> None:
    """Render the per-pack ``org-charter.yaml`` status line."""
    if not (isinstance(charter, dict) and charter.get("present")):
        console.print("  org-charter.yaml: [dim]not present[/dim]")
        return
    if not charter.get("module_available", True):
        console.print("  org-charter.yaml: present (policy module not yet shipped)")
        return
    counts_msg = (
        f"{charter.get('interview_defaults_count', 0)} interview defaults, "
        f"{charter.get('required_directives_count', 0)} required directives, "
        f"{charter.get('governance_policies_count', 0)} governance policies"
    )
    console.print(f"  org-charter.yaml: {counts_msg}")


def _emit_doctrine_human(
    pack_entries: list[dict[str, object]],
    collision_summaries: list[dict[str, object]],
    selection_block: dict[str, list[dict[str, str]]],
    repo_root: Path,
) -> None:
    """Render the human-readable ``doctor doctrine`` report.

    The report is the single source: pack health was attached to
    ``pack_entries`` by :func:`_attach_pack_health`, and the org-DRG section is
    re-rendered from the same data path.  No parallel assembly (R-011-C).
    """
    console.print(
        f"\n[bold]Org Doctrine[/bold] — {len(pack_entries)} pack(s) configured\n"
    )
    for idx, entry in enumerate(pack_entries):
        _render_doctrine_pack(entry, idx)

    if collision_summaries:
        console.print(
            f"\n[bold]Collisions[/bold] — {len(collision_summaries)} override(s) detected\n"
        )
        for collision in collision_summaries:
            console.print(
                f"  • [yellow]{collision['kind']}[/yellow] "
                f"{collision['item_id']}: "
                f"{collision['higher_layer']} shadowed {collision['lower_layer']} "
                f"({collision['replaced']} replaced, {collision['inherited']} inherited)"
            )
    else:
        console.print(
            "\n[dim]Collisions:[/dim] none — every artifact resolves from a single layer."
        )

    # WP07 T037 (FR-007): surface org-layer DRG state in human-readable output.
    _render_org_layer_section(repo_root, console)

    # FR-018 / WP09 T050: render the Selections section verbatim so the
    # snapshot test in tests/cli/test_doctor_doctrine_selections_snapshot.py
    # can pin the operator-facing format byte-for-byte.
    console.print()
    for line in _render_selection_block_lines(selection_block):
        console.print(line)
    console.print()


def _emit_doctrine_json(
    report: DoctrineHealthReport,
    *,
    org_configured: bool,
    pack_entries: list[dict[str, object]],
    collision_summaries: list[dict[str, object]],
    selection_block: dict[str, list[dict[str, str]]],
) -> None:
    """Emit the ``doctor doctrine --json`` payload as a passthrough of the report.

    ``profile_health`` is a verbatim ``report.to_dict()`` so the invalid-profile
    fields (layer/path/profile_id/error_summary) and the derived ``healthy``
    flag are a single source of truth shared with the human surface (FR-010).
    """
    report_dict = report.to_dict()
    payload: dict[str, object] = {
        "org_configured": org_configured,
        "packs": pack_entries,
        "selections": selection_block,
        # WP07 FR-007: always include org_drg key so callers can rely on it.
        "org_drg": report_dict["org_drg"],
        # WP08 FR-008/009/010: derived profile health + invalid-profile diagnostics.
        "profile_health": report_dict,
    }
    if org_configured:
        payload["collisions"] = collision_summaries
    console.print_json(json.dumps(payload, indent=2, default=str))


def _emit_doctrine_no_packs(
    report: DoctrineHealthReport,
    selection_block: dict[str, list[dict[str, str]]],
    *,
    json_output: bool,
) -> None:
    """Emit the ``doctor doctrine`` output when no org packs are configured.

    A project with built-in + project-only doctrine still has selections (and
    profile health) to audit, so both are emitted before the command exits.
    """
    if json_output:
        _emit_doctrine_json(
            report,
            org_configured=False,
            pack_entries=[],
            collision_summaries=[],
            selection_block=selection_block,
        )
        return
    console.print("[yellow]No org doctrine configured.[/yellow]")
    console.print(
        "Add a 'doctrine.org' block to .kittify/config.yaml to register a pack."
    )
    console.print()
    for line in _render_selection_block_lines(selection_block):
        console.print(line)


def _render_org_layer_section(repo_root: Path, console: Console) -> None:
    """Surface organisation-tier DRG state in ``doctor doctrine`` (FR-007).

    Lists each configured pack with its fetched/missing status, node/edge
    counts, and any collision warnings from ``merge_three_layers``.

    Diagnostic commands are READ-ONLY and must never crash on operator
    misconfiguration.  All exceptions are caught and rendered as findings
    so ``doctor doctrine`` always returns a usable report.
    """
    from charter.drg import (  # noqa: PLC0415
        OrgDRGConflictError,
        OrgPackMissingError,
        load_org_drg,
        merge_three_layers,
    )
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415
    from doctrine.drg.loader import load_graph_or_dir  # noqa: PLC0415

    console.print("\n[bold]Organisation Layer[/bold] (WP07 / FR-007)")

    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as exc:
        console.print(f"  [red]org pack missing:[/red] {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        console.print(f"  [red]org-DRG load error:[/red] {exc}")
        return

    if not fragments:
        console.print("  (no organisation packs configured)")
        return

    for frag in fragments:
        node_count = len(frag.nodes)
        edge_count = len(frag.edges)
        console.print(
            f"  - [green]{frag.pack_name}[/green] "
            f"[{frag.source_kind}: {frag.source_ref}] "
            f"✓ loaded ({node_count} nodes, {edge_count} edges)"
        )

    # Merge with built-in layer to surface collision warnings.
    # Truncate to ≤3 lines per the WP07 risk table (risk 4: verbosity mitigation).
    try:
        built_in = load_graph_or_dir(resolve_doctrine_root())
        merge_three_layers(built_in=built_in, org_fragments=fragments, project=None)
        console.print("  collisions: none")
    except OrgDRGConflictError as exc:
        shown = exc.conflicts[:3]
        console.print(f"  collisions: {len(exc.conflicts)} built-in invariant override(s)")
        for conflict in shown:
            console.print(
                f"    [yellow]•[/yellow] {conflict.kind} "
                f"target={conflict.target_id} "
                f"resolution={conflict.resolution_applied}"
            )
        if len(exc.conflicts) > 3:
            console.print(f"    … and {len(exc.conflicts) - 3} more (run charter lint for details)")
    except Exception as exc:  # noqa: BLE001 — doctor must not crash
        console.print(f"  [yellow]collision check skipped:[/yellow] {exc}")


def _render_selection_block_lines(
    selections: dict[str, list[dict[str, str]]],
) -> list[str]:
    """Render the Selections block as a list of pinned-format lines.

    The exact layout is pinned by the snapshot test
    ``tests/cli/test_doctor_doctrine_selections_snapshot.py``.  Every
    change to spacing, punctuation, or per-kind ordering MUST update the
    snapshot fixture in the same commit.
    """
    lines: list[str] = ["Selections (active globally-selected artifacts):"]
    for kind in _SELECTION_KIND_PLURALS:
        entries = selections.get(kind, [])
        if not entries:
            lines.append(f"  {kind}: (none)")
            continue
        lines.append(f"  {kind}:")
        for entry in entries:
            lines.append(f"    - {entry['id']:<24}(source: {entry['source']})")
    return lines
