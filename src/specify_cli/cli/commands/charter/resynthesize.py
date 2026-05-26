"""``spec-kitty charter resynthesize`` command (WP06 per-subcommand split)."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import (
    METADATA_FILENAME,
    charter_app,
    console,
)
# See ``synthesize.py`` for the package-module pattern: patches of
# ``specify_cli.cli.commands.charter.<name>`` must be visible here too. We route
# ``_assert_bundle_compatible``, ``_build_synthesis_request``,
# ``_collect_evidence_result``, and ``_list_resynthesis_topics`` through the
# package module at call time so legacy ``patch("…charter.X", …)`` fixtures
# remain effective across the WP06 split.
import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["charter_resynthesize"]


@charter_app.command("resynthesize")
def charter_resynthesize(  # noqa: C901
    topic: str | None = typer.Option(
        None,
        "--topic",
        help=(
            "Structured topic selector: "
            "<kind>:<slug> (project-local), "
            "<drg-urn> (built-in+project graph), "
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
      references the built-in DIRECTIVE_003 URN.
    - ``testing-philosophy`` — regenerate all artifacts from that interview section.

    Unrelated artifacts are never touched (FR-017).

    Examples
    --------
    Resynthesize a single tactic::

        spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003

    Resynthesize all artifacts referencing a built-in directive::

        spec-kitty charter resynthesize --topic directive:DIRECTIVE_003
    """
    from charter.synthesizer.errors import (
        SynthesisError,
        TopicSelectorUnresolvedError,
        render_error_panel,
    )

    err_console = Console(stderr=True)

    try:
        repo_root = _charter_pkg.find_repo_root()
        charter_dir = repo_root / ".kittify" / "charter"
        if (charter_dir / METADATA_FILENAME).exists():
            _charter_pkg._assert_bundle_compatible(charter_dir)
        evidence_result = _charter_pkg._collect_evidence_result(
            repo_root,
            skip_code_evidence=skip_code_evidence,
            skip_corpus=skip_corpus,
        )
        for warning in evidence_result.warnings:
            console.print(f"[yellow]⚠ {warning}[/yellow]")

        request, syn_adapter = _charter_pkg._build_synthesis_request(repo_root, adapter, evidence=evidence_result.bundle)

        if list_topics:
            topics = _charter_pkg._list_resynthesis_topics(request, repo_root)
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
