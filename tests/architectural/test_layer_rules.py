"""2.x package boundary invariants.

These tests enforce the dependency direction documented in
architecture/2.x/00_landscape/README.md:

    kernel (root) <- doctrine <- constitution <- specify_cli

A violation here means a package imports from a package it should not.
See ADR 2026-03-27-1 for rationale.
"""
from __future__ import annotations

import pytest
from pytestarch import LayerRule

pytestmark = pytest.mark.architectural


# --- Invariant 1: kernel is the true root (zero outgoing deps) ---


class TestKernelIsolation:
    """kernel must not import from any other landscape container."""

    def test_kernel_does_not_import_doctrine(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("doctrine")
        ).assert_applies(evaluable)

    def test_kernel_does_not_import_constitution(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("constitution")
        ).assert_applies(evaluable)

    def test_kernel_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)


# --- Invariant 2: doctrine depends only on kernel ---


class TestDoctrineIsolation:
    """doctrine must not import from specify_cli or constitution."""

    def test_doctrine_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("doctrine")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)

    def test_doctrine_does_not_import_constitution(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("doctrine")
            .should_not()
            .access_layers_that()
            .are_named("constitution")
        ).assert_applies(evaluable)


# --- Invariant 3: constitution boundary ---


class TestConstitutionBoundary:
    """constitution may import doctrine + kernel only. No specify_cli imports."""

    def test_constitution_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("constitution")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)
