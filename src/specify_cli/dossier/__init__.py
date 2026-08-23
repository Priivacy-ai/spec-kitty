"""Mission dossier system for artifact indexing, classification, and parity detection."""

from .models import ArtifactRef, MissionDossier, MissionDossierSnapshot
from .hasher import (
    WP_STATIC_PROJECTION_FIELDS,
    compute_dossier_snapshot_hash,
    hash_file,
    hash_file_with_validation,
    hash_wp_static_projection,
    wp_static_projection,
)
# C-001 relocation (WP04 / #3599): the manifest schema types now live in
# doctrine.missions.expected_artifact_manifest -- re-exported from their new
# home (specify_cli -> doctrine is a legal direction). ManifestRegistry
# stays specify_cli-owned and keeps importing from .manifest. The explicit
# ``as <name>`` self-aliases are the standard PEP 484 explicit-re-export
# marker (ruff/mypy both honor it) -- these three are deliberately NOT in
# __all__ below: no other src/ file imports them via this package path
# (indexer.py now goes straight to doctrine.missions), and adding them to
# __all__ without such a caller reds tests/architectural/test_no_dead_symbols.py.
# The attribute is still importable for any external caller of this package.
from charter.missions import (
    ArtifactClassEnum as ArtifactClassEnum,
    ExpectedArtifactManifest as ExpectedArtifactManifest,
    ExpectedArtifactSpec as ExpectedArtifactSpec,
)
from .manifest import ManifestRegistry
from .events import (
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_snapshot_computed,
    emit_parity_drift_detected,
)
from .snapshot import (
    compute_snapshot,
    compute_parity_hash_from_dossier,
    get_parity_hash_components,
    save_snapshot,
    load_snapshot,
    get_latest_snapshot,
)

__all__ = [
    "ArtifactRef",
    "MissionDossier",
    "MissionDossierSnapshot",
    "hash_file",
    "hash_file_with_validation",
    "compute_dossier_snapshot_hash",
    "wp_static_projection",
    "hash_wp_static_projection",
    "WP_STATIC_PROJECTION_FIELDS",
    "ManifestRegistry",
    "emit_artifact_indexed",
    "emit_artifact_missing",
    "emit_snapshot_computed",
    "emit_parity_drift_detected",
    "compute_snapshot",
    "compute_parity_hash_from_dossier",
    "get_parity_hash_components",
    "save_snapshot",
    "load_snapshot",
    "get_latest_snapshot",
]
