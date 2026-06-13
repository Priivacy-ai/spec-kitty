"""CLI command: spec-kitty do <request> [--profile <id>] [--json]

Anonymous profile dispatch — routes through ActionRouter by default.
An optional --profile bypasses the router when the caller already knows
which profile to target (avoids ROUTER_AMBIGUOUS on generic verbs like "fix").

`do` is a first-class alias of the canonical `spec-kitty dispatch` mechanism
(WP03). It shares the single `_dispatch_impl` body in `dispatch.py` so the Op
record, JSON envelope, and exit codes stay byte/contract-identical (NFR-001).

`find_repo_root` and `ProfileRegistry` are imported here (not only used inside
`dispatch.py`) so existing tests that patch
`specify_cli.cli.commands.do_cmd.find_repo_root` /
`specify_cli.cli.commands.do_cmd.ProfileRegistry` keep working: the executor
this module builds is the one passed into `_dispatch_impl`.

Registration: do is a plain function registered via @app.command() in __init__.py.
"""

from __future__ import annotations

from pathlib import Path

import typer

from specify_cli.cli.commands.dispatch import (
    _dispatch_impl,
    profile_not_found_routing,
    render_open_hint_task_execution,
)
from specify_cli.invocation.executor import ProfileInvocationExecutor
from specify_cli.invocation.modes import derive_mode
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter
from specify_cli.task_utils import find_repo_root


def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
    """Construct the executor using this module's patchable seams.

    Resolving `ProfileRegistry` (and `find_repo_root` upstream) here — rather
    than inside `dispatch.py` — preserves the patch targets the existing `do`
    integration tests rely on.
    """
    registry = ProfileRegistry(repo_root)
    router = ActionRouter(registry)
    propagator = InvocationSaaSPropagator(repo_root)
    return ProfileInvocationExecutor(repo_root, router=router, propagator=propagator)


def do(
    request: str = typer.Argument(..., help="Natural language request. The router picks the best profile."),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Optional profile ID. Bypasses the router — use when the request is ambiguous.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Route a request to the best-matching profile (anonymous dispatch).

    Uses ActionRouter by default. Pass --profile to bypass routing when the
    request verb is ambiguous (e.g. 'fix' matches multiple implementer profiles).
    On ambiguity or no-match without --profile, exits 1 with a structured error.
    """
    repo_root = find_repo_root()
    executor = _build_executor(repo_root)
    _dispatch_impl(
        request,
        profile,
        derive_mode("do"),
        json_output,
        repo_root=repo_root,
        executor=executor,
        render_open_hint=render_open_hint_task_execution,
        on_profile_not_found=profile_not_found_routing,
    )
