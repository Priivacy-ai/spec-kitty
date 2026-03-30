"""Agent profile management commands.

Commands for listing, inspecting, and creating agent profiles from the
doctrine framework's two-source profile repository (shipped + project).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from doctrine.agent_profiles import AgentProfileRepository, get_capabilities
from doctrine.agent_profiles.profile import AgentProfile
from doctrine.agent_profiles.validation import validate_agent_profile_yaml
from ruamel.yaml import YAML

from specify_cli.core.tool_config import load_tool_config

app = typer.Typer(
    name="profile",
    help="Manage and inspect agent profiles from the doctrine framework",
    no_args_is_help=True,
)
console = Console()

# Default project profile directory relative to .kittify
_DEFAULT_PROJECT_SUBDIR = Path(".kittify") / "constitution" / "agents"

_TOOL_CONTEXT_PATHS: dict[str, Path] = {
    "claude": Path(".claude/commands/spec-kitty.profile-context.md"),
    "codex": Path(".codex/prompts/spec-kitty.profile-context.md"),
    "opencode": Path(".opencode/command/spec-kitty.profile-context.md"),
    "cursor": Path(".cursor/commands/spec-kitty.profile-context.md"),
    "gemini": Path(".gemini/commands/spec-kitty.profile-context.md"),
    "qwen": Path(".qwen/commands/spec-kitty.profile-context.md"),
    "windsurf": Path(".windsurf/workflows/spec-kitty.profile-context.md"),
    "copilot": Path(".github/prompts/spec-kitty.profile-context.md"),
    "q": Path(".amazonq/prompts/spec-kitty.profile-context.md"),
}


def _get_repository(project_dir: Path | None = None) -> AgentProfileRepository:
    """Initialize AgentProfileRepository, using project_dir only if it exists."""
    if project_dir is not None:
        proj = project_dir if project_dir.exists() else None
    else:
        candidate = Path(".") / _DEFAULT_PROJECT_SUBDIR
        proj = candidate if candidate.exists() else None
    return AgentProfileRepository(project_dir=proj)


def _source_label(profile: AgentProfile, project_dir: Path | None) -> str:
    """Return 'project' if profile exists in project_dir, else 'shipped'."""
    if project_dir and project_dir.exists():
        candidate = project_dir / f"{profile.profile_id}.agent.yaml"
        if candidate.exists():
            return "project"
    return "shipped"


@app.command(name="list")
def list_profiles(
    project_dir: Path | None = typer.Option(
        None,
        "--project-dir",
        help="Project profiles directory (default: .kittify/constitution/agents)",
        show_default=False,
    ),
) -> None:
    """List all available agent profiles with role, priority, and source."""
    repo = _get_repository(project_dir)
    profiles = repo.list_all()

    if not profiles:
        console.print("[yellow]No agent profiles found.[/yellow]")
        return

    effective_project_dir = project_dir or (
        Path(".") / _DEFAULT_PROJECT_SUBDIR
        if (Path(".") / _DEFAULT_PROJECT_SUBDIR).exists()
        else None
    )

    table = Table(title="Agent Profiles")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Role", style="green")
    table.add_column("Priority", justify="right")
    table.add_column("Source", style="dim")

    for profile in profiles:
        source = _source_label(profile, effective_project_dir)
        source_styled = f"[bold]{source}[/bold]" if source == "project" else source
        table.add_row(
            profile.profile_id,
            profile.name,
            str(profile.role.value if hasattr(profile.role, "value") else profile.role),
            str(profile.routing_priority),
            source_styled,
        )

    console.print(table)


@app.command(name="show")
def show_profile(
    profile_id: str = typer.Argument(..., help="Profile ID to display"),
    project_dir: Path | None = typer.Option(
        None,
        "--project-dir",
        help="Project profiles directory (default: .kittify/constitution/agents)",
        show_default=False,
    ),
) -> None:
    """Show all sections of an agent profile."""
    repo = _get_repository(project_dir)
    profile = repo.get(profile_id)

    if profile is None:
        console.print(f"[red]Error:[/red] Profile '{profile_id}' not found.")
        console.print("\nAvailable profiles:")
        for p in repo.list_all():
            console.print(f"  - {p.profile_id} ({p.name})")
        raise typer.Exit(1)

    effective_project_dir = project_dir or (
        Path(".") / _DEFAULT_PROJECT_SUBDIR
        if (Path(".") / _DEFAULT_PROJECT_SUBDIR).exists()
        else None
    )
    source = _source_label(profile, effective_project_dir)
    role_str = profile.role.value if hasattr(profile.role, "value") else str(profile.role)

    # Header panel
    header = (
        f"[bold cyan]{profile.name}[/bold cyan]  "
        f"[dim]({profile.profile_id})[/dim]\n"
        f"[green]Role:[/green] {role_str}  "
        f"[green]Priority:[/green] {profile.routing_priority}  "
        f"[green]Max Tasks:[/green] {profile.max_concurrent_tasks}  "
        f"[dim]Source: {source}[/dim]\n\n"
        f"{profile.description}"
    )
    console.print(Panel(header, title="Agent Profile", border_style="cyan"))

    # Purpose
    if profile.purpose:
        console.print(Panel(profile.purpose.strip(), title="Purpose", border_style="blue"))

    # Specialization
    spec = profile.specialization
    spec_text = (
        f"[bold]Primary Focus:[/bold] {spec.primary_focus}\n"
        f"[bold]Secondary Awareness:[/bold] {spec.secondary_awareness}\n"
        f"[bold]Avoidance Boundary:[/bold] {spec.avoidance_boundary}\n"
        f"[bold]Success Definition:[/bold] {spec.success_definition}"
    )
    console.print(Panel(spec_text, title="Specialization", border_style="yellow"))

    # Collaboration
    collab = profile.collaboration
    collab_lines = []
    if collab.handoff_to:
        collab_lines.append(f"[bold]Handoff To:[/bold] {', '.join(collab.handoff_to)}")
    if collab.handoff_from:
        collab_lines.append(f"[bold]Handoff From:[/bold] {', '.join(collab.handoff_from)}")
    if collab.works_with:
        collab_lines.append(f"[bold]Works With:[/bold] {', '.join(collab.works_with)}")
    if collab.output_artifacts:
        collab_lines.append(f"[bold]Output Artifacts:[/bold] {', '.join(collab.output_artifacts)}")
    if collab.canonical_verbs:
        collab_lines.append(f"[bold]Canonical Verbs:[/bold] {', '.join(collab.canonical_verbs)}")
    if collab_lines:
        console.print(Panel("\n".join(collab_lines), title="Collaboration", border_style="magenta"))

    # Capabilities
    if profile.capabilities:
        console.print(
            Panel(
                "\n".join(f"  - {cap}" for cap in profile.capabilities),
                title="Capabilities",
                border_style="green",
            )
        )

    # Mode Defaults
    if profile.mode_defaults:
        mode_lines = []
        for mode in profile.mode_defaults:
            mode_lines.append(
                f"[bold]{mode.mode}[/bold]: {mode.description}\n"
                f"  [dim]Use case:[/dim] {mode.use_case}"
            )
        console.print(
            Panel("\n\n".join(mode_lines), title="Mode Defaults", border_style="white")
        )

    # Initialization Declaration
    if profile.initialization_declaration:
        console.print(
            Panel(
                profile.initialization_declaration.strip(),
                title="Initialization Declaration",
                border_style="dim",
            )
        )


@app.command(name="create")
def create_profile(
    from_template: str | None = typer.Option(
        None,
        "--from-template",
        help="Source profile ID to copy as template",
    ),
    profile_id: str | None = typer.Option(
        None,
        "--profile-id",
        help="New profile ID for the project profile",
    ),
    interview: bool = typer.Option(
        False,
        "--interview",
        help="Create profile via guided interview flow",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Fast interview path: ask only required questions",
    ),
    project_dir: Path | None = typer.Option(
        None,
        "--project-dir",
        help="Project profiles directory (default: .kittify/constitution/agents)",
        show_default=False,
    ),
) -> None:
    """Create a new project profile by copying a template profile.

    The new profile YAML is written to the project profiles directory so it
    can be customized without modifying the shipped (read-only) profiles.

    Example:
        spec-kitty agent profile create --from-template implementer --profile-id my-implementer
    """
    # Resolve the effective project_dir (we always need one to save)
    effective_project_dir = project_dir if project_dir is not None else Path(".") / _DEFAULT_PROJECT_SUBDIR

    if interview:
        _run_profile_interview_create(
            effective_project_dir=effective_project_dir,
            profile_id=profile_id,
            defaults=defaults,
        )
        return

    if defaults and not interview:
        console.print("[red]Error:[/red] --defaults requires --interview.")
        raise typer.Exit(1)

    if not from_template or not profile_id:
        console.print(
            "[red]Error:[/red] Template mode requires --from-template and --profile-id, "
            "or use --interview."
        )
        raise typer.Exit(1)

    repo = _get_repository(project_dir)

    # Check template exists
    template_profile = repo.get(from_template)
    if template_profile is None:
        console.print(f"[red]Error:[/red] Template profile '{from_template}' not found.")
        console.print("\nAvailable profiles:")
        for p in repo.list_all():
            console.print(f"  - {p.profile_id} ({p.name})")
        raise typer.Exit(1)

    # Check new profile_id doesn't already exist in project dir
    dest_file = effective_project_dir / f"{profile_id}.agent.yaml"
    if dest_file.exists():
        console.print(
            f"[red]Error:[/red] Project profile '{profile_id}' already exists at "
            f"{dest_file}"
        )
        raise typer.Exit(1)

    # Find source YAML file from shipped profiles
    shipped_yaml = repo._shipped_dir / f"{from_template}.agent.yaml"  # noqa: SLF001
    if shipped_yaml.exists():
        # Copy from shipped YAML and update profile-id
        effective_project_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(shipped_yaml, dest_file)

        # Read and update the profile-id field
        content = dest_file.read_text(encoding="utf-8")
        # Replace the profile-id line
        lines = content.splitlines(keepends=True)
        updated_lines = []
        for line in lines:
            if line.startswith("profile-id:"):
                updated_lines.append(f"profile-id: {profile_id}\n")
            else:
                updated_lines.append(line)
        dest_file.write_text("".join(updated_lines), encoding="utf-8")

        console.print(
            f"[green]Created[/green] project profile '{profile_id}' "
            f"from template '{from_template}'"
        )
        console.print(f"  File: {dest_file}")
        console.print(
            "\n[dim]Edit the YAML file to customize this profile for your project.[/dim]"
        )
    else:
        # No shipped file — create repo with project_dir set and use save()
        effective_project_dir.mkdir(parents=True, exist_ok=True)
        save_repo = AgentProfileRepository(project_dir=effective_project_dir)

        # Build new profile from template using model_copy with updated profile_id
        new_profile = template_profile.model_copy(
            update={"profile_id": profile_id},
        )
        save_repo.save(new_profile)

        console.print(
            f"[green]Created[/green] project profile '{profile_id}' "
            f"from template '{from_template}'"
        )
        console.print(f"  File: {dest_file}")
        console.print(
            "\n[dim]Edit the YAML file to customize this profile for your project.[/dim]"
        )


@app.command(name="hierarchy")
def show_hierarchy(
    project_dir: Path | None = typer.Option(
        None,
        "--project-dir",
        help="Project profiles directory (default: .kittify/constitution/agents)",
        show_default=False,
    ),
) -> None:
    """Show the specialization hierarchy of agent profiles as a tree."""
    repo = _get_repository(project_dir)
    profiles = repo.list_all()

    if not profiles:
        console.print("[yellow]No agent profiles found.[/yellow]")
        return

    # Validate hierarchy first
    errors = repo.validate_hierarchy()
    if errors:
        console.print("[yellow]Hierarchy warnings:[/yellow]")
        for error in errors:
            console.print(f"  [yellow]⚠[/yellow] {error}")
        console.print()

    hierarchy = repo.get_hierarchy_tree()
    profiles_by_id = {p.profile_id: p for p in profiles}

    tree = Tree("[bold cyan]Agent Profile Hierarchy[/bold cyan]")

    def _add_subtree(node: Tree, profile_id: str, subtree_data: dict[str, Any]) -> None:
        profile = profiles_by_id.get(profile_id)
        if profile is None:
            return
        role_str = (
            profile.role.value if hasattr(profile.role, "value") else str(profile.role)
        )
        label = (
            f"[cyan]{profile.profile_id}[/cyan] "
            f"[dim]({profile.name})[/dim] "
            f"[green]{role_str}[/green] "
            f"[dim]priority={profile.routing_priority}[/dim]"
        )
        child_node = node.add(label)
        for child_id, child_data in subtree_data.get("children", {}).items():
            _add_subtree(child_node, child_id, child_data)

    if not hierarchy:
        console.print("[dim]No hierarchy defined (all profiles are root-level).[/dim]")
        # Fall back to flat list
        for profile in profiles:
            role_str = (
                profile.role.value
                if hasattr(profile.role, "value")
                else str(profile.role)
            )
            tree.add(
                f"[cyan]{profile.profile_id}[/cyan] "
                f"[dim]({profile.name})[/dim] "
                f"[green]{role_str}[/green]"
            )
    else:
        for root_id, subtree_data in hierarchy.items():
            _add_subtree(tree, root_id, subtree_data)

    console.print(tree)

    # Summary counts
    root_count = len(hierarchy)
    total_count = len(profiles)
    specialized_count = sum(1 for p in profiles if p.specializes_from)
    console.print(
        f"\n[dim]{total_count} total profiles, "
        f"{root_count} root profiles, "
        f"{specialized_count} specialized[/dim]"
    )


@app.command(name="init")
def init_profile(
    profile_id: str = typer.Argument(..., help="Profile ID to initialize"),
    project_dir: Path | None = typer.Option(
        None,
        "--project-dir",
        help="Project profiles directory (default: .kittify/constitution/agents)",
        show_default=False,
    ),
) -> None:
    """Initialize the active tool context from a profile's governance artifacts."""
    effective_project_dir = project_dir or (
        Path(".") / _DEFAULT_PROJECT_SUBDIR if (Path(".") / _DEFAULT_PROJECT_SUBDIR).exists() else None
    )
    repo = _get_repository(project_dir)

    try:
        profile = repo.resolve_profile(profile_id)
    except KeyError:
        console.print(f"[red]Error:[/red] Profile '{profile_id}' not found.")
        raise typer.Exit(1) from None
    except ValueError as exc:
        console.print(f"[red]Error:[/red] Failed resolving profile '{profile_id}': {exc}")
        raise typer.Exit(1) from exc

    tool_config = load_tool_config(Path(".").resolve())
    active_tools = tool_config.available
    if not active_tools:
        console.print("[red]Error:[/red] No configured tools found in .kittify/config.yaml.")
        raise typer.Exit(1)

    target_tool = active_tools[0]
    target_rel = _TOOL_CONTEXT_PATHS.get(target_tool, Path(f".{target_tool}/spec-kitty.profile-context.md"))
    target_path = Path(".") / target_rel
    target_path.parent.mkdir(parents=True, exist_ok=True)

    content = _render_profile_context_fragment(profile)
    target_path.write_text(content, encoding="utf-8")

    source = _source_label(profile, effective_project_dir)
    console.print(
        f"[green]Initialized[/green] profile '[cyan]{profile.profile_id}[/cyan]' "
        f"(source: {source}) for tool '[cyan]{target_tool}[/cyan]'."
    )
    console.print(f"[dim]Context file:[/dim] {target_path}")


def _prompt_csv(prompt: str) -> list[str]:
    raw = typer.prompt(prompt, default="")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _run_profile_interview_create(
    *,
    effective_project_dir: Path,
    profile_id: str | None,
    defaults: bool,
) -> None:
    """Run guided interview and create a project profile file."""
    profile_id_value = profile_id or typer.prompt("Profile ID (kebab-case)")
    name = typer.prompt("Profile name")
    purpose = typer.prompt("Purpose")
    role = typer.prompt("Role", default="implementer")
    primary_focus = typer.prompt("Primary focus")

    specializes_from: str | None = None
    secondary_awareness = ""
    avoidance_boundary = ""
    success_definition = ""
    languages: list[str] = []
    frameworks: list[str] = []
    domain_keywords: list[str] = []
    handoff_to: list[str] = []
    handoff_from: list[str] = []
    works_with: list[str] = []
    directives: list[str] = []
    directive_refs: list[dict[str, str]] = []

    if not defaults:
        specializes_from = typer.prompt("specializes-from (optional)", default="").strip() or None
        secondary_awareness = typer.prompt("Secondary awareness (optional)", default="")
        avoidance_boundary = typer.prompt("Avoidance boundary (optional)", default="")
        success_definition = typer.prompt("Success definition (optional)", default="")
        languages = _prompt_csv("Specialization languages (comma-separated, optional)")
        frameworks = _prompt_csv("Specialization frameworks (comma-separated, optional)")
        domain_keywords = _prompt_csv("Specialization keywords (comma-separated, optional)")
        handoff_to = _prompt_csv("Collaboration handoff-to (comma-separated, optional)")
        handoff_from = _prompt_csv("Collaboration handoff-from (comma-separated, optional)")
        works_with = _prompt_csv("Collaboration works-with (comma-separated, optional)")
        directives = _prompt_csv("Directive codes (comma-separated, optional)")

    capabilities_cfg = get_capabilities(role)
    capabilities = capabilities_cfg.default_capabilities if capabilities_cfg else []
    canonical_verbs = capabilities_cfg.canonical_verbs if capabilities_cfg else []

    for code in directives:
        directive_refs.append(
            {
                "code": code,
                "name": f"Directive {code}",
                "rationale": "Added via interview",
            }
        )

    payload: dict[str, Any] = {
        "profile-id": profile_id_value,
        "name": name,
        "purpose": purpose,
        "role": role,
        "capabilities": capabilities,
        "specialization": {
            "primary-focus": primary_focus,
            "secondary-awareness": secondary_awareness,
            "avoidance-boundary": avoidance_boundary,
            "success-definition": success_definition,
        },
        "collaboration": {
            "handoff-to": handoff_to,
            "handoff-from": handoff_from,
            "works-with": works_with,
            "canonical-verbs": canonical_verbs,
        },
    }

    if specializes_from:
        payload["specializes-from"] = specializes_from

    if languages or frameworks or domain_keywords:
        payload["specialization-context"] = {
            "languages": languages,
            "frameworks": frameworks,
            "domain-keywords": domain_keywords,
        }

    if directive_refs:
        payload["directive-references"] = directive_refs

    errors = validate_agent_profile_yaml(payload)
    if errors:
        console.print("[red]Error:[/red] Generated profile failed schema validation:")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)

    effective_project_dir.mkdir(parents=True, exist_ok=True)
    dest_file = effective_project_dir / f"{profile_id_value}.agent.yaml"
    if dest_file.exists():
        console.print(f"[red]Error:[/red] Profile already exists at {dest_file}")
        raise typer.Exit(1)

    yaml = YAML()
    yaml.default_flow_style = False
    with dest_file.open("w", encoding="utf-8") as fh:
        yaml.dump(payload, fh)

    console.print(f"[green]Created[/green] profile '{profile_id_value}' via interview")
    console.print(f"  File: {dest_file}")


def _render_profile_context_fragment(profile: AgentProfile) -> str:
    """Render profile context fragment consumed by tool integrations."""
    directives = ", ".join(d.code for d in profile.directive_references) or "none"
    role = profile.role.value if hasattr(profile.role, "value") else str(profile.role)
    specialization = profile.specialization.primary_focus
    collaboration = ", ".join(profile.collaboration.works_with) or "none"
    modes = ", ".join(m.mode for m in profile.mode_defaults) or "none"

    return (
        f"# Spec Kitty Agent Profile Context\n\n"
        f"- profile_id: {profile.profile_id}\n"
        f"- name: {profile.name}\n"
        f"- role: {role}\n"
        f"- purpose: {profile.purpose}\n"
        f"- specialization: {specialization}\n"
        f"- directives: {directives}\n"
        f"- collaboration_partners: {collaboration}\n"
        f"- mode_defaults: {modes}\n"
        f"- initialization_declaration: {profile.initialization_declaration or 'none'}\n"
    )


__all__ = ["app"]
