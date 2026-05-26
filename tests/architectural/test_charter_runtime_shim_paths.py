"""Architectural regression guard for charter_runtime/ umbrella + shim paths.

LD-5 / FR-014 / C-008 introduced ``specify_cli.charter_runtime`` as the
canonical umbrella for the three charter-runtime sub-packages, while keeping
the legacy paths importable for one deprecation cycle.

This test locks the contract so the shim layer cannot be silently removed:

1. The new canonical paths must import.
2. The legacy paths must re-export the same public surface.
3. Submodule dotted-path imports through the shim must resolve to the
   canonical module's source (verified by symbol equivalence).
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
    """Legacy dotted-path submodule imports load the canonical sources.

    The legacy shim shares ``__path__`` with the canonical package, so
    ``import specify_cli.charter_preflight.cli`` finds and loads ``cli.py``
    from the canonical directory. Python registers the loaded module under
    the legacy dotted name; the underlying code object is the same as the
    canonical module's, but the two ``__name__`` strings differ — so we
    assert symbol equivalence rather than module-object identity.
    """
    cases: list[tuple[str, str, str]] = [
        (
            "specify_cli.charter_preflight.cli",
            "specify_cli.charter_runtime.preflight.cli",
            "charter_preflight",
        ),
        (
            "specify_cli.charter_preflight.hook",
            "specify_cli.charter_runtime.preflight.hook",
            "run_preflight_or_abort",
        ),
        (
            "specify_cli.charter_preflight.config",
            "specify_cli.charter_runtime.preflight.config",
            "load_preflight_config",
        ),
        (
            "specify_cli.charter_freshness.computer",
            "specify_cli.charter_runtime.freshness.computer",
            "compute_freshness",
        ),
        (
            "specify_cli.charter_lint.engine",
            "specify_cli.charter_runtime.lint.engine",
            "LintEngine",
        ),
        (
            "specify_cli.charter_lint.findings",
            "specify_cli.charter_runtime.lint.findings",
            "LintFinding",
        ),
        (
            "specify_cli.charter_lint.checks.staleness",
            "specify_cli.charter_runtime.lint.checks.staleness",
            "StalenessChecker",
        ),
    ]
    for legacy_path, canonical_path, sentinel in cases:
        legacy_mod = importlib.import_module(legacy_path)
        canonical_mod = importlib.import_module(canonical_path)
        # Both module objects must load from the SAME source file on disk —
        # this is the equivalence the deprecation contract really needs.
        # Module-object identity differs because Python's dotted-import
        # registers them under separate names (PEP 420-style ``__path__``
        # sharing).
        assert legacy_mod.__file__ == canonical_mod.__file__, (
            f"shim source-file mismatch: "
            f"{legacy_path}.__file__={legacy_mod.__file__!r} vs "
            f"{canonical_path}.__file__={canonical_mod.__file__!r}"
        )
        assert hasattr(legacy_mod, sentinel), (
            f"{legacy_path} missing sentinel symbol {sentinel!r}"
        )
        assert hasattr(canonical_mod, sentinel), (
            f"{canonical_path} missing sentinel symbol {sentinel!r}"
        )
