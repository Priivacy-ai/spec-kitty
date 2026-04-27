"""Opt-in configuration helpers for the retrospective lifecycle.

Determines whether the runtime should invoke ``run_terminus()`` at mission
terminus. Until projects explicitly opt in, the gate stays out of the live
mission-completion path so existing missions remain unaffected.

Opt-in signals (any one suffices):

- Charter frontmatter declares ``mode:`` with a retrospective-aware value
  (``autonomous`` or ``human_in_command``). This re-uses the same charter
  read path as :func:`specify_cli.retrospective.mode.detect`.
- ``SPEC_KITTY_RETROSPECTIVE`` environment variable is ``"1"`` / ``"true"``.

A malformed charter raises ``ModeResolutionError`` from the underlying
reader; this module surfaces that to the caller (the runtime should
fail-fast rather than silently bypass governance on a malformed charter).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from specify_cli.retrospective.mode import _read_charter_mode

_TRUTHY_ENV = frozenset({"1", "true", "True", "TRUE", "yes", "on"})


def is_retrospective_enabled(
    repo_root: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return True if the retrospective lifecycle is opted in for this project.

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
