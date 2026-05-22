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

# WS2 (Workstream 2, issue #1094): auth probe wiring landed. The probe in
# ``specify_cli.readiness.auth.probe_auth_status`` wraps
# ``detect_logged_out_with_connected_teamspace`` and the renderer in
# ``specify_cli.readiness.render.render_auth_guidance`` produces the
# per-output-policy guidance. The import below is retained as the Wave 1
# hand-off marker; it remains a grep target for the symbol and ensures any
# future refactor of ``_auth_recovery`` cannot silently delete the helper.
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

    Wave 1 (issue #1093) shipped ``NOT_CHECKED`` and ``DISABLED``. WS2
    (issue #1094) extends this enum with the authoritative values produced
    by the readiness auth probe
    (``specify_cli.readiness.auth.probe_auth_status``):
    ``AUTHENTICATED``, ``LOGGED_OUT_IN_TEAMSPACE``, ``NOT_IN_TEAMSPACE``,
    ``UNKNOWN``.

    ``NOT_CHECKED`` is preserved for backward compatibility with the Wave 1
    public contract but is no longer produced by the coordinator: on the
    hosted-enabled path the probe always sets one of the four authoritative
    values (or ``UNKNOWN`` on internal error). On the hosted-disabled path
    the coordinator continues to set ``DISABLED``.
    """

    NOT_CHECKED = "not_checked"
    DISABLED = "disabled"
    AUTHENTICATED = "authenticated"
    LOGGED_OUT_IN_TEAMSPACE = "logged_out_in_teamspace"
    NOT_IN_TEAMSPACE = "not_in_teamspace"
    UNKNOWN = "unknown"


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


def _invoke_upgrade_ux(ctx: typer.Context) -> None:
    """Run the hosted-mode upgrade-readiness UX (WS3, issue #1092).

    Suppression is delegated to the canonical
    ``cli.helpers._should_suppress_nag`` predicate; when that predicate
    returns True this function passes ``suppressed=True`` into the UX
    layer so the UX MUST NOT prompt, MUST NOT invoke a subprocess, and
    MUST NOT mutate the cache.

    Exceptions are swallowed — the coordinator must never raise out of
    the CLI startup path.
    """
    try:
        from specify_cli.cli.helpers import _should_suppress_nag  # noqa: PLC0415
        from specify_cli.readiness.upgrade_ux import run_upgrade_ux  # noqa: PLC0415

        run_upgrade_ux(ctx, suppressed=_should_suppress_nag())
    except Exception:  # noqa: BLE001 — UX must never crash the CLI
        pass


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

    # WS2 (issue #1094): auth probe + renderer. Each step is independently
    # exception-wrapped: a probe failure degrades to ``UNKNOWN`` rather than
    # collapsing the whole ReadinessResult to ``_NOOP_DISABLED`` (which is
    # what ``evaluate_readiness``'s outer ``except`` would do). The renderer
    # is then gated on the verdict + output policy.
    try:
        from specify_cli.readiness.auth import probe_auth_status  # noqa: PLC0415 — lazy
        auth_status, teamspace_handle = probe_auth_status()
    except Exception:  # noqa: BLE001 — coordinator must never raise; degrade to UNKNOWN.
        auth_status = AuthStatus.UNKNOWN
        teamspace_handle = None

    # Gate the renderer per the suppression contract:
    # - LOGGED_OUT_IN_TEAMSPACE is the only verdict that produces visible
    #   guidance.
    # - MACHINE_OUTPUT (``--json``/``--quiet``) is always silent.
    # - ``--help``/``--version`` is always silent: users asking for help
    #   text or a version number are not asking to be told about auth.
    help_or_version = any(
        tok in {"--help", "-h", "--version", "-v"} for tok in sys.argv[1:]
    )
    if (
        auth_status == AuthStatus.LOGGED_OUT_IN_TEAMSPACE
        and output_policy != OutputPolicy.MACHINE_OUTPUT
        and not help_or_version
    ):
        try:
            from specify_cli.readiness.render import render_auth_guidance  # noqa: PLC0415 — lazy
            command_name = ctx.invoked_subcommand or "spec-kitty"
            render_auth_guidance(
                status=auth_status,
                teamspace=teamspace_handle,
                command_name=command_name,
                output_policy=output_policy,
            )
        except Exception:  # noqa: BLE001 — render must never raise out of the coordinator
            pass

    # WS3 (issue #1092): on the hosted-enabled path the upgrade UX
    # subsumes the legacy nag. It owns prompt cadence, choice
    # persistence, and auto-upgrade gating, and applies its own
    # suppression checks via ``_should_suppress_nag``.
    _invoke_upgrade_ux(ctx)
    return ReadinessResult(
        enabled=True,
        ran=True,
        output_policy=output_policy,
        auth_status=auth_status,
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
