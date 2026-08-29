"""Project-local doctrine-artifact root resolution (CR-07 dual-root reader).

Mission ``charter-code-topology-01M152G1`` S4 renames the operator-facing
per-project doctrine-artifact tree from ``.kittify/doctrine/`` to
``.kittify/charter-packs/`` (MAP-CR CR-07). This module is the M2 half of
that cutover: a READ-side dual-root resolver only (canonical-preferred,
legacy-fallback with a warn-once notice). M3 performs the actual on-disk
data move and flips write call sites over; nothing in this module writes or
moves any file. Precedent for the read-both/canonical-wins/warn-once shape:
``charter.activation.sync``'s CR-01 governance-selection-key compat
(``src/charter/sync.py:245-311``).

Lives in ``kernel`` -- not ``charter`` or ``specify_cli`` -- because both
``charter.activation.synthesizer.*`` (the live-tree write/reconcile pipeline) and
``specify_cli.doctrine_synthesizer.apply`` (the retrospective-proposal
applier) need to resolve the same project-local root, and the
kernel<-charter<-specify_cli layer direction means kernel is the only shared
floor both can import without violating it.
"""

from __future__ import annotations

import functools
import warnings
from pathlib import Path

__all__ = [
    "CANONICAL_DOCTRINE_DIRNAME",
    "LEGACY_DOCTRINE_DIRNAME",
    "LegacyDoctrineRootWarning",
    "resolve_doctrine_read_root",
]

_KITTIFY_DIRNAME = ".kittify"

#: The retired per-project doctrine-artifact directory name under
#: ``.kittify/``. Exported so call sites that still target this root for
#: writes (M3 territory) derive their own local constant from this single
#: owned source instead of re-spelling the literal -- the "split-literal,
#: census-invisible" trap CR-07 calls out (e.g. a constant literally named
#: ``_DOCTRINE_DIRNAME`` holding ``".kittify"``, with the ``"doctrine"``
#: segment spelled bare at each call site).
LEGACY_DOCTRINE_DIRNAME = "doctrine"

#: The canonical replacement (CR-07).
CANONICAL_DOCTRINE_DIRNAME = "charter-packs"


class LegacyDoctrineRootWarning(UserWarning):
    """Emitted once per process when a project is read from the retired
    ``.kittify/doctrine/`` root because the canonical ``.kittify/charter-packs/``
    does not exist yet (CR-07)."""


@functools.lru_cache(maxsize=1)
def _warn_legacy_doctrine_root_once() -> None:
    """Emit the CR-07 compat warning exactly once per process.

    Gated by ``lru_cache`` rather than the ``warnings`` module's own de-dup
    filter for the same reason as every other CR shim in this mission
    (precedent: ``charter.activation.sync._warn_legacy_governance_key_once``, CR-01) --
    a caller running under a stricter ``filterwarnings`` configuration could
    otherwise turn a *repeated* warning into a hard failure. Tests reset this
    gate via ``_warn_legacy_doctrine_root_once.cache_clear()``.
    """
    warnings.warn(
        f"'{_KITTIFY_DIRNAME}/{LEGACY_DOCTRINE_DIRNAME}/' is the legacy "
        "per-project doctrine-artifact root; reading it because "
        f"'{_KITTIFY_DIRNAME}/{CANONICAL_DOCTRINE_DIRNAME}/' does not exist "
        "yet. A future migration moves this data to the canonical root.",
        LegacyDoctrineRootWarning,
        stacklevel=3,
    )


def resolve_doctrine_read_root(repo_root: Path, *, quiet: bool = False) -> Path:
    """Return the project-local doctrine-artifact root to read from.

    Canonical-preferred: ``repo_root/.kittify/charter-packs`` wins whenever
    it exists on disk, even alongside a still-present legacy tree (M3 moves
    the data; until then an operator who has already migrated is never
    nagged about a stale legacy directory nobody reads any more -- mirrors
    CR-01's ``apply_legacy_governance_selection_key_compat``).

    Falls back to the legacy ``repo_root/.kittify/doctrine`` when only that
    exists, emitting :func:`_warn_legacy_doctrine_root_once` (unless
    *quiet*).

    When NEITHER exists yet (a fresh project with no doctrine artifacts at
    all), returns the canonical path: there is nothing to read, and nothing
    to warn about -- any future write should land in the canonical
    location.
    """
    canonical = repo_root / _KITTIFY_DIRNAME / CANONICAL_DOCTRINE_DIRNAME
    if canonical.is_dir():
        return canonical

    legacy = repo_root / _KITTIFY_DIRNAME / LEGACY_DOCTRINE_DIRNAME
    if legacy.is_dir():
        if not quiet:
            _warn_legacy_doctrine_root_once()
        return legacy

    return canonical
