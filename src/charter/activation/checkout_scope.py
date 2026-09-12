"""Invocation-local charter reads for an explicitly owned Git checkout.

The CLI validates ownership before opening this scope. Repository identity and
default charter resolution retain their canonical common-directory semantics.
Only charter bundle readers consult this scope; no environment override exists.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from kernel.git_topology import git_common_dir, git_toplevel

__all__ = ["charter_checkout_scope", "selected_charter_checkout"]

_SELECTED_CHECKOUT: ContextVar[Path | None] = ContextVar("charter_selected_checkout", default=None)


@contextmanager
def charter_checkout_scope(checkout: Path) -> Iterator[None]:
    """Bind a validated checkout for one invocation, restoring it even on error."""
    root = checkout.resolve()
    if git_toplevel(root) != root:
        raise ValueError("Charter checkout scope requires a Git checkout root.")
    previous = _SELECTED_CHECKOUT.get()
    if previous is not None and git_common_dir(previous) != git_common_dir(root):
        raise ValueError("Nested charter checkout belongs to another repository.")
    token = _SELECTED_CHECKOUT.set(root)
    try:
        yield
    finally:
        _SELECTED_CHECKOUT.reset(token)


def selected_charter_checkout(path: Path) -> Path | None:
    """Return the scoped checkout; refuse an attempt to read a different one."""
    root = _SELECTED_CHECKOUT.get()
    if root is not None and git_toplevel(path) != root:
        raise ValueError("Charter read escapes the explicitly owned checkout.")
    return root
