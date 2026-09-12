"""Canonical environment-variable truthy parsing — the single authority.

Every ``SPEC_KITTY_*`` on/off flag reader delegates here so the truthy grammar
is defined exactly once. Truthy tokens (case-insensitive, surrounding
whitespace stripped): ``1``, ``true``, ``yes``, ``y``, ``on``. Everything else
— including ``None`` and the empty string — is falsy.
"""
from __future__ import annotations

import os
import sys
import warnings
from collections.abc import Mapping

__all__ = [
    "MOMENT_HANDLER_DISABLE_ENV_VARS",
    "PRE_REVIEW_GATE_SKIP_ENV_VAR",
    "SYNC_KILL_SWITCH_ENV_VAR",
    "is_interactive",
    "is_truthy",
    "moment_handlers_disabled_reason",
    "pre_review_gate_skip_reason",
    "sync_kill_switch_active",
]

# Private: the canonical truthy grammar is an implementation detail of
# ``is_truthy`` — callers use the function, never the set (keeps a single public
# surface + satisfies the symbol-level dead-code gate).
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "y", "on"})

#: The one process-wide kill switch for sync-adjacent work (#3980 launch
#: table): ``SPEC_KITTY_SYNC_DISABLE`` disarms hosted sync
#: (:func:`specify_cli.core.saas_sync_config.sync_active`) and folds into the
#: moment-handler import gate. Nothing else reads it.
SYNC_KILL_SWITCH_ENV_VAR = "SPEC_KITTY_SYNC_DISABLE"

#: The moment-handler import gate (#3980): ``SPEC_KITTY_NO_MOMENT_HANDLERS``
#: is its own name, the kill switch folds in (a disarmed process registers no
#: transport), and ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` is the deprecated alias
#: of the gate — honored, with a once-per-process deprecation warning.
MOMENT_HANDLER_DISABLE_ENV_VARS: tuple[str, str, str] = (
    "SPEC_KITTY_NO_MOMENT_HANDLERS",
    SYNC_KILL_SWITCH_ENV_VAR,
    "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
)

#: The pre-review regression gate's own process-wide opt-out (#3980): the gate
#: no longer reads the sync-disable vocabulary — only this name (plus its
#: per-invocation ``--skip-pre-review-gate`` flag).
PRE_REVIEW_GATE_SKIP_ENV_VAR = "SPEC_KITTY_SKIP_PRE_REVIEW_GATE"

#: Deprecated-alias names already warned about this process — the notice
#: fires once per name, never once per read.
_deprecation_warned: set[str] = set()


def is_truthy(value: str | None) -> bool:
    """Return True iff ``value`` is a recognized truthy token (see module docstring)."""
    if value is None:
        return False
    return value.strip().casefold() in _TRUTHY_VALUES


def is_interactive() -> bool:
    """Return True iff the caller may block on a human at the terminal.

    The single authority for the non-interactive contract. Decision matrix,
    highest priority first:

      1. ``SPEC_KITTY_FORCE_INTERACTIVE`` truthy -> True (escape hatch).
      2. ``SPEC_KITTY_NON_INTERACTIVE`` truthy   -> False (how agents/CI drive us).
      3. Otherwise: ``sys.stdin.isatty()``.

    The single authority for **prompt-gating**: any surface about to block on a
    human — ``typer.prompt``, ``input()``, ``typer.confirm``, a keystroke read —
    must consult this first. Prompting when this returns False is the #2876 class
    of defect: in an agent harness with an open-but-silent stdin pipe, the prompt
    blocks forever. (`init`, `merge` preflight, `intake`, and `doctor` all route
    through this — #2912.)

    This is distinct from using ``stdin`` as a *data channel*: code that reads a
    piped payload (e.g. a harness hook JSON on stdin) legitimately checks
    ``sys.stdin.isatty()`` directly, because "is there piped input?" is a
    different question from "may I prompt?" and must not be swayed by
    ``SPEC_KITTY_FORCE_INTERACTIVE`` / ``NON_INTERACTIVE``.

    Tests monkeypatch ``sys.stdin`` or ``os.environ`` rather than relying on the
    real shell.
    """
    if is_truthy(os.environ.get("SPEC_KITTY_FORCE_INTERACTIVE")):
        return True
    if is_truthy(os.environ.get("SPEC_KITTY_NON_INTERACTIVE")):
        return False
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):  # pragma: no cover - defensive
        return False


def sync_kill_switch_active(environ: Mapping[str, str] | None = None) -> bool:
    """Return True iff the process-wide kill switch is truthy.

    Single source of truth for "is ``SPEC_KITTY_SYNC_DISABLE`` active" —
    :func:`specify_cli.core.saas_sync_config.sync_active` and the
    moment-handler import gate both build their answer from this, so the name
    and the ``is_truthy`` grammar are defined once. ``environ`` defaults to
    ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    return is_truthy(env.get(SYNC_KILL_SWITCH_ENV_VAR))


def pre_review_gate_skip_reason(environ: Mapping[str, str] | None = None) -> str | None:
    """Return why the pre-review regression gate should be skipped, or ``None`` to run it.

    #3980: the gate's process-wide opt-out is its own name,
    ``SPEC_KITTY_SKIP_PRE_REVIEW_GATE`` — it no longer reads the sync-disable
    vocabulary, so disarming sync no longer silently skips a review gate.
    ``environ`` defaults to ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    if is_truthy(env.get(PRE_REVIEW_GATE_SKIP_ENV_VAR)):
        return f"{PRE_REVIEW_GATE_SKIP_ENV_VAR} is set"
    return None


def moment_handlers_disabled_reason(environ: Mapping[str, str] | None = None) -> str | None:
    """Return why no moment handler should register at import, or ``None`` to register.

    Precedence: ``SPEC_KITTY_NO_MOMENT_HANDLERS``, then the kill switch
    (a disarmed process registers no transport), then the deprecated
    ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` alias — which warns once per process
    when honored. ``environ`` defaults to ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    for name in MOMENT_HANDLER_DISABLE_ENV_VARS:
        if is_truthy(env.get(name)):
            if name == "SPEC_KITTY_SYNC_MINIMAL_IMPORT":
                _warn_deprecated_minimal_import_once()
            return f"{name} is set"
    return None


def _warn_deprecated_minimal_import_once() -> None:
    """Warn once per process that ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` is deprecated."""
    if "SPEC_KITTY_SYNC_MINIMAL_IMPORT" in _deprecation_warned:
        return
    _deprecation_warned.add("SPEC_KITTY_SYNC_MINIMAL_IMPORT")
    warnings.warn(
        "SPEC_KITTY_SYNC_MINIMAL_IMPORT is deprecated as a moment-handler gate "
        "alias; set SPEC_KITTY_NO_MOMENT_HANDLERS instead (post-launch the "
        "deprecated name is removed).",
        DeprecationWarning,
        stacklevel=3,
    )
