"""Regression test for the #3677 dossier re-export trim (WP04).

Pins the removal of the seven ``spec_kitty_events`` type re-exports from
``specify_cli.dossier``'s public namespace. Before the trim (commit
``920678964``) these seven names were importable via ``specify_cli.dossier``
in addition to their canonical home in ``spec_kitty_events`` -- two import
paths for one type, violating the charter's single-canonical-authority
principle. After the trim (commit ``02ef48fc3``) only the canonical
``spec_kitty_events`` path remains.

This test guards against a future re-introduction of any of the seven
re-exports, and equally guards against an over-trim that accidentally
removes one of the four ``emit_*`` re-exports -- an over-trim there would
silently break WP02's widened dossier guard with no other test catching it.
(The original callers, ``sync/dossier_pipeline.py`` and
``dossier/drift_detector.py``, were themselves deleted as sync-transport
collateral -- issues #5 and #116 respectively -- but the re-export contract
remains load-bearing per C-002 regardless of who currently calls it.)
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# The seven type re-exports removed from specify_cli.dossier's public
# namespace by #3677 / WP04. These remain importable directly from
# spec_kitty_events -- the charter's declared canonical external contract
# package -- just no longer via specify_cli.dossier.
REMOVED_TYPE_REEXPORTS = (
    "ArtifactIdentity",
    "ContentHashRef",
    "LocalNamespaceTuple",
    "MissionDossierArtifactIndexedPayload",
    "MissionDossierArtifactMissingPayload",
    "MissionDossierSnapshotComputedPayload",
    "MissionDossierParityDriftDetectedPayload",
)

# The four emit_* function re-exports that MUST remain reachable via
# specify_cli.dossier -- C-002, untouched by this WP.
RETAINED_EMIT_REEXPORTS = (
    "emit_artifact_indexed",
    "emit_artifact_missing",
    "emit_snapshot_computed",
    "emit_parity_drift_detected",
)


@pytest.fixture()
def dossier_module():
    import specify_cli.dossier as dossier

    # Reload defensively in case an earlier test in the same process
    # mutated sys.modules state; this keeps the assertions honest against
    # the real, currently-installed module rather than a stale cache.
    return importlib.reload(dossier)


@pytest.mark.parametrize("name", REMOVED_TYPE_REEXPORTS)
def test_type_reexport_no_longer_reachable_as_attribute(dossier_module, name):
    """The seven type re-exports are gone from specify_cli.dossier's namespace."""
    assert not hasattr(dossier_module, name), (
        f"specify_cli.dossier still exposes {name!r}; expected it removed "
        "per #3677 (WP04 dossier re-export trim)."
    )


@pytest.mark.parametrize("name", REMOVED_TYPE_REEXPORTS)
def test_type_reexport_no_longer_importable_from(name):
    """A direct `from specify_cli.dossier import <name>` now fails.

    Runs the real import statement (not just an attribute-presence check)
    so the test reproduces exactly what a caller doing
    ``from specify_cli.dossier import ArtifactIdentity`` would hit.
    """
    with pytest.raises(ImportError):
        exec(f"from specify_cli.dossier import {name}")


@pytest.mark.parametrize("name", REMOVED_TYPE_REEXPORTS)
def test_type_reexport_absent_from_dunder_all(dossier_module, name):
    """The seven names are also gone from __all__, not just unreachable."""
    assert name not in dossier_module.__all__


@pytest.mark.parametrize("name", RETAINED_EMIT_REEXPORTS)
def test_emit_reexport_still_reachable_as_attribute(dossier_module, name):
    """The four emit_* re-exports are untouched by the trim (C-002)."""
    assert hasattr(dossier_module, name), (
        f"specify_cli.dossier no longer exposes {name!r}; the emit_* "
        "re-exports must survive the #3677 trim untouched (C-002)."
    )


@pytest.mark.parametrize("name", RETAINED_EMIT_REEXPORTS)
def test_emit_reexport_still_importable_from(name):
    """A direct `from specify_cli.dossier import <name>` still succeeds."""
    namespace: dict[str, object] = {}
    exec(f"from specify_cli.dossier import {name}", namespace)
    assert name in namespace


@pytest.mark.parametrize("name", RETAINED_EMIT_REEXPORTS)
def test_emit_reexport_still_present_in_dunder_all(dossier_module, name):
    """The four emit_* names remain listed in __all__."""
    assert name in dossier_module.__all__
