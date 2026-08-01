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

Two additional authorities (mission ``doctrine-built-in-seam-consolidation-01KYW3TX``,
WP01) sit on top of the tier resolver above: :func:`built_in_root` (the bare
built-in root, for callers like the DRG loader/extractor that need no kind
subdirectory) and :func:`built_in_dir` (the per-kind
``packs/built-in/<plural>/`` directory, refusing the 3-kind carve-out with
:class:`BuiltInContentDirNotAvailable`). These are the seam every doctrine
repository default and DRG root caller routes through -- no other module
should compose its own ``resolve_pack_root("built-in") / ...`` join.

Layer note (C-004): doctrine sits below charter/specify_cli in the dependency
graph and must not import upward. This module imports only the standard
library (``os``, ``pathlib``, :func:`importlib.resources.files`) plus
:class:`~doctrine.artifact_kinds.ArtifactKind`, an in-layer sibling that is
itself a zero-dependency leaf (imports only ``enum``) -- so this stays
import-cycle-safe. The ``files("doctrine")`` call is an in-layer
self-reference and is made lazily *inside* the function to avoid an import
cycle with ``doctrine/__init__.py``.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Literal

from doctrine.artifact_kinds import ArtifactKind

# ``PackTier`` is intentionally *not* exported: it is the internal annotation
# for ``resolve_pack_root``'s ``tier`` parameter and has no external importer, so
# listing it in ``__all__`` would trip the symbol-level dead-code gate
# (tests/architectural/test_no_dead_symbols.py). It stays a module-level name
# usable as ``pack_paths.PackTier``; re-export it here once a real consumer imports it.
#
# ``resolve_pack_root`` is likewise not exported: after the built-in seam
# consolidation (doctrine-built-in-seam-consolidation) every external caller
# resolves built-in location through the ``built_in_dir``/``built_in_root``
# authorities (C1.6 — it is the internal tier resolver those two wrap), so it has
# no external ``src/`` importer and would trip the dead-code gate. It remains a
# module-level name (``pack_paths.resolve_pack_root``); re-export it if a real
# non-seam consumer (e.g. org/project-tier resolution) imports it directly.
__all__ = [
    "BuiltInContentDirNotAvailable",
    "PackRootNotFound",
    "built_in_dir",
    "built_in_root",
    "doctrine_package_dir",
]

PackTier = Literal["built-in", "org", "project"]

_PACKS_ROOT_ENV = "SPEC_KITTY_PACKS_ROOT"
_BUILT_IN = "built-in"


class PackRootNotFound(Exception):
    """Raised when no pack root can be resolved for a tier (fail-closed)."""

    def __init__(self, tier: str) -> None:
        self.tier = tier
        super().__init__(f"No pack root found for tier {tier!r}")


class BuiltInContentDirNotAvailable(Exception):
    """Raised by :func:`built_in_dir` for a kind with no built-in content dir.

    The refused kinds are the derived complement of
    :attr:`~doctrine.artifact_kinds.ArtifactKind.has_built_in_content_dir`
    (currently ``MISSION_STEP_CONTRACT``, ``TEMPLATE``, ``ANTI_PATTERN``) --
    package-resource/graph-only kinds with no shipped
    ``packs/built-in/<plural>/`` directory (see mission #3091 for the
    step-contract/template relocation). Raising a named error here instead of
    silently joining to a non-existent path is the C1.4 contract obligation.
    """

    def __init__(self, kind: ArtifactKind) -> None:
        self.kind = kind
        super().__init__(
            f"ArtifactKind.{kind.name} has no packs/built-in/ content "
            "directory (package-resource/graph-only kind; see mission #3091 "
            "for the step-contract/template relocation)."
        )


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


def built_in_root() -> Path:
    """Return the filesystem root of the built-in pack tier (FR-001b / C1.6).

    The single callable a root-needing reader (e.g. the DRG loader, the DRG
    migration extractor, a reference-pointer walk, ``doctrine
    regenerate-graph``) uses instead of scattering bare
    ``resolve_pack_root("built-in")`` calls across modules.

    :raises PackRootNotFound: when the built-in pack root cannot be located
        (fail-closed -- see :func:`resolve_pack_root`).
    """
    return resolve_pack_root("built-in")


def built_in_dir(kind: ArtifactKind) -> Path:
    """Return the built-in content directory for *kind* (FR-001).

    ``resolve_pack_root("built-in") / kind.plural`` -- the canonical plural is
    read from :class:`~doctrine.artifact_kinds.ArtifactKind`, never a
    hand-typed string.

    The refusal below is computed straight from
    :attr:`~doctrine.artifact_kinds.ArtifactKind.has_built_in_content_dir` --
    there is no hand-listed complement set in this module (FR-005 / NFR-005).
    A kind gaining or losing a content dir is a one-place edit in
    ``artifact_kinds.py``; this function needs no change.

    :raises BuiltInContentDirNotAvailable: for a kind with no shipped content
        dir (the derived complement -- currently ``MISSION_STEP_CONTRACT``,
        ``TEMPLATE``, ``ANTI_PATTERN``; C1.4).
    :raises PackRootNotFound: when the built-in pack root cannot be located
        (C1.3 -- no empty-set substitute).
    """
    if not kind.has_built_in_content_dir:
        raise BuiltInContentDirNotAvailable(kind)
    return resolve_pack_root("built-in") / kind.plural


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
    doctrine_dir = doctrine_package_dir()
    if doctrine_dir is not None:
        installed_candidate = doctrine_dir.parent / "packs" / _BUILT_IN
        if installed_candidate.is_dir():
            return installed_candidate

    # (4) Fail-closed.
    raise PackRootNotFound(_BUILT_IN)


def doctrine_package_dir() -> Path | None:
    """Return the installed ``doctrine`` package directory, or ``None``.

    ``files("doctrine")`` is called lazily here (not at import time) to avoid an
    import cycle with ``doctrine/__init__.py``. Public (WP01-fold, mission
    ``doctrine-built-in-seam-consolidation-01KYW3TX``) so
    :mod:`doctrine.drg.migration.extractor` can import this instead of
    carrying a byte-identical private copy.
    """
    try:
        return Path(str(files("doctrine")))
    except (ModuleNotFoundError, TypeError):
        return None
