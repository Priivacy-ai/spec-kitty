"""Consumer contract for spec-kitty-tracker.

Pins the subset of the tracker public surface that CLI uses. Upstream
contract changes (renaming or removing pinned symbols, or shifting their
shape) MUST break this test, per FR-005 / FR-009 / C-003 of mission
``shared-package-boundary-cutover-01KQ22DS``.

The pinned surface is documented in
``kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/tracker_consumer_surface.md``.

The pin list was derived by grep over ``src/`` on the post-WP02 tree:

* ``from spec_kitty_tracker import FieldOwner, OwnershipMode, OwnershipPolicy, SyncEngine``
* ``from spec_kitty_tracker.models import ExternalRef``

CLI's tracker integration (``src/specify_cli/tracker/*``) is the consumer;
``specify_cli.tracker`` is the CLI-internal adapter package and MUST NOT
re-export the public PyPI surface (C-003 — enforced by the architectural
suite, not by this contract).

If future CLI work uses additional tracker symbols, update both the
contract doc and this test in the same PR.
"""
from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Top-level package surface (``import spec_kitty_tracker as X``)
# ---------------------------------------------------------------------------

_TOP_LEVEL_SYMBOLS = (
    "FieldOwner",
    "OwnershipMode",
    "OwnershipPolicy",
    "SyncEngine",
)


@pytest.mark.parametrize("symbol_name", _TOP_LEVEL_SYMBOLS)
def test_top_level_symbol_exists(symbol_name: str) -> None:
    """FR-009: Each pinned top-level tracker symbol must resolve."""
    module = importlib.import_module("spec_kitty_tracker")
    assert hasattr(module, symbol_name), (
        f"spec_kitty_tracker.{symbol_name} is missing. "
        f"This breaks CLI imports in mission "
        f"shared-package-boundary-cutover-01KQ22DS. "
        f"Update the consumer contract (and "
        f"contracts/tracker_consumer_surface.md) or fix upstream."
    )


# ---------------------------------------------------------------------------
# spec_kitty_tracker.models
# ---------------------------------------------------------------------------

_MODELS_SYMBOLS = (
    "ExternalRef",
)


@pytest.mark.parametrize("symbol_name", _MODELS_SYMBOLS)
def test_models_symbol_exists(symbol_name: str) -> None:
    """FR-009: Each pinned ``spec_kitty_tracker.models`` symbol must resolve."""
    module = importlib.import_module("spec_kitty_tracker.models")
    assert hasattr(module, symbol_name), (
        f"spec_kitty_tracker.models.{symbol_name} is missing in "
        f"spec-kitty-tracker. Update the consumer contract or fix the "
        f"upstream surface."
    )


# ---------------------------------------------------------------------------
# Structural shape (matches CLI's actual usage shape)
# ---------------------------------------------------------------------------


def test_ownership_mode_is_enum_like() -> None:
    """``OwnershipMode`` must expose an enum-like surface.

    CLI reads named ownership modes; an enum (or enum-like object with
    ``__members__`` mapping or class-level constants) is the canonical
    shape. If upstream ever swaps to a plain class, this test fires.
    """
    from spec_kitty_tracker import OwnershipMode

    has_members = hasattr(OwnershipMode, "__members__")
    has_class_callable = callable(getattr(OwnershipMode, "__class__", None))
    assert has_members or has_class_callable, (
        "spec_kitty_tracker.OwnershipMode no longer exposes an enum-like "
        "interface. CLI's tracker integration relies on this surface."
    )


def test_field_owner_class_exists() -> None:
    """``FieldOwner`` must be a class (CLI instantiates / type-hints it)."""
    from spec_kitty_tracker import FieldOwner

    assert isinstance(FieldOwner, type), (
        f"spec_kitty_tracker.FieldOwner is not a class (got {type(FieldOwner)}). "
        "CLI's tracker integration relies on FieldOwner being a class."
    )


def test_sync_engine_class_exists() -> None:
    """``SyncEngine`` must be a class (CLI instantiates it)."""
    from spec_kitty_tracker import SyncEngine

    assert isinstance(SyncEngine, type), (
        f"spec_kitty_tracker.SyncEngine is not a class (got {type(SyncEngine)}). "
        "CLI's tracker integration relies on SyncEngine being a class."
    )
