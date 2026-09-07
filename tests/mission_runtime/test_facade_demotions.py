"""Residue pins for the ``mission_runtime`` / ``kernel.paths`` public surfaces.

Mission ``dead-port-disposition-01M1TZVN`` WP03 (FR-014, contract
``contracts/residue-and-emitter-shrunk.md`` §1 R-3 / R-4):

* R-3 -- the transitional ``ActionContext`` alias of
  :class:`mission_runtime.MissionExecutionContext` is deleted from both files
  that carried it (``context.py`` and the package ``__getattr__`` compat shim).
* R-4 -- the thirteen test-only ``__all__`` exports are **demoted**, never
  deleted: they leave the package-root ``__all__`` (and the facade re-export
  that existed only for it) but stay importable from their defining module,
  because each still has an in-package caller.

The tests assert both halves of "demote": the name is gone from the public
surface AND the symbol is still reachable by module path.
"""

from __future__ import annotations

import importlib

import pytest

import kernel.paths
import mission_runtime
import mission_runtime.context
import mission_runtime.lifecycle_phase

pytestmark = pytest.mark.fast

#: The eleven ``mission_runtime`` facade names with no ``src/`` importer
#: outside the package (name -> defining submodule).
_DEMOTED_FACADE_EXPORTS: dict[str, str] = {
    "ArtifactPlacementFragment": "mission_runtime.context",
    "BranchRefFragment": "mission_runtime.context",
    "IdentityFragment": "mission_runtime.context",
    "MissionArtifactContext": "mission_runtime.context",
    "MissionArtifactHome": "mission_runtime.artifacts",
    "ResolvedSurface": "mission_runtime.resolution",
    "StatusSurfaceFragment": "mission_runtime.context",
    "SurfaceLocations": "mission_runtime.resolution",
    "WorkspaceFragment": "mission_runtime.context",
    "artifact_home_for": "mission_runtime.artifacts",
    "translate_surface": "mission_runtime.resolution",
}


class TestActionContextAliasDeleted:
    """R-3: the alias is gone from ``context.py`` and from the compat shim."""

    def test_alias_absent_from_context_module(self) -> None:
        assert "ActionContext" not in mission_runtime.context.__all__
        assert not hasattr(mission_runtime.context, "ActionContext")

    def test_alias_absent_from_package_compat_shim(self) -> None:
        with pytest.raises(AttributeError):
            _ = mission_runtime.ActionContext

    def test_canonical_name_still_public(self) -> None:
        assert "MissionExecutionContext" in mission_runtime.__all__
        assert mission_runtime.MissionExecutionContext is mission_runtime.context.MissionExecutionContext


class TestFacadeExportsDemoted:
    """R-4 (mission_runtime half): out of ``__all__``, still importable by module path."""

    @pytest.mark.parametrize("name", sorted(_DEMOTED_FACADE_EXPORTS))
    def test_name_left_package_root_surface(self, name: str) -> None:
        assert name not in mission_runtime.__all__
        assert name not in vars(mission_runtime), f"{name} is still re-exported by mission_runtime/__init__.py"

    @pytest.mark.parametrize(("name", "module"), sorted(_DEMOTED_FACADE_EXPORTS.items()))
    def test_symbol_survives_at_defining_module(self, name: str, module: str) -> None:
        # Reachability by module path is the whole "keep the symbol" half.
        # Submodule ``__all__`` membership is deliberately NOT asserted: the
        # dead-symbol gate reads ``__all__`` as a cross-module export claim, so
        # a name with no importer outside its module leaves that list too
        # (``resolution.ResolvedSurface`` / ``SurfaceLocations`` /
        # ``translate_surface``) while staying a live in-module symbol.
        defining = importlib.import_module(module)
        assert hasattr(defining, name), f"{module} no longer defines {name}: demotion must not delete"


class TestModuleLevelExportsDemoted:
    """R-4 (the two module-level names with in-package callers)."""

    def test_content_present_at_primary_tip_demoted_not_deleted(self) -> None:
        assert "content_present_at_primary_tip" not in mission_runtime.lifecycle_phase.__all__
        assert callable(mission_runtime.lifecycle_phase.content_present_at_primary_tip)

    def test_get_packs_root_default_demoted_not_deleted(self) -> None:
        assert "get_packs_root_default" not in kernel.paths.__all__
        assert callable(kernel.paths.get_packs_root_default)
