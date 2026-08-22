"""``spec-kitty zeitgeist`` (Z7-C, program-graph handle Z7-C: "Spec Kitty
subscription CLI/MCP adapters").

A thin Typer shell over ``zeitgeist_client.subscription``'s shared
status()/watch() surface — the same functions ``mcp_stdio.py``'s stdio
MCP adapter calls, so a terminal user and an MCP client observe identical
bounded-read/bounded-watch behavior over one team's live presence/focus
stream (Z7-C's own "share Z1 service" criterion). This module owns no
network logic, no credential storage, and no snapshot/frame serialization
of its own — it only formats what ``subscription.py`` returns.

``repo`` is the one explicit, required, positional argument on both
commands; neither takes a relay URL or a bearer/capability value — the
credential is resolved solely from ``credentials.py``'s existing store
(``subscription.resolve_stream``). A caller with no stored checkout for
``repo`` gets :class:`subscription.NotCheckedOut`, reported here as a clean
exit-1 message, never an auto-provisioned one — this module never calls
``credentials.store``/``credentials.revoke`` (no administration).

``mcp-serve`` is registered ``hidden=True`` (not a public CLI surface a
human is meant to invoke directly) — it is the process entry point an MCP
client's own launcher runs, matching
``docs/plans/zeitgeist-client-wp01-remaining.md`` item 4's "a status/watch
sub-group plus a hidden mcp-serve command".

Item 4's ``checkout``/``focus`` subcommands are NOT part of this pass — see
this module's own scope note in
``docs/plans/zeitgeist-client-wp01-remaining.md``: ``checkout`` writes a
credential (administration, Z7-C's own node criterion forbids it here) and
``focus`` belongs to ``transport.ZeitgeistClient``'s control-envelope surface,
not the ``FilteredStream`` subscription surface this node scopes
("watch/status/subscribe").

Z8-C adds the ``outbox`` sub-group: ``list``/``show``/``approve``/``reject``/
``revoke`` over ``outbox_approval.py``'s bundled, human-gesture-gated
approval surface for locally queued Zeitgeist prose (program-graph handle
Z8-C, "Bundled outside-model approval surface"). Unlike ``status``/``watch``,
this is deliberately NOT wired into ``mcp_stdio.py`` — see that module's own
docstring and ``outbox_approval.py``'s "hard trust requirement" section for
why a model talking over MCP must have no tool that reaches it.
``approve``/``reject``/``revoke`` below take no ``--yes``/``--force``/
``--non-interactive`` option; each is a thin pass-through to
``outbox_approval.approve``/``.reject``/``.revoke``, which raise
``HumanGestureRequired`` whenever no controlling terminal is available to
capture a real human gesture — that fault, not a CLI flag, is what a
non-interactive caller here hits.
"""

from __future__ import annotations

import asyncio
import dataclasses
import getpass
import urllib.error
from typing import Any

import typer

from specify_cli.cli.console import console
from specify_cli.zeitgeist_client import outbox_approval, subscription

app = typer.Typer(
    name="zeitgeist",
    help="Read-only access to one team's live Zeitgeist presence/focus stream, plus a local human-gated prose approval surface.",
)

_REPO_ARGUMENT = typer.Argument(
    ...,
    help="Canonical repo key this checkout's credential is stored under (the one explicit team context).",
)
_JSON_OPTION = typer.Option(False, "--json", help="Emit plain JSON instead of a human-readable summary.")


def _report_not_checked_out(exc: subscription.NotCheckedOut) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    console.print(
        "[yellow]Hint:[/yellow] no Zeitgeist checkout is stored for this repo yet. "
        "Run the checkout flow first, then retry."
    )
    raise typer.Exit(1)


def _report_connection_fault(exc: urllib.error.URLError) -> None:
    console.print(f"[red]Error:[/red] could not reach the relay: {exc}")
    raise typer.Exit(1)


def _print_snapshot_summary(result: dict[str, Any]) -> None:
    presence: list[dict[str, Any]] = result.get("presence") or []
    focus: list[dict[str, Any]] = result.get("focus") or []
    console.print(f"[bold]{result.get('repo')}[/bold]  epoch={result.get('epoch')}")
    if not presence and not focus:
        console.print("  (nothing observed within the bounded window)")
        return
    for p in presence:
        console.print(f"  presence  {p.get('session_ref')}  user={p.get('user')}  path={p.get('path')}")
    for f in focus:
        console.print(f"  focus     {f.get('session_ref')}  {f.get('focus_ref')}  state={f.get('state')}")


@app.command()
def status(
    repo: str = _REPO_ARGUMENT,
    timeout: float = typer.Option(
        subscription.DEFAULT_STATUS_TIMEOUT_S,
        "--timeout",
        min=0.001,
        help=f"Seconds to listen before reporting (clamped to <= {subscription.MAX_TIMEOUT_S}s, the honest reported-live ceiling).",
    ),
    as_json: bool = _JSON_OPTION,
) -> None:
    """One bounded snapshot of ``repo``'s live presence/focus state."""
    try:
        result = subscription.status(repo, timeout_s=timeout)
    except subscription.NotCheckedOut as exc:
        _report_not_checked_out(exc)
        return
    except urllib.error.URLError as exc:
        _report_connection_fault(exc)
        return

    if as_json:
        console.emit_json(result)
    else:
        _print_snapshot_summary(result)


@app.command()
def watch(
    repo: str = _REPO_ARGUMENT,
    timeout: float = typer.Option(
        subscription.DEFAULT_WATCH_TIMEOUT_S,
        "--timeout",
        min=0.001,
        help=f"Idle seconds before the watch ends (clamped to <= {subscription.MAX_TIMEOUT_S}s, the honest reported-live ceiling).",
    ),
    max_frames: int = typer.Option(
        subscription.MAX_WATCH_FRAMES,
        "--max-frames",
        min=1,
        help="Stop after this many frames even if the window has not elapsed.",
    ),
    as_json: bool = _JSON_OPTION,
) -> None:
    """Print each live presence/focus frame for ``repo`` as it arrives,
    bounded by ``--timeout`` idleness and ``--max-frames`` count."""
    try:
        frame_iter = subscription.watch(repo, timeout_s=timeout, max_frames=max_frames)
        for frame in frame_iter:
            if as_json:
                # One compact JSON object per line (JSON Lines), never the
                # multi-line pretty form status() uses — a stream of frames
                # must stay line-delimited for a caller piping this output.
                console.emit_json(frame, indent=None)
            else:
                console.print(f"[bold]{frame['frame_type']}[/bold]  seq={frame['seq']}  {frame['payload']}")
    except subscription.NotCheckedOut as exc:
        _report_not_checked_out(exc)
    except urllib.error.URLError as exc:
        _report_connection_fault(exc)
    except KeyboardInterrupt:
        raise typer.Exit(130) from None


@app.command(name="mcp-serve", hidden=True)
def mcp_serve() -> None:
    """Serve the Z7-C stdio MCP adapter (``mcp_stdio.run_stdio``) until the
    client disconnects. Process entry point for an MCP client's launcher —
    not meant for direct interactive use, hence hidden."""
    from specify_cli.zeitgeist_client import mcp_stdio

    asyncio.run(mcp_stdio.run_stdio())


# --- Z8-C: outbox (bundled outside-model approval surface) -----------------

outbox_app = typer.Typer(
    name="outbox",
    help="Inspect/approve/reject/revoke locally queued Zeitgeist prose. Every "
    "decision requires a real human at a real terminal — there is no --yes/"
    "--force option and no reachability from MCP or a script.",
)
app.add_typer(outbox_app, name="outbox")

_ITEM_ID_ARGUMENT = typer.Argument(..., help="The content-addressed id of the pending/decided item.")
_ACTOR_OPTION = typer.Option(None, "--actor", help="Attribution recorded on the receipt. Defaults to the local OS user.")


def _resolve_actor(actor: str | None) -> str:
    return actor if actor else getpass.getuser()


@outbox_app.command("list")
def outbox_list(
    repo: str | None = typer.Option(None, "--repo", help="Only items queued for this repo."),
    as_json: bool = _JSON_OPTION,
) -> None:
    """Every item still awaiting a human disposition. Content is shown only
    as a bounded, redacted preview — never the exact prose (use ``show`` for
    that, by exact id)."""
    items = outbox_approval.list_pending(repo=repo)
    if as_json:
        console.emit_json(
            [
                {
                    "item_id": item.item_id,
                    "repo": item.repo,
                    "audience": item.audience,
                    "content_preview": outbox_approval.redacted_preview(item.content),
                    "created_at": item.created_at,
                    "expires_at": item.expires_at,
                }
                for item in items
            ]
        )
        return
    if not items:
        console.print("(no pending items)")
        return
    for item in items:
        preview = outbox_approval.redacted_preview(item.content)
        console.print(f"[bold]{item.item_id[:12]}[/bold]  repo={item.repo}  audience={item.audience}  expires={item.expires_at}  {preview!r}")


@outbox_app.command("show")
def outbox_show(item_id: str = _ITEM_ID_ARGUMENT, as_json: bool = _JSON_OPTION) -> None:
    """The exact full record for ``item_id`` — the one explicit, per-id
    disclosure action (see ``outbox_approval.py``'s module docstring)."""
    try:
        item = outbox_approval.show(item_id)
    except outbox_approval.NotFound as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    if as_json:
        console.emit_json(dataclasses.asdict(item))
        return
    console.print(f"[bold]{item.item_id}[/bold]  status={item.status}")
    console.print(f"  repo={item.repo}  audience={item.audience}")
    console.print(f"  context={item.context}")
    console.print(f"  created_at={item.created_at}  expires_at={item.expires_at}")
    console.print("  content (exact, verbatim):")
    console.print(f"    {item.content}")


def _run_decision(item_id: str, actor: str | None, decide: Any, verb: str) -> None:
    resolved_actor = _resolve_actor(actor)
    try:
        receipt = decide(item_id, actor=resolved_actor)
    except outbox_approval.HumanGestureRequired as exc:
        console.print(f"[red]Refused:[/red] {exc}")
        raise typer.Exit(1) from None
    except outbox_approval.OutboxError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"[green]{verb}[/green]  item={receipt.item_id[:12]}  receipt={receipt.receipt_id[:12]}  actor={receipt.actor}")


@outbox_app.command("approve")
def outbox_approve(item_id: str = _ITEM_ID_ARGUMENT, actor: str | None = _ACTOR_OPTION) -> None:
    """Approve ``item_id``. Requires typing back the item's own challenge at
    the controlling terminal when prompted — there is no flag to skip this."""
    _run_decision(item_id, actor, outbox_approval.approve, "approved")


@outbox_app.command("reject")
def outbox_reject(item_id: str = _ITEM_ID_ARGUMENT, actor: str | None = _ACTOR_OPTION) -> None:
    """Reject ``item_id``. Same human-gesture requirement as ``approve``."""
    _run_decision(item_id, actor, outbox_approval.reject, "rejected")


@outbox_app.command("revoke")
def outbox_revoke(item_id: str = _ITEM_ID_ARGUMENT, actor: str | None = _ACTOR_OPTION) -> None:
    """Pull back an already-approved ``item_id``. Same human-gesture
    requirement as ``approve``; only valid from ``approved``."""
    _run_decision(item_id, actor, outbox_approval.revoke, "revoked")
