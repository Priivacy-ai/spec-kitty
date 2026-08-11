"""Curated public surface for the ``spec-kitty-doctrine`` wheel (FR-001).

This module is the **single, enumerable manifest** of doctrine symbols that are
externally consumable — the exact set the future standalone ``spec-kitty-doctrine``
wheel is intended to export (FR-001 / FR-008). A maintainer can read one file,
``doctrine/api.py``, and see the complete public contract; the wheel-closure gate
(``tests/architectural/test_doctrine_wheel_closure.py``) pins this ``__all__`` so
the packaged surface cannot silently drift from it.

Layering invariant (C-001)
--------------------------
``doctrine/api.py`` exists **for the charter facades and the wheel**, not as a
runtime door. The sanctioned reach stays ``runtime → charter.* facade → doctrine``.
Runtime code under ``src/specify_cli/`` must NOT ``from doctrine.api import …``
directly; the charter facades (WP03) re-export these symbols *by object identity*
and are the only sanctioned importers (see the doctrine-reach-through boundary gate
``tests/architectural/test_runtime_charter_doctrine_boundary.py``).

Disposition provenance
----------------------
Every symbol below is tagged ``PUBLIC`` in the authoritative disposition manifest
``tests/architectural/test_doctrine_census.py::DISPOSITION`` (WP01). ``FACADE-ONLY``
paths (fronted by a charter facade but *not* part of the wheel's public contract)
and ``INTERNAL`` paths are deliberately absent — the negative guard
``tests/architectural/test_doctrine_public_surface.py`` asserts that absence.

Contract kind (C-003)
---------------------
This is an in-process Python contract (versioned via wheel semver + ``py.typed``),
not an HTTP/REST schema — OpenAPI conventions do not apply.
"""

from __future__ import annotations

# ArtifactKind — the doctrine artifact-kind taxonomy enum (also fronted by
# charter.drg). PUBLIC per DISPOSITION["doctrine.artifact_kinds"].
from doctrine.artifact_kinds import ArtifactKind

# Asset resolution surface — repository, sidecar manifest model, and the typed
# (fail-closed) error hierarchy a consumer catches. PUBLIC per
# DISPOSITION["doctrine.assets.repository"] / ["doctrine.assets.models"].
from doctrine.assets.models import AssetManifest
from doctrine.assets.repository import (
    AssetNotFoundError,
    AssetPathEscapeError,
    AssetRepository,
    AssetResolutionError,
)

# Model→task-type routing surface — the deterministic evaluator/loader callables
# plus their result types. PUBLIC per DISPOSITION["doctrine.model_task_routing"]
# (the spec's "true gap" #1: evaluator / loader / RoutingRecommendation).
from doctrine.model_task_routing.evaluator import RoutingRecommendation, evaluate
from doctrine.model_task_routing.loader import CatalogLoadResult, load

#: The complete, curated doctrine public surface. This is the manifest the wheel
#: exports and the set the wheel-closure gate pins. Keep it sorted and explicit;
#: every entry MUST carry a disposition of ``PUBLIC`` in the WP01 census manifest.
__all__ = [
    "ArtifactKind",
    "AssetManifest",
    "AssetNotFoundError",
    "AssetPathEscapeError",
    "AssetRepository",
    "AssetResolutionError",
    "CatalogLoadResult",
    "RoutingRecommendation",
    "evaluate",
    "load",
]
