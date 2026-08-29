"""C-001 relocation characterization: expected-artifact manifest schema (#3599).

Mission rc3-charter-gate-predicate-inversion-01M0GGT1, WP04: relocates
``ArtifactClassEnum`` / ``ExpectedArtifactSpec`` / ``ExpectedArtifactManifest``
from ``specify_cli.dossier.manifest`` into
``charter.offering.missions.expected_artifact_manifest`` (charter ⊥ specify_cli --
these are pure pydantic data models with no ``specify_cli`` dependency, so
doctrine, not a ``specify_cli`` subpackage, is their correct home).

These tests are the load-bearing proof that the relocation is real (not a
type-only shim that ``NameError``s at runtime): they exercise
``ManifestRegistry.load_manifest`` -- the actual RUNTIME
``ExpectedArtifactManifest.model_validate(...)`` call site -- not merely the
import statement. A ``TYPE_CHECKING``-only import would pass every static
check here and still blow up the moment ``load_manifest`` is called; this
file specifically prevents that regression.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


class TestNewHomeImports:
    """The relocated names resolve from their new doctrine-layer home."""

    def test_imports_from_doctrine_missions_package(self) -> None:
        from charter.offering.missions import (
            ArtifactClassEnum,
            ExpectedArtifactManifest,
            ExpectedArtifactSpec,
        )

        assert ArtifactClassEnum.INPUT.value == "input"
        assert ExpectedArtifactSpec is not None
        assert ExpectedArtifactManifest is not None

    def test_imports_from_expected_artifact_manifest_module_directly(self) -> None:
        from charter.offering.missions.expected_artifact_manifest import (
            ArtifactClassEnum,
            ExpectedArtifactManifest,
            ExpectedArtifactSpec,
        )

        assert ArtifactClassEnum.OUTPUT.value == "output"
        assert ExpectedArtifactSpec is not None
        assert ExpectedArtifactManifest is not None

    def test_new_module_declares_its_own_all(self) -> None:
        """C-007: the new module carries its own ``__all__``."""
        import charter.offering.missions.expected_artifact_manifest as eam

        assert set(eam.__all__) == {
            "ArtifactClassEnum",
            "ExpectedArtifactManifest",
            "ExpectedArtifactSpec",
        }

    def test_doctrine_missions_public_surface_enrolls_the_three_names(self) -> None:
        """The doctrine public surface (``doctrine/missions/__init__.py``) enrolls all three."""
        import charter.offering.missions as dm

        for name in ("ArtifactClassEnum", "ExpectedArtifactManifest", "ExpectedArtifactSpec"):
            assert name in dm.__all__, f"{name} missing from charter.offering.missions.__all__"
            assert hasattr(dm, name)


class TestLegacyImportStillResolvesAtRuntime:
    """The pre-relocation import path keeps working -- lazily, at runtime.

    Not a TYPE_CHECKING-only shim: these assertions run the actual import
    statement and use the resulting object, so a NameError-at-runtime
    regression (the two-traps warning) would fail loudly here.
    """

    def test_legacy_from_import_resolves(self) -> None:
        from specify_cli.dossier.manifest import (
            ArtifactClassEnum,
            ExpectedArtifactManifest,
            ExpectedArtifactSpec,
        )

        assert ArtifactClassEnum.EVIDENCE.value == "evidence"
        assert ExpectedArtifactSpec is not None
        assert ExpectedArtifactManifest is not None

    def test_legacy_import_is_the_same_object_as_the_new_home(self) -> None:
        """Object identity preserved -- not a re-implemented duplicate."""
        from charter.offering.missions import (
            ArtifactClassEnum as NewArtifactClassEnum,
            ExpectedArtifactManifest as NewExpectedArtifactManifest,
            ExpectedArtifactSpec as NewExpectedArtifactSpec,
        )
        from specify_cli.dossier.manifest import (
            ArtifactClassEnum as LegacyArtifactClassEnum,
            ExpectedArtifactManifest as LegacyExpectedArtifactManifest,
            ExpectedArtifactSpec as LegacyExpectedArtifactSpec,
        )

        assert LegacyArtifactClassEnum is NewArtifactClassEnum
        assert LegacyExpectedArtifactSpec is NewExpectedArtifactSpec
        assert LegacyExpectedArtifactManifest is NewExpectedArtifactManifest

    def test_legacy_module_attribute_access_resolves(self) -> None:
        """Attribute access (not just ``from ... import``) triggers the PEP 562 hook too."""
        import specify_cli.dossier.manifest as manifest_module

        assert manifest_module.ExpectedArtifactManifest is not None
        assert manifest_module.ExpectedArtifactSpec is not None
        assert manifest_module.ArtifactClassEnum is not None

    def test_unrelated_attribute_still_raises_attribute_error(self) -> None:
        """The PEP 562 hook is narrowly scoped -- it must not swallow real typos."""
        import specify_cli.dossier.manifest as manifest_module

        with pytest.raises(AttributeError):
            manifest_module.ThisNameDoesNotExist  # noqa: B018 -- deliberate attribute-error probe


class TestRuntimeLoadManifestPathExercised:
    """The RUNTIME ``load_manifest`` -> ``model_validate`` call site, not just types.

    This is the specific trap the WP04 contract calls out: a
    TYPE_CHECKING-only import would pass every static/import-time check
    above and still NameError here, the first time ``load_manifest``
    actually runs ``ExpectedArtifactManifest.model_validate(...)``.
    """

    def test_load_manifest_returns_a_relocated_manifest_instance(self) -> None:
        from charter.offering.missions import ExpectedArtifactManifest
        from specify_cli.dossier.manifest import ManifestRegistry

        ManifestRegistry.clear_cache()
        manifest = ManifestRegistry.load_manifest("software-dev")

        assert manifest is not None
        assert isinstance(manifest, ExpectedArtifactManifest)
        assert manifest.mission_type == "software-dev"
        assert manifest.get_step_ids()

    def test_load_manifest_second_call_hits_cache_with_same_relocated_type(self) -> None:
        """Cache path (no re-parse) still yields the relocated type -- not a stale copy."""
        from charter.offering.missions import ExpectedArtifactManifest
        from specify_cli.dossier.manifest import ManifestRegistry

        ManifestRegistry.clear_cache()
        first = ManifestRegistry.load_manifest("research")
        second = ManifestRegistry.load_manifest("research")

        assert first is second
        assert isinstance(second, ExpectedArtifactManifest)
