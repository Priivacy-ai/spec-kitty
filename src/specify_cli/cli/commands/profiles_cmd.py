"""CLI command group: spec-kitty profiles."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.task_utils import find_repo_root

app = typer.Typer(name="profiles", help="Manage and list agent profiles.")
console = Console()


@app.command("list")
def list_profiles(
    json_output: bool = typer.Option(False, "--json", help="Output JSON array."),
) -> None:
    """List all available agent profiles."""
    # FR-008 / T031: This command does not open an InvocationRecord at baseline.
    # If a future version of `profiles list` opens an invocation, it should use:
    #   derive_mode("profiles.list")  -> ModeOfWork.QUERY
    # The mapping is reserved in _ENTRY_COMMAND_MODE (modes.py) for enforcement
    # consistency (QUERY mode disallows Tier 2 evidence promotion per FR-009).
    # TODO(future): wire derive_mode("profiles.list") when InvocationRecord is opened here.
    repo_root = find_repo_root()
    registry = ProfileRegistry(repo_root)
    profiles = registry.list_all()

    if not profiles:
        if json_output:
            typer.echo("[]")
        else:
            console.print(
                "[yellow]No profiles found.[/yellow] "
                "Run 'spec-kitty charter synthesize' to create project-local profiles."
            )
        raise typer.Exit(0)

    descriptors = []
    for p in profiles:
        from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
        from doctrine.agent_profiles.profile import Role

        caps = DEFAULT_ROLE_CAPABILITIES.get(p.role) if isinstance(p.role, Role) else None
        canonical_verbs = list(caps.canonical_verbs) if caps else []
        # domain_keywords lives in specialization_context (SpecializationContext), NOT specialization
        sc = getattr(p, "specialization_context", None)
        domain_kws = list(sc.domain_keywords) if sc and sc.domain_keywords else []
        # collaboration.canonical_verbs also carries per-profile verbs
        collab = getattr(p, "collaboration", None)
        collab_verbs = list(collab.canonical_verbs) if collab and collab.canonical_verbs else []
        source = "project_local" if getattr(p, "_source", None) == "project" else "shipped"
        descriptors.append(
            {
                "profile_id": p.profile_id,
                "name": p.name,  # AgentProfile.name (not friendly_name — that field does not exist)
                "role": str(p.role),
                "action_domains": sorted({*canonical_verbs, *collab_verbs, *domain_kws}),
                "source": source,
            }
        )

    if json_output:
        typer.echo(json.dumps(descriptors, indent=2))
    else:
        table = Table(title="Agent Profiles")
        table.add_column("Profile ID")
        table.add_column("Friendly Name")
        table.add_column("Role")
        table.add_column("Source")
        for d in descriptors:
            table.add_row(str(d["profile_id"]), str(d["name"]), str(d["role"]), str(d["source"]))
        console.print(table)
