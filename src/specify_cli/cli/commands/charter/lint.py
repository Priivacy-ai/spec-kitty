"""``spec-kitty charter lint`` command (WP06 per-subcommand split)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console
from specify_cli.cli.commands.charter._common import _emit_error

# Test-patch shim — see ``synthesize.py``.
import specify_cli.cli.commands.charter as _charter_pkg

if TYPE_CHECKING:
    from charter.drg import OrgDRGFragment

__all__ = ["charter_lint"]


def _print_charter_lint_banner(
    report: Any,
    org_layer_summary: list[str],
) -> bool:
    """Print the human-readable banner block for ``charter lint``.

    Implements the FR-003 / ``contracts/charter-lint-json.md`` human-banner
    mapping table:

    - ``GraphState.MISSING`` → one terse "no lintable graph" line and
      return ``True`` to signal the caller to short-circuit.
    - ``GraphState.BUILT_IN_ONLY`` → per-layer block with ``[built-in]``
      and a "no project overlay" qualifier; on empty findings, the
      "No decay detected" line carries a dim ``(in built-in graph)``
      qualifier; return ``True`` only when findings are empty.
    - ``GraphState.MERGED`` → existing per-layer block with org markers
      and ``[project]``; on empty findings, the unchanged
      "No decay detected" line; return ``True`` only when findings are
      empty.

    Returns ``True`` when the caller should not print the per-finding
    list (i.e., the banner already conveyed the full result).
    """
    from specify_cli.charter_runtime.lint import GraphState as _GraphState  # local alias

    if report.graph_state is _GraphState.MISSING:
        console.print(
            "[bold]Charter Lint:[/bold] no lintable graph found — "
            "run `spec-kitty charter synthesize`"
        )
        return True

    console.print("[bold]Charter Lint - layers:[/bold]")
    console.print(r"  [dim]\[built-in][/dim]")
    if report.graph_state is _GraphState.BUILT_IN_ONLY and not org_layer_summary:
        console.print(
            r"  [dim]\[no project overlay — run `spec-kitty charter synthesize`][/dim]"
        )
    else:
        for org_marker in org_layer_summary:
            console.print(rf"  [dim]\[{org_marker}][/dim]")
        if report.graph_state is not _GraphState.BUILT_IN_ONLY:
            console.print(r"  [dim]\[project][/dim]")

    if report.findings:
        return False

    if report.graph_state is _GraphState.BUILT_IN_ONLY:
        console.print(
            "[green]No decay detected[/green] [dim](in built-in graph)[/dim]"
        )
    else:
        console.print("[green]No decay detected[/green]")
    console.print(
        f"[dim]Scanned {report.drg_node_count} nodes in {report.duration_seconds:.2f}s[/dim]"
    )
    return True


@charter_app.command("lint")
def charter_lint(
    mission: str | None = typer.Option(None, "--mission", help="Scope lint to a specific mission slug"),
    orphans: bool = typer.Option(False, "--orphans", help="Run only orphan checks"),
    contradictions: bool = typer.Option(False, "--contradictions", help="Run only contradiction checks"),
    stale: bool = typer.Option(False, "--stale", help="Run only staleness checks"),
    output_json: bool = typer.Option(False, "--json", help="Output findings as JSON"),
    severity: str = typer.Option("low", "--severity", help="Minimum severity (low/medium/high/critical)"),
) -> None:
    """Detect decay in charter artifacts via graph-native checks."""
    import sys

    from specify_cli.charter_runtime.lint import LintEngine

    try:
        repo_root = _charter_pkg.find_repo_root()
    except TaskCliError as e:
        _emit_error(console, json_output=output_json, message=str(e))
        raise typer.Exit(code=1) from e

    scope = mission

    # Resolve which checks to run
    explicit = {k for k, v in [("orphans", orphans), ("contradictions", contradictions), ("staleness", stale)] if v}
    active_checks: set[str] | None = explicit if explicit else None  # None = all

    engine = LintEngine(repo_root)
    report = engine.run(
        feature_scope=scope,
        checks=active_checks,
        min_severity=severity,
    )

    # Slice F WP06 / FR-003: load the three-layer DRG fragment list so
    # the human-readable surface can attribute findings (or the OK
    # marker) to each configured layer by name. JSON output is unchanged
    # — programmatic consumers read provenance from the merged DRG via
    # ``charter.drg.merge_three_layers`` directly.
    org_layer_summary: list[str] = []
    org_fragments: list[OrgDRGFragment] = []
    try:
        from charter.drg import OrgDRGFragment, load_org_drg

        org_fragments = load_org_drg(repo_root)
        # Type-narrow against the public Pydantic schema so a regression
        # that returns the wrong shape fails fast at the CLI boundary.
        assert all(isinstance(f, OrgDRGFragment) for f in org_fragments), (
            "load_org_drg must return OrgDRGFragment instances"
        )
        for fragment in org_fragments:
            org_layer_summary.append(f"org:{fragment.pack_name}")
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on bad pack
        # A pack-loading failure (e.g. ``OrgPackMissingError``) should
        # surface as a lint-time hard error, not silently swallow.
        # FR-004 binding: hard-fail with a named error so the operator
        # can fix the missing pack before re-running lint.
        from charter.drg import OrgDRGConflictError, OrgPackMissingError

        if isinstance(exc, (OrgPackMissingError, OrgDRGConflictError)):
            message = f"Charter Lint: org-layer load failed: {exc}"
            _emit_error(console, json_output=output_json, message=message)
            raise typer.Exit(code=1) from exc
        # Unknown failure shape — log and continue without org layer.
        if not output_json:
            console.print(
                f"[yellow]warning:[/yellow] org-layer skipped (load error): {exc}"
            )

    # When org packs are configured, exercise ``merge_three_layers``
    # against an empty built-in graph so any pack-level conflict (layer
    # rule violation, built-in invariant override) surfaces here at lint
    # time rather than at first-use of the merged DRG. The merge result
    # itself is not consumed by the human-readable banner — the engine's
    # existing graph load remains authoritative for findings — but the
    # call enforces FR-005 hard-fails as a lint gate.
    if org_fragments:
        import datetime as _dt

        from charter.drg import (
            DRGGraph,
            OrgDRGConflict,
            OrgDRGConflictError,
            merge_three_layers,
        )

        empty_built_in = DRGGraph(
            schema_version="1.0",
            generated_at=_dt.datetime.now(_dt.UTC).isoformat(),
            generated_by="charter-lint",
            nodes=[],
            edges=[],
        )
        try:
            merge_three_layers(
                built_in=empty_built_in, org_fragments=org_fragments, project=None
            )
        except OrgDRGConflictError as exc:
            # ``exc.conflicts`` is a list of ``OrgDRGConflict`` records;
            # re-format with the conflict kind named so operators see
            # which org pack(s) misbehaved.
            conflicts: list[OrgDRGConflict] = list(exc.conflicts)
            if output_json:
                details = "; ".join(
                    f"kind={c.kind} target_id={c.target_id} layers={c.conflicting_layers}"
                    for c in conflicts
                )
                _emit_error(
                    console,
                    json_output=True,
                    message=(
                        f"Charter Lint: {len(conflicts)} org-layer conflict(s) detected"
                        + (f": {details}" if details else "")
                    ),
                )
                raise typer.Exit(code=1) from exc
            console.print(
                f"[red]Charter Lint:[/red] {len(conflicts)} org-layer "
                f"conflict(s) detected"
            )
            for c in conflicts:
                console.print(
                    f"  - kind={c.kind} target_id={c.target_id} "
                    f"layers={c.conflicting_layers}"
                )
            raise typer.Exit(code=1) from exc

    if output_json:
        sys.stdout.write(report.to_json())
        sys.stdout.write("\n")
        return

    # FR-003 / charter-lint-json.md "Human-banner mapping" table: the
    # human-readable banner branches on ``report.graph_state``. We delegate
    # to ``_print_charter_lint_banner`` so the outer command stays under
    # the cyclomatic-complexity gate.
    if _print_charter_lint_banner(report, org_layer_summary):
        return

    console.print(
        f"\n[bold]Charter Lint[/bold] — {len(report.findings)} finding(s)"
        f" in {report.duration_seconds:.2f}s\n"
    )
    for finding in report.findings:
        severity_color = {
            "low": "dim",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(finding.severity, "white")
        console.print(
            f"  [{severity_color}][{finding.severity.upper()}][/{severity_color}]"
            f" [{finding.category}] {finding.type}: {finding.id}"
        )
        console.print(f"    {finding.message}")
        if finding.remediation_hint:
            console.print(f"    [dim]→ {finding.remediation_hint}[/dim]")
