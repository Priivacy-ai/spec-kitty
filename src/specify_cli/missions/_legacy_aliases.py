"""Hidden CLI aliases for legacy mission selectors (FR-035, WP07/T042).

Spec Kitty's terminology canon is "mission" / ``--mission``. The legacy
``--feature`` flag is retained for back-compat but must never appear in
``--help`` output: the contract test
``tests/contract/test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands``
fails CI if any ``typer.Option("--feature", ...)`` block is declared
without ``hidden=True``.

This module exposes :func:`hidden_feature_option`, a tiny helper that
returns a ``typer.Option`` configured as a hidden deprecated alias for
``--mission``. Commands can call it to keep their option declarations
consistent and to make the intent obvious at the call site.

Resolution semantics (canonical wins, alias is fallback) live in
:mod:`specify_cli.cli.selector_resolution.resolve_selector` -- this
helper only owns the *declaration shape*, not the precedence logic.
"""

from __future__ import annotations

import typer

__all__ = ["LEGACY_FEATURE_HELP", "hidden_feature_option"]

LEGACY_FEATURE_HELP = "(deprecated) Use --mission"


def hidden_feature_option(
    *,
    help_text: str = LEGACY_FEATURE_HELP,
) -> typer.models.OptionInfo:
    """Return a hidden ``--feature`` Typer option that mirrors ``--mission``.

    Usage::

        feature: str | None = hidden_feature_option()

    The returned option is always ``hidden=True`` so it does not appear
    in ``--help`` output. Help text defaults to the canonical deprecation
    message; callers may override it for command-specific phrasing.
    """
    return typer.Option(
        None,
        "--feature",
        hidden=True,
        help=help_text,
    )
