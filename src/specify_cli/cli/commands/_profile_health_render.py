"""Doctrinal health-render helpers for ``spec-kitty doctor doctrine``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from ._doctrine_health import DoctrineHealthReport


def _render_pack_invalid_profiles(console: Console, pack_health: object) -> None:
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


def _render_doctrine_pack(
    console: Console, pack_entry: dict[str, object], pack_index: int
) -> None:
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
    _render_pack_invalid_profiles(console, pack_health)

    charter = pack_entry.get("org_charter") or {}
    if isinstance(charter, dict) and charter.get("present"):
        if charter.get("module_available", True):
            counts_msg = (
                f"{charter.get('interview_defaults_count', 0)} interview defaults, "
                f"{charter.get('required_directives_count', 0)} required directives, "
                f"{charter.get('governance_policies_count', 0)} governance policies"
            )
            console.print(f"  org-charter.yaml: {counts_msg}")
        else:
            console.print(
                "  org-charter.yaml: present (policy module not yet shipped)"
            )
    else:
        console.print("  org-charter.yaml: [dim]not present[/dim]")


def _attach_pack_health(
    pack_entries: list[dict[str, object]], report: DoctrineHealthReport
) -> None:
    """Attach per-layer ``PackHealth`` to registry pack entries for FR-010 rendering.

    Org-pack registry entries are org-layer snapshots, so each present pack is
    annotated with the report's ``org`` layer health (if any).  This is what
    makes the human renderer color the pack header from derived health rather
    than snapshot presence.
    """
    org_pack = next((p for p in report.packs if p.layer == "org"), None)
    if org_pack is None:
        return
    health_dict = org_pack.to_dict()
    for entry in pack_entries:
        if entry.get("snapshot_present"):
            entry["pack_health"] = health_dict
