"""Equality regression proving the missions-root hardcode consolidation (FR-004).

Mission ``charter-sole-door-bypass-closure-01KZ3WAA`` / WP06. Before this WP,
3 sites independently constructed the shipped ``src/doctrine/missions`` root:

1. ``charter.mission_type_profile_repository.builtin_missions_root()`` — a
   ``Path(__file__).resolve().parents[1] / "doctrine" / "missions"`` literal.
2. ``specify_cli.runtime.home.get_package_asset_root()``'s ``dev_roots``
   fallback tuple — a ``Path(__file__).parents[2] / "doctrine" / "missions"``
   literal.
3. ``doctrine.missions.repository.MissionTemplateRepository.default_missions_root()``
   — the ``importlib.resources``-based, wheel-safe implementation.

WP06 retargets (1) and (2) onto (3) as the ONE promoted authority, per
plan.md's Project Structure notes. ``builtin_missions_root()`` becomes a thin
delegate (not a second co-equal authority); ``home.py``'s ``dev_roots``
fallback calls the same authority.

Full convergence onto ``doctrine.pack_paths.built_in_missions_root`` was
completed by issue #3575: ``builtin_missions_root()`` now delegates straight
to :func:`~doctrine.pack_paths.built_in_missions_root` (the single canonical
source), rather than hopping through
:meth:`~doctrine.missions.repository.MissionTemplateRepository.default_missions_root`.
The equivalence assertions below still hold because
``default_missions_root()`` is itself a thin wrapper over the same
``pack_paths`` call (plus an existence check that ``builtin_missions_root()``
does not replicate — see its docstring for that behaviour note).
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest

from charter.mission_type_profile_repository import builtin_missions_root
from doctrine.missions.repository import MissionTemplateRepository
from doctrine.pack_paths import built_in_missions_root as pack_paths_built_in_missions_root
from specify_cli.runtime import home as home_module

pytestmark = [pytest.mark.unit]


def test_builtin_missions_root_matches_promoted_authority() -> None:
    """T022: ``builtin_missions_root()`` is a thin delegate, not a rival authority."""
    assert builtin_missions_root() == MissionTemplateRepository.default_missions_root()


def test_builtin_missions_root_delegates_directly_to_pack_paths() -> None:
    """#3575: ``builtin_missions_root()`` now converges directly onto
    ``pack_paths.built_in_missions_root()`` — the single canonical missions-root
    authority — rather than hopping through ``default_missions_root()``.
    """
    root = builtin_missions_root()

    assert root == pack_paths_built_in_missions_root()
    assert root.is_dir(), (
        "sanity: the canonical authority must resolve to the real built-in "
        "missions directory in this editable-install test environment"
    )


def test_home_dev_roots_fallback_matches_promoted_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T023: ``home.py``'s ``dev_roots`` fallback resolves to the promoted authority.

    Forces the earlier resolution steps (the ``SPEC_KITTY_TEMPLATE_ROOT`` env
    override and the ``importlib.resources`` probe) to miss, so the
    caller-visible ``get_package_asset_root()`` return value is answered by
    the retargeted ``dev_roots`` entry itself — not merely a private helper
    that happens to agree with it.
    """
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)

    def _raise_module_not_found(_package: str) -> Path:
        raise ModuleNotFoundError("forced miss: exercise the dev_roots fallback")

    # Patches the SAME ``importlib.resources`` module object ``home.py``
    # imports and calls internally (module singletons in ``sys.modules``),
    # without reaching through ``home_module`` for an attribute it does not
    # re-export.
    monkeypatch.setattr(importlib.resources, "files", _raise_module_not_found)

    promoted_root = MissionTemplateRepository.default_missions_root()
    assert promoted_root.is_dir(), (
        "sanity: the promoted authority must resolve to a real directory in "
        "this editable-install test environment for the fallback comparison "
        "to be meaningful"
    )

    assert home_module.get_package_asset_root() == promoted_root


def test_home_dev_roots_tuple_first_entry_is_the_promoted_authority() -> None:
    """Direct unit pin: ``home.py`` delegates to the single resolution authority.

    Complements the behavioral test above with a structural check that
    ``home.py`` reconstructs nothing itself. Updated for mission
    ``resolution-activation-foundation`` WP01 (DR-1/DR-2): ``home.py`` collapsed
    from a second resolver (which called
    ``MissionTemplateRepository.default_missions_root()`` inside its own
    ``dev_roots`` fallback) into a thin delegate to the ONE canonical door,
    ``kernel.paths.get_package_asset_root()``. The old
    ``Path(__file__).parents[2] / "doctrine" / "missions"`` literal stays gone;
    the doctrine-repository call it once carried is now equally gone -- home
    no longer reaches doctrine at all, it delegates to the kernel authority.
    """
    source = Path(home_module.__file__).read_text(encoding="utf-8")
    assert 'Path(__file__).parents[2] / "doctrine" / "missions"' not in source
    assert "kernel.paths.get_package_asset_root()" in source
