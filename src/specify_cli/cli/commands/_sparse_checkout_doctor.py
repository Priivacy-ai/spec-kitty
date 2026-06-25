"""Legacy sparse-checkout detection + remediation cluster for ``doctor`` (WP08, #2059).

Extracts Cluster E out of ``doctor.py`` and decomposes the ``sparse-checkout``
command (CC19) into <=15-CC sub-helpers (detect → render-finding →
build-remediation-plan → apply-or-refuse).

Import discipline (one-way, I-2): imports shared infra from
:mod:`._doctor_shared`; never imports the CLI ``doctor`` module. Heavy domain
imports (``specify_cli.git.sparse_checkout*``) stay FUNCTION-LOCAL to keep module
import cheap and avoid circular-import edge cases, mirroring the pre-extraction
pattern. The ``sparse-checkout`` subcommand name is owned by the shell in
``doctor.py`` and is byte-preserved (I-7: the compat safety predicate keys on it).
"""

from __future__ import annotations

from pathlib import Path

import typer

from specify_cli.core.paths import locate_project_root

from ._doctor_shared import _is_interactive_environment, console

# ``__all__`` lists this sibling's single cross-module entrypoint. The render
# helpers are intra-module (used here + by this module's own unit tests) and are
# deliberately NOT exported — listing them would register orphan public symbols
# under the dead-symbol gate (tests/architectural/test_no_dead_symbols).
__all__ = [
    "run_sparse_checkout",
]

_FIX_HINT = "spec-kitty doctor sparse-checkout --fix"


def _render_sparse_finding(report: object) -> None:
    """Render Quickstart Flow 1 finding output to the console.

    Kept separate from the command callback so tests can exercise the
    reporting surface directly. Uses ``soft_wrap=True`` to keep file
    paths on a single line regardless of terminal width — the doctor
    output contract is that affected paths are grep-able verbatim.
    """
    # Local import avoids circular-import edge cases during module load.
    from specify_cli.git.sparse_checkout import SparseCheckoutScanReport

    assert isinstance(report, SparseCheckoutScanReport)

    console.print(
        "[yellow]⚠ Legacy sparse-checkout state detected[/yellow]",
        soft_wrap=True,
    )
    if report.primary.is_active:
        console.print(f"  Primary: {report.primary.path}", soft_wrap=True)
        console.print("    core.sparseCheckout = true", soft_wrap=True)
        if report.primary.pattern_file_present and report.primary.pattern_file_path is not None:
            pf_rel = report.primary.pattern_file_path
            console.print(
                f"    pattern file: {pf_rel} ({report.primary.pattern_line_count} lines)",
                soft_wrap=True,
            )
    active_wts = [w for w in report.worktrees if w.is_blocking]
    if active_wts:
        console.print(
            f"  Lane worktrees: {len(active_wts)} affected", soft_wrap=True
        )
        for wt in active_wts:
            console.print(f"    {wt.path}", soft_wrap=True)
    console.print()
    console.print("  Why this matters:", soft_wrap=True)
    console.print(
        "    spec-kitty v3.0+ removed sparse-checkout support but does not ship a",
        soft_wrap=True,
    )
    console.print(
        "    migration. This state can cause silent data loss during mission merge",
        soft_wrap=True,
    )
    console.print(
        "    and broken lane worktrees on agent action implement.", soft_wrap=True
    )
    console.print("    See Priivacy-ai/spec-kitty#588.", soft_wrap=True)
    console.print()
    console.print("  Fix:", soft_wrap=True)
    console.print(f"    {_FIX_HINT}", soft_wrap=True)


def _render_remediation_plan(report: object) -> None:
    """Print the numbered step-by-step plan operators see before consenting."""
    from specify_cli.git.sparse_checkout import SparseCheckoutScanReport

    assert isinstance(report, SparseCheckoutScanReport)

    console.print("Proceed? This will:")
    step = 1
    console.print(f"  {step}. git sparse-checkout disable (primary)")
    step += 1
    console.print(f"  {step}. git config --unset core.sparseCheckout (primary)")
    step += 1
    console.print(f"  {step}. rm {report.primary.path}/.git/info/sparse-checkout (primary)")
    step += 1
    console.print(f"  {step}. git checkout HEAD -- . (primary)")
    for wt in report.worktrees:
        if not wt.is_blocking:
            continue
        step += 1
        console.print(f"  {step}. repeat steps 1–4 in {wt.path}")


def _resolve_repo_root() -> Path:
    """Resolve the project root or exit(1) with the standard message."""
    try:
        repo_root: Path | None = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)
    return repo_root


def _emit_clean_state(fix: bool) -> None:
    """Emit the no-state message for both modes and exit 0."""
    if fix:
        console.print("No sparse-checkout state to remediate.")
    else:
        console.print("[green]✓ No legacy sparse-checkout state detected.[/green]")
    raise typer.Exit(0)


def _prompt_consent() -> bool:
    """Prompt the operator once for plan consent; return True iff they consented."""
    try:
        response = input("[y/N] ").strip().lower()
    except EOFError:
        response = ""
    return response == "y"


def _render_remediation_results(results: list[object]) -> bool:
    """Render per-path remediation results; return True iff any path failed."""
    any_failure = False
    for r in results:
        if r.success:  # type: ignore[attr-defined]
            steps = len(r.steps_completed)  # type: ignore[attr-defined]
            console.print(
                f"[green]✓[/green] {r.path}: remediated "  # type: ignore[attr-defined]
                f"({steps} steps, clean verify)"
            )
        else:
            any_failure = True
            detail = r.error_detail or "unknown error"  # type: ignore[attr-defined]
            step = r.error_step or "unknown step"  # type: ignore[attr-defined]
            console.print(
                f"[red]✗[/red] {r.path}: failed at {step} — {detail}"  # type: ignore[attr-defined]
            )
    return any_failure


def _emit_dirty_refusal(results: list[object]) -> None:
    """Emit the dirty-tree refusal message and exit 1."""
    console.print("[red]✗ Cannot remediate: uncommitted changes detected.[/red]")
    for r in results:
        if r.dirty_before_remediation:  # type: ignore[attr-defined]
            console.print(f"  {r.path}")  # type: ignore[attr-defined]
    console.print()
    console.print("  Commit or stash your changes and retry:")
    console.print("    git stash push -u")
    console.print(f"    {_FIX_HINT}")
    raise typer.Exit(1)


def _apply_sparse_remediation(report: object) -> None:
    """Interactive --fix arm: show plan, prompt, remediate, render results.

    Exits 0 on operator abort or full success; exits 1 on dirty-tree refusal
    or any per-path failure.
    """
    from specify_cli.git.sparse_checkout_remediation import remediate

    _render_remediation_plan(report)
    if not _prompt_consent():
        console.print("Aborted — no changes made.")
        raise typer.Exit(0)

    # Consent already obtained for the whole plan; pass ``interactive=False``
    # so the remediator does not re-prompt per path.
    rep = remediate(report, interactive=False, confirm=None)
    results = [rep.primary_result, *rep.worktree_results]

    if any(r.dirty_before_remediation for r in results):
        _emit_dirty_refusal(results)

    any_failure = _render_remediation_results(results)
    raise typer.Exit(0 if rep.overall_success and not any_failure else 1)


def run_sparse_checkout(fix: bool) -> None:
    """Entry point for ``doctor sparse-checkout`` (0 clean / 1 state-or-CI-refusal)."""
    from specify_cli.git.sparse_checkout import scan_repo

    repo_root = _resolve_repo_root()
    report = scan_repo(repo_root)

    if not report.any_blocking:
        _emit_clean_state(fix)

    # Detection-only surface: print the finding and exit non-zero so CI scripts
    # that invoke `doctor sparse-checkout` can gate on the result.
    if not fix:
        _render_sparse_finding(report)
        raise typer.Exit(1)

    # --fix path: route by interactivity.
    if not _is_interactive_environment():
        # FR-023: CI/non-TTY surface is a single deterministic pointer line so
        # scripts can grep it reliably. No state mutation; non-zero exit.
        # Bypass Rich's auto-wrapping (which splits on terminal width and breaks
        # grep) by using the stdlib print.
        print(
            "sparse-checkout --fix requires an interactive terminal; "
            f"run '{_FIX_HINT}' from a local TTY to remediate."
        )
        raise typer.Exit(1)

    _apply_sparse_remediation(report)
