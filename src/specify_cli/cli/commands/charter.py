"""Charter management commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from charter.compiler import compile_charter, write_compiled_charter
from charter.context import BOOTSTRAP_ACTIONS, build_charter_context
from charter.hasher import is_stale
from charter.interview import (
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    QUESTION_PROMPTS,
    apply_answer_overrides,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)
from charter.sync import ensure_charter_bundle_fresh, sync as sync_charter
from specify_cli.cli.commands.charter_bundle import app as charter_bundle_app
from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.tasks_support import TaskCliError, find_repo_root

app = typer.Typer(
    name="charter",
    help="Charter management commands",
    no_args_is_help=True,
)

# WP01 introduced ``charter_bundle_app`` as a self-contained Typer sub-app.
# WP03 registers it under ``bundle`` so users can invoke
# ``spec-kitty charter bundle validate`` from the unified CLI surface
# (FR-013).
app.add_typer(charter_bundle_app, name="bundle")

console = Console()


def _resolve_charter_path(repo_root: Path) -> Path:
    """Find charter.md in canonical location only.

    Does not fall back to legacy locations. Users with pre-charter state
    must run 'spec-kitty upgrade' first (handled by the charter-rename migration).
    """
    charter_path = repo_root / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return charter_path

    raise TaskCliError(
        f"Charter not found at {charter_path}\n"
        "  Run 'spec-kitty charter interview' to create one,\n"
        "  or 'spec-kitty upgrade' if migrating from an older version."
    )


def _parse_csv_option(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [part.strip() for part in raw.split(",")]
    normalized = [value for value in values if value]
    return normalized if normalized else []


def _interview_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"


@app.command()
def interview(
    mission_type: str | None = typer.Option(
        None,
        "--mission-type",
        help="Mission type for charter defaults (default: software-dev)",
    ),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    profile: str = typer.Option("minimal", "--profile", help="Interview profile: minimal or comprehensive"),
    use_defaults: bool = typer.Option(False, "--defaults", help="Use deterministic defaults without prompts"),
    selected_paradigms: str | None = typer.Option(
        None,
        "--selected-paradigms",
        help="Comma-separated paradigm IDs override",
    ),
    selected_directives: str | None = typer.Option(
        None,
        "--selected-directives",
        help="Comma-separated directive IDs override",
    ),
    available_tools: str | None = typer.Option(
        None,
        "--available-tools",
        help="Comma-separated tool IDs override",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Capture charter interview answers for later generation."""
    try:
        repo_root = find_repo_root()
        normalized_profile = profile.strip().lower()
        if normalized_profile not in {"minimal", "comprehensive"}:
            raise ValueError("--profile must be 'minimal' or 'comprehensive'")

        resolved_mission_type = "software-dev"
        if mission_type is not None or mission is not None:
            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value

        interview_data = default_interview(mission=resolved_mission_type, profile=normalized_profile)

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
                        "result": "success",
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

        console.print("[green]Charter interview answers saved[/green]")
        console.print(f"Interview file: {answers_path.relative_to(repo_root)}")
        console.print(f"Mission: {interview_data.mission}")
        console.print(f"Profile: {interview_data.profile}")

    except (TaskCliError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def generate(
    mission_type: str | None = typer.Option(None, "--mission-type", help="Mission type for template-set defaults"),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    template_set: str | None = typer.Option(
        None,
        "--template-set",
        help="Override doctrine template set (must exist in packaged doctrine missions)",
    ),
    from_interview: bool = typer.Option(
        True, "--from-interview/--no-from-interview", help="Load interview answers if present"
    ),
    profile: str = typer.Option("minimal", "--profile", help="Default profile when no interview is available"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing charter bundle"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Generate charter bundle from interview answers + doctrine references."""
    try:
        repo_root = find_repo_root()
        charter_dir = repo_root / ".kittify" / "charter"
        answers_path = _interview_path(repo_root)
        resolved_mission_type = None
        if mission_type is not None or mission is not None:
            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value

        interview_data = read_interview_answers(answers_path) if from_interview else None
        if interview_data is None:
            resolved_mission = resolved_mission_type or "software-dev"
            interview_data = default_interview(
                mission=resolved_mission,
                profile=profile.strip().lower(),
            )
            interview_source = "defaults"
        else:
            interview_source = "interview"

        resolved_mission = resolved_mission_type or interview_data.mission

        compiled = compile_charter(
            mission=resolved_mission,
            interview=interview_data,
            template_set=template_set,
            repo_root=repo_root,
        )
        bundle_result = write_compiled_charter(charter_dir, compiled, force=force)
        if interview_source == "defaults":
            # Legacy CLI contract: default generation materializes an empty
            # library/ directory for older consumers. Interview-driven flows
            # keep the newer no-materialization behavior.
            (charter_dir / "library").mkdir(exist_ok=True)

        charter_path = charter_dir / "charter.md"
        sync_result = sync_charter(charter_path, charter_dir, force=True)

        if sync_result.error:
            raise RuntimeError(sync_result.error)

        files_written = list(bundle_result.files_written)
        for file_name in sync_result.files_written:
            if file_name not in files_written:
                files_written.append(file_name)

        if json_output:
            local_support_files = [
                reference.source_path
                for reference in compiled.references
                if reference.kind == "local_support"
            ]
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "charter_path": str(charter_path.relative_to(repo_root)),
                        "interview_source": interview_source,
                        "mission": compiled.mission,
                        "template_set": compiled.template_set,
                        "selected_paradigms": compiled.selected_paradigms,
                        "selected_directives": compiled.selected_directives,
                        "available_tools": compiled.available_tools,
                        "references_count": len(compiled.references),
                        "library_files": local_support_files,
                        "files_written": files_written,
                        "diagnostics": compiled.diagnostics,
                    },
                    indent=2,
                )
            )
            return

        console.print("[green]Charter generated and synced[/green]")
        console.print(f"Charter: {charter_path.relative_to(repo_root)}")
        console.print(f"Mission: {compiled.mission}")
        console.print(f"Template set: {compiled.template_set}")
        if compiled.diagnostics:
            console.print("Diagnostics:")
            for line in compiled.diagnostics:
                console.print(f"  - {line}")
        console.print("Files written:")
        for filename in files_written:
            console.print(f"  ✓ {filename}")

    except (FileExistsError, TaskCliError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def context(
    action: str = typer.Option(..., "--action", help="Workflow action (specify|plan|implement|review)"),
    mark_loaded: bool = typer.Option(True, "--mark-loaded/--no-mark-loaded", help="Persist first-load state"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Render charter context for a specific workflow action."""
    try:
        repo_root = find_repo_root()
        result = build_charter_context(repo_root, action=action, mark_loaded=mark_loaded)

        if json_output:
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "action": result.action,
                        "mode": result.mode,
                        "first_load": result.first_load,
                        "references_count": result.references_count,
                        "context": result.text,
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
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if not stale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync charter.md to structured YAML config files."""
    try:
        repo_root = find_repo_root()
        charter_path = _resolve_charter_path(repo_root)
        output_dir = charter_path.parent

        result = sync_charter(charter_path, output_dir, force=force)

        if json_output:
            data = {
                "result": "success" if result.synced else "noop",
                "success": result.synced,
                "stale_before": result.stale_before,
                "files_written": result.files_written,
                "extraction_mode": result.extraction_mode,
                "error": result.error,
            }
            print(json.dumps(data, indent=2))
            return

        if result.error:
            console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(code=1)

        if result.synced:
            console.print("[green]Charter synced successfully[/green]")
            console.print(f"Mode: {result.extraction_mode}")
            console.print("\nFiles written:")
            for filename in result.files_written:
                console.print(f"  ✓ {filename}")
        else:
            console.print("[blue]Charter already in sync[/blue] (use --force to re-extract)")

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Display charter sync status."""
    try:
        repo_root = find_repo_root()
        # FR-004 chokepoint: route the status handler through
        # ``ensure_charter_bundle_fresh`` so the displayed metadata reflects
        # a freshly synced bundle, and so the displayed paths are anchored at
        # the canonical (main-checkout) root even when invoked from a worktree.
        sync_result = ensure_charter_bundle_fresh(repo_root)
        canonical_root = sync_result.canonical_root if sync_result and sync_result.canonical_root else repo_root
        charter_path = _resolve_charter_path(canonical_root)
        output_dir = charter_path.parent
        metadata_path = output_dir / "metadata.yaml"

        stale, current_hash, stored_hash = is_stale(charter_path, metadata_path)

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
                "charter_path": str(charter_path.relative_to(canonical_root)),
                "status": "stale" if stale else "synced",
                "current_hash": current_hash,
                "stored_hash": stored_hash,
                "last_sync": last_sync,
                "library_docs": library_count,
                "files": files_info,
            }
            print(json.dumps(data, indent=2))
            return

        console.print(f"Charter: {charter_path.relative_to(canonical_root)}")

        if stale:
            console.print("Status: [yellow]STALE[/yellow] (modified since last sync)")
            if stored_hash:
                console.print(f"Expected hash: {stored_hash}")
            console.print(f"Current hash:  {current_hash}")
            console.print("\n[dim]Run: spec-kitty charter sync[/dim]")
        else:
            console.print("Status: [green]SYNCED[/green]")
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
                status_icon = "[green]Y[/green]"
                size_str = f"{size_kb:.1f} KB"
            else:
                status_icon = "[red]N[/red]"
                size_str = "[dim]-[/dim]"

            table.add_row(name, status_icon, size_str)

        console.print(table)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# Synthesizer subcommands (Phase 3 — T030)
# ---------------------------------------------------------------------------


def _build_synthesis_request(
    repo_root: Path,
    adapter_name: str,
    evidence: Any = None,
) -> tuple[Any, Any]:
    """Build a SynthesisRequest + adapter from the project's current interview state.

    Returns ``(SynthesisRequest, adapter)`` ready for synthesize() / resynthesize().
    Raises ``TaskCliError`` if the interview answers file does not exist.
    """
    import uuid

    from charter.interview import read_interview_answers
    from charter.synthesizer.fixture_adapter import FixtureAdapter
    from charter.synthesizer.generated_artifact_adapter import GeneratedArtifactAdapter
    from charter.synthesizer.request import SynthesisRequest, SynthesisTarget

    answers_path = _interview_path(repo_root)
    interview_data = read_interview_answers(answers_path)
    if interview_data is None:
        raise TaskCliError(
            "No interview answers found. "
            "Run 'spec-kitty charter interview' first."
        )

    # Build a minimal interview snapshot from the interview data
    interview_snapshot: dict[str, Any] = {
        "mission_type": interview_data.mission,
        "selected_directives": interview_data.selected_directives,
        "selected_paradigms": interview_data.selected_paradigms,
    }
    interview_snapshot.update(dict(interview_data.answers))

    # Build a minimal doctrine snapshot (directives only for now)
    doctrine_snapshot: dict[str, Any] = {
        "directives": {},
        "tactics": {},
        "styleguides": {},
    }

    # Build a minimal DRG snapshot with shipped directives as nodes
    drg_nodes = []
    for directive_id in interview_data.selected_directives:
        drg_nodes.append({
            "urn": f"directive:{directive_id}",
            "kind": "directive",
            "id": directive_id,
        })
    drg_snapshot: dict[str, Any] = {
        "nodes": drg_nodes,
        "edges": [],
        "schema_version": "1",
    }

    # Placeholder target (synthesize() derives actual targets from interview)
    target = SynthesisTarget(
        kind="directive",
        slug="synthesize-placeholder",
        title="Synthesize Placeholder",
        artifact_id="PROJECT_000",
        source_section="mission_type",
    )

    run_id = str(uuid.uuid4()).replace("-", "").upper()[:26]

    request = SynthesisRequest(
        target=target,
        interview_snapshot=interview_snapshot,
        doctrine_snapshot=doctrine_snapshot,
        drg_snapshot=drg_snapshot,
        run_id=run_id,
        evidence=evidence,
    )

    if adapter_name == "generated":
        adapter_obj = GeneratedArtifactAdapter(repo_root=repo_root)
    elif adapter_name == "fixture":
        adapter_obj = FixtureAdapter()
    else:
        raise TaskCliError(
            f"Unknown adapter '{adapter_name}'. "
            "Supported adapters are '--adapter generated' and '--adapter fixture'. "
            "Doctrine generation is performed by the LLM harness (Claude Code, Codex, "
            "Cursor, etc.) via the spec-kitty-charter-doctrine skill. "
            "spec-kitty never calls an LLM itself."
        )

    return request, adapter_obj


def _collect_evidence_result(
    repo_root: Path,
    *,
    skip_code_evidence: bool,
    skip_corpus: bool,
) -> Any:
    from charter.evidence.orchestrator import EvidenceOrchestrator, load_url_list_from_config

    url_list = load_url_list_from_config(repo_root)
    orchestrator = EvidenceOrchestrator(
        repo_root=repo_root,
        url_list=url_list,
        skip_code=skip_code_evidence,
        skip_corpus=skip_corpus,
    )
    return orchestrator.collect()


def _build_synthesis_validation_callback(request: Any) -> Any:
    from doctrine.drg.models import DRGGraph
    from importlib.metadata import version as pkg_version

    from charter.synthesizer.interview_mapping import resolve_sections
    from charter.synthesizer.orchestrator import _shipped_drg_from_snapshot
    from charter.synthesizer.project_drg import emit_project_layer, persist as persist_project_graph
    from charter.synthesizer.targets import build_targets, detect_duplicates, order_targets
    from charter.synthesizer.validation_gate import validate as validate_project_graph

    spec_kitty_version = pkg_version("spec-kitty-cli")
    shipped_drg = DRGGraph.model_validate(_shipped_drg_from_snapshot(request.drg_snapshot))
    sections = resolve_sections(dict(request.interview_snapshot))
    targets = build_targets(
        interview_snapshot=dict(request.interview_snapshot),
        mappings=sections,
        drg_snapshot=dict(request.drg_snapshot),
    )
    targets = order_targets(targets)
    detect_duplicates(targets)
    if not targets:
        targets = [request.target]

    def _validation_callback(staged_dir: Any) -> None:
        project_graph = emit_project_layer(
            targets=targets,
            spec_kitty_version=spec_kitty_version,
            shipped_drg=shipped_drg,
        )
        persist_project_graph(project_graph, staged_dir.root, staged_dir.guard)
        validate_project_graph(staged_dir.root, shipped_drg)

    return _validation_callback


def _run_synthesis_dry_run(
    request: Any,
    syn_adapter: Any,
    repo_root: Path,
) -> list[str]:
    from charter.synthesizer.staging import StagingDir
    from charter.synthesizer.synthesize_pipeline import run_all
    from charter.synthesizer.write_pipeline import stage_and_validate

    results = run_all(request, adapter=syn_adapter)
    validation_callback = _build_synthesis_validation_callback(request)

    with StagingDir.create(repo_root, request.run_id) as staging_dir:
        staged_artifacts = stage_and_validate(
            request,
            staging_dir,
            results,
            validation_callback,
        )
        staging_dir.wipe()

    return staged_artifacts


def _list_resynthesis_topics(
    request: Any,
    repo_root: Path,
) -> dict[str, list[str]]:
    from charter.synthesizer.resynthesize_pipeline import (
        _load_merged_drg,
        _load_project_artifacts_from_provenance,
    )

    project_artifacts = _load_project_artifacts_from_provenance(repo_root)
    merged_drg = _load_merged_drg(repo_root, request)
    interview_sections = sorted(str(section) for section in request.interview_snapshot)

    artifact_topics = []
    for artifact in project_artifacts:
        selector = artifact.urn if artifact.kind == "directive" else f"{artifact.kind}:{artifact.slug}"
        artifact_topics.append(selector)

    drg_topics: list[str] = []
    for node in merged_drg.get("nodes", []):
        if isinstance(node, dict):
            urn = node.get("urn")
            if isinstance(urn, str) and urn:
                drg_topics.append(urn)

    return {
        "project_artifacts": sorted(dict.fromkeys(artifact_topics)),
        "drg_urns": sorted(dict.fromkeys(drg_topics)),
        "interview_sections": interview_sections,
        "interview_section_aliases": sorted(section.replace("_", "-") for section in interview_sections),
    }


@app.command("synthesize")
def charter_synthesize(
    adapter: str = typer.Option(
        "generated",
        "--adapter",
        help=(
            "Adapter to use. 'generated' (default) validates agent-authored YAML under "
            ".kittify/charter/generated/. 'fixture' is offline/testing only."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Stage and validate artifacts but do not promote to live tree.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    skip_code_evidence: bool = typer.Option(
        False,
        "--skip-code-evidence",
        help="Skip code-reading evidence collection.",
    ),
    skip_corpus: bool = typer.Option(
        False,
        "--skip-corpus",
        help="Skip best-practice corpus loading.",
    ),
    dry_run_evidence: bool = typer.Option(
        False,
        "--dry-run-evidence",
        help="Print evidence summary and exit without running synthesis.",
    ),
) -> None:
    """Validate and promote agent-generated project-local doctrine artifacts.

    Reads the charter interview answers, resolves synthesis targets from the
    DRG + doctrine, and writes all artifacts to .kittify/doctrine/.

    Doctrine generation is performed by the LLM harness (Claude Code, Codex,
    Cursor, etc.) via the spec-kitty-charter-doctrine skill. This command
    validates and promotes the artifacts the agent has written.

    Examples
    --------
    Validate + promote generated artifacts written by the harness::

        spec-kitty charter synthesize

    Validate + promote with fixture adapter (offline/testing)::

        spec-kitty charter synthesize --adapter fixture

    Dry-run (stage + validate, no promote)::

        spec-kitty charter synthesize --dry-run
    """
    from charter.synthesizer.errors import NeutralityGateViolation, SynthesisError, render_error_panel

    err_console = Console(stderr=True)

    try:
        repo_root = find_repo_root()

        # Collect evidence before building the synthesis request
        evidence_result = _collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        for warning in evidence_result.warnings:
            console.print(f"[yellow]\u26a0 {warning}[/yellow]")

        if dry_run_evidence:
            bundle = evidence_result.bundle
            console.print("[bold]Evidence dry-run summary:[/bold]")
            if bundle.code_signals:
                cs = bundle.code_signals
                console.print(f"  Code signals: stack={cs.stack_id}, lang={cs.primary_language}")
                console.print(f"  Representative files: {len(cs.representative_files)} found")
            else:
                console.print("  Code signals: none (skipped or not detected)")
            console.print(f"  URL list: {len(bundle.url_list)} URL(s) configured")
            if bundle.corpus_snapshot:
                console.print(
                    f"  Corpus: {bundle.corpus_snapshot.snapshot_id} "
                    f"({len(bundle.corpus_snapshot.entries)} entries)"
                )
            else:
                console.print("  Corpus: none")
            for w in evidence_result.warnings:
                console.print(f"  [yellow]Warning: {w}[/yellow]")
            raise typer.Exit(0)

        request, syn_adapter = _build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if dry_run:
            staged_files = _run_synthesis_dry_run(request, syn_adapter, repo_root)

            if json_output:
                print(json.dumps({
                    "result": "dry_run",
                    "staged_artifacts": staged_files,
                    "artifact_count": len(staged_files),
                    "validated": True,
                }, indent=2))
                return

            console.print("[yellow]Dry-run:[/yellow] synthesis staged and validated (not promoted)")
            for f in staged_files:
                console.print(f"  [dim]staged:[/dim] {f}")
            return

        from charter.synthesizer import synthesize

        result = synthesize(request, adapter=syn_adapter, repo_root=repo_root)

        if json_output:
            print(json.dumps({
                "result": "success",
                "target_kind": result.target_kind,
                "target_slug": result.target_slug,
                "inputs_hash": result.inputs_hash,
                "adapter_id": result.effective_adapter_id,
                "adapter_version": result.effective_adapter_version,
            }, indent=2))
            return

        console.print("[green]Charter synthesis complete[/green]")
        console.print(f"Primary artifact: {result.target_kind}:{result.target_slug}")
        console.print(f"Adapter: {result.effective_adapter_id} v{result.effective_adapter_version}")

    except typer.Exit:
        raise
    except NeutralityGateViolation as e:
        render_error_panel(e, err_console)
        err_console.print(
            f"\n[yellow]Staging directory preserved at:[/yellow] {e.staging_dir}\n"
            "Inspect the staged artifacts, adjust the synthesis prompt or scope, and retry."
        )
        raise typer.Exit(code=1) from e
    except SynthesisError as e:
        render_error_panel(e, err_console)
        raise typer.Exit(code=1) from e
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


@app.command("resynthesize")
def charter_resynthesize(  # noqa: C901
    topic: str | None = typer.Option(
        None,
        "--topic",
        help=(
            "Structured topic selector: "
            "<kind>:<slug> (project-local), "
            "<drg-urn> (shipped+project graph), "
            "or <interview-section-label>."
        ),
    ),
    list_topics: bool = typer.Option(
        False,
        "--list-topics",
        help="List valid structured topic selectors and exit.",
    ),
    adapter: str = typer.Option(
        "generated",
        "--adapter",
        help=(
            "Adapter to use. 'generated' (default) validates agent-authored YAML under "
            ".kittify/charter/generated/. 'fixture' is offline/testing only."
        ),
    ),
    skip_code_evidence: bool = typer.Option(
        False,
        "--skip-code-evidence",
        help="Skip code-reading evidence collection.",
    ),
    skip_corpus: bool = typer.Option(
        False,
        "--skip-corpus",
        help="Skip best-practice corpus loading.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Regenerate a bounded set of project-local doctrine artifacts (partial resynthesis).

    Uses a structured selector to identify the target set:

    - ``directive:PROJECT_001`` — regenerate a specific project directive.
    - ``tactic:how-we-apply-directive-003`` — regenerate one tactic.
    - ``directive:DIRECTIVE_003`` — regenerate every artifact whose provenance
      references the shipped DIRECTIVE_003 URN.
    - ``testing-philosophy`` — regenerate all artifacts from that interview section.

    Unrelated artifacts are never touched (FR-017).

    Examples
    --------
    Resynthesize a single tactic::

        spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003

    Resynthesize all artifacts referencing a shipped directive::

        spec-kitty charter resynthesize --topic directive:DIRECTIVE_003
    """
    from charter.synthesizer.errors import (
        SynthesisError,
        TopicSelectorUnresolvedError,
        render_error_panel,
    )
    from rich.panel import Panel
    from rich.text import Text

    err_console = Console(stderr=True)

    try:
        repo_root = find_repo_root()
        evidence_result = _collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        for warning in evidence_result.warnings:
            console.print(f"[yellow]\u26a0 {warning}[/yellow]")

        request, syn_adapter = _build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if list_topics:
            topics = _list_resynthesis_topics(request, repo_root)
            if json_output:
                print(json.dumps({
                    "result": "success",
                    "topics": topics,
                }, indent=2))
                return

            if not any(topics.values()):
                console.print("[yellow]No topic selectors available yet.[/yellow]")
                return

            if topics["project_artifacts"]:
                console.print("[bold]Project artifact selectors[/bold]")
                for selector in topics["project_artifacts"]:
                    console.print(f"  {selector}")
            if topics["drg_urns"]:
                console.print("[bold]DRG URNs[/bold]")
                for selector in topics["drg_urns"]:
                    console.print(f"  {selector}")
            if topics["interview_sections"]:
                console.print("[bold]Interview sections[/bold]")
                for selector in topics["interview_sections"]:
                    alias = selector.replace("_", "-")
                    console.print(f"  {selector}  [dim](alias: {alias})[/dim]")
            return

        if topic is None:
            raise TaskCliError("Pass --topic <selector> or use --list-topics.")

        from charter.synthesizer.resynthesize_pipeline import run as resynthesize_run

        result = resynthesize_run(
            request=request,
            adapter=syn_adapter,
            topic=topic,
            repo_root=repo_root,
        )

        if result.is_noop:
            if json_output:
                print(json.dumps({
                    "result": "noop",
                    "topic": topic,
                    "diagnostic": result.diagnostic,
                    "matched_form": result.resolved_topic.matched_form,
                    "targets_count": 0,
                }, indent=2))
                return
            console.print(f"[yellow]No-op:[/yellow] {result.diagnostic}")
            return

        regenerated = [
            f"{t.kind}:{t.slug}"
            for t in result.resolved_topic.targets
        ]

        if json_output:
            print(json.dumps({
                "result": "success",
                "topic": topic,
                "matched_form": result.resolved_topic.matched_form,
                "matched_value": result.resolved_topic.matched_value,
                "regenerated": regenerated,
                "run_id": result.manifest.run_id,
                "manifest_artifacts": len(result.manifest.artifacts),
            }, indent=2))
            return

        console.print(f"[green]Resynthesis complete[/green] (topic: {topic!r})")
        console.print(f"Matched form: {result.resolved_topic.matched_form}")
        console.print(f"Run ID: {result.manifest.run_id}")
        console.print("Regenerated artifacts:")
        for art in regenerated:
            console.print(f"  [green]✓[/green] {art}")

    except TopicSelectorUnresolvedError as e:
        # Exit code 2 — invalid usage (contracts/topic-selector.md §2.2)
        panel_body = str(e)
        if hasattr(e, "candidates") and e.candidates:
            cands = "\n".join(f"  * {c}" for c in e.candidates)
            panel_body += f"\n\nNearest candidates:\n{cands}"
        panel_body += (
            "\n\nRun 'spec-kitty charter resynthesize --list-topics' to see all valid selectors."
        )
        err_console.print(
            Panel(
                Text(panel_body),
                title=f'[bold red]Cannot resolve --topic "{e.raw}"[/]',
                border_style="red",
            )
        )
        raise typer.Exit(code=2) from e
    except SynthesisError as e:
        render_error_panel(e, err_console)
        raise typer.Exit(code=1) from e
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e
