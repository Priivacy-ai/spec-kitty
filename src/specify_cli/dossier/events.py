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
from typing import Any

from spec_kitty_events import (
    ArtifactIdentity,
    ContentHashRef,
    LocalNamespaceTuple,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierParityDriftDetectedPayload,
    MissionDossierSnapshotComputedPayload,
    ProvenanceRef,
)

from kernel.clock import now_utc_iso
from specify_cli.dossier.emitter_adapter import fire_dossier_event

# Sync-owned types are deliberately not imported (even under TYPE_CHECKING):
# the dossier->sync edge is inverted through emitter_adapter
# (tests/architectural/test_dossier_sync_boundary.py), so the explicit-context
# parameters are typed structurally.

logger = logging.getLogger(__name__)


# ── Canonical sub-objects (imported from `spec_kitty_events`) ──────────
#
# The 7 wire-shape types this module previously hand-maintained as a local
# Pydantic mirror (``LocalNamespaceTuple``, ``ArtifactIdentity``,
# ``ContentHashRef``, and the four ``MissionDossier*Payload`` classes) are
# imported from the canonical ``spec_kitty_events`` package above instead —
# it already owns and ships these shapes (installed 6.1.0, pinned
# ``>=6.0.0,<7.0.0``). See Priivacy-ai/spec-kitty#1058.


# Server schema (`artifact_identity`) defines six artifact classes — no
# ``other`` fallback. Legacy CLI code occasionally produced ``other``; we
# map it to ``runtime`` at the wire boundary so events still land.
_LEGACY_ARTIFACT_CLASS_MAP = {"other": "runtime"}


def _normalize_artifact_class(value: str) -> str:
    """Map legacy ``other`` to ``runtime``; pass through valid enum values."""
    if value in _LEGACY_ARTIFACT_CLASS_MAP:
        return _LEGACY_ARTIFACT_CLASS_MAP[value]
    return value


# ── Internal helpers ───────────────────────────────────────────────────


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
        logger.exception("Cannot build LocalNamespaceTuple from %r: %s", namespace, exc)
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
    *,
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    mission_type: str | None = None,
    wp_id: str | None = None,
    step_id: str | None = None,
    required_status: str = "optional",
    indexed_at: str | None = None,
    context_diagnostics: dict[str, str] | None = None,
    provenance: ProvenanceRef | dict[str, Any] | None = None,
    project_context: Any | None = None,
    project_unit: Any | None = None,
    project_layout: Any | None = None,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierArtifactIndexed`` in the namespaced envelope.

    ``artifact_key`` and ``required_status`` from the legacy signature are
    preserved as informational diagnostics rather than top-level fields —
    the server schema (``additionalProperties: False``) does not accept
    them at the top level.

    ``provenance``, if given, must match the canonical ``ProvenanceRef``
    shape (``actor_id``, ``actor_kind``, ``git_ref``, ``git_sha``,
    ``revised_at``, ``source_event_ids``) — the frozen, ``extra="forbid"``
    model ``spec_kitty_events`` ships for this field. It does **not** accept
    this package's own artifact-level provenance shape (``source_kind`` /
    ``actor_id`` / ``captured_at``, see
    ``specify_cli.dossier.models.ArtifactRef.provenance``): that shape is a
    different, CLI-internal concept and passing it here raises
    ``pydantic.ValidationError`` rather than silently dropping the event.

    Returns the enqueued event dict on success, or ``None`` if the artifact
    identity/content-hash inputs fail validation. An invalid ``provenance``
    is deliberately NOT folded into that ``None`` path — see above — so it
    raises instead.
    """
    ns = _coerce_namespace(namespace, mission_slug=mission_slug, step_id=step_id)
    if ns is None:
        _missing_namespace_log("MissionDossierArtifactIndexed")
        return None

    if provenance is not None and not isinstance(provenance, ProvenanceRef):
        # Deliberately outside the try/except below: a malformed provenance
        # payload is a caller programming error, not a routine validation
        # failure, and must surface loudly (PR-CONTRACT-001) rather than
        # being absorbed into the generic "return None" path used for
        # artifact_id/content_ref construction failures.
        provenance = ProvenanceRef.model_validate(provenance)

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
            indexed_at=indexed_at or now_utc_iso(),
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
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
    )


def emit_artifact_missing(
    mission_slug: str,
    artifact_key: str,  # legacy arg
    artifact_class: str,
    expected_path_pattern: str,
    reason_code: str,
    *,
    namespace: LocalNamespaceTuple | dict[str, Any] | None = None,
    mission_type: str | None = None,
    reason_detail: str | None = None,
    blocking: bool = True,
    manifest_step: str | None = None,
    checked_at: str | None = None,
    context_diagnostics: dict[str, str] | None = None,
    project_context: Any | None = None,
    project_unit: Any | None = None,
    project_layout: Any | None = None,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierArtifactMissing`` in the namespaced envelope.

    The event fires only when ``blocking=True`` (legacy convention).
    """
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
        payload = MissionDossierArtifactMissingPayload(
            namespace=ns,
            expected_identity=identity,
            manifest_step=manifest_step or "default",
            checked_at=checked_at or now_utc_iso(),
            last_known_ref=None,
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
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
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
    mission_type: str | None = None,
    computed_at: str | None = None,
    anomaly_count: int | None = None,
    context_diagnostics: dict[str, str] | None = None,
    project_context: Any | None = None,
    project_unit: Any | None = None,
    project_layout: Any | None = None,
) -> dict[str, Any] | None:
    """Emit ``MissionDossierSnapshotComputed`` in the namespaced envelope.

    The legacy ``artifact_counts`` breakdown is folded into
    ``context_diagnostics`` so downstream consumers can still recover it.
    """
    ns = _coerce_namespace(namespace, mission_slug=mission_slug)
    if ns is None:
        _missing_namespace_log("MissionDossierSnapshotComputed")
        return None
    if mission_type and mission_type != ns.mission_type:
        logger.warning(
            "Snapshot mission_type %r did not match namespace mission_type %r; using namespace value",
            mission_type,
            ns.mission_type,
        )

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
            computed_at=computed_at or now_utc_iso(),
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
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
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
    project_context: Any | None = None,
    project_unit: Any | None = None,
    project_layout: Any | None = None,
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
            detected_at=detected_at or now_utc_iso(),
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
        # mode="json" (T002 fallout): the canonical payload's
        # ``artifact_ids_changed`` is ``Optional[Tuple[ArtifactIdentity, ...]]``
        # (was ``list[...] | None`` on the deleted local mirror) -- the default
        # python-mode model_dump() renders a tuple-typed field as a Python
        # ``tuple``, which the server's ``anyOf: [array, null]`` JSON Schema
        # rejects on strict Python-type checking (a tuple is not a ``list``).
        # ``mode="json"`` renders it as a plain list, matching the pre-T002
        # wire shape exactly; every other field here is already a plain
        # str/dict, so this is a no-op for them.
        payload=payload.model_dump(exclude_none=True, mode="json"),
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
    )
