"""Mission Dossier Parity Event Contracts domain module.

Provides constants, exception, provenance value objects, four event payload models,
reducer output models, and the reduce_mission_dossier() reducer for the Mission
Dossier contract.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .models import Event

# ── Section 1: Event Type Constants ──────────────────────────────────────────

MISSION_DOSSIER_ARTIFACT_INDEXED: str = "MissionDossierArtifactIndexed"
MISSION_DOSSIER_ARTIFACT_MISSING: str = "MissionDossierArtifactMissing"
MISSION_DOSSIER_SNAPSHOT_COMPUTED: str = "MissionDossierSnapshotComputed"
MISSION_DOSSIER_PARITY_DRIFT_DETECTED: str = "MissionDossierParityDriftDetected"

DOSSIER_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_DOSSIER_ARTIFACT_INDEXED,
    MISSION_DOSSIER_ARTIFACT_MISSING,
    MISSION_DOSSIER_SNAPSHOT_COMPUTED,
    MISSION_DOSSIER_PARITY_DRIFT_DETECTED,
})

# ── Section 2: Exception ──────────────────────────────────────────────────────


class NamespaceMixedStreamError(ValueError):
    """Raised when reduce_mission_dossier() receives events from multiple namespaces.

    Message format:
        "Namespace mismatch in dossier event stream.
         Expected: <expected_ns>. Got: <offending_ns>."
    """


# ── Section 3: Value Objects (provenance sub-types) ───────────────────────────

ArtifactClassT = Literal["input", "workflow", "output", "evidence", "policy", "runtime"]
DriftKindT = Literal[
    "artifact_added", "artifact_removed", "artifact_mutated",
    "anomaly_introduced", "anomaly_resolved", "manifest_version_changed",
]
AlgorithmT = Literal["sha256", "sha512", "md5"]
ParityStatusT = Literal["clean", "drifted", "unknown"]
ActorKindT = Literal["human", "llm", "system"]


class LocalNamespaceTuple(BaseModel):
    """Minimum collision-safe key for parity baseline scoping.

    manifest_version is defined HERE ONLY — event payloads must NOT duplicate it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_uuid: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    target_branch: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    manifest_version: str = Field(..., min_length=1)
    step_id: Optional[str] = Field(default=None)


class ArtifactIdentity(BaseModel):
    """Canonical identity for one artifact instance.

    artifact_class is the SINGLE source of truth for artifact taxonomy.
    Event payloads MUST NOT duplicate this field at the top level.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_type: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1, description="Repository-relative path")
    artifact_class: ArtifactClassT = Field(...)
    run_id: Optional[str] = Field(default=None)
    wp_id: Optional[str] = Field(default=None)


class ContentHashRef(BaseModel):
    """Content fingerprint with optional size and encoding metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hash: str = Field(..., min_length=1, description="Hex-encoded content hash")
    algorithm: AlgorithmT = Field(...)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    encoding: Optional[str] = Field(default=None)


class ProvenanceRef(BaseModel):
    """Source trace connecting an artifact or event to its authoritative origin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_event_ids: Optional[Tuple[str, ...]] = Field(default=None)
    git_sha: Optional[str] = Field(default=None)
    git_ref: Optional[str] = Field(default=None)
    actor_id: Optional[str] = Field(default=None)
    actor_kind: Optional[ActorKindT] = Field(default=None)
    revised_at: Optional[str] = Field(default=None, description="ISO 8601")


# ── Section 4: Payload Models ─────────────────────────────────────────────────


class MissionDossierArtifactIndexedPayload(BaseModel):
    """Payload for MissionDossierArtifactIndexed events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: LocalNamespaceTuple = Field(
        ...,
        description="Carries manifest_version — not duplicated in payload",
    )
    artifact_id: ArtifactIdentity = Field(
        ...,
        description="Carries artifact_class — not duplicated at top level",
    )
    content_ref: ContentHashRef = Field(...)
    indexed_at: str = Field(..., description="ISO 8601")
    provenance: Optional[ProvenanceRef] = Field(default=None)
    step_id: Optional[str] = Field(default=None)
    supersedes: Optional[ArtifactIdentity] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)


class MissionDossierArtifactMissingPayload(BaseModel):
    """Payload for MissionDossierArtifactMissing events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: LocalNamespaceTuple = Field(...)
    expected_identity: ArtifactIdentity = Field(
        ...,
        description="Carries path and artifact_class of missing artifact",
    )
    manifest_step: str = Field(
        ...,
        min_length=1,
        description='"required_always" or step_id',
    )
    checked_at: str = Field(..., description="ISO 8601")
    last_known_ref: Optional[ProvenanceRef] = Field(default=None)
    remediation_hint: Optional[str] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)


class MissionDossierSnapshotComputedPayload(BaseModel):
    """Payload for MissionDossierSnapshotComputed events.

    manifest_version NOT duplicated here — use namespace.manifest_version.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: LocalNamespaceTuple = Field(
        ...,
        description="manifest_version lives here only",
    )
    snapshot_hash: str = Field(
        ...,
        min_length=1,
        description="Hex-encoded deterministic hash",
    )
    artifact_count: int = Field(..., ge=0)
    anomaly_count: int = Field(..., ge=0)
    computed_at: str = Field(..., description="ISO 8601")
    algorithm: Optional[AlgorithmT] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)


class MissionDossierParityDriftDetectedPayload(BaseModel):
    """Payload for MissionDossierParityDriftDetected events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: LocalNamespaceTuple = Field(...)
    expected_hash: str = Field(..., min_length=1)
    actual_hash: str = Field(..., min_length=1)
    drift_kind: DriftKindT = Field(...)
    detected_at: str = Field(..., description="ISO 8601")
    artifact_ids_changed: Optional[Tuple[ArtifactIdentity, ...]] = Field(default=None)
    rebuild_hint: Optional[str] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)


# ── Section 5: Reducer Output Models ─────────────────────────────────────────


class ArtifactEntry(BaseModel):
    """A single indexed artifact in the dossier state."""

    model_config = ConfigDict(frozen=True)

    identity: ArtifactIdentity
    content_ref: ContentHashRef
    indexed_at: str
    provenance: Optional[ProvenanceRef] = None
    superseded: bool = False
    step_id: Optional[str] = None


class AnomalyEntry(BaseModel):
    """A single missing-artifact anomaly in the dossier state."""

    model_config = ConfigDict(frozen=True)

    anomaly_type: Literal["missing_artifact"] = Field(default="missing_artifact")
    expected_identity: ArtifactIdentity
    manifest_step: str
    checked_at: str
    remediation_hint: Optional[str] = None


class SnapshotSummary(BaseModel):
    """Summary of the latest computed snapshot."""

    model_config = ConfigDict(frozen=True)

    snapshot_hash: str
    artifact_count: int
    anomaly_count: int
    computed_at: str
    algorithm: str = Field(default="sha256")


class DriftRecord(BaseModel):
    """A single parity drift detection record."""

    model_config = ConfigDict(frozen=True)

    expected_hash: str
    actual_hash: str
    drift_kind: str
    detected_at: str


class MissionDossierState(BaseModel):
    """Deterministic projection output of reduce_mission_dossier()."""

    model_config = ConfigDict(frozen=True)

    namespace: Optional[LocalNamespaceTuple] = None
    artifacts: Dict[str, ArtifactEntry] = Field(default_factory=dict)
    anomalies: Tuple[AnomalyEntry, ...] = Field(default_factory=tuple)
    latest_snapshot: Optional[SnapshotSummary] = None
    drift_history: Tuple[DriftRecord, ...] = Field(default_factory=tuple)
    parity_status: ParityStatusT = Field(default="unknown")
    event_count: int = Field(default=0)


# ── Section 6: Reducer ────────────────────────────────────────────────────────


def _extract_namespace(event: Event) -> Optional[LocalNamespaceTuple]:
    """Extract namespace from a dossier event's payload dict."""
    ns_dict: Any = event.payload.get("namespace")
    if ns_dict is None:
        return None
    try:
        return LocalNamespaceTuple(**ns_dict)
    except Exception:
        return None


def _namespace_key(ns: LocalNamespaceTuple) -> Tuple[str, str, str, str, str]:
    """Return the 5-field identity key, excluding optional step_id.

    step_id is optional context within a namespace — the same mission stream
    can have events with different step_id values without constituting a
    namespace mismatch.
    """
    return (
        ns.project_uuid,
        ns.mission_slug,
        ns.target_branch,
        ns.mission_type,
        ns.manifest_version,
    )


def reduce_mission_dossier(events: Sequence[Event]) -> MissionDossierState:
    """Fold dossier events into deterministic MissionDossierState.

    Pipeline:
    1. Filter to DOSSIER_EVENT_TYPES
    2. Sort by (lamport_clock, timestamp, event_id) via status_event_sort_key
    3. Deduplicate by event_id via dedup_events
    4. Validate namespace consistency (5-field key; step_id excluded) —
       raise NamespaceMixedStreamError on mismatch; skip events with
       malformed/missing namespace (they will also be skipped in fold)
    5. Fold each event into mutable intermediates
    6. Assemble and return frozen MissionDossierState

    Raises:
        NamespaceMixedStreamError: If events span multiple namespace tuples.

    Pure function. No I/O. No global state. Deterministic.
    """
    from .status import dedup_events, status_event_sort_key

    # 1. Filter to dossier event types
    dossier_events = [e for e in events if e.event_type in DOSSIER_EVENT_TYPES]
    if not dossier_events:
        return MissionDossierState()

    # 2. Sort by (lamport_clock, timestamp, event_id)
    sorted_events = sorted(dossier_events, key=status_event_sort_key)

    # 3. Deduplicate by event_id
    unique_events = dedup_events(sorted_events)

    # 4. Validate single-namespace invariant
    # Events with None namespace are malformed — skip them here; the fold loop
    # will also skip them via try/except.  Compare using the 5-field key so
    # that optional step_id variance does not falsely trigger a mismatch.
    canonical_ns: Optional[LocalNamespaceTuple] = None
    for ev in unique_events:
        ns = _extract_namespace(ev)
        if ns is None:
            continue
        if canonical_ns is None:
            canonical_ns = ns
            continue
        if _namespace_key(ns) != _namespace_key(canonical_ns):
            raise NamespaceMixedStreamError(
                f"Namespace mismatch in dossier event stream. "
                f"Expected: {canonical_ns!r}. Got: {ns!r}."
            )

    # 4b. Normalize step_id: if multiple distinct non-null step_ids seen, set None
    if canonical_ns is not None:
        seen_step_ids: set[str] = set()
        for ev in unique_events:
            ns = _extract_namespace(ev)
            if ns is not None and ns.step_id is not None:
                seen_step_ids.add(ns.step_id)
        if len(seen_step_ids) > 1:
            canonical_ns = canonical_ns.model_copy(update={"step_id": None})

    # 5. Fold events into mutable intermediates
    namespace = canonical_ns
    artifacts: Dict[str, ArtifactEntry] = {}
    anomalies: List[AnomalyEntry] = []
    latest_snapshot: Optional[SnapshotSummary] = None
    drift_history: List[DriftRecord] = []

    for event in unique_events:
        etype = event.event_type

        if etype == MISSION_DOSSIER_ARTIFACT_INDEXED:
            try:
                payload_indexed = MissionDossierArtifactIndexedPayload(
                    **event.payload
                )
            except Exception:
                continue
            # Mark superseded artifact if applicable
            if payload_indexed.supersedes is not None:
                superseded_path = payload_indexed.supersedes.path
                if superseded_path in artifacts:
                    old_entry = artifacts[superseded_path]
                    artifacts[superseded_path] = ArtifactEntry(
                        identity=old_entry.identity,
                        content_ref=old_entry.content_ref,
                        indexed_at=old_entry.indexed_at,
                        provenance=old_entry.provenance,
                        superseded=True,
                        step_id=old_entry.step_id,
                    )
            # Upsert artifact entry keyed by path
            artifacts[payload_indexed.artifact_id.path] = ArtifactEntry(
                identity=payload_indexed.artifact_id,
                content_ref=payload_indexed.content_ref,
                indexed_at=payload_indexed.indexed_at,
                provenance=payload_indexed.provenance,
                superseded=False,
                step_id=payload_indexed.step_id,
            )

        elif etype == MISSION_DOSSIER_ARTIFACT_MISSING:
            try:
                payload_missing = MissionDossierArtifactMissingPayload(
                    **event.payload
                )
            except Exception:
                continue
            anomalies.append(
                AnomalyEntry(
                    anomaly_type="missing_artifact",
                    expected_identity=payload_missing.expected_identity,
                    manifest_step=payload_missing.manifest_step,
                    checked_at=payload_missing.checked_at,
                    remediation_hint=payload_missing.remediation_hint,
                )
            )

        elif etype == MISSION_DOSSIER_SNAPSHOT_COMPUTED:
            try:
                payload_snapshot = MissionDossierSnapshotComputedPayload(
                    **event.payload
                )
            except Exception:
                continue
            algorithm_value: str = (
                payload_snapshot.algorithm
                if payload_snapshot.algorithm is not None
                else "sha256"
            )
            latest_snapshot = SnapshotSummary(
                snapshot_hash=payload_snapshot.snapshot_hash,
                artifact_count=payload_snapshot.artifact_count,
                anomaly_count=payload_snapshot.anomaly_count,
                computed_at=payload_snapshot.computed_at,
                algorithm=algorithm_value,
            )

        elif etype == MISSION_DOSSIER_PARITY_DRIFT_DETECTED:
            try:
                payload_drift = MissionDossierParityDriftDetectedPayload(
                    **event.payload
                )
            except Exception:
                continue
            drift_history.append(
                DriftRecord(
                    expected_hash=payload_drift.expected_hash,
                    actual_hash=payload_drift.actual_hash,
                    drift_kind=payload_drift.drift_kind,
                    detected_at=payload_drift.detected_at,
                )
            )

    # 6. Derive parity_status AFTER full fold
    final_parity_status: ParityStatusT
    if drift_history:
        final_parity_status = "drifted"
    elif latest_snapshot is not None:
        final_parity_status = "clean"
    else:
        final_parity_status = "unknown"

    # 7. Assemble frozen state
    return MissionDossierState(
        namespace=namespace,
        artifacts=artifacts,
        anomalies=tuple(anomalies),
        latest_snapshot=latest_snapshot,
        drift_history=tuple(drift_history),
        parity_status=final_parity_status,
        event_count=len(unique_events),
    )
