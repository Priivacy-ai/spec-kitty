"""Mission dossier event types and emission.

Emits the 4 canonical dossier event payloads in the **namespaced envelope**
shape expected by ``spec-kitty-events>=5.0.0``:

* ``MissionDossierArtifactIndexed`` — one per indexed artifact.
* ``MissionDossierArtifactMissing`` — one per blocking missing artifact.
* ``MissionDossierSnapshotComputed`` — one per dossier scan.
* ``MissionDossierParityDriftDetected`` — emitted only on detected drift.

Each payload's top-level keys are constrained by the server schema with
``additionalProperties: False``. The canonical sub-objects are:

* ``namespace`` → ``LocalNamespaceTuple``
  ``(project_uuid, mission_slug, target_branch, mission_type, manifest_version, step_id?)``
* ``artifact_id`` → ``ArtifactIdentity``
  ``(mission_type, path, artifact_class, wp_id?, run_id?)``
* ``content_ref`` → ``ContentHashRef``
  ``(algorithm, hash, size_bytes?, encoding?)``
* ``provenance`` → ``ProvenanceRef`` (optional)

See ``spec_kitty_events.schemas.load_schema('mission_dossier_artifact_indexed_payload')``
and the companion ``artifact_identity`` / ``content_hash_ref`` /
``local_namespace_tuple`` schemas for the binding shape.

This module previously emitted a **legacy flat envelope**
(``mission_slug``, ``artifact_key``, ``relative_path``, ``content_hash_sha256``,
``size_bytes``, ``required_status``, …) which the deployed SaaS now rejects
with ``Additional properties are not allowed``. The migration is tracked
under Priivacy-ai/spec-kitty#1047 and the SaaS launch evidence lives in
Priivacy-ai/spec-kitty-end-to-end-testing#37.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from specify_cli.dossier.emitter_adapter import fire_dossier_event

logger = logging.getLogger(__name__)


# ── Canonical sub-objects (mirror `spec_kitty_events` schemas) ─────────


# Server schema (`artifact_identity`) defines six artifact classes — no
# ``other`` fallback. Legacy CLI code occasionally produced ``other``; we
# map it to ``runtime`` at the wire boundary so events still land.
ARTIFACT_CLASS_ENUM = {"input", "workflow", "output", "evidence", "policy", "runtime"}
_LEGACY_ARTIFACT_CLASS_MAP = {"other": "runtime"}


def _normalize_artifact_class(value: str) -> str:
    """Map legacy ``other`` to ``runtime``; pass through valid enum values."""
    if value in _LEGACY_ARTIFACT_CLASS_MAP:
        return _LEGACY_ARTIFACT_CLASS_MAP[value]
    return value


class LocalNamespaceTuple(BaseModel):
    """Minimum collision-safe key for parity baseline scoping.

    Mirrors ``spec_kitty_events/local_namespace_tuple.schema.json``.
    """

    model_config = {"extra": "forbid"}

    project_uuid: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    target_branch: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    manifest_version: str = Field(..., min_length=1)
    step_id: str | None = Field(default=None)


class ArtifactIdentity(BaseModel):
    """Canonical identity for one artifact instance.

    Mirrors ``spec_kitty_events/artifact_identity.schema.json``.
    """

    model_config = {"extra": "forbid"}

    mission_type: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    artifact_class: str = Field(...)
    wp_id: str | None = Field(default=None)
    run_id: str | None = Field(default=None)

    @field_validator("artifact_class")
    @classmethod
    def _validate_class(cls, v: str) -> str:
        if v not in ARTIFACT_CLASS_ENUM:
            raise ValueError(
                f"artifact_class must be one of {sorted(ARTIFACT_CLASS_ENUM)}; got {v!r}"
            )
        return v


class ContentHashRef(BaseModel):
    """Content fingerprint with optional size and encoding metadata.

    Mirrors ``spec_kitty_events/content_hash_ref.schema.json``.
    """

    model_config = {"extra": "forbid"}

    algorithm: str = Field(...)
    hash: str = Field(..., min_length=1)
    size_bytes: int | None = Field(default=None, ge=0)
    encoding: str | None = Field(default=None)

    @field_validator("algorithm")
    @classmethod
    def _validate_algorithm(cls, v: str) -> str:
        if v not in {"sha256", "sha512", "md5"}:
            raise ValueError(f"algorithm must be sha256/sha512/md5; got {v!r}")
        return v

    @field_validator("hash")
    @classmethod
    def _validate_hash(cls, v: str) -> str:
        if not re.match(r"^[A-Fa-f0-9]+$", v):
            raise ValueError("hash must be a hex-encoded string")
        return v.lower()


# ── Top-level event payloads (wire shape) ──────────────────────────────


class MissionDossierArtifactIndexedPayload(BaseModel):
    """Wire payload for ``MissionDossierArtifactIndexed``.

    Mirrors ``spec_kitty_events/mission_dossier_artifact_indexed_payload``.
    Required: ``namespace``, ``artifact_id``, ``content_ref``, ``indexed_at``.
    """

    model_config = {"extra": "forbid"}

    namespace: LocalNamespaceTuple
    artifact_id: ArtifactIdentity
    content_ref: ContentHashRef
    indexed_at: str = Field(..., min_length=1)
    provenance: dict[str, Any] | None = Field(default=None)
    step_id: str | None = Field(default=None)
    context_diagnostics: dict[str, str] | None = Field(default=None)
    supersedes: ArtifactIdentity | None = Field(default=None)


class MissionDossierArtifactMissingPayload(BaseModel):
    """Wire payload for ``MissionDossierArtifactMissing``.

    Required: ``namespace``, ``expected_identity``, ``manifest_step``, ``checked_at``.
    """

    model_config = {"extra": "forbid"}

    namespace: LocalNamespaceTuple
    expected_identity: ArtifactIdentity
    manifest_step: str = Field(..., min_length=1)
    checked_at: str = Field(..., min_length=1)
    last_known_ref: ContentHashRef | None = Field(default=None)
    remediation_hint: str | None = Field(default=None)
    context_diagnostics: dict[str, str] | None = Field(default=None)


class MissionDossierSnapshotComputedPayload(BaseModel):
    """Wire payload for ``MissionDossierSnapshotComputed``.

    Required: ``namespace``, ``snapshot_hash``, ``artifact_count``,
    ``anomaly_count``, ``computed_at``.
    """

    model_config = {"extra": "forbid"}

    namespace: LocalNamespaceTuple
    snapshot_hash: str = Field(..., min_length=1)
    artifact_count: int = Field(..., ge=0)
    anomaly_count: int = Field(..., ge=0)
    computed_at: str = Field(..., min_length=1)
    algorithm: str | None = Field(default=None)
    context_diagnostics: dict[str, str] | None = Field(default=None)


class MissionDossierParityDriftDetectedPayload(BaseModel):
    """Wire payload for ``MissionDossierParityDriftDetected``.

    Required: ``namespace``, ``expected_hash``, ``actual_hash``,
    ``drift_kind``, ``detected_at``.
    """

    model_config = {"extra": "forbid"}

    namespace: LocalNamespaceTuple
    expected_hash: str = Field(..., min_length=1)
    actual_hash: str = Field(..., min_length=1)
    drift_kind: str = Field(..., min_length=1)
    detected_at: str = Field(..., min_length=1)
    artifact_ids_changed: list[ArtifactIdentity] | None = Field(default=None)
    rebuild_hint: str | None = Field(default=None)
    context_diagnostics: dict[str, str] | None = Field(default=None)


# ── Internal helpers ───────────────────────────────────────────────────


def _iso_utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _coerce_namespace(
    namespace: LocalNamespaceTuple | dict[str, Any] | None,
    *,
    mission_slug: str | None = None,
    step_id: str | None = None,
) -> LocalNamespaceTuple | None:
    """Coerce a caller-supplied namespace dict into ``LocalNamespaceTuple``.

    Callers commonly pass the 5-field dict produced by
    ``specify_cli.sync.namespace.NamespaceRef.to_dict()``. We tolerate either
    that or a fully-constructed ``LocalNamespaceTuple``. Returns ``None`` when
    the namespace cannot be constructed (in which case the caller MUST refuse
    to emit — the server schema requires ``namespace``).
    """
    if namespace is None:
        return None
    if isinstance(namespace, LocalNamespaceTuple):
        if step_id is not None and namespace.step_id is None:
            return namespace.model_copy(update={"step_id": step_id})
        return namespace
    try:
        merged = dict(namespace)
    except TypeError:
        return None
    if "step_id" not in merged and step_id is not None:
        merged["step_id"] = step_id
    if "mission_slug" not in merged and mission_slug is not None:
        merged["mission_slug"] = mission_slug
    try:
        return LocalNamespaceTuple(**merged)
    except (TypeError, ValueError) as exc:
        logger.error("Cannot build LocalNamespaceTuple from %r: %s", namespace, exc)
        return None


def _build_artifact_identity(
    *,
    mission_type: str,
    path: str,
    artifact_class: str,
    wp_id: str | None = None,
    run_id: str | None = None,
) -> ArtifactIdentity:
    return ArtifactIdentity(
        mission_type=mission_type,
        path=path,
        artifact_class=_normalize_artifact_class(artifact_class),
        wp_id=wp_id,
        run_id=run_id,
    )


def _build_content_ref(
    *,
    content_hash_sha256: str,
    size_bytes: int | None,
) -> ContentHashRef:
    return ContentHashRef(
        algorithm="sha256",
        hash=content_hash_sha256,
        size_bytes=size_bytes,
    )


def _missing_namespace_log(event_type: str) -> None:
    logger.error(
        "Refusing to emit %s without a complete LocalNamespaceTuple namespace; "
        "the SaaS schema rejects events missing project_uuid/mission_slug/"
        "target_branch/mission_type/manifest_version.",
        event_type,
    )


def _consume_legacy_values(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    *,
    names: tuple[str, ...],
    defaults: dict[str, object],
) -> dict[str, object]:
    if len(args) > len(names):
        raise TypeError(f"Expected at most {len(names)} legacy positional arguments, got {len(args)}")
    values = dict(defaults)
    for name, value in zip(names, args, strict=False):
        values[name] = value
    for name in names[len(args):]:
        if name in kwargs:
            values[name] = kwargs.pop(name)
    if kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise TypeError(f"Unexpected keyword argument(s): {unexpected}")
    return values


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _snapshot_legacy_diagnostics(
    *,
    snapshot_id: str,
    completeness_status: str,
    required_artifacts: int,
    required_present: int,
    optional_artifacts: int,
    optional_present: int,
    context_diagnostics: dict[str, str] | None,
) -> dict[str, str]:
    diagnostics = dict(context_diagnostics or {})
    diagnostics.setdefault("snapshot_id", snapshot_id)
    diagnostics.setdefault("completeness_status", completeness_status)
    diagnostics.setdefault("required_artifacts", str(required_artifacts))
    diagnostics.setdefault("required_present", str(required_present))
    diagnostics.setdefault("optional_artifacts", str(optional_artifacts))
    diagnostics.setdefault("optional_present", str(optional_present))
    return diagnostics


# ── Event emitters ─────────────────────────────────────────────────────


def emit_artifact_indexed(
    mission_slug: str,
    artifact_key: str,  # legacy arg, retained for caller compatibility
    artifact_class: str,
    relative_path: str,
    content_hash_sha256: str,
    size_bytes: int,
    *args: object,
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    mission_type: str | None = None,
    indexed_at: str | None = None,
    context_diagnostics: dict[str, str] | None = None,
    provenance: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierArtifactIndexed`` in the namespaced envelope.

    ``artifact_key`` and ``required_status`` from the legacy signature are
    preserved as informational diagnostics rather than top-level fields —
    the server schema (``additionalProperties: False``) does not accept
    them at the top level.

    Returns the enqueued event dict on success, or ``None`` if validation or
    routing fails.
    """
    legacy = _consume_legacy_values(
        args,
        kwargs,
        names=("wp_id", "step_id", "required_status"),
        defaults={"wp_id": None, "step_id": None, "required_status": "optional"},
    )
    wp_id = _optional_str(legacy["wp_id"])
    step_id = _optional_str(legacy["step_id"])
    required_status = str(legacy["required_status"])
    ns = _coerce_namespace(namespace, mission_slug=mission_slug, step_id=step_id)
    if ns is None:
        _missing_namespace_log("MissionDossierArtifactIndexed")
        return None

    effective_mission_type = mission_type or ns.mission_type
    try:
        identity = _build_artifact_identity(
            mission_type=effective_mission_type,
            path=relative_path,
            artifact_class=artifact_class,
            wp_id=wp_id,
        )
        content_ref = _build_content_ref(
            content_hash_sha256=content_hash_sha256,
            size_bytes=size_bytes,
        )
        diagnostics = dict(context_diagnostics or {})
        # Carry the legacy artifact_key / required_status forward as
        # diagnostics so downstream consumers (and audit logs) can still
        # discover them without violating ``additionalProperties: False``.
        diagnostics.setdefault("artifact_key", artifact_key)
        diagnostics.setdefault("required_status", required_status)
        payload = MissionDossierArtifactIndexedPayload(
            namespace=ns,
            artifact_id=identity,
            content_ref=content_ref,
            indexed_at=indexed_at or _iso_utc_now(),
            step_id=step_id,
            context_diagnostics=diagnostics or None,
            provenance=provenance,
        )
    except (TypeError, ValueError) as exc:
        logger.exception("Payload validation failed for MissionDossierArtifactIndexed: %s", exc)
        return None

    return fire_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        aggregate_id=f"{ns.mission_slug}:{relative_path}",
        aggregate_type="MissionDossier",
        payload=payload.model_dump(exclude_none=True),
    )


def emit_artifact_missing(
    mission_slug: str,
    artifact_key: str,  # legacy arg
    artifact_class: str,
    expected_path_pattern: str,
    reason_code: str,
    *args: object,
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    mission_type: str | None = None,
    manifest_step: str | None = None,
    checked_at: str | None = None,
    last_known_content_hash_sha256: str | None = None,
    last_known_size_bytes: int | None = None,
    context_diagnostics: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierArtifactMissing`` in the namespaced envelope.

    The event fires only when ``blocking=True`` (legacy convention).
    """
    legacy = _consume_legacy_values(
        args,
        kwargs,
        names=("reason_detail", "blocking"),
        defaults={"reason_detail": None, "blocking": True},
    )
    reason_detail = _optional_str(legacy["reason_detail"])
    blocking = bool(legacy["blocking"])
    if not blocking:
        logger.debug("Skipping non-blocking missing-artifact event for %s", artifact_key)
        return None

    ns = _coerce_namespace(namespace, mission_slug=mission_slug)
    if ns is None:
        _missing_namespace_log("MissionDossierArtifactMissing")
        return None

    effective_mission_type = mission_type or ns.mission_type
    try:
        identity = _build_artifact_identity(
            mission_type=effective_mission_type,
            path=expected_path_pattern,
            artifact_class=artifact_class,
        )
        diagnostics = dict(context_diagnostics or {})
        diagnostics.setdefault("artifact_key", artifact_key)
        diagnostics.setdefault("reason_code", reason_code)
        if reason_detail:
            diagnostics.setdefault("reason_detail", reason_detail)
        last_known = None
        if last_known_content_hash_sha256:
            last_known = _build_content_ref(
                content_hash_sha256=last_known_content_hash_sha256,
                size_bytes=last_known_size_bytes,
            )
        payload = MissionDossierArtifactMissingPayload(
            namespace=ns,
            expected_identity=identity,
            manifest_step=manifest_step or "default",
            checked_at=checked_at or _iso_utc_now(),
            last_known_ref=last_known,
            remediation_hint=reason_detail,
            context_diagnostics=diagnostics or None,
        )
    except (TypeError, ValueError) as exc:
        logger.exception("Payload validation failed for MissionDossierArtifactMissing: %s", exc)
        return None

    return fire_dossier_event(
        event_type="MissionDossierArtifactMissing",
        aggregate_id=f"{ns.mission_slug}:{expected_path_pattern}",
        aggregate_type="MissionDossier",
        payload=payload.model_dump(exclude_none=True),
    )


def emit_snapshot_computed(
    mission_slug: str,
    parity_hash_sha256: str,
    total_artifacts: int,
    required_artifacts: int,
    required_present: int,
    required_missing: int,
    optional_artifacts: int,
    optional_present: int,
    completeness_status: str,
    snapshot_id: str,
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    *,
    mission_type: str | None = None,  # noqa: ARG001 — pulled from namespace
    computed_at: str | None = None,
    anomaly_count: int | None = None,
    context_diagnostics: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierSnapshotComputed`` in the namespaced envelope.

    The legacy ``artifact_counts`` breakdown is folded into
    ``context_diagnostics`` so downstream consumers can still recover it.
    """
    ns = _coerce_namespace(namespace, mission_slug=mission_slug)
    if ns is None:
        _missing_namespace_log("MissionDossierSnapshotComputed")
        return None

    try:
        diagnostics = _snapshot_legacy_diagnostics(
            snapshot_id=snapshot_id,
            completeness_status=completeness_status,
            required_artifacts=required_artifacts,
            required_present=required_present,
            optional_artifacts=optional_artifacts,
            optional_present=optional_present,
            context_diagnostics=context_diagnostics,
        )
        payload = MissionDossierSnapshotComputedPayload(
            namespace=ns,
            snapshot_hash=parity_hash_sha256,
            artifact_count=total_artifacts,
            anomaly_count=(anomaly_count if anomaly_count is not None else required_missing),
            computed_at=computed_at or _iso_utc_now(),
            algorithm="sha256",
            context_diagnostics=diagnostics or None,
        )
    except (TypeError, ValueError) as exc:
        logger.exception("Payload validation failed for MissionDossierSnapshotComputed: %s", exc)
        return None

    return fire_dossier_event(
        event_type="MissionDossierSnapshotComputed",
        aggregate_id=f"{ns.mission_slug}:{snapshot_id}",
        aggregate_type="MissionDossier",
        payload=payload.model_dump(exclude_none=True),
    )


def emit_parity_drift_detected(
    mission_slug: str,
    local_parity_hash: str,
    baseline_parity_hash: str,
    missing_in_local: list[str] | None = None,
    missing_in_baseline: list[str] | None = None,
    severity: str = "warning",
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    *,
    mission_type: str | None = None,
    drift_kind: str | None = None,
    detected_at: str | None = None,
    rebuild_hint: str | None = None,
    context_diagnostics: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierParityDriftDetected`` in the namespaced envelope.

    Only fires when ``local_parity_hash != baseline_parity_hash`` (matching
    the legacy short-circuit).
    """
    if local_parity_hash == baseline_parity_hash:
        logger.debug("No parity drift detected for %s", mission_slug)
        return None

    ns = _coerce_namespace(namespace, mission_slug=mission_slug)
    if ns is None:
        _missing_namespace_log("MissionDossierParityDriftDetected")
        return None

    effective_mission_type = mission_type or ns.mission_type
    try:
        diagnostics = dict(context_diagnostics or {})
        diagnostics.setdefault("severity", severity)
        if missing_in_local:
            diagnostics.setdefault("missing_in_local", ",".join(missing_in_local))
        if missing_in_baseline:
            diagnostics.setdefault("missing_in_baseline", ",".join(missing_in_baseline))
        # When the caller provides per-key changes we surface them as
        # ArtifactIdentity entries against the well-known mission_type so a
        # consumer can reason about drift without a separate lookup.
        artifacts_changed: list[ArtifactIdentity] | None = None
        all_missing = (missing_in_local or []) + (missing_in_baseline or [])
        if all_missing:
            artifacts_changed = [
                _build_artifact_identity(
                    mission_type=effective_mission_type,
                    path=path,
                    artifact_class="evidence",
                )
                for path in all_missing
            ] or None
        payload = MissionDossierParityDriftDetectedPayload(
            namespace=ns,
            expected_hash=baseline_parity_hash,
            actual_hash=local_parity_hash,
            drift_kind=drift_kind or "anomaly_introduced",
            detected_at=detected_at or _iso_utc_now(),
            artifact_ids_changed=artifacts_changed,
            rebuild_hint=rebuild_hint,
            context_diagnostics=diagnostics or None,
        )
    except (TypeError, ValueError) as exc:
        logger.exception("Payload validation failed for MissionDossierParityDriftDetected: %s", exc)
        return None

    return fire_dossier_event(
        event_type="MissionDossierParityDriftDetected",
        aggregate_id=f"{ns.mission_slug}:drift",
        aggregate_type="MissionDossier",
        payload=payload.model_dump(exclude_none=True),
    )
