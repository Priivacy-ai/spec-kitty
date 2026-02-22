"""Constitution management commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.constitution.compiler import compile_constitution, write_compiled_constitution
from specify_cli.constitution.context import BOOTSTRAP_ACTIONS, build_constitution_context
from specify_cli.constitution.hasher import is_stale
from specify_cli.constitution.interview import (
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    QUESTION_PROMPTS,
    apply_answer_overrides,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)
from specify_cli.constitution.sync import sync as sync_constitution
from specify_cli.tasks_support import TaskCliError, find_repo_root

app = typer.Typer(
    name="constitution",
    help="Constitution management commands",
    no_args_is_help=True,
)

console = Console()


def _resolve_constitution_path(repo_root: Path) -> Path:
    """Find constitution.md in project, trying new and legacy locations."""
    new_path = repo_root / ".kittify" / "constitution" / "constitution.md"
    if new_path.exists():
        return new_path

    legacy_path = repo_root / ".kittify" / "memory" / "constitution.md"
    if legacy_path.exists():
        return legacy_path

    raise TaskCliError(f"Constitution not found. Expected:\n  - {new_path}\n  - {legacy_path} (legacy)")


def _parse_csv_option(raw: Optional[str]) -> list[str] | None:
    if raw is None:
        return None
    values = [part.strip() for part in raw.split(",")]
    normalized = [value for value in values if value]
    return normalized if normalized else []


def _interview_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "constitution" / "interview" / "answers.yaml"


@app.command()
def interview(
    mission: str = typer.Option("software-dev", "--mission", help="Mission key for constitution defaults"),
    profile: str = typer.Option("minimal", "--profile", help="Interview profile: minimal or comprehensive"),
    use_defaults: bool = typer.Option(False, "--defaults", help="Use deterministic defaults without prompts"),
    selected_paradigms: Optional[str] = typer.Option(
        None,
        "--selected-paradigms",
        help="Comma-separated paradigm IDs override",
    ),
    selected_directives: Optional[str] = typer.Option(
        None,
        "--selected-directives",
        help="Comma-separated directive IDs override",
    ),
    available_tools: Optional[str] = typer.Option(
        None,
        "--available-tools",
        help="Comma-separated tool IDs override",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Capture constitution interview answers for later generation."""
    try:
        repo_root = find_repo_root()
        normalized_profile = profile.strip().lower()
        if normalized_profile not in {"minimal", "comprehensive"}:
            raise ValueError("--profile must be 'minimal' or 'comprehensive'")

        interview_data = default_interview(mission=mission, profile=normalized_profile)

        if not use_defaults:
            question_order = MINIMAL_QUESTION_ORDER if normalized_profile == "minimal" else QUESTION_ORDER
            answers_override: dict[str, str] = {}
            for question_id in question_order:
                prompt = QUESTION_PROMPTS.get(question_id, question_id.replace("_", " ").title())
                default_value = interview_data.answers.get(question_id, "")
                answers_override[question_id] = typer.prompt(prompt, default=default_value)

            paradigms_default = ", ".join(interview_data.selected_paradigms)
            directives_default = ", ".join(interview_data.selected_directives)
            tools_default = ", ".join(interview_data.available_tools)

            selected_paradigms = typer.prompt(
                "Selected paradigms (comma-separated)",
                default=selected_paradigms or paradigms_default,
            )
            selected_directives = typer.prompt(
                "Selected directives (comma-separated)",
                default=selected_directives or directives_default,
            )
            available_tools = typer.prompt(
                "Available tools (comma-separated)",
                default=available_tools or tools_default,
            )

            interview_data = apply_answer_overrides(
                interview_data,
                answers=answers_override,
                selected_paradigms=_parse_csv_option(selected_paradigms),
                selected_directives=_parse_csv_option(selected_directives),
                available_tools=_parse_csv_option(available_tools),
            )
        else:
            interview_data = apply_answer_overrides(
                interview_data,
                selected_paradigms=_parse_csv_option(selected_paradigms),
                selected_directives=_parse_csv_option(selected_directives),
                available_tools=_parse_csv_option(available_tools),
            )

        answers_path = _interview_path(repo_root)
        write_interview_answers(answers_path, interview_data)

        if json_output:
            print(
                json.dumps(
                    {
                        "success": True,
                        "interview_path": str(answers_path.relative_to(repo_root)),
                        "mission": interview_data.mission,
                        "profile": interview_data.profile,
                        "selected_paradigms": interview_data.selected_paradigms,
                        "selected_directives": interview_data.selected_directives,
                        "available_tools": interview_data.available_tools,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]✅ Constitution interview answers saved[/green]")
        console.print(f"Interview file: {answers_path.relative_to(repo_root)}")
        console.print(f"Mission: {interview_data.mission}")
        console.print(f"Profile: {interview_data.profile}")

    except (TaskCliError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def generate(
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission key for template-set defaults"),
    template_set: Optional[str] = typer.Option(
        None,
        "--template-set",
        help="Override doctrine template set (must exist in packaged doctrine missions)",
    ),
    from_interview: bool = typer.Option(True, "--from-interview/--no-from-interview", help="Load interview answers if present"),
    profile: str = typer.Option("minimal", "--profile", help="Default profile when no interview is available"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing constitution bundle"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Generate constitution bundle from interview answers + doctrine references."""
    try:
        repo_root = find_repo_root()
        constitution_dir = repo_root / ".kittify" / "constitution"
        answers_path = _interview_path(repo_root)

        interview_data = read_interview_answers(answers_path) if from_interview else None
        if interview_data is None:
            resolved_mission = mission or "software-dev"
            interview_data = default_interview(
                mission=resolved_mission,
                profile=profile.strip().lower(),
            )
            interview_source = "defaults"
        else:
            interview_source = "interview"

        resolved_mission = mission or interview_data.mission

        compiled = compile_constitution(
            mission=resolved_mission,
            interview=interview_data,
            template_set=template_set,
        )
        bundle_result = write_compiled_constitution(constitution_dir, compiled, force=force)

        constitution_path = constitution_dir / "constitution.md"
        sync_result = sync_constitution(constitution_path, constitution_dir, force=True)

        if sync_result.error:
            raise RuntimeError(sync_result.error)

        files_written = list(bundle_result.files_written)
        for file_name in sync_result.files_written:
            if file_name not in files_written:
                files_written.append(file_name)

        if json_output:
            print(
                json.dumps(
                    {
                        "success": True,
                        "constitution_path": str(constitution_path.relative_to(repo_root)),
                        "interview_source": interview_source,
                        "mission": compiled.mission,
                        "template_set": compiled.template_set,
                        "selected_paradigms": compiled.selected_paradigms,
                        "selected_directives": compiled.selected_directives,
                        "available_tools": compiled.available_tools,
                        "references_count": len(compiled.references),
                        "files_written": files_written,
                        "diagnostics": compiled.diagnostics,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]✅ Constitution generated and synced[/green]")
        console.print(f"Constitution: {constitution_path.relative_to(repo_root)}")
        console.print(f"Mission: {compiled.mission}")
        console.print(f"Template set: {compiled.template_set}")
        if compiled.diagnostics:
            console.print("Diagnostics:")
            for line in compiled.diagnostics:
                console.print(f"  - {line}")
        console.print("Files written:")
        for filename in files_written:
            console.print(f"  ✓ {filename}")

    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except (TaskCliError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def context(
    action: str = typer.Option(..., "--action", help="Workflow action (specify|plan|implement|review)"),
    mark_loaded: bool = typer.Option(True, "--mark-loaded/--no-mark-loaded", help="Persist first-load state"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Render constitution context for a specific workflow action."""
    try:
        repo_root = find_repo_root()
        result = build_constitution_context(repo_root, action=action, mark_loaded=mark_loaded)

        if json_output:
            print(
                json.dumps(
                    {
                        "success": True,
                        "action": result.action,
                        "mode": result.mode,
                        "first_load": result.first_load,
                        "references_count": result.references_count,
                        "text": result.text,
                    },
                    indent=2,
                )
            )
            return

        if result.action in BOOTSTRAP_ACTIONS:
            console.print(f"Action: {result.action} ({result.mode})")
        console.print(result.text)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if not stale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync constitution.md to structured YAML config files."""
    try:
        repo_root = find_repo_root()
        constitution_path = _resolve_constitution_path(repo_root)
        output_dir = constitution_path.parent

        result = sync_constitution(constitution_path, output_dir, force=force)

        if json_output:
            data = {
                "success": result.synced,
                "stale_before": result.stale_before,
                "files_written": result.files_written,
                "extraction_mode": result.extraction_mode,
                "error": result.error,
            }
            print(json.dumps(data, indent=2))
            return

        if result.error:
            console.print(f"[red]❌ Error:[/red] {result.error}")
            raise typer.Exit(code=1)

        if result.synced:
            console.print("[green]✅ Constitution synced successfully[/green]")
            console.print(f"Mode: {result.extraction_mode}")
            console.print("\nFiles written:")
            for filename in result.files_written:
                console.print(f"  ✓ {filename}")
        else:
            console.print("[blue]ℹ️  Constitution already in sync[/blue] (use --force to re-extract)")

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Display constitution sync status."""
    try:
        repo_root = find_repo_root()
        constitution_path = _resolve_constitution_path(repo_root)
        output_dir = constitution_path.parent
        metadata_path = output_dir / "metadata.yaml"

        stale, current_hash, stored_hash = is_stale(constitution_path, metadata_path)

        files_info: list[dict[str, str | bool | float]] = []
        for filename in ["governance.yaml", "directives.yaml", "metadata.yaml", "references.yaml"]:
            file_path = output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                size_kb = size / 1024
                files_info.append({"name": filename, "exists": True, "size_kb": size_kb})
            else:
                files_info.append({"name": filename, "exists": False, "size_kb": 0.0})

        library_count = len(list((output_dir / "library").glob("*.md"))) if (output_dir / "library").exists() else 0

        last_sync = None
        if metadata_path.exists():
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")
            metadata = yaml.load(metadata_path.read_text(encoding="utf-8")) or {}
            if isinstance(metadata, dict):
                last_sync = metadata.get("timestamp_utc") or metadata.get("extracted_at")

        if json_output:
            data = {
                "constitution_path": str(constitution_path.relative_to(repo_root)),
                "status": "stale" if stale else "synced",
                "current_hash": current_hash,
                "stored_hash": stored_hash,
                "last_sync": last_sync,
                "library_docs": library_count,
                "files": files_info,
            }
            print(json.dumps(data, indent=2))
            return

        console.print(f"Constitution: {constitution_path.relative_to(repo_root)}")

        if stale:
            console.print("Status: [yellow]⚠️  STALE[/yellow] (modified since last sync)")
            if stored_hash:
                console.print(f"Expected hash: {stored_hash}")
            console.print(f"Current hash:  {current_hash}")
            console.print("\n[dim]Run: spec-kitty constitution sync[/dim]")
        else:
            console.print("Status: [green]✅ SYNCED[/green]")
            if last_sync:
                console.print(f"Last sync: {last_sync}")
            console.print(f"Hash: {current_hash}")

        console.print(f"Library docs: {library_count}")

        console.print("\nExtracted files:")
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Size", justify="right")

        for file_info in files_info:
            name = str(file_info["name"])
            exists = bool(file_info["exists"])
            size_kb = float(file_info["size_kb"])

            if exists:
                status_icon = "[green]✓[/green]"
                size_str = f"{size_kb:.1f} KB"
            else:
                status_icon = "[red]✗[/red]"
                size_str = "[dim]—[/dim]"

            table.add_row(name, status_icon, size_str)

        console.print(table)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)
