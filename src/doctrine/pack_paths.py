"""Shared pack-root resolver for doctrine packs (built-in, org, project).

This module is the single seam through which every consumer resolves the
filesystem root of a doctrine pack tier. ``packs/built-in/`` is deliberately
*not* a Python package -- the hyphen in ``built-in`` is not a legal identifier
-- so a package-relative :func:`importlib.resources.files` lookup cannot
address it. A filesystem walk is required instead.

Resolution order for the ``built-in`` tier:

1. ``SPEC_KITTY_PACKS_ROOT`` environment override -> ``<env>/built-in`` if it
   exists.
2. Editable checkout: the nearest ancestor of this module's resolved location
   that contains ``packs/built-in/``. ``Path(__file__).resolve()`` is called
   **before** iterating ``.parents`` so that symlinked editable installs still
   walk up the real repository tree rather than the symlink's parent.
3. Installed wheel: ``packs/`` ships as a site-packages sibling of the
   ``doctrine`` package (hatch ``force-include``), so
   ``files("doctrine").parent / "packs" / "built-in"``.
4. Otherwise :class:`PackRootNotFound` -- fail-closed; never fall open to an
   arbitrary tree or to a path inside ``src/doctrine/``.

For the ``org`` / ``project`` tiers the seam is shared but the input differs:
the caller-supplied root is returned unchanged.

Layer note (C-004): doctrine sits below charter/specify_cli in the dependency
graph and must not import upward. This module imports only the standard library
(``os``, ``pathlib``, :func:`importlib.resources.files`). The ``files("doctrine")``
call is an in-layer self-reference and is made lazily *inside* the function to
avoid an import cycle with ``doctrine/__init__.py``.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Literal

# ``PackTier`` is intentionally *not* exported: it is the internal annotation
# for ``resolve_pack_root``'s ``tier`` parameter and has no external importer, so
# listing it in ``__all__`` would trip the symbol-level dead-code gate
# (tests/architectural/test_no_dead_symbols.py). It stays a module-level name
# usable as ``pack_paths.PackTier``; re-export it here once a real consumer imports it.
__all__ = ["PackRootNotFound", "resolve_pack_root"]

PackTier = Literal["built-in", "org", "project"]

_PACKS_ROOT_ENV = "SPEC_KITTY_PACKS_ROOT"
_BUILT_IN = "built-in"


class PackRootNotFound(Exception):
    """Raised when no pack root can be resolved for a tier (fail-closed)."""

    def __init__(self, tier: str) -> None:
        self.tier = tier
        super().__init__(f"No pack root found for tier {tier!r}")


def resolve_pack_root(
    tier: PackTier,
    *,
    org_root: Path | None = None,
    project_root: Path | None = None,
) -> Path:
    """Resolve the filesystem root of a doctrine pack *tier*.

    :param tier: ``"built-in"``, ``"org"``, or ``"project"``.
    :param org_root: caller-supplied root for the ``org`` tier.
    :param project_root: caller-supplied root for the ``project`` tier.
    :returns: an existing directory for the requested tier.
    :raises PackRootNotFound: when the tier cannot be resolved. Fail-closed:
        never returns a path inside ``src/doctrine/`` and never falls open to an
        arbitrary tree.

    Pure and idempotent: same inputs (and environment) yield the same path.
    """
    if tier == "org":
        if org_root is None:
            raise PackRootNotFound("org")
        return org_root
    if tier == "project":
        if project_root is None:
            raise PackRootNotFound("project")
        return project_root
    return _resolve_built_in()


def _resolve_built_in() -> Path:
    """Resolve the ``built-in`` tier via the 4-step order (env, editable, installed, fail)."""
    # (1) Explicit environment override wins.
    env_value = os.environ.get(_PACKS_ROOT_ENV)
    if env_value:
        env_candidate = Path(env_value) / _BUILT_IN
        if env_candidate.is_dir():
            return env_candidate

    # (2) Editable checkout: nearest ancestor holding packs/built-in/.
    #     .resolve() BEFORE walking parents so symlinked installs reach the
    #     real repository root.
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        editable_candidate = ancestor / "packs" / _BUILT_IN
        if editable_candidate.is_dir():
            return editable_candidate

    # (3) Installed wheel: packs/ is a site-packages sibling of the doctrine pkg.
    doctrine_dir = _doctrine_package_dir()
    if doctrine_dir is not None:
        installed_candidate = doctrine_dir.parent / "packs" / _BUILT_IN
        if installed_candidate.is_dir():
            return installed_candidate

    # (4) Fail-closed.
    raise PackRootNotFound(_BUILT_IN)


def _doctrine_package_dir() -> Path | None:
    """Return the installed ``doctrine`` package directory, or ``None``.

    ``files("doctrine")`` is called lazily here (not at import time) to avoid an
    import cycle with ``doctrine/__init__.py``.
    """
    try:
        return Path(str(files("doctrine")))
    except (ModuleNotFoundError, TypeError):
        return None
