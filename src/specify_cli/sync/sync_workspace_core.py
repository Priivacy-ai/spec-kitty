"""Pure decision core for ``spec-kitty sync workspace`` (WP11).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``)
restructures the third and last ``# noqa: C901`` monster — ``sync_workspace``
(measured complexity 18) — from a monolithic gather-and-render body into a thin
``gather-I/O -> pure core -> render`` shell (architect finding A-1). This module is
the **pure core**: given an already-computed :class:`SyncResult` it *decides* the
ordered sequence of render steps and the process exit code. It is **I/O-free** — no
``Console``, no ``print``, no ``git``, no filesystem, no network. The reviewer
co-gate greps this module for ``Console`` / ``print`` / ``git``; any hit is a reject.

The observable contract (identical glyphs / stats wording / exit codes pre and post
restructure) is guarded by the WP11 monkeypatch-golden
(``tests/characterization/test_sync_workspace_render.py``), which stubs the live
``git rebase`` seam so the SYNCED / CONFLICTS / FAILED arms are deterministic.

Render-step model
-----------------
The core cannot print — but the arms interleave literal lines with two Rich-table
helpers (``_display_conflicts`` / ``_display_changes_integrated``) that live on the
host and consume the ``SyncResult``. So the plan is an ordered tuple of *steps*:

* :class:`RenderLine` — a single ``console.print(text)`` (Rich markup passed
  through verbatim, exactly as the pre-restructure body emitted it).
* :class:`RenderConflicts` — the host renders ``_display_conflicts(result.conflicts)``.
* :class:`RenderChanges` — the host renders ``_display_changes_integrated(...)``.

``exit_code`` is the process exit (``None`` = fall through to the shell's trailing
blank line and return normally; an int = ``raise typer.Exit(exit_code)`` after the
steps are emitted, *without* the trailing blank — matching the pre-restructure
FAILED arm which raises before the outer ``console.print()``).
"""

from __future__ import annotations

from dataclasses import dataclass

from specify_cli.core.vcs import SyncResult, SyncStatus

# ---------------------------------------------------------------------------
# The "not in a recognized workspace" arm (mission_slug is None).
#
# These three lines + exit 1 relocate verbatim from the pre-restructure body.
# They are a fixed constant (no ``SyncResult`` is available yet at this point in
# the command), so the shell iterates them directly. The ``<feature>-lane-a``
# token is an existing frozen output string (a worktree-path placeholder, not a
# new ``--feature`` flag); zero-behaviour-change forbids editing it here.
# ---------------------------------------------------------------------------
NOT_IN_WORKSPACE_LINES: tuple[str, ...] = (
    "[yellow]⚠ Not in a recognized workspace[/yellow]",
    "Run this command from a worktree directory:",
    "  cd .worktrees/<feature>-lane-a/",
)
NOT_IN_WORKSPACE_EXIT: int = 1

#: Exit code the FAILED sync arm raises (``raise typer.Exit(1)`` in the shell).
_SYNC_FAILED_EXIT: int = 1


@dataclass(frozen=True)
class RenderLine:
    """A single ``console.print(text)`` step (Rich markup passed through)."""

    text: str


@dataclass(frozen=True)
class RenderConflicts:
    """Step marker: host renders ``_display_conflicts(result.conflicts)``."""


@dataclass(frozen=True)
class RenderChanges:
    """Step marker: host renders ``_display_changes_integrated(result.changes_integrated)``."""


RenderStep = RenderLine | RenderConflicts | RenderChanges


@dataclass(frozen=True)
class SyncRenderPlan:
    """The pure render decision for one ``SyncResult``.

    ``steps`` is emitted in order by the host shell; ``exit_code`` is ``None`` for
    the normal (fall-through) arms and an int for the FAILED arm that raises.
    """

    steps: tuple[RenderStep, ...]
    exit_code: int | None


def sync_stats_summary(result: SyncResult) -> str:
    """Format the SYNCED stats line, e.g. ``"3 updated, 1 added, 2 deleted"``.

    Mirrors the pre-restructure body exactly: only non-zero counts contribute, in
    updated/added/deleted order; an all-zero result yields ``"no file changes"``.
    """
    parts: list[str] = []
    if result.files_updated > 0:
        parts.append(f"{result.files_updated} updated")
    if result.files_added > 0:
        parts.append(f"{result.files_added} added")
    if result.files_deleted > 0:
        parts.append(f"{result.files_deleted} deleted")
    return ", ".join(parts) if parts else "no file changes"


def _up_to_date_steps(result: SyncResult) -> list[RenderStep]:
    steps: list[RenderStep] = [RenderLine("\n[green]✓ Already up to date[/green]")]
    if result.message:
        steps.append(RenderLine(f"[dim]{result.message}[/dim]"))
    return steps


def _synced_steps(result: SyncResult, *, verbose: bool) -> list[RenderStep]:
    steps: list[RenderStep] = [RenderLine(f"\n[green]✓ Synced[/green] - {sync_stats_summary(result)}")]
    if verbose:
        steps.append(RenderChanges())
    if result.message:
        steps.append(RenderLine(f"[dim]{result.message}[/dim]"))
    return steps


def _conflicts_steps(*, verbose: bool) -> list[RenderStep]:
    steps: list[RenderStep] = [
        RenderLine("\n[yellow]⚠ Synced with conflicts[/yellow]"),
        RenderLine("[dim]You must resolve conflicts before continuing.[/dim]"),
        RenderConflicts(),
    ]
    if verbose:
        steps.append(RenderChanges())
    return steps


def _failed_steps(result: SyncResult) -> list[RenderStep]:
    steps: list[RenderStep] = [RenderLine("\n[red]✗ Sync failed[/red]")]
    if result.message:
        steps.append(RenderLine(f"[dim]{result.message}[/dim]"))
    if result.conflicts:
        steps.append(RenderConflicts())
    steps.append(RenderLine(""))
    steps.append(RenderLine("[dim]Try:[/dim]"))
    steps.append(RenderLine("  spec-kitty sync workspace --repair"))
    return steps


def build_sync_render_plan(result: SyncResult, *, verbose: bool) -> SyncRenderPlan:
    """Decide the ordered render steps + exit code for a synced ``SyncResult``.

    The four ``SyncStatus`` arms reproduce the pre-restructure body line-for-line:

    * ``UP_TO_DATE`` / ``SYNCED`` / ``CONFLICTS`` — exit ``None`` (the shell then
      emits its trailing blank line and returns).
    * ``FAILED`` — the steps carry the arm's own trailing blank + ``Try:`` hint and
      ``exit_code`` is ``1`` (the shell raises ``typer.Exit(1)`` without the outer
      blank, matching the original early ``raise``).

    An unrecognised status yields an empty plan with ``exit_code=None`` — identical
    to the original ``if/elif`` chain falling through to only the trailing blank.
    """
    if result.status == SyncStatus.UP_TO_DATE:
        return SyncRenderPlan(tuple(_up_to_date_steps(result)), None)
    if result.status == SyncStatus.SYNCED:
        return SyncRenderPlan(tuple(_synced_steps(result, verbose=verbose)), None)
    if result.status == SyncStatus.CONFLICTS:
        return SyncRenderPlan(tuple(_conflicts_steps(verbose=verbose)), None)
    if result.status == SyncStatus.FAILED:
        return SyncRenderPlan(tuple(_failed_steps(result)), _SYNC_FAILED_EXIT)
    return SyncRenderPlan((), None)


__all__ = [
    "NOT_IN_WORKSPACE_EXIT",
    "NOT_IN_WORKSPACE_LINES",
    "RenderChanges",
    "RenderConflicts",
    "RenderLine",
    "SyncRenderPlan",
    "build_sync_render_plan",
]
