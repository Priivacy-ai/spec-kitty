"""Deprecation helpers for legacy retrospective environment variables.

This module provides one-warn-per-process deprecation notices for
``SPEC_KITTY_RETROSPECTIVE`` and ``SPEC_KITTY_MODE``.

Background
----------
Both env vars are retained as **test/dev overrides only** (FR-015).  They were
promoted to first-class configuration signals before the durable policy resolver
(WP01) was in place.  As of spec-kitty 3.2, the canonical way to set retrospective
policy is via ``.kittify/config.yaml`` or charter frontmatter.

Suppression flag
----------------
Set ``SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`` to suppress the Rich stderr notice.
This is useful for CI environments that already capture ``warnings.warn`` output
and don't want duplicate console noise.

**Important distinction**: ``SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`` suppresses
ONLY the Rich stderr notice.  The Python ``DeprecationWarning`` issued via
``warnings.warn`` is **not** suppressed by this flag.  Test runners (pytest,
unittest) capture ``DeprecationWarning`` through the Python warnings machinery;
suppressing it there would hide real signal.

Process-global state
--------------------
``_EMITTED`` is a module-level set that tracks which variable names have already
triggered a warning in the current process.  This enforces the NFR-006 requirement
of one warning per process, not per command invocation.

Tests that exercise the deprecation pathway MUST reset ``_EMITTED`` between test
cases.  Use the provided ``reset_emitted_for_testing()`` helper in a pytest fixture
(see ``tests/retrospective/test_env_deprecation.py`` for the canonical pattern).

Replacement-key mapping
-----------------------
- ``SPEC_KITTY_RETROSPECTIVE``  →  ``retrospective.enabled``
- ``SPEC_KITTY_MODE``           →  ``retrospective.timing + retrospective.failure_policy``

Docs URL
--------
User-facing migration guidance lives at:
    ``docs/guides/use-retrospective-learning.md``
(written by WP07; referenced here as a relative path).
"""

from __future__ import annotations

import os
import warnings

# ---------------------------------------------------------------------------
# Process-global deprecation budget (NFR-006: one warning per process)
# ---------------------------------------------------------------------------

_EMITTED: set[str] = set()

# ---------------------------------------------------------------------------
# Public replacement-key mapping
# ---------------------------------------------------------------------------

#: Maps each deprecated env-var name to the canonical config key it replaces.
REPLACEMENT_KEYS: dict[str, str] = {
    "SPEC_KITTY_RETROSPECTIVE": "retrospective.enabled",
    "SPEC_KITTY_MODE": "retrospective.timing + retrospective.failure_policy",
}

#: User-facing docs URL (relative path; WP07 ensures this doc exists).
_DOCS_URL: str = "docs/guides/use-retrospective-learning.md"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def warn_env_var_deprecated(
    var_name: str,
    replacement_key: str,
    docs_url: str,
) -> None:
    """Emit a one-per-process deprecation warning for a legacy env var.

    Idempotent: the warning is emitted at most once per ``var_name`` per
    process, regardless of how many times the policy resolver runs.

    Two complementary channels are used:

    1. ``warnings.warn(..., DeprecationWarning, stacklevel=2)`` — captured by
       pytest, CI warning filters, and ``-W error::DeprecationWarning``.
    2. A Rich stderr notice (yellow ``DEPRECATED:`` prefix) — visible to
       operators running the CLI interactively.  Can be suppressed by setting
       ``SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`` without silencing the Python
       warning.

    Args:
        var_name: The environment variable name being deprecated
            (e.g. ``"SPEC_KITTY_RETROSPECTIVE"``).
        replacement_key: The canonical config key that replaces it
            (e.g. ``"retrospective.enabled"``).
        docs_url: Relative path or URL for user-facing migration docs.
    """
    if var_name in _EMITTED:
        return
    _EMITTED.add(var_name)

    msg = (
        f"{var_name} is a test/dev override only and will be removed. "
        f"Set durable policy via {replacement_key} in .kittify/config.yaml "
        f"or charter frontmatter. Docs: {docs_url}"
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    _emit_rich_stderr_notice(var_name, replacement_key, docs_url)


def _emit_rich_stderr_notice(
    var_name: str,
    replacement_key: str,
    docs_url: str,
) -> None:
    """Print a yellow DEPRECATED: notice to stderr via Rich.

    Returns early (without printing) when
    ``SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`` is set.  This suppression flag
    affects ONLY this Rich stderr notice — the ``DeprecationWarning`` emitted
    via ``warnings.warn`` in the caller is not affected.

    Args:
        var_name: The env var being deprecated.
        replacement_key: The canonical replacement config key.
        docs_url: Migration docs URL or relative path.
    """
    if os.environ.get("SPEC_KITTY_NO_DEPRECATION_WARNINGS") == "1":
        return

    from rich.console import Console

    Console(stderr=True).print(
        f"[yellow]DEPRECATED:[/yellow] {var_name} is a test/dev override only. "
        f"Set {replacement_key} instead. See {docs_url}"
    )


# ---------------------------------------------------------------------------
# Testing helper
# ---------------------------------------------------------------------------


def reset_emitted_for_testing() -> None:
    """Clear the ``_EMITTED`` set to allow re-emission in tests.

    This function is provided exclusively for use in test fixtures.  Production
    code MUST NOT call it.  The correct pattern is::

        @pytest.fixture(autouse=True)
        def reset_deprecation_state():
            from specify_cli.retrospective.deprecation import reset_emitted_for_testing
            reset_emitted_for_testing()
            yield
            reset_emitted_for_testing()
    """
    _EMITTED.clear()
