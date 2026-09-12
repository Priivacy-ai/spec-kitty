"""Alias-aware installed distribution version lookup for compat/planner paths.

Do not confuse with ``version_utils.get_version`` (WP02-owned). This helper is
the FR-011 / T020 surface for planner and related callers that must try
``package_name`` then ``package_aliases`` without editing ``version_utils``.
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version

__all__ = ["resolve_installed_distribution_version"]

_log = logging.getLogger(__name__)


def resolve_installed_distribution_version(
    package_name: str,
    package_aliases: tuple[str, ...] = (),
    *,
    default: str = "unknown",
) -> str:
    """Return the installed version for *package_name*, then aliases.

    Never raises. Returns *default* when no candidate distribution is found.
    """
    for name in (package_name, *package_aliases):
        if not name:
            continue
        try:
            return version(name)
        except PackageNotFoundError:
            continue
        except Exception:
            # Contract: never raise — a malformed/unreadable metadata entry must
            # degrade to the next candidate (ultimately ``default``), not crash a
            # caller. Log at debug so the swallow is observable to packagers.
            _log.debug(
                "importlib.metadata.version(%r) raised unexpectedly; trying next candidate",
                name,
                exc_info=True,
            )
            continue
    return default
