"""spec-kitty charter activate — activate a doctrine artifact.

FR-004 (direct activation), FR-008 (in-flight step-removal warning),
FR-013/FR-014 (cascade scope), FR-035 (fail-closed on invalid pack config).

Wiring (R-011-D, Contracts C3.2/C3.3, C1.5)
-------------------------------------------
This is the live caller that finally wires the WP10 plan/commit engine and the
WP11 scoped cascade engine into the CLI surface:

* ``--cascade`` is parsed through :meth:`charter.cascade.CascadeScope.parse`
  (WP11) into a real scope value object — it is **never** collapsed to a bool
  (Contract C3.3). Absence of ``--cascade`` routes through
  :func:`charter.cascade.referenced_but_not_cascaded` so the operator is warned
  about referenced-but-skipped artifacts (FR-013).
* In-scope cascade targets (:func:`charter.cascade.cascade_activation_targets`)
  are activated through the same :class:`~charter.pack_manager.CharterPackManager`
  seam as the direct activation, and rendered per kind (FR-014).
* :class:`charter.pack_context.CharterPackConfigError` is caught and surfaced as
  a clean exit-1 with its diagnostic code + remediation, before any mutation
  (FR-035 fail-closed, C1.5).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from charter.cascade import (
    CascadeScope,
    cascade_activation_targets,
    referenced_but_not_cascaded,
)
from charter.catalog import resolve_doctrine_root
from charter.invocation_context import ProjectContext
from charter.kind_vocabulary import (
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
    UnknownArtifactIdError,
    resolve_artifact_urn,
    resolve_config_id,
)
from charter.pack_context import CharterPackConfigError, PackContext
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager

__all__ = ["activate_cmd"]

console = Console()


def render_pack_config_error(exc: CharterPackConfigError, console: Console) -> None:
    """Render a :class:`CharterPackConfigError` as fail-closed CLI guidance (FR-035).

    Surfaces the stable ``CHARTER_PACK_CONFIG_INVALID`` diagnostic code plus the
    error body (which already carries the remediation hint). Shared by the
    activate and deactivate commands so both fail closed identically.
    """
    console.print(f"[red]Error[/red] ({exc.code}): {exc.body}")


def validate_pack_config(repo_root: Path) -> None:
    """Load the project pack context to fail closed on invalid config (FR-035).

    :meth:`PackContext.from_config` raises :class:`CharterPackConfigError` when
    ``.kittify/config.yaml`` has an invalid charter-pack shape. Calling it here
    — *before* any mutation — gives that previously dead-ended error type a live
    external caller and guarantees no write happens on a malformed config (C1.5).
    """
    PackContext.from_config(repo_root)


def _source_urn(kind: str, artifact_id: str) -> str | None:
    """Resolve the DRG source URN for ``(kind, config-stem artifact_id)``.

    Returns ``None`` when the kind has no DRG artifact-node representation
    (``mission-type``) or the artifact has no resolvable DRG node — cascade is a
    no-op in those cases rather than an error.
    """
    try:
        kind_enum = ArtifactKind.from_operator_token(kind)
    except MissionTypeNotAnArtifactKind:
        return None
    try:
        return resolve_artifact_urn(
            kind_enum, artifact_id, doctrine_root=resolve_doctrine_root()
        )
    except UnknownArtifactIdError:
        return None


def _drg_id_to_config_id(kind_value: str, drg_id: str, doctrine_root: Path) -> str:
    """Map a cascade-reported DRG bare ID back to its config-stem ID.

    The cascade engine works in DRG URN space (e.g. ``DIRECTIVE_001``) while
    activation lists use config-stem IDs (e.g.
    ``001-architectural-integrity-standard``). Falls back to the DRG ID when no
    config stem resolves (so rendering never crashes on an orphan node).
    """
    try:
        return resolve_config_id(f"{kind_value}:{drg_id}", doctrine_root=doctrine_root)
    except (UnknownArtifactIdError, ValueError):
        return drg_id


def _emit_step_removal_warnings(kind: str, artifact_id: str, repo_root: Path) -> None:
    """Emit in-flight step-removal warnings for the activation (FR-008).

    Generalized out of the command body: the command no longer branches on
    ``kind == "mission-type"`` inline — it always calls this collector, which is
    a no-op for kinds that have no step-sequence semantics. Mission-type
    activations still surface the in-flight warning, now via this single seam.
    """
    if kind != "mission-type":
        return

    from doctrine.missions.mission_type_repository import (  # noqa: PLC0415  # boundary: lazy import intentionally not facaded (PLC0415; boundary-invisible)
        MissionTypeRepository,
    )

    from specify_cli.charter_activate import (  # noqa: PLC0415
        emit_step_removal_warnings,
        find_removed_steps,
        scan_inflight_missions,
    )

    try:
        from charter.mission_type_profiles import (  # noqa: PLC0415
            resolve_action_sequence,
        )

        current_seq: list[str] = resolve_action_sequence(artifact_id, repo_root)
    except Exception:  # noqa: BLE001 — type not yet activated or unknown
        current_seq = []

    mt = MissionTypeRepository.default().get(artifact_id)
    incoming_seq: list[str] = list(mt.action_sequence) if mt is not None else []

    removed = find_removed_steps(current_seq, incoming_seq)
    if removed:
        step_warnings = scan_inflight_missions(removed, repo_root / "kitty-specs")
        emit_step_removal_warnings(step_warnings, console)


def _render_cascade_activation(
    manager: CharterPackManager,
    ctx_project: ProjectContext,
    source_urn: str,
    scope: CascadeScope,
    repo_root: Path,
) -> None:
    """Activate scoped cascade targets and render the outcome (FR-014).

    Walks the merged DRG from ``source_urn`` via the WP11 cascade engine, keeps
    only the kinds the scope selects, and activates each in-scope target through
    the same activation seam. Skipped-by-scope kinds are reported so the operator
    sees exactly what the explicit scope excluded.
    """
    from charter._drg_helpers import load_validated_graph  # noqa: PLC0415

    graph = load_validated_graph(repo_root)
    result = cascade_activation_targets(graph, source_urn, scope)
    doctrine_root = resolve_doctrine_root()

    for kind_value in sorted(result.activated):
        kind_token = ArtifactKind(kind_value).operator_token
        for cascade_drg_id in result.activated[kind_value]:
            # The cascade engine reports DRG bare IDs; activation lists use
            # config-stem IDs. Resolve back through the kind-vocabulary bridge.
            config_id = _drg_id_to_config_id(kind_value, cascade_drg_id, doctrine_root)
            try:
                manager.activate(ctx_project, kind_token, config_id, cascade=False)
            except ValueError as exc:
                console.print(
                    f"[yellow]Warning[/yellow]: could not cascade-activate "
                    f"{kind_token}/{config_id}: {exc}"
                )
                continue
            console.print(
                f"[cyan]Cascade-activated[/cyan]: {kind_token}/{config_id}"
            )

    for kind_value in sorted(result.skipped_by_scope):
        kind_token = ArtifactKind(kind_value).operator_token
        for skipped_id in result.skipped_by_scope[kind_value]:
            config_id = _drg_id_to_config_id(kind_value, skipped_id, doctrine_root)
            console.print(
                f"[dim]Skipped (out of scope)[/dim]: {kind_token}/{config_id}"
            )


def _render_no_cascade_warning(source_urn: str, repo_root: Path) -> None:
    """Warn about referenced-but-not-cascaded artifacts (FR-013, Contract C3.2)."""
    from charter._drg_helpers import load_validated_graph  # noqa: PLC0415

    graph = load_validated_graph(repo_root)
    report = referenced_but_not_cascaded(graph, source_urn)
    if not report.has_skipped:
        return
    doctrine_root = resolve_doctrine_root()
    for kind_value in sorted(report.skipped):
        kind_token = ArtifactKind(kind_value).operator_token
        for skipped_drg_id in report.skipped[kind_value]:
            config_id = _drg_id_to_config_id(kind_value, skipped_drg_id, doctrine_root)
            console.print(
                f"[yellow]Warning[/yellow]: referenced {kind_token}/{config_id} "
                f"was not activated (no --cascade)."
            )
    console.print(f"[yellow]Hint[/yellow]: {report.recovery_hint}")


def activate_cmd(
    ctx: typer.Context,
    kind: str | None = typer.Argument(None, help="Activation kind (e.g. directive, agent-profile)."),
    artifact_id: str | None = typer.Argument(None, help="Artifact ID to activate."),
    cascade: str | None = typer.Option(
        None,
        "--cascade",
        help=(
            "Cascade activation scope: 'all' for every referenced kind, or a "
            "comma-separated kind list (e.g. 'agent-profile,tactic'). "
            "Omit to skip cascade (referenced artifacts are reported as a warning)."
        ),
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Activate a doctrine artifact by kind and ID (FR-004), with optional cascade."""
    if ctx.invoked_subcommand is not None:
        return
    if kind is None or artifact_id is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)
    if kind not in YAML_KEY_MAP:
        console.print(f"[red]Error:[/red] Unknown kind '{kind}'. Valid kinds: {', '.join(sorted(YAML_KEY_MAP))}.")
        raise typer.Exit(1)

    # FR-013/014: parse the scope value object — never collapsed to a bool
    # (Contract C3.3). A bad kind token raises a structured ValueError.
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

    # FR-008: in-flight step-removal warnings (generalized — no inline
    # `kind == "mission-type"` branch in the command flow).
    _emit_step_removal_warnings(kind, artifact_id, repo_root)

    manager = CharterPackManager()
    try:
        result = manager.activate(ctx_project, kind, artifact_id, cascade=scope is not None)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    for msg in result.activated:
        console.print(f"[green]Activated[/green]: {msg}")
    for warn in result.warnings:
        console.print(f"[yellow]Warning[/yellow]: {warn}")

    # FR-013/014: cascade is driven from the CLI via the WP11 engine over the
    # merged DRG (pack_manager's own cascade is deferred — the live wiring is
    # here). Resolve the source URN; mission-type / non-DRG kinds short-circuit.
    source_urn = _source_urn(kind, artifact_id)
    if source_urn is None:
        return
    if scope is None:
        _render_no_cascade_warning(source_urn, repo_root)
    else:
        _render_cascade_activation(manager, ctx_project, source_urn, scope, repo_root)
