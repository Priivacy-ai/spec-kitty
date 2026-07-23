"""Snapshot computation and parity hash for mission dossiers.

This module provides deterministic snapshot computation from MissionDossier
objects, including order-independent parity hash calculation and persistence.

Key responsibilities:
- Compute deterministic snapshots (T023)
- Implement order-independent parity hash algorithm (T024)
- Persist and load snapshots (T025)
- Validate snapshot reproducibility (T026)
- Support snapshot equality comparison (T027)

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, UTC
from pathlib import Path

from specify_cli.core.paths import assert_safe_path_segment
from .hasher import compute_dossier_snapshot_hash
from .models import MissionDossier, MissionDossierSnapshot


def _artifact_field(artifact: object, key: str) -> object:
    """Read *key* from either an ArtifactRef object or a recorded summary dict."""
    if isinstance(artifact, Mapping):
        return artifact.get(key)
    return getattr(artifact, key, None)


def present_projection(artifacts: Iterable[object]) -> list[tuple[str, str | None]]:
    """Canonical ``(relative_path, content_hash)`` projection of PRESENT artifacts.

    Single source of the present-artifact filter used by BOTH the snapshot-hash
    producer and the reconciler's source/recorded projections, so they can never
    drift apart (#2883 item 2). An artifact contributes iff it is present with a
    non-empty content hash — the exact basis the recorded snapshot hash is built
    on. Accepts both :class:`ArtifactRef` objects and recorded summary dicts so
    the source (objects) and recorded (dicts) sides share one definition.
    """
    entries: list[tuple[str, str | None]] = []
    for artifact in artifacts:
        content_hash = _artifact_field(artifact, "content_hash_sha256")
        if _artifact_field(artifact, "is_present") and content_hash:
            relative_path = _artifact_field(artifact, "relative_path")
            entries.append((str(relative_path or ""), str(content_hash)))
    return entries


def compute_parity_hash_from_dossier(dossier: MissionDossier) -> str:
    """Compute the canonical dossier snapshot hash for a dossier (FR-008).

    Delegates to WP01's single canonical definition
    :func:`specify_cli.dossier.hasher.compute_dossier_snapshot_hash` over the
    ``(relative_path, content_hash)`` entries of the present artifacts. The
    canonical form is content-addressed, order-independent (sorted by path),
    and byte-identical to the SaaS server (cross-repo contract C-003). The
    prior concat-of-hashes / bare-hex form is retired (FR-003).

    Args:
        dossier: MissionDossier with indexed artifacts

    Returns:
        The canonical ``"sha256:<64-hex>"`` snapshot hash.
    """
    entries = present_projection(dossier.artifacts)
    # Explicit annotation: mypy's narrow-file override skips following the
    # specify_cli.* import graph, so the canonical function's declared ``str``
    # return would otherwise read as ``Any`` here.
    canonical_hash: str = compute_dossier_snapshot_hash(entries)
    return canonical_hash


def get_parity_hash_components(dossier: MissionDossier) -> list[str]:
    """Return sorted list of artifact hashes (for audit).

    Args:
        dossier: MissionDossier with indexed artifacts

    Returns:
        Sorted list of SHA256 hashes from present artifacts
    """
    present_hashes = [content_hash for _, content_hash in present_projection(dossier.artifacts) if content_hash]
    return sorted(present_hashes)


def compute_snapshot(dossier: MissionDossier) -> MissionDossierSnapshot:
    """Deterministically compute snapshot from dossier.

    Algorithm:
    1. Sort artifacts by artifact_key (deterministic ordering)
    2. Count artifacts by status (required/optional, present/missing)
    3. Compute completeness status (all required present? → complete)
    4. Compute the canonical parity hash (see compute_parity_hash_from_dossier)
    5. Return snapshot object

    Args:
        dossier: MissionDossier to snapshot

    Returns:
        MissionDossierSnapshot with all fields populated
    """
    # 1. Sort artifacts
    sorted_artifacts = sorted(dossier.artifacts, key=lambda a: a.artifact_key)

    # 2. Count artifacts
    required_artifacts = [a for a in sorted_artifacts if a.required_status == "required"]
    optional_artifacts = [a for a in sorted_artifacts if a.required_status == "optional"]
    required_present = sum(1 for a in required_artifacts if a.is_present)
    required_missing = len(required_artifacts) - required_present
    optional_present = sum(1 for a in optional_artifacts if a.is_present)

    # 3. Completeness status
    completeness_status = "unknown" if not dossier.manifest else "complete" if required_missing == 0 else "incomplete"

    # 4. Parity hash
    parity_hash = compute_parity_hash_from_dossier(dossier)

    # 5. Create snapshot
    return MissionDossierSnapshot(
        mission_slug=dossier.mission_slug,
        total_artifacts=len(sorted_artifacts),
        required_artifacts=len(required_artifacts),
        required_present=required_present,
        required_missing=required_missing,
        optional_artifacts=len(optional_artifacts),
        optional_present=optional_present,
        completeness_status=completeness_status,
        parity_hash_sha256=parity_hash,
        parity_hash_components=get_parity_hash_components(dossier),
        artifact_summaries=[
            {
                "artifact_key": a.artifact_key,
                "artifact_class": a.artifact_class,
                "relative_path": a.relative_path,
                "content_hash_sha256": a.content_hash_sha256,
                "size_bytes": a.size_bytes,
                "wp_id": a.wp_id,
                "step_id": a.step_id,
                "required_status": a.required_status,
                "is_present": a.is_present,
                "error_reason": a.error_reason,
                "indexed_at": a.indexed_at.isoformat() if a.indexed_at else None,
                "provenance": a.provenance,
            }
            for a in sorted_artifacts
        ],
        computed_at=datetime.now(UTC),
    )


def save_snapshot(snapshot: MissionDossierSnapshot, feature_dir: Path) -> None:
    """Persist snapshot to JSON file.

    File location: {feature_dir}/.kittify/dossiers/{mission_slug}/snapshot-latest.json

    Args:
        snapshot: MissionDossierSnapshot to persist
        feature_dir: Root directory of feature (Path object)
    """
    # FR-001: validate snapshot.mission_slug before joining into a FS path (traversal guard).
    _safe_slug = assert_safe_path_segment(snapshot.mission_slug)
    dossier_dir = feature_dir / ".kittify" / "dossiers" / _safe_slug
    dossier_dir.mkdir(parents=True, exist_ok=True)

    snapshot_file = dossier_dir / "snapshot-latest.json"
    with open(snapshot_file, "w") as f:
        json.dump(snapshot.model_dump(), f, indent=2, default=str)


def load_snapshot(feature_dir: Path, mission_slug: str) -> MissionDossierSnapshot | None:
    """Load snapshot from JSON file.

    Args:
        feature_dir: Root directory of feature (Path object)
        mission_slug: Feature identifier

    Returns:
        MissionDossierSnapshot or None if not found
    """
    # FR-001: validate mission_slug before joining into a FS path (traversal guard).
    _safe_slug = assert_safe_path_segment(mission_slug)
    snapshot_file = feature_dir / ".kittify" / "dossiers" / _safe_slug / "snapshot-latest.json"
    if not snapshot_file.exists():
        return None

    with open(snapshot_file) as f:
        data = json.load(f)
    return MissionDossierSnapshot(**data)


def get_latest_snapshot(feature_dir: Path, mission_slug: str) -> MissionDossierSnapshot | None:
    """Get most recent snapshot (convenience alias).

    Args:
        feature_dir: Root directory of feature (Path object)
        mission_slug: Feature identifier

    Returns:
        MissionDossierSnapshot or None if not found
    """
    return load_snapshot(feature_dir, mission_slug)
