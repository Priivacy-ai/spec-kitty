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
import pkgutil
import sys

import pytest


pytestmark = [pytest.mark.architectural]


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
    """Legacy dotted-path submodule imports resolve to the SAME canonical module.

    The legacy shim eagerly aliases canonical submodules in ``sys.modules``
    under the legacy dotted names, so both ``import legacy.submod`` and
    ``from legacy import submod`` return the identical module object as
    ``import canonical.submod``. Module-object identity is critical for
    ``mock.patch`` correctness — a test that patches
    ``specify_cli.charter_preflight.hook.X`` must see the patch take
    effect inside production code that imports via that same dotted path.
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
        assert legacy_mod is canonical_mod, (
            f"shim identity mismatch: {legacy_path} is not {canonical_path} "
            f"(legacy id={id(legacy_mod)}, canonical id={id(canonical_mod)}). "
            f"This breaks ``mock.patch('{legacy_path}.X', ...)`` contracts."
        )
        assert hasattr(legacy_mod, sentinel), (
            f"{legacy_path} missing sentinel symbol {sentinel!r}"
        )


def test_all_canonical_lint_checks_have_legacy_aliases() -> None:
    """Every canonical lint checker module must keep legacy identity."""
    canonical_checks = importlib.import_module(
        "specify_cli.charter_runtime.lint.checks"
    )

    for module_info in pkgutil.iter_modules(canonical_checks.__path__):
        canonical_path = f"specify_cli.charter_runtime.lint.checks.{module_info.name}"
        legacy_path = f"specify_cli.charter_lint.checks.{module_info.name}"

        canonical_mod = importlib.import_module(canonical_path)
        legacy_mod = importlib.import_module(legacy_path)

        assert legacy_mod is canonical_mod, (
            f"shim identity mismatch: {legacy_path} is not {canonical_path}"
        )


def test_missing_legacy_lint_check_alias_fails_loudly() -> None:
    """Deleted/missing nested aliases must not import duplicate modules.

    This guards issue #1459: if a nested legacy check alias disappears from
    ``sys.modules``, Python must not discover the canonical file through the
    legacy parent package and instantiate it as
    ``specify_cli.charter_lint.checks.<name>``.
    """
    legacy_path = "specify_cli.charter_lint.checks.staleness"
    canonical_path = "specify_cli.charter_runtime.lint.checks.staleness"

    canonical_mod = importlib.import_module(canonical_path)
    original_legacy_mod = importlib.import_module(legacy_path)
    assert original_legacy_mod is canonical_mod

    sys.modules.pop(legacy_path, None)
    try:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(legacy_path)
        assert sys.modules.get(legacy_path) is None
    finally:
        sys.modules[legacy_path] = canonical_mod
