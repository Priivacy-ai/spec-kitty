"""Canonical environment-variable truthy parsing — the single authority.

Every ``SPEC_KITTY_*`` on/off flag reader delegates here so the truthy grammar
is defined exactly once. Truthy tokens (case-insensitive, surrounding
whitespace stripped): ``1``, ``true``, ``yes``, ``y``, ``on``. Everything else
— including ``None`` and the empty string — is falsy.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

__all__ = ["first_set_sync_disable_env", "is_truthy"]

# Private: the canonical truthy grammar is an implementation detail of
# ``is_truthy`` — callers use the function, never the set (keeps a single public
# surface + satisfies the symbol-level dead-code gate).
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "y", "on"})

#: The canonical set of env vars that disable sync-adjacent work — the single
#: source of truth consumed by the sync daemon, the pre-review gate, and the
#: per-test isolation fixtures. Do NOT re-scatter this tuple; import it.
SYNC_DISABLE_ENV_VARS: tuple[str, str] = (
    "SPEC_KITTY_SYNC_DISABLE",
    "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
)


def is_truthy(value: str | None) -> bool:
    """Return True iff ``value`` is a recognized truthy token (see module docstring)."""
    if value is None:
        return False
    return value.strip().casefold() in _TRUTHY_VALUES


def first_set_sync_disable_env(environ: Mapping[str, str] | None = None) -> str | None:
    """Return the first :data:`SYNC_DISABLE_ENV_VARS` name whose value is truthy, else None.

    Single source of truth for "is a sync-disable env active, and which one".
    Both the sync daemon and the pre-review gate build their skip reason from
    this, so the vocabulary and the ``is_truthy`` grammar are defined once.
    ``environ`` defaults to ``os.environ``.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    for name in SYNC_DISABLE_ENV_VARS:
        if is_truthy(env.get(name)):
            return name
    return None
