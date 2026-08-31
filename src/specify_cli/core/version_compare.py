"""Canonical version-comparison primitives shared across upgrade surfaces (#2417).

Before this module existed, "is candidate version newer than current version"
was implemented independently in three places:

- ``cli/commands/upgrade.py::_version_is_newer`` — caught the broad
  ``Exception`` (``# noqa: BLE001``) rather than the specific parse failure.
- ``core/upgrade_probe.py::_classify`` — a richer PyPI-channel classifier
  that needs version *parsing* and *ordering* as building blocks alongside
  releases-membership checks; only its comparison sub-logic is unified here.
- ``session_presence/manager.py::_upgrade_is_available`` — added to fix #2413,
  where a bare inequality (``avail != current``) reported "upgrade available"
  whenever the cached PyPI latest lagged the installed version (fresh release
  not yet cached, rc/dev installs), instead of comparing ordering.

This module is the single source of truth for both operations. It is pure
(no CLI/click/typer imports) so it is safe to import from any layer — CLI
commands, core probes, session-presence writers, or future callers.
"""

from __future__ import annotations

from packaging.version import InvalidVersion, Version


def try_parse_version(value: str | None) -> Version | None:
    """Parse *value* as a PEP 440 version, or return ``None`` if it cannot be.

    ``None``, the empty string, and any string ``packaging.version`` rejects
    all resolve to ``None``. Callers that need a well-formed comparison
    target should treat ``None`` as "unknown — do not compare".
    """
    if not value:
        return None
    try:
        return Version(value)
    except InvalidVersion:
        return None


def is_version_newer(candidate: str | None, current: str) -> bool:
    """Return True iff *candidate* is a parseable version strictly newer than *current*.

    - ``None``, empty, or unparseable *candidate* -> ``False`` (never blocks
      on bad input).
    - Unparseable *current* -> ``False`` (conservative: can't prove an
      upgrade exists if we can't parse the baseline).
    """
    candidate_ver = try_parse_version(candidate)
    if candidate_ver is None:
        return False
    current_ver = try_parse_version(current)
    if current_ver is None:
        return False
    return candidate_ver > current_ver


__all__ = ["is_version_newer", "try_parse_version"]
