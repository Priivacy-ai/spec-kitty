"""Architectural regression guard for charter_runtime/ umbrella + shim paths.

LD-5 / FR-014 / C-008 introduced ``specify_cli.charter_runtime`` as the
canonical umbrella for the three charter-runtime sub-packages, while keeping
the legacy paths importable for one deprecation cycle.

This test locks the contract so the shim layer cannot be silently removed:

1. The new canonical paths must import.
2. The legacy paths must re-export the same public surface.
3. Submodule dotted-path imports through the shim must resolve via
   ``sys.modules`` aliasing.
"""

from __future__ import annotations

import importlib


def test_canonical_paths_import() -> None:
    """All four umbrella sub-packages exist at the new canonical paths."""
    for path in (
        "specify_cli.charter_runtime",
        "specify_cli.charter_runtime.lint",
        "specify_cli.charter_runtime.freshness",
        "specify_cli.charter_runtime.preflight",
        "specify_cli.charter_runtime.facade",
    ):
        mod = importlib.import_module(path)
        assert mod is not None, f"{path} failed to import"


def test_legacy_paths_still_import() -> None:
    """The pre-WP08 import paths still resolve via shim re-exports (C-008)."""
    for path in (
        "specify_cli.charter_lint",
        "specify_cli.charter_freshness",
        "specify_cli.charter_preflight",
    ):
        mod = importlib.import_module(path)
        assert mod is not None, f"legacy path {path} failed to import"


def test_legacy_submodules_resolve_via_shim() -> None:
    """Legacy dotted-path submodule imports resolve to the new canonical modules."""
    cases: list[tuple[str, str]] = [
        ("specify_cli.charter_preflight.cli", "specify_cli.charter_runtime.preflight.cli"),
        ("specify_cli.charter_preflight.hook", "specify_cli.charter_runtime.preflight.hook"),
        ("specify_cli.charter_preflight.config", "specify_cli.charter_runtime.preflight.config"),
        (
            "specify_cli.charter_freshness.computer",
            "specify_cli.charter_runtime.freshness.computer",
        ),
        ("specify_cli.charter_lint.engine", "specify_cli.charter_runtime.lint.engine"),
        ("specify_cli.charter_lint.findings", "specify_cli.charter_runtime.lint.findings"),
        (
            "specify_cli.charter_lint.checks.staleness",
            "specify_cli.charter_runtime.lint.checks.staleness",
        ),
    ]
    for legacy_path, canonical_path in cases:
        legacy_mod = importlib.import_module(legacy_path)
        canonical_mod = importlib.import_module(canonical_path)
        assert legacy_mod is canonical_mod, (
            f"shim mismatch: {legacy_path} != {canonical_path}"
        )
