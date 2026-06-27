"""Scope-aware wrapper around :func:`charter.context.build_charter_context`.

Combines :meth:`charter.scope.CharterScope.resolve` with the existing
``build_charter_context`` call so callers in the prompt-rendering pipeline
get monorepo-aware charter resolution without changing
``build_charter_context``'s signature (which is owned by WP07).

For single-project repos (no ``charter_scopes:`` configured),
``CharterScope.resolve`` returns the default scope with
``scope.root == repo_root`` and the wrapper is a pass-through. The 23
``test_wp_prompt_governance_contract.py`` fixtures pass unchanged
(NFR-001 binding).

See ADR-8 (``docs/adr/3.x/2026-05-18-1-monorepo-charter-scope.md``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from charter.context import CharterContextResult, build_charter_context
from charter.scope import CharterScope

__all__ = ["build_with_scope"]


def build_with_scope(
    repo_root: Path,
    feature_dir: Path,
    **kwargs: Any,
) -> CharterContextResult:
    """Resolve the charter scope for *feature_dir* then build context.

    Parameters
    ----------
    repo_root:
        Repository root (the ``.kittify/`` directory containing
        ``config.yaml`` lives here).
    feature_dir:
        Filesystem directory whose enclosing charter should govern the
        rendered context. For single-project repos this argument is
        ignored after scope resolution (the default scope has
        ``root == repo_root``).
    **kwargs:
        Forwarded verbatim to :func:`charter.context.build_charter_context`.

    Returns
    -------
    :class:`charter.context.CharterContextResult`
        The rendered charter context payload from the resolved scope.

    Raises
    ------
    charter.scope.CharterScopeConflict
        When two configured scopes have incompatible nesting that renders
        *feature_dir* ambiguous.
    charter.scope.CharterScopeNotFound
        When ``charter_scopes:`` is configured but no scope encloses
        *feature_dir*.
    """
    scope = CharterScope.resolve(repo_root, feature_dir)
    # For the single-project default, scope.root == repo_root and this call
    # is byte-identical to today. For monorepos, scope.root is the
    # per-package charter root.
    return build_charter_context(scope.root, **kwargs)
