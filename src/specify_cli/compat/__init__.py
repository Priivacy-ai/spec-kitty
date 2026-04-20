"""Compatibility-shim infrastructure for spec-kitty.

This package owns:
- Loading and validating architecture/2.x/shim-registry.yaml
- Classifying each registered shim (pending/overdue/grandfathered/removed)
- The engine behind `spec-kitty doctor shim-registry`

Public API:
    check_shim_registry, ShimRegistryReport, ShimStatus, ShimStatusEntry, RegistrySchemaError

NOTE: src/specify_cli/shims/ is a DIFFERENT domain (agent-skill shims).
Do not confuse the two packages.

# Baseline audit (2026-04-19): zero modules under src/specify_cli/ carry
# __deprecated__ = True at mission start. Registry begins empty.
"""
from __future__ import annotations

from specify_cli.compat.registry import RegistrySchemaError
from specify_cli.compat.doctor import ShimRegistryReport, ShimStatus, ShimStatusEntry, check_shim_registry

__all__ = ["check_shim_registry", "ShimRegistryReport", "ShimStatus", "ShimStatusEntry", "RegistrySchemaError"]
