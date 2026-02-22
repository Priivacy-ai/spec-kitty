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

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import MissionDossier, MissionDossierSnapshot


def compute_parity_hash_from_dossier(dossier: MissionDossier) -> str:
    """Compute SHA256 parity hash from artifact content hashes.

    Algorithm (order-independent):
    1. Extract content_hash_sha256 from all artifacts (skip missing/unreadable)
    2. Sort hashes lexicographically
    3. Concatenate sorted hashes
    4. Compute SHA256 of concatenation
    5. Return hex string

    Args:
        dossier: MissionDossier with indexed artifacts

    Returns:
        Hex string of SHA256 parity hash (64 characters)
    """
    # 1. Extract hashes from present artifacts only
    present_hashes = [
        a.content_hash_sha256
        for a in dossier.artifacts
        if a.is_present and a.content_hash_sha256
    ]

    # 2. Sort lexicographically
    sorted_hashes = sorted(present_hashes)

    # 3. Concatenate
    combined = "".join(sorted_hashes)

    # 4. Hash
    parity_hash = hashlib.sha256(combined.encode()).hexdigest()

    return parity_hash


def get_parity_hash_components(dossier: MissionDossier) -> List[str]:
    """Return sorted list of artifact hashes (for audit).

    Args:
        dossier: MissionDossier with indexed artifacts

    Returns:
        Sorted list of SHA256 hashes from present artifacts
    """
    present_hashes = [
        a.content_hash_sha256
        for a in dossier.artifacts
        if a.is_present and a.content_hash_sha256
    ]
    return sorted(present_hashes)


def compute_snapshot(dossier: MissionDossier) -> MissionDossierSnapshot:
    """Deterministically compute snapshot from dossier.

    Algorithm:
    1. Sort artifacts by artifact_key (deterministic ordering)
    2. Count artifacts by status (required/optional, present/missing)
    3. Compute completeness status (all required present? → complete)
    4. Compute parity hash (sorted artifact hashes, combined hash)
    5. Return snapshot object

    Args:
        dossier: MissionDossier to snapshot

    Returns:
        MissionDossierSnapshot with all fields populated
    """
    # 1. Sort artifacts
    sorted_artifacts = sorted(dossier.artifacts, key=lambda a: a.artifact_key)

    # 2. Count artifacts
    required_artifacts = [
        a for a in sorted_artifacts if a.required_status == "required"
    ]
    optional_artifacts = [
        a for a in sorted_artifacts if a.required_status == "optional"
    ]
    required_present = sum(1 for a in required_artifacts if a.is_present)
    required_missing = len(required_artifacts) - required_present
    optional_present = sum(1 for a in optional_artifacts if a.is_present)

    # 3. Completeness status
    if not dossier.manifest:
        completeness_status = "unknown"
    else:
        completeness_status = "complete" if required_missing == 0 else "incomplete"

    # 4. Parity hash
    parity_hash = compute_parity_hash_from_dossier(dossier)

    # 5. Create snapshot
    return MissionDossierSnapshot(
        feature_slug=dossier.feature_slug,
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
        computed_at=datetime.utcnow(),
    )


def save_snapshot(snapshot: MissionDossierSnapshot, feature_dir: Path) -> None:
    """Persist snapshot to JSON file.

    File location: {feature_dir}/.kittify/dossiers/{feature_slug}/snapshot-latest.json

    Args:
        snapshot: MissionDossierSnapshot to persist
        feature_dir: Root directory of feature (Path object)
    """
    dossier_dir = feature_dir / ".kittify" / "dossiers" / snapshot.feature_slug
    dossier_dir.mkdir(parents=True, exist_ok=True)

    snapshot_file = dossier_dir / "snapshot-latest.json"
    with open(snapshot_file, "w") as f:
        json.dump(snapshot.dict(), f, indent=2, default=str)


def load_snapshot(
    feature_dir: Path, feature_slug: str
) -> Optional[MissionDossierSnapshot]:
    """Load snapshot from JSON file.

    Args:
        feature_dir: Root directory of feature (Path object)
        feature_slug: Feature identifier

    Returns:
        MissionDossierSnapshot or None if not found
    """
    snapshot_file = (
        feature_dir / ".kittify" / "dossiers" / feature_slug / "snapshot-latest.json"
    )
    if not snapshot_file.exists():
        return None

    with open(snapshot_file) as f:
        data = json.load(f)
    return MissionDossierSnapshot(**data)


def get_latest_snapshot(
    feature_dir: Path, feature_slug: str
) -> Optional[MissionDossierSnapshot]:
    """Get most recent snapshot (convenience alias).

    Args:
        feature_dir: Root directory of feature (Path object)
        feature_slug: Feature identifier

    Returns:
        MissionDossierSnapshot or None if not found
    """
    return load_snapshot(feature_dir, feature_slug)
