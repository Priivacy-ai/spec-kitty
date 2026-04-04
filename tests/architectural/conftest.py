"""Architectural dependency test fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest
from pytestarch import LayeredArchitecture, get_evaluable_architecture

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture(scope="session")
def evaluable():
    """Session-scoped evaluable architecture for all src/ packages.

    Uses SRC as both root and module path so that top-level package names
    are ``src.kernel``, ``src.doctrine``, etc.

    ``exclude_external_libraries`` is **False** so that cross-package
    imports (e.g. ``from specify_cli import X`` inside charter) are
    visible in the dependency graph.  The mypy_cache directory is excluded
    to avoid polluting the graph with cached stubs.
    """
    return get_evaluable_architecture(
        root_path=str(SRC),
        module_path=str(SRC),
        exclude_external_libraries=False,
        exclusions=("*__pycache__*", "*mypy_cache*"),
    )


@pytest.fixture(scope="session")
def landscape():
    """2.x C4 landscape: kernel <- doctrine <- charter <- specify_cli.

    Each layer includes both the ``src.``-prefixed module path (local source)
    and the bare module name (as seen when the package is installed), so that
    imports resolved through either path are correctly attributed.
    """
    return (
        LayeredArchitecture()
        .layer("kernel")  # type: ignore[attr-defined]
        .containing_modules(["src.kernel", "kernel"])
        .layer("doctrine")
        .containing_modules(["src.doctrine", "doctrine"])
        .layer("charter")
        .containing_modules(["src.charter", "charter"])
        .layer("specify_cli")
        .containing_modules(["src.specify_cli", "specify_cli"])
    )
