"""Compatibility shim for the legacy ``retrospective.config`` surface.

This module is retained to preserve back-compat for callers that import from
``specify_cli.retrospective.config``.  The canonical surface for controlling
whether the retrospective lifecycle is enabled is now
``specify_cli.retrospective.policy.resolve_policy``.

``is_retrospective_enabled()`` was the pre-3.2 entry point.  It is preserved
here as a thin wrapper for callers that haven't migrated yet.

**Retirement plan:**
- Deprecation target: spec-kitty 3.3.0
- Follow-up issue: https://github.com/Priivacy-ai/spec-kitty/issues/TBD
  (Issue title: "Retire retrospective.config + mode shim modules")
- Rationale: ``runtime_bridge.py`` imports ``is_retrospective_enabled`` from
  here at two call sites; migrating those in a safe, reviewable way requires
  a dedicated WP to avoid a rushed refactor in the 3.2 release window.

Opt-in signals (any one suffices):

- Charter frontmatter declares ``mode:`` with a retrospective-aware value
  (``autonomous`` or ``human_in_command``).
- ``SPEC_KITTY_RETROSPECTIVE`` environment variable is ``"1"`` / ``"true"``.

A malformed charter raises ``ModeResolutionError`` from the underlying
reader; this module surfaces that to the caller.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from specify_cli.retrospective.mode import ModeResolutionError as ModeResolutionError  # noqa: F401
from specify_cli.retrospective.mode import _read_charter_mode

_TRUTHY_ENV = frozenset({"1", "true", "True", "TRUE", "yes", "on"})


def is_retrospective_enabled(
    repo_root: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return True if the retrospective lifecycle is opted in for this project.

    .. deprecated::
        Use ``specify_cli.retrospective.policy.resolve_policy()`` instead.
        This function is retained for back-compat through spec-kitty 3.2.x.

    Args:
        repo_root: Project root used to locate ``.kittify/charter/charter.md``.
        env: Environment mapping for testing; defaults to ``os.environ``.

    Returns:
        True if the project has explicitly opted into the retrospective
        lifecycle via charter clause or environment variable; False otherwise.

    Raises:
        ModeResolutionError: re-raised from the underlying charter reader if
            the charter exists but its frontmatter is malformed. The runtime
            should treat this as fail-closed (do not bypass the gate).
    """
    effective_env: Mapping[str, str] = env if env is not None else os.environ
    if effective_env.get("SPEC_KITTY_RETROSPECTIVE", "").strip() in _TRUTHY_ENV:
        return True

    return _read_charter_mode(repo_root) is not None
