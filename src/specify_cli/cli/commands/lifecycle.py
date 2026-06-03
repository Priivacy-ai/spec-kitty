"""Top-level lifecycle command shims.

These commands provide CLI-visible entry points that delegate to the
agent lifecycle implementations.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path

import typer
from rich.console import Console

from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.cli.commands.agent import mission as agent_feature
from specify_cli.core.paths import locate_project_root
from specify_cli.workspace.assert_initialized import (
    SPEC_KITTY_REPO_NOT_INITIALIZED,
    SpecKittyNotInitialized,
    assert_initialized,
)

#: Canonical question sets for the specify/plan widen-enabled interview loops.
#: Each entry is a ``(question_id, question_text)`` pair consumed by
#: ``run_specify_interview`` / ``run_plan_interview``.
SPECIFY_WIDEN_QUESTIONS: list[tuple[str, str]] = [
    ("problem_statement", "What problem does this feature solve?"),
    ("success_criteria", "How will we know this feature is successful?"),
    ("scope_boundaries", "What is explicitly out of scope for this feature?"),
]

PLAN_WIDEN_QUESTIONS: list[tuple[str, str]] = [
    ("approach", "What is the high-level implementation approach?"),
    ("risks", "What are the main risks or unknowns?"),
    ("dependencies", "What upstream dependencies does this plan rely on?"),
]

_console = Console()


def _scaffold_next_action(mission_slug: str) -> str:
    return (
        "Open spec_file and replace the scaffold with a complete specification; "
        f"then run `spec-kitty plan --mission {mission_slug}`."
    )


def _with_specify_scaffold_state(payload: dict[str, object], mission_slug: str) -> dict[str, object]:
    """Expose that direct ``spec-kitty specify`` only creates a scaffold."""
    enriched = dict(payload)
    enriched["scaffold_only"] = True
    enriched["spec_state"] = "scaffold_only"
    enriched["next_action"] = _scaffold_next_action(str(enriched.get("mission_slug") or mission_slug))
    enriched["next_step"] = enriched["next_action"]
    return enriched


def _emit_scaffold_only_guidance(mission_slug: str) -> None:
    _console.print("[yellow]Scaffold-only:[/yellow] spec.md was created as a scaffold; no complete spec was authored.")
    _console.print(f"[cyan]Next:[/cyan] {_scaffold_next_action(mission_slug)}")


def _create_mission_for_specify_json(slug: str, mission_type: str | None) -> None:
    """Run mission creation and enrich its single JSON payload for direct specify."""
    capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(capture):
            agent_feature.create_mission(mission_slug=slug, mission_type=mission_type, json_output=True)
    except typer.Exit:
        print(capture.getvalue(), end="")
        raise

    output = capture.getvalue()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        print(json.dumps(_with_specify_scaffold_state(payload, slug)))
        return
    print(output, end="")


def _enforce_initialized(*, require_specs: bool = True, json_output: bool = False) -> None:
    """Fail-loud if the cwd's canonical repo is not a Spec Kitty project (FR-032).

    Symmetric with FR-005's no-silent-fallback selector stance: if the
    operator runs ``specify`` / ``plan`` / ``tasks`` from a directory that
    is not an initialized Spec Kitty project, we exit non-zero with an
    actionable message instead of silently writing to a parent or
    sibling repo.
    """
    try:
        assert_initialized(require_specs=require_specs)
    except SpecKittyNotInitialized as exc:
        if json_output:
            print(
                json.dumps(
                    {
                        "error_code": SPEC_KITTY_REPO_NOT_INITIALIZED,
                        "error": str(exc),
                    }
                )
            )
            raise typer.Exit(code=1) from exc
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def _slugify_feature_input(value: str) -> str:
    """Normalize a free-form feature name to kebab-case slug text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise typer.BadParameter("Feature name cannot be empty.")
    return slug


def specify(
    feature: str = typer.Argument(..., help="Feature name or slug (e.g., user-authentication)"),
    mission_type: str | None = typer.Option(None, "--mission-type", help="Mission type (e.g., software-dev, research)"),
    mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Create a feature scaffold in kitty-specs/."""
    _enforce_initialized(require_specs=False, json_output=json_output)
    slug = _slugify_feature_input(feature)
    resolved_mission_type = mission_type
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
    if json_output:
        _create_mission_for_specify_json(slug, resolved_mission_type)
    else:
        agent_feature.create_mission(mission_slug=slug, mission_type=resolved_mission_type, json_output=False)
        _emit_scaffold_only_guidance(slug)

    # FR-002: Wire widen-enabled interview for the specify flow.
    # Only run in interactive (non-JSON) mode so agent/script callers are unaffected.
    if not json_output:
        from specify_cli.missions.plan.specify_interview import run_specify_interview

        repo_root = locate_project_root()
        if repo_root is not None:
            with contextlib.suppress(Exception):
                run_specify_interview(
                    questions=SPECIFY_WIDEN_QUESTIONS,
                    repo_root=repo_root,
                    mission_slug=slug,
                    console=_console,
                )


def plan(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug (e.g., 001-user-authentication)"),
    feature: str | None = typer.Option(None, "--feature", hidden=True, help="(deprecated) Use --mission"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Scaffold plan.md for a feature."""
    _enforce_initialized(json_output=json_output)
    resolved_mission = None
    if mission is not None or feature is not None:
        resolved = resolve_selector(
            canonical_value=mission,
            canonical_flag="--mission",
            alias_value=feature,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )
        resolved_mission = resolved.canonical_value
    agent_feature.setup_plan(feature=resolved_mission, json_output=json_output)

    # FR-002: Wire widen-enabled interview for the plan flow.
    # Only run in interactive (non-JSON) mode so agent/script callers are unaffected.
    if not json_output:
        import pathlib

        from specify_cli.missions.plan.plan_interview import run_plan_interview

        repo_root = locate_project_root()
        if repo_root is not None:
            # Resolve the mission slug from the plan context.
            # When the caller supplies --mission, that slug is already resolved;
            # otherwise we fall back to detecting the slug from the working tree.
            _mission_slug = resolved_mission
            if _mission_slug is None:
                with contextlib.suppress(Exception):
                    from specify_cli.cli.commands.agent.mission import (
                        _find_feature_directory,
                    )

                    _fd = _find_feature_directory(repo_root, pathlib.Path.cwd())
                    _mission_slug = _fd.name

            if _mission_slug is not None:
                with contextlib.suppress(Exception):
                    run_plan_interview(
                        questions=PLAN_WIDEN_QUESTIONS,
                        repo_root=repo_root,
                        mission_slug=_mission_slug,
                        console=_console,
                    )


def _emit_tasks_missing_mission_guidance(repo_root: Path, *, json_output: bool) -> None:
    payload = agent_feature._build_setup_plan_detection_error(  # noqa: SLF001
        repo_root,
        "--mission <slug> is required",
        None,
        error_code="FEATURE_CONTEXT_UNRESOLVED",
        command_name="finalize-tasks",
        command_args=["--json"] if json_output else [],
    )
    missions = payload.get("available_missions")
    if isinstance(missions, list) and missions:
        args_suffix = " --json" if json_output else ""
        payload["example_command"] = f"spec-kitty tasks --mission {missions[0]}{args_suffix}"

    if json_output:
        print(json.dumps(payload))
    else:
        _console.print(f"[red]Error:[/red] {payload['error']}")
        if isinstance(missions, list):
            for slug in missions[:10]:
                _console.print(f"  - {slug}")
        if "example_command" in payload:
            _console.print(f"  {payload['example_command']}")


def tasks(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug (e.g., 001-user-authentication)"),
    feature: str | None = typer.Option(None, "--feature", hidden=True, help="(deprecated) Use --mission"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
) -> None:
    """Finalize tasks metadata after task generation."""
    _enforce_initialized(json_output=json_output)
    resolved_mission = None
    if mission is not None or feature is not None:
        try:
            resolved = resolve_selector(
                canonical_value=mission,
                canonical_flag="--mission",
                alias_value=feature,
                alias_flag="--feature",
                suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
                command_hint="--mission <slug>",
            )
        except typer.BadParameter as exc:
            if json_output:
                print(json.dumps({"error": str(exc)}))
            else:
                _console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        resolved_mission = resolved.canonical_value
    else:
        repo_root = locate_project_root()
        if repo_root is not None:
            _emit_tasks_missing_mission_guidance(repo_root, json_output=json_output)
            raise typer.Exit(1)
    agent_feature.finalize_tasks(feature=resolved_mission, json_output=json_output)


__all__ = ["specify", "plan", "tasks"]
