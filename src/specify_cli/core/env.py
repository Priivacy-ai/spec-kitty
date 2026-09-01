"""Canonical environment-variable truthy parsing — the single authority.

Every ``SPEC_KITTY_*`` on/off flag reader delegates here so the truthy grammar
is defined exactly once. Truthy tokens (case-insensitive, surrounding
whitespace stripped): ``1``, ``true``, ``yes``, ``y``, ``on``. Everything else
— including ``None`` and the empty string — is falsy.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping

__all__ = ["first_set_sync_disable_env", "is_interactive", "is_truthy"]

# Private: the canonical truthy grammar is an implementation detail of
# ``is_truthy`` — callers use the function, never the set (keeps a single public
# surface + satisfies the symbol-level dead-code gate).
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "y", "on"})

#: The canonical set of env vars that disable sync-adjacent work — the single
#: source of truth consumed by the pre-review gate and the per-test isolation
#: fixtures. Do NOT re-scatter this tuple; import it.
SYNC_DISABLE_ENV_VARS: tuple[str, str] = (
    "SPEC_KITTY_SYNC_DISABLE",
    "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
)


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


def first_set_sync_disable_env(environ: Mapping[str, str] | None = None) -> str | None:
    """Return the first :data:`SYNC_DISABLE_ENV_VARS` name whose value is truthy, else None.

    Single source of truth for "is a sync-disable env active, and which one".
    The pre-review gate builds its skip reason from this helper, while the
    per-test isolation fixtures consume :data:`SYNC_DISABLE_ENV_VARS`, so the
    vocabulary and the ``is_truthy`` grammar are defined once. ``environ``
    defaults to ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    for name in SYNC_DISABLE_ENV_VARS:
        if is_truthy(env.get(name)):
            return name
    return None
