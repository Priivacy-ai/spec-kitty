"""Session-start hook helpers (T023 / T024 / FR-006 caller contract).

These helpers implement the rules in
``contracts/charter-preflight-json.md`` § "Hook caller contract":

| Consumer                | passed=True   | passed=False                                     |
|-------------------------|---------------|--------------------------------------------------|
| spec-kitty next         | log + cont    | print blocked_reason, exit 1, NO state mutation  |
| spec-kitty implement WP | log + cont    | abort BEFORE worktree alloc or .kittify writes   |
| dashboard serve / start | log + cont    | start server, inject blocked_reason as warning   |

The helpers are intentionally CLI-side (typer-aware): they are the shared
glue between the three consumer entry points and ``run_charter_preflight``.
The runner itself stays framework-free.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import typer

from specify_cli.charter_preflight.config import load_preflight_config
from specify_cli.charter_preflight.result import CharterPreflightResult
from specify_cli.charter_preflight.runner import run_charter_preflight

__all__ = [
    "run_preflight_or_abort",
    "run_preflight_for_dashboard",
]


_logger = logging.getLogger(__name__)


def run_preflight_or_abort(
    repo_root: Path,
    *,
    consumer: str,
    stderr=None,
) -> CharterPreflightResult:
    """Run charter preflight; abort the process if it fails.

    Shared implementation for ``spec-kitty next`` (T023) and
    ``spec-kitty implement`` (T024). Both consumers behave identically on
    failure: print ``blocked_reason`` and exit with code 1, with **no
    state mutation** (no worktree allocation, no ``.kittify/`` writes,
    no event-log appends).

    Args:
        repo_root: Repository root used to load the config flag and to
            resolve ``.kittify/charter/`` / ``.kittify/doctrine/`` paths.
        consumer: Human-readable consumer name for log lines, e.g.
            ``"next"`` or ``"implement"``. Used only for observability.
        stderr: Optional stream override (mostly for tests). Defaults to
            ``sys.stderr``.

    Returns:
        The :class:`CharterPreflightResult` when ``passed`` is ``True``.

    Raises:
        typer.Exit: Exit code 1 when ``passed`` is ``False``.
    """
    # Honour SPEC_KITTY_TEST_MODE=1 (test fixtures) and a dedicated opt-out
    # SPEC_KITTY_SKIP_PREFLIGHT=1 (solo operators who own the charter freshness
    # state externally). Either bypass returns a synthetic "passed" result so
    # callers see uniform shape but skip the freshness-state check. Matches the
    # protected-branch guard's bypass convention.
    _truthy = ("1", "true", "yes")
    if (
        os.environ.get("SPEC_KITTY_TEST_MODE", "").lower() in _truthy
        or os.environ.get("SPEC_KITTY_SKIP_PREFLIGHT", "").lower() in _truthy
    ):
        _logger.info(
            "charter preflight bypassed via env (consumer=%s)", consumer
        )
        return CharterPreflightResult(passed=True, checks=[])

    cfg = load_preflight_config(repo_root)
    result = run_charter_preflight(
        repo_root=repo_root,
        auto_refresh=cfg.auto_refresh,
        strict=False,
    )

    if result.passed:
        _logger.info("charter preflight passed (consumer=%s)", consumer)
        return result

    err = stderr if stderr is not None else sys.stderr
    reason = result.blocked_reason or "charter preflight failed"
    print(f"Error: {reason}", file=err)
    raise typer.Exit(1)


def run_preflight_for_dashboard(repo_root: Path) -> CharterPreflightResult:
    """Run charter preflight without aborting; dashboard always starts.

    Implements the dashboard side of the caller contract (T025): the
    server is allowed to come up even when preflight fails, but the
    ``blocked_reason`` MUST be surfaced to the SPA so the operator sees a
    critical banner instead of silently consuming stale doctrine.

    Args:
        repo_root: Repository root used to load the config flag.

    Returns:
        The :class:`CharterPreflightResult`. Callers inspect
        ``result.passed`` / ``result.blocked_reason`` directly.
    """
    cfg = load_preflight_config(repo_root)
    result = run_charter_preflight(
        repo_root=repo_root,
        auto_refresh=cfg.auto_refresh,
        strict=False,
    )
    if result.passed:
        _logger.info("charter preflight passed (consumer=dashboard)")
    else:
        _logger.warning(
            "charter preflight failed (consumer=dashboard): %s",
            result.blocked_reason,
        )
    return result
