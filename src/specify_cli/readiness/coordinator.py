"""Central CLI startup readiness coordinator implementation.

See spec: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md
See data model: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/data-model.md
See contracts: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md

The coordinator's first gate is ``is_saas_sync_enabled()``. When hosted mode is
disabled the coordinator returns a no-op result and emits no Teamspace-labeled
output. When hosted mode is enabled the coordinator composes (stubbed in this
mission) feature-gate state, output policy, auth readiness, and upgrade
readiness into a typed ``ReadinessResult`` cached on ``ctx.obj``.

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1093
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum

import typer

# WS2 (Workstream 2, issue #1094): auth probe wiring — imported as a typed
# stub seam, not exercised in this mission. The next mission will call this
# from inside ``_evaluate_uncached`` on the enabled path; this import keeps
# the symbol type-checked and grep-able as a hand-off marker.
from specify_cli.cli.commands._auth_recovery import (  # noqa: F401
    detect_logged_out_with_connected_teamspace,
)

_READINESS_CTX_KEY = "readiness"


class OutputPolicy(StrEnum):
    """Three-bucket suppression classification.

    See ``data-model.md`` for the precedence rules.
    """

    INTERACTIVE = "interactive"
    NON_INTERACTIVE = "non_interactive"
    MACHINE_OUTPUT = "machine_output"


class AuthStatus(StrEnum):
    """Coordinator's record of Teamspace-auth state.

    This mission ships only ``NOT_CHECKED`` and ``DISABLED``. WS2 (issue
    #1094) widens this enum with values like ``AUTHENTICATED`` and
    ``LOGGED_OUT_ON_CONNECTED_TEAMSPACE``.
    """

    NOT_CHECKED = "not_checked"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Cached readiness verdict for a single CLI invocation.

    Frozen and slotted: subcommands MUST NOT mutate fields. Field additions
    in future missions are allowed; removals require a mission-level
    deprecation per ``contracts/readiness-api.md``.
    """

    enabled: bool
    ran: bool
    output_policy: OutputPolicy
    auth_status: AuthStatus
    nag_invoked: bool


_NOOP_DISABLED: ReadinessResult = ReadinessResult(
    enabled=False,
    ran=False,
    output_policy=OutputPolicy.NON_INTERACTIVE,
    auth_status=AuthStatus.DISABLED,
    nag_invoked=False,
)


def _derive_output_policy(argv: list[str] | None = None) -> OutputPolicy:
    """Classify the active suppression conditions into the 3-bucket policy.

    Precedence (highest first):
      ``MACHINE_OUTPUT`` — ``--json`` or ``--quiet`` in argv.
      ``NON_INTERACTIVE`` — ``--help``/``-h``/``--version``/``-v`` in argv,
                            OR ``is_ci_env()`` true,
                            OR stdout is not a TTY.
      ``INTERACTIVE`` — otherwise.

    Mirrors the signal set consulted by
    ``specify_cli.cli.helpers._should_suppress_nag`` but produces a
    three-bucket value instead of a single boolean. The single source of
    truth for nag suppression remains ``_should_suppress_nag`` inside
    ``_render_nag_if_needed``; this function records the bucket for
    downstream consumers (WS2 auth, WS3 upgrade UX).
    """
    if argv is None:
        argv = sys.argv[1:]

    if "--json" in argv or "--quiet" in argv:
        return OutputPolicy.MACHINE_OUTPUT

    help_flags = {"--help", "-h", "--version", "-v"}
    if any(tok in help_flags for tok in argv):
        return OutputPolicy.NON_INTERACTIVE

    # Lazy import: keeps coordinator import-time cheap.
    from specify_cli.compat.planner import is_ci_env  # noqa: PLC0415

    if is_ci_env():
        return OutputPolicy.NON_INTERACTIVE

    try:
        if not sys.stdout.isatty():
            return OutputPolicy.NON_INTERACTIVE
    except Exception:  # noqa: BLE001 — isatty() can raise on exotic stream objects; treat as non-tty.
        return OutputPolicy.NON_INTERACTIVE

    return OutputPolicy.INTERACTIVE


def _read_cached(ctx: typer.Context) -> ReadinessResult | None:
    """Return the cached readiness result if reachable, else ``None``.

    Never raises. Returns ``None`` (not ``_NOOP_DISABLED``) so callers can
    distinguish "no cache" from "cached no-op".
    """
    obj = ctx.obj
    if not isinstance(obj, dict):
        return None
    cached = obj.get(_READINESS_CTX_KEY)
    if isinstance(cached, ReadinessResult):
        return cached
    return None


def _write_cached(ctx: typer.Context, result: ReadinessResult) -> None:
    """Store ``result`` on ``ctx.obj`` under ``_READINESS_CTX_KEY``.

    If ``ctx.obj`` is ``None``, initialize it to ``{}``. If ``ctx.obj`` is
    already a dict, set the key (other keys like ``compat_plan_result``
    remain untouched). If ``ctx.obj`` is a non-dict, non-None object
    (defensive), skip caching silently — ``get_readiness`` will return
    ``_NOOP_DISABLED`` for that ``ctx``.
    """
    obj = ctx.obj
    if obj is None:
        ctx.obj = {_READINESS_CTX_KEY: result}
        return
    if isinstance(obj, dict):
        obj[_READINESS_CTX_KEY] = result


def _invoke_nag(ctx: typer.Context) -> None:
    """Invoke the existing upgrade-nag renderer through the coordinator.

    Lazy import: ``helpers.callback`` imports ``evaluate_readiness`` from
    ``specify_cli.readiness`` at call time. Importing
    ``_render_nag_if_needed`` at module scope here would form an import
    cycle.

    ``_render_nag_if_needed`` already swallows its own exceptions and
    applies its own suppression checks; this wrapper adds no gating of its
    own. Preserves byte-for-byte behavior of the pre-mission inline call
    from ``callback()``.
    """
    from specify_cli.cli.helpers import _render_nag_if_needed  # noqa: PLC0415

    _render_nag_if_needed(ctx)


def _evaluate_uncached(ctx: typer.Context) -> ReadinessResult:
    """Compute a fresh ``ReadinessResult`` for the current invocation.

    Branches on ``is_saas_sync_enabled()``:

    - **Disabled path**: return a ``ReadinessResult`` with ``enabled=False``
      and ``ran=False``. The legacy upgrade-nag still fires (existing
      behavior is preserved exactly), so ``_invoke_nag`` is called before
      returning.

    - **Enabled path**: derive the output policy, stub ``auth_status`` as
      ``NOT_CHECKED`` (WS2 will wire the real probe here using the import
      already established in this module), invoke the nag, and return a
      ``ReadinessResult`` with ``enabled=True`` and ``ran=True``.

    No network I/O. No SaaS DB / queue / readiness counter mutation.
    """
    from specify_cli.saas.rollout import is_saas_sync_enabled  # noqa: PLC0415

    output_policy = _derive_output_policy()

    if not is_saas_sync_enabled():
        _invoke_nag(ctx)
        return ReadinessResult(
            enabled=False,
            ran=False,
            output_policy=output_policy,
            auth_status=AuthStatus.DISABLED,
            nag_invoked=True,
        )

    # WS2: auth probe wiring — the next mission will call
    # detect_logged_out_with_connected_teamspace() here and translate the
    # result into the appropriate AuthStatus value.
    _invoke_nag(ctx)
    return ReadinessResult(
        enabled=True,
        ran=True,
        output_policy=output_policy,
        auth_status=AuthStatus.NOT_CHECKED,
        nag_invoked=True,
    )


def evaluate_readiness(ctx: typer.Context) -> ReadinessResult:
    """Compute (or return the cached) readiness result for this CLI invocation.

    Idempotent: a second call on the same ``ctx`` returns the cached
    ``ReadinessResult`` without re-running any logic (FR-009).

    Never raises. Internal exceptions are swallowed and the caller receives
    ``_NOOP_DISABLED`` instead (FR-010). The CLI cannot crash because of
    readiness logic.

    Side effects:
      - On the first invocation, stores the result on
        ``ctx.obj['readiness']`` when ``ctx.obj`` is ``None`` or a dict.
      - Invokes ``_render_nag_if_needed(ctx)`` exactly once during the
        first invocation under both the disabled and enabled paths.
    """
    cached = _read_cached(ctx)
    if cached is not None:
        return cached

    try:
        result = _evaluate_uncached(ctx)
    except Exception:  # noqa: BLE001 — coordinator must never raise out of the CLI startup path.
        result = _NOOP_DISABLED

    _write_cached(ctx, result)
    return result


def get_readiness(ctx: typer.Context) -> ReadinessResult:
    """Return the cached readiness result, or ``_NOOP_DISABLED`` if none cached.

    Never re-runs ``evaluate_readiness``. Never raises. Safe to call from
    any subcommand handler regardless of ``ctx.obj`` state.
    """
    cached = _read_cached(ctx)
    return cached if cached is not None else _NOOP_DISABLED
