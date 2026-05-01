"""2.x package boundary invariants.

These tests enforce the dependency direction documented in
architecture/2.x/00_landscape/README.md:

    kernel (root) <- doctrine <- charter <- specify_cli

A violation here means a package imports from a package it should not.
See ADR 2026-03-27-1 for rationale.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from pytestarch import LayerRule

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Layer coverage guards (issue #395)
# ---------------------------------------------------------------------------

# Top-level src/ packages intentionally excluded from layer enforcement.
# Add entries here only for transitional / deprecated packages that will be
# removed once migration is complete.  Entries MUST include a comment
# explaining WHY they are excluded and when they can be removed.
_EXCLUDED_FROM_LAYER_ENFORCEMENT: frozenset[str] = frozenset(
    [
        # `constitution` is the pre-3.x predecessor of `charter`.  It is kept
        # for backward-compatibility shims until all 2.x consumers migrate.
        # Remove once mission 063 (rename-constitution-to-charter) is complete
        # and the compatibility layer is dropped.
        "constitution",
    ]
)

_SRC = Path(__file__).resolve().parents[2] / "src"

# Layer names as defined in the `landscape` fixture in conftest.py.
# Keep this in sync with that fixture; both lists must agree.
_DEFINED_LAYERS: frozenset[str] = frozenset(["kernel", "doctrine", "charter", "specify_cli"])


class TestLayerCoverage:
    """Meta-tests that keep the landscape fixture honest."""

    def test_no_unregistered_src_packages(self) -> None:
        """Every top-level src/ package must have a layer definition.

        When a new package is added to src/ without a corresponding layer,
        architectural boundary rules pass vacuously for it — violations go
        undetected.  Add the package to `_DEFINED_LAYERS` in the landscape
        fixture *and* to this file's `_DEFINED_LAYERS` constant, or add it
        to `_EXCLUDED_FROM_LAYER_ENFORCEMENT` with a documented reason.
        """
        src_packages = {p.name for p in _SRC.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").exists()}
        unregistered = src_packages - _DEFINED_LAYERS - _EXCLUDED_FROM_LAYER_ENFORCEMENT
        assert not unregistered, (
            f"src/ packages with no architectural layer assignment: "
            f"{sorted(unregistered)!r}.  "
            "Add a layer to tests/architectural/conftest.py or add to "
            "_EXCLUDED_FROM_LAYER_ENFORCEMENT with a documented reason."
        )

    def test_all_defined_layers_match_at_least_one_module(self) -> None:
        """Every defined layer must match at least one importable module.

        If a package is renamed or removed, the layer definition becomes an
        empty set and all its rules pass vacuously.
        """
        empty: list[str] = []
        for layer in sorted(_DEFINED_LAYERS):
            installed = importlib.util.find_spec(layer) is not None
            on_disk = (_SRC / layer / "__init__.py").exists()
            if not installed and not on_disk:
                empty.append(layer)
        assert not empty, (
            f"Layers defined but no matching module found: {empty!r}.  "
            "The boundary rules for these layers would pass vacuously.  "
            "Remove the layer or restore the package."
        )


# --- Invariant 1: kernel is the true root (zero outgoing deps) ---


class TestKernelIsolation:
    """kernel must not import from any other landscape container."""

    def test_kernel_does_not_import_doctrine(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("kernel").should_not().access_layers_that().are_named("doctrine")).assert_applies(evaluable)

    def test_kernel_does_not_import_charter(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("kernel").should_not().access_layers_that().are_named("charter")).assert_applies(evaluable)

    def test_kernel_does_not_import_specify_cli(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("kernel").should_not().access_layers_that().are_named("specify_cli")).assert_applies(evaluable)


# --- Invariant 2: doctrine depends only on kernel ---


class TestDoctrineIsolation:
    """doctrine must not import from specify_cli or charter."""

    def test_doctrine_does_not_import_specify_cli(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("doctrine").should_not().access_layers_that().are_named("specify_cli")).assert_applies(evaluable)

    def test_doctrine_does_not_import_charter(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("doctrine").should_not().access_layers_that().are_named("charter")).assert_applies(evaluable)


# --- Invariant 3: charter boundary ---


class TestCharterBoundary:
    """charter may import doctrine + kernel only. No specify_cli imports."""

    def test_charter_does_not_import_specify_cli(self, evaluable, landscape):
        (LayerRule().based_on(landscape).layers_that().are_named("charter").should_not().access_layers_that().are_named("specify_cli")).assert_applies(evaluable)
