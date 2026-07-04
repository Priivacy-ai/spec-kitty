"""Canonical environment-variable truthy parsing — the single authority.

Every ``SPEC_KITTY_*`` on/off flag reader delegates here so the truthy grammar
is defined exactly once. Truthy tokens (case-insensitive, surrounding
whitespace stripped): ``1``, ``true``, ``yes``, ``y``, ``on``. Everything else
— including ``None`` and the empty string — is falsy.
"""
from __future__ import annotations

__all__ = ["is_truthy"]

# Private: the canonical truthy grammar is an implementation detail of
# ``is_truthy`` — callers use the function, never the set (keeps a single public
# surface + satisfies the symbol-level dead-code gate).
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "y", "on"})


def is_truthy(value: str | None) -> bool:
    """Return True iff ``value`` is a recognized truthy token (see module docstring)."""
    if value is None:
        return False
    return value.strip().casefold() in _TRUTHY_VALUES
