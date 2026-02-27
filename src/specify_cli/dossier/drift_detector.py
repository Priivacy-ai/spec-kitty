"""Local parity-drift detection for mission dossiers.

This module implements baseline management and drift detection, enabling
offline detection of unintended content changes. Baseline keys are fully
namespaced (project, node, feature, branch, mission, manifest) to prevent
false positives in multi-feature, multi-branch, multi-user scenarios.

Key Functions:
- compute_baseline_key(): Create unique baseline identity tuple
- save_baseline() / load_baseline(): Persistence to JSON file
- accept_baseline(): Validate baseline key matches current context
- detect_drift(): Compare current snapshot hash vs cached baseline
- emit_drift_if_detected(): Detect drift and emit event
- capture_baseline(): Capture new baseline when accepted

See: kitty-specs/042-local-mission-dossier-authority-parity-export/tasks/WP08-parity-detection.md
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from specify_cli.dossier.events import emit_parity_drift_detected
from specify_cli.dossier.models import MissionDossierSnapshot
from specify_cli.sync.project_identity import ProjectIdentity

logger = logging.getLogger(__name__)


@dataclass
class BaselineKey:
    """Unique identifier for baseline scope (prevent false positives).

    A fully namespaced identity tuple that uniquely identifies the baseline scope,
    ensuring that different projects, nodes, features, branches, missions, and
    manifest versions each have independent baselines.

    Attributes:
        project_uuid: Project identifier (from sync/project_identity.py)
        node_id: Machine ID (from sync/project_identity.py)
        feature_slug: Feature identifier (e.g., "042-local-mission-dossier")
        target_branch: Target branch (e.g., "main", "2.x")
        mission_key: Mission type (e.g., "software-dev")
        manifest_version: Manifest schema version (e.g., "1")
    """

    project_uuid: str
    node_id: str
    feature_slug: str
    target_branch: str
    mission_key: str
    manifest_version: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all 6 baseline key components.
        """
        return {
            "project_uuid": self.project_uuid,
            "node_id": self.node_id,
            "feature_slug": self.feature_slug,
            "target_branch": self.target_branch,
            "mission_key": self.mission_key,
            "manifest_version": self.manifest_version,
        }

    def compute_hash(self) -> str:
        """Compute SHA256 hash of baseline key.

        Hash is deterministic and order-independent (uses sorted JSON keys)
        for use in file-safe comparisons.

        Returns:
            64-character SHA256 hash in hex format.
        """
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def __eq__(self, other: object) -> bool:
        """Check equality with another BaselineKey.

        Args:
            other: Object to compare with.

        Returns:
            True if all 6 components match.
        """
        if not isinstance(other, BaselineKey):
            return False
        return (
            self.project_uuid == other.project_uuid
            and self.node_id == other.node_id
            and self.feature_slug == other.feature_slug
            and self.target_branch == other.target_branch
            and self.mission_key == other.mission_key
            and self.manifest_version == other.manifest_version
        )

    def __hash__(self) -> int:
        """Hash for use in sets/dicts.

        Returns:
            Hash of the baseline key hash.
        """
        return hash(self.compute_hash())


@dataclass
class BaselineSnapshot:
    """Cached baseline with metadata.

    Immutable snapshot of a baseline at the time it was captured, including
    the key, parity hash, and metadata about when/who captured it.

    Attributes:
        baseline_key: The BaselineKey identifying this baseline
        baseline_key_hash: SHA256 hash of baseline_key
        parity_hash_sha256: Snapshot parity hash at baseline capture
        captured_at: When baseline was captured (UTC)
        captured_by: node_id that captured this baseline
    """

    baseline_key: BaselineKey
    baseline_key_hash: str
    parity_hash_sha256: str
    captured_at: datetime
    captured_by: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all fields (datetime as ISO string).
        """
        return {
            "baseline_key": self.baseline_key.to_dict(),
            "baseline_key_hash": self.baseline_key_hash,
            "parity_hash_sha256": self.parity_hash_sha256,
            "captured_at": self.captured_at.isoformat(),
            "captured_by": self.captured_by,
        }

    @staticmethod
    def from_dict(data: dict) -> BaselineSnapshot:
        """Create from dictionary (loaded from JSON).

        Args:
            data: Dictionary with baseline fields.

        Returns:
            New BaselineSnapshot instance.
        """
        return BaselineSnapshot(
            baseline_key=BaselineKey(**data["baseline_key"]),
            baseline_key_hash=data["baseline_key_hash"],
            parity_hash_sha256=data["parity_hash_sha256"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
            captured_by=data["captured_by"],
        )


def compute_baseline_key(
    feature_slug: str,
    target_branch: str,
    mission_key: str,
    manifest_version: str,
    project_identity: ProjectIdentity,
) -> BaselineKey:
    """Compute baseline key from current context.

    Creates a fully namespaced identity tuple that uniquely identifies
    the baseline scope.

    Args:
        feature_slug: Feature identifier (e.g., "042-local-mission-dossier")
        target_branch: Target branch (e.g., "main", "2.x")
        mission_key: Mission type (e.g., "software-dev")
        manifest_version: Manifest schema version (e.g., "1")
        project_identity: ProjectIdentity with project_uuid and node_id

    Returns:
        BaselineKey with all 6 components populated.
    """
    return BaselineKey(
        project_uuid=str(project_identity.project_uuid),
        node_id=project_identity.node_id or "unknown",
        feature_slug=feature_slug,
        target_branch=target_branch,
        mission_key=mission_key,
        manifest_version=manifest_version,
    )


def save_baseline(
    feature_slug: str, baseline: BaselineSnapshot, repo_root: Path
) -> None:
    """Persist baseline to JSON file.

    File location: {repo_root}/.kittify/dossiers/{feature_slug}/parity-baseline.json

    Args:
        feature_slug: Feature identifier
        baseline: BaselineSnapshot to persist
        repo_root: Repository root path
    """
    baseline_dir = repo_root / ".kittify" / "dossiers" / feature_slug
    baseline_dir.mkdir(parents=True, exist_ok=True)

    baseline_file = baseline_dir / "parity-baseline.json"
    with open(baseline_file, "w") as f:
        json.dump(baseline.to_dict(), f, indent=2)

    logger.info(f"Baseline saved to {baseline_file}")


def load_baseline(
    feature_slug: str, repo_root: Path
) -> Optional[BaselineSnapshot]:
    """Load baseline from JSON file.

    File location: {repo_root}/.kittify/dossiers/{feature_slug}/parity-baseline.json

    Args:
        feature_slug: Feature identifier
        repo_root: Repository root path

    Returns:
        BaselineSnapshot if file exists and is valid, None otherwise.
    """
    baseline_file = repo_root / ".kittify" / "dossiers" / feature_slug / "parity-baseline.json"
    if not baseline_file.exists():
        logger.debug(f"No baseline file found at {baseline_file}")
        return None

    try:
        with open(baseline_file) as f:
            data = json.load(f)
        return BaselineSnapshot.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to load baseline from {baseline_file}: {e}")
        return None


def accept_baseline(
    loaded_baseline: BaselineSnapshot,
    current_key: BaselineKey,
    strict: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Check if loaded baseline matches current context.

    Validates that the baseline was captured for the same project, node, feature,
    branch, mission, and manifest version. If any component differs, the baseline
    is rejected and treated as "no baseline".

    Args:
        loaded_baseline: Baseline loaded from file
        current_key: Computed baseline key for current context
        strict: If True, exact match required (default True)

    Returns:
        Tuple of (is_accepted, reason):
            - (True, None): Baseline accepted, safe to compare hashes
            - (False, reason): Baseline rejected, treat as "no baseline"
    """
    if strict:
        # Exact match: all components must match
        if loaded_baseline.baseline_key != current_key:
            # Detailed comparison to find which components differ
            diffs = []
            if (
                loaded_baseline.baseline_key.project_uuid
                != current_key.project_uuid
            ):
                diffs.append("project_uuid")
            if loaded_baseline.baseline_key.node_id != current_key.node_id:
                diffs.append("node_id")
            if (
                loaded_baseline.baseline_key.feature_slug
                != current_key.feature_slug
            ):
                diffs.append("feature_slug")
            if (
                loaded_baseline.baseline_key.target_branch
                != current_key.target_branch
            ):
                diffs.append("target_branch")
            if (
                loaded_baseline.baseline_key.mission_key
                != current_key.mission_key
            ):
                diffs.append("mission_key")
            if (
                loaded_baseline.baseline_key.manifest_version
                != current_key.manifest_version
            ):
                diffs.append("manifest_version")

            reason = f"Baseline key mismatch: {', '.join(diffs)}"
            return False, reason

    # Accepted
    return True, None


def detect_drift(
    feature_slug: str,
    current_snapshot: MissionDossierSnapshot,
    repo_root: Path,
    project_identity: ProjectIdentity,
    target_branch: str,
    mission_key: str,
    manifest_version: str,
) -> Tuple[bool, Optional[dict]]:
    """Detect parity drift by comparing current snapshot against baseline.

    Works offline: no SaaS call required. Returns False if no baseline exists
    or baseline key is rejected.

    Args:
        feature_slug: Feature identifier
        current_snapshot: Current MissionDossierSnapshot
        repo_root: Repository root path
        project_identity: ProjectIdentity with project_uuid and node_id
        target_branch: Target branch (e.g., "main", "2.x")
        mission_key: Mission type (e.g., "software-dev")
        manifest_version: Manifest schema version (e.g., "1")

    Returns:
        Tuple of (has_drift, drift_info):
            - (False, None): No drift or no baseline to compare
            - (True, drift_info): Drift detected with details
    """
    # Compute current baseline key
    current_key = compute_baseline_key(
        feature_slug=feature_slug,
        target_branch=target_branch,
        mission_key=mission_key,
        manifest_version=manifest_version,
        project_identity=project_identity,
    )

    # Load stored baseline
    stored_baseline = load_baseline(feature_slug, repo_root)
    if not stored_baseline:
        logger.debug(f"No baseline available for {feature_slug}")
        return False, None

    # Accept baseline (validate key match)
    accepted, reason = accept_baseline(stored_baseline, current_key)
    if not accepted:
        logger.info(f"Baseline rejected: {reason}")
        return False, None

    # Compare parity hashes
    current_hash = current_snapshot.parity_hash_sha256
    baseline_hash = stored_baseline.parity_hash_sha256

    if current_hash == baseline_hash:
        logger.debug(f"No parity drift detected for {feature_slug}")
        return False, None

    # Drift detected
    logger.warning(
        f"Parity drift detected for {feature_slug}: "
        f"{baseline_hash[:8]}... -> {current_hash[:8]}..."
    )

    # Compute severity based on completeness status changes
    severity = "warning"
    if (
        current_snapshot.completeness_status
        != "unknown"
    ):
        # Check if completeness changed
        if stored_baseline.parity_hash_sha256 != current_snapshot.parity_hash_sha256:
            # Could check stored completeness, but we don't have it here
            # Default to warning for any drift
            severity = "warning"

    drift_info = {
        "local_parity_hash": current_hash,
        "baseline_parity_hash": baseline_hash,
        "missing_in_local": [],  # TODO: compute from artifact summaries
        "missing_in_baseline": [],  # TODO: compute from artifact summaries
        "severity": severity,
    }

    return True, drift_info


async def emit_drift_if_detected(
    feature_slug: str,
    current_snapshot: MissionDossierSnapshot,
    repo_root: Path,
    project_identity: ProjectIdentity,
    target_branch: str,
    mission_key: str,
    manifest_version: str,
    actor: Optional[str] = None,
) -> Optional[dict]:
    """Detect drift and emit event if found.

    Conditional emission: event only emitted if has_drift=True and baseline accepted.

    Args:
        feature_slug: Feature identifier
        current_snapshot: Current MissionDossierSnapshot
        repo_root: Repository root path
        project_identity: ProjectIdentity with project_uuid and node_id
        target_branch: Target branch
        mission_key: Mission type
        manifest_version: Manifest schema version
        actor: Optional actor identifier

    Returns:
        Event dict if drift emitted, None otherwise.
    """
    has_drift, drift_info = detect_drift(
        feature_slug=feature_slug,
        current_snapshot=current_snapshot,
        repo_root=repo_root,
        project_identity=project_identity,
        target_branch=target_branch,
        mission_key=mission_key,
        manifest_version=manifest_version,
    )

    if not has_drift:
        return None

    # Emit ParityDriftDetected event
    event = emit_parity_drift_detected(
        feature_slug=feature_slug,
        local_parity_hash=drift_info["local_parity_hash"],
        baseline_parity_hash=drift_info["baseline_parity_hash"],
        missing_in_local=drift_info["missing_in_local"],
        missing_in_baseline=drift_info["missing_in_baseline"],
        severity=drift_info["severity"],
    )

    return event


def capture_baseline(
    feature_slug: str,
    current_snapshot: MissionDossierSnapshot,
    repo_root: Path,
    project_identity: ProjectIdentity,
    target_branch: str,
    mission_key: str,
    manifest_version: str,
) -> BaselineSnapshot:
    """Capture current snapshot as new baseline.

    Call this after curator reviews drift and accepts new content as correct.
    This is a manual operation (not automatic) to prevent unintended baseline drift.

    Args:
        feature_slug: Feature identifier
        current_snapshot: Current MissionDossierSnapshot to capture as baseline
        repo_root: Repository root path
        project_identity: ProjectIdentity with project_uuid and node_id
        target_branch: Target branch
        mission_key: Mission type
        manifest_version: Manifest schema version

    Returns:
        BaselineSnapshot that was captured and saved.
    """
    current_key = compute_baseline_key(
        feature_slug=feature_slug,
        target_branch=target_branch,
        mission_key=mission_key,
        manifest_version=manifest_version,
        project_identity=project_identity,
    )

    baseline = BaselineSnapshot(
        baseline_key=current_key,
        baseline_key_hash=current_key.compute_hash(),
        parity_hash_sha256=current_snapshot.parity_hash_sha256,
        captured_at=datetime.now(timezone.utc),
        captured_by=project_identity.node_id or "unknown",
    )

    save_baseline(feature_slug, baseline, repo_root)
    logger.info(
        f"Baseline captured for {feature_slug} "
        f"(hash: {baseline.parity_hash_sha256[:8]}...)"
    )
    return baseline
