"""Dossier sync pipeline orchestration.

Wires indexer → event emission → body upload preparation
as a single pipeline invoked during feature-aware sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.core.saas_sync_config import sync_active
from specify_cli.dossier.manifest import ManifestSchemaError

if TYPE_CHECKING:
    from specify_cli.dossier.models import MissionDossier, MissionDossierSnapshot
    from specify_cli.identity.project import ProjectIdentity

    from .body_queue import OfflineBodyUploadQueue
    from .layout_generation import LayoutGenerationAuthority
    from .namespace import NamespaceRef, UploadOutcome
    from .project_context import ProjectSyncContext
    from .project_store import ProjectUnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class DossierSyncResult:
    """Result of a full dossier sync pipeline run."""

    dossier: MissionDossier | None
    events_emitted: int
    body_outcomes: list[UploadOutcome]
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.dossier is not None and not self.errors


_MANIFEST_SCHEMA_ERROR_TEMPLATE = (
    "expected-artifacts.yaml is schema-invalid for mission type {mission_type!r}"
    "{location}: {detail} Fix your expected-artifacts.yaml."
)


def _format_manifest_schema_error(mission_type: str, exc: ManifestSchemaError) -> str:
    """Render a schema-invalid-manifest ``ManifestSchemaError`` as one
    structured, user-legible, greppable line (#3542-B).

    ``Indexer.index_feature`` -> ``ManifestRegistry.load_manifest`` raises
    ``ManifestSchemaError`` (FR-016 / adversarial-review MAJOR fix) when
    ``expected-artifacts.yaml`` fails schema validation (e.g. a typo'd/extra
    key) -- a domain type, not a raw ``pydantic.ValidationError``, so callers
    can distinguish a genuine manifest-schema failure from an unrelated
    ``ValidationError`` (e.g. an ``ArtifactRef`` model-validator bug) that
    happens to propagate through the same call stack. Its typed ``origin``
    field names the manifest's source, and its chained ``__cause__`` is the
    underlying ``pydantic.ValidationError`` naming the bad key. This helper
    folds both into a single line so ``DossierSyncResult.errors`` carries a
    user-legible string rather than a raw exception repr, and so the
    caller's ``logger.warning(...)`` call is self-contained (no need to also
    format the traceback to be actionable).
    """
    detail = str(exc.__cause__ or exc).replace("\n", " ")
    return _MANIFEST_SCHEMA_ERROR_TEMPLATE.format(
        mission_type=mission_type, location=f" ({exc.origin})", detail=detail
    )


def _emit_artifact_events(
    dossier: MissionDossier,
    namespace_ref: NamespaceRef,
    step_id: str | None,
    ns_dict: dict[str, Any],
    *,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> int:
    """Emit indexed/missing events for every artifact in the dossier.

    Each artifact's emission is independently isolated (its own try/except)
    so one artifact's failure never blocks the rest — mirrors the original
    inline loop's per-artifact isolation. Returns the count of events
    successfully emitted (a non-``None`` result).

    The optional same-UoW project authority tuple is threaded through to the
    emitters unchanged; ``None`` means the caller carries no store-minted
    local-capture authority.
    """
    from specify_cli.dossier.events import emit_artifact_indexed, emit_artifact_missing

    events_emitted = 0
    for artifact in dossier.artifacts:
        if artifact.is_present:
            try:
                result = emit_artifact_indexed(
                    mission_slug=namespace_ref.mission_slug,
                    artifact_key=artifact.artifact_key,
                    artifact_class=artifact.artifact_class,
                    relative_path=artifact.relative_path,
                    content_hash_sha256=artifact.content_hash_sha256,
                    size_bytes=artifact.size_bytes,
                    step_id=step_id,
                    required_status=artifact.required_status,
                    namespace=ns_dict,
                    project_context=project_context,
                    project_unit=project_unit,
                    project_layout=project_layout,
                )
                if result is not None:
                    events_emitted += 1
            except Exception as e:
                logger.warning(
                    "Event emission failed for %s: %s",
                    artifact.relative_path,
                    e,
                )
        else:
            # Emit missing event for non-present required artifacts
            try:
                result = emit_artifact_missing(
                    mission_slug=namespace_ref.mission_slug,
                    artifact_key=artifact.artifact_key,
                    artifact_class=artifact.artifact_class,
                    expected_path_pattern=artifact.relative_path,
                    reason_code=artifact.error_reason or "not_found",
                    blocking=artifact.required_status == "required",
                    namespace=ns_dict,
                    project_context=project_context,
                    project_unit=project_unit,
                    project_layout=project_layout,
                )
                if result is not None:
                    events_emitted += 1
            except Exception as e:
                logger.warning(
                    "Missing event emission failed for %s: %s",
                    artifact.relative_path,
                    e,
                )
    return events_emitted


def _emit_snapshot(
    dossier: MissionDossier,
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    ns_dict: dict[str, Any],
    *,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> tuple[MissionDossierSnapshot | None, int]:
    """Compute, persist, and emit the dossier snapshot.

    Retains its own try/except so a snapshot failure never aborts the other
    pipeline steps. Returns ``(snapshot, events_emitted)`` — ``snapshot`` is
    ``None`` and ``events_emitted`` is ``0`` on failure.
    """
    from specify_cli.dossier.events import emit_snapshot_computed
    from specify_cli.dossier.snapshot import compute_snapshot, save_snapshot

    snapshot: MissionDossierSnapshot | None = None
    events_emitted = 0
    try:
        snapshot = compute_snapshot(dossier)
        save_snapshot(snapshot, feature_dir)
        dossier.latest_snapshot = snapshot.model_dump(mode="json")

        result = emit_snapshot_computed(
            mission_slug=namespace_ref.mission_slug,
            parity_hash_sha256=snapshot.parity_hash_sha256,
            total_artifacts=snapshot.total_artifacts,
            required_artifacts=snapshot.required_artifacts,
            required_present=snapshot.required_present,
            required_missing=snapshot.required_missing,
            optional_artifacts=snapshot.optional_artifacts,
            optional_present=snapshot.optional_present,
            completeness_status=snapshot.completeness_status,
            snapshot_id=snapshot.snapshot_id,
            namespace=ns_dict,
            project_context=project_context,
            project_unit=project_unit,
            project_layout=project_layout,
        )
        if result is not None:
            events_emitted += 1
    except Exception as e:
        logger.warning("Snapshot computation/emission failed for %s: %s", feature_dir, e)
    return snapshot, events_emitted


def _emit_drift(
    snapshot: MissionDossierSnapshot,
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    ns_dict: dict[str, Any],
    repo_root: Path,
    project_identity: ProjectIdentity,
    *,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> int:
    """Detect and emit parity drift against the baseline snapshot.

    Retains its own try/except so a drift-detection failure never aborts the
    other pipeline steps. Returns the count of events emitted (0 or 1).
    """
    from specify_cli.dossier.drift_detector import detect_drift
    from specify_cli.dossier.events import emit_parity_drift_detected

    events_emitted = 0
    try:
        has_drift, drift_info = detect_drift(
            mission_slug=namespace_ref.mission_slug,
            current_snapshot=snapshot,
            repo_root=repo_root,
            project_identity=project_identity,
            target_branch=namespace_ref.target_branch,
            mission_type=namespace_ref.mission_type,
            manifest_version=namespace_ref.manifest_version,
        )
        if has_drift and drift_info is not None:
            result = emit_parity_drift_detected(
                mission_slug=namespace_ref.mission_slug,
                local_parity_hash=drift_info["local_parity_hash"],
                baseline_parity_hash=drift_info["baseline_parity_hash"],
                missing_in_local=drift_info["missing_in_local"],
                missing_in_baseline=drift_info["missing_in_baseline"],
                severity=drift_info["severity"],
                namespace=ns_dict,
                project_context=project_context,
                project_unit=project_unit,
                project_layout=project_layout,
            )
            if result is not None:
                events_emitted += 1
    except Exception as e:
        logger.warning("Parity drift detection/emission failed for %s: %s", feature_dir, e)
    return events_emitted


def _prepare_bodies(
    dossier: MissionDossier,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    feature_dir: Path,
    *,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> tuple[list[UploadOutcome], list[str]]:
    """Prepare body uploads for the dossier's artifacts.

    Retains its own try/except so a body-upload-preparation failure never
    aborts the events already emitted. Returns ``(body_outcomes, errors)``.

    When the caller supplies the full explicit same-UoW authority tuple it is
    forwarded so ``prepare_body_uploads`` validates and uses that exact store
    decision; otherwise the legacy fail-closed consent lookup applies.
    """
    from .body_upload import prepare_body_uploads

    body_outcomes: list[UploadOutcome] = []
    errors: list[str] = []
    try:
        if project_context is not None and project_unit is not None and project_layout is not None:
            body_outcomes = prepare_body_uploads(
                artifacts=dossier.artifacts,
                namespace_ref=namespace_ref,
                body_queue=body_queue,
                feature_dir=feature_dir,
                project_context=project_context,
                project_unit=project_unit,
                project_layout=project_layout,
            )
        else:
            body_outcomes = prepare_body_uploads(
                artifacts=dossier.artifacts,
                namespace_ref=namespace_ref,
                body_queue=body_queue,
                feature_dir=feature_dir,
            )
    except Exception as e:
        logger.exception("Body upload preparation failed for %s", feature_dir)
        errors.append(f"body_upload_preparation_failed: {e}")
    return body_outcomes, errors


def sync_feature_dossier(
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    mission_type: str = "software-dev",
    step_id: str | None = None,
    *,
    repo_root: Path | None = None,
    project_identity: ProjectIdentity | None = None,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> DossierSyncResult:
    """Run full dossier sync: index → emit events → prepare body uploads.

    This is the ONLY entrypoint for body upload preparation.
    BackgroundSyncService only drains already-enqueued work.
    """
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry

    from .body_upload import log_upload_outcomes
    from .lint_report_staging import stage_charter_lint_report
    from .namespace import UploadStatus

    try:
        if project_context is None or project_unit is None or project_layout is None:
            raise ValueError("no explicit same-UoW project authority; hosted event emission will be withheld")
        from .project_context import validate_project_sync_context_authority

        validate_project_sync_context_authority(project_context)
        if project_unit.store_identity is not project_context.store_identity:
            raise ValueError("dossier project unit does not match the explicit project context")
        project_uuid = project_context.project_uuid.storage_token
        if namespace_ref.project_uuid != project_uuid:
            raise ValueError("dossier namespace belongs to another project")
        if body_queue.project_uuid != project_uuid:
            raise ValueError("dossier body queue belongs to another project")
        if project_identity is not None and project_identity.project_uuid is not None and str(project_identity.project_uuid) != project_uuid:
            raise ValueError("dossier identity belongs to another project")
    except (TypeError, ValueError) as exc:
        if project_context is None or project_unit is None or project_layout is None:
            logger.debug("Dossier event egress disabled: %s", exc)
        else:
            return DossierSyncResult(
                dossier=None,
                events_emitted=0,
                body_outcomes=[],
                errors=[f"dossier_project_context_invalid: {exc}"],
            )

    # Step 0: Stage the repo-global charter-lint decay report into this
    # mission's dossier BEFORE indexing, but only when the report was produced
    # for this mission (issue #2481, unblocks saas #392). Best-effort no-op.
    if stage_charter_lint_report(feature_dir, namespace_ref.mission_slug):
        logger.info(
            "Staged charter-lint decay report into dossier for %s",
            namespace_ref.mission_slug,
        )

    # Step 1: Index
    try:
        # #3525 Fold C: thread repo_root through so a configured org-pack
        # expected-artifacts.yaml override is honored by the dossier
        # completeness index, not just the governance gate.
        indexer = Indexer(ManifestRegistry(), repo_root=repo_root)
        dossier = indexer.index_feature(feature_dir, mission_type, step_id)
    except ManifestSchemaError as e:
        # #3542-B / adversarial-review MAJOR fix: a schema-invalid
        # expected-artifacts.yaml is an author-actionable misconfiguration,
        # not a genuine indexer bug -- this is the dominant runtime path
        # (fired on every status transition via
        # trigger_feature_dossier_sync_if_enabled, which is fire-and-forget
        # and never raises), so without this branch the failure was
        # previously invisible: caught by the generic `except Exception`
        # below, logged at ERROR with a full stack trace meant for real
        # bugs, and reduced to a bare `str(exc)` that names the bad key but
        # not the file. Catching the domain `ManifestSchemaError` type here
        # -- instead of the raw `pydantic.ValidationError` this branch used
        # to catch -- means a genuine `ArtifactRef`/`MissionDossier`
        # validator bug (which also raises `ValidationError`, but well
        # after the manifest already loaded successfully) is NOT
        # misattributed to "fix your expected-artifacts.yaml": it falls
        # through to the generic `except Exception` below instead, where it
        # belongs. WARNING + a structured, file-naming message keeps the
        # "never raises" contract intact while making the failure findable.
        schema_error = _format_manifest_schema_error(mission_type, e)
        logger.warning(schema_error)
        return DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
            errors=[schema_error],
        )
    except Exception as e:
        logger.exception("Indexer failed for %s", feature_dir)
        return DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
            errors=[str(e)],
        )

    ns_dict = namespace_ref.to_dict()
    events_emitted = 0

    # Step 2: Emit dossier events for present and missing artifacts
    events_emitted += _emit_artifact_events(
        dossier,
        namespace_ref,
        step_id,
        ns_dict,
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
    )

    # Step 3: Compute + emit snapshot (always) and drift (if baseline exists)
    snapshot, snapshot_events = _emit_snapshot(
        dossier,
        feature_dir,
        namespace_ref,
        ns_dict,
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
    )
    events_emitted += snapshot_events

    if snapshot is not None and repo_root is not None and project_identity is not None:
        events_emitted += _emit_drift(
            snapshot,
            feature_dir,
            namespace_ref,
            ns_dict,
            repo_root,
            project_identity,
            project_context=project_context,
            project_unit=project_unit,
            project_layout=project_layout,
        )

    # Step 4: Prepare body uploads
    body_outcomes, errors = _prepare_bodies(
        dossier,
        namespace_ref,
        body_queue,
        feature_dir,
        project_context=project_context,
        project_unit=project_unit,
        project_layout=project_layout,
    )

    # Per-artifact result logging (FR-012)
    if body_outcomes:
        log_upload_outcomes(body_outcomes, namespace_ref.mission_slug, logger)

    # Summary logging
    queued = sum(1 for o in body_outcomes if o.status == UploadStatus.QUEUED)
    skipped = sum(1 for o in body_outcomes if o.status == UploadStatus.SKIPPED)
    logger.info(
        "Dossier sync for %s: %d events emitted, %d bodies queued, %d skipped",
        namespace_ref.mission_slug,
        events_emitted,
        queued,
        skipped,
    )

    return DossierSyncResult(
        dossier=dossier,
        events_emitted=events_emitted,
        body_outcomes=body_outcomes,
        errors=errors,
    )


def trigger_feature_dossier_sync_if_enabled(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
    mission_type: str = "software-dev",
    step_id: str | None = None,
) -> DossierSyncResult | None:
    """Fire-and-forget dossier sync triggered after feature artifact mutations.

    Never raises. Logs failures. The historical function name is retained for
    callers, but this path performs project-isolated local capture only: the
    machine SaaS flag and project egress decision are enforced later by the
    canonical dispatcher and therefore cannot suppress local dossier capture.

    When the sync surface is inactive (``not sync_active()``) this short-circuits
    BEFORE any body-capture work (#3470, FR-007/FR-008). On a bare install no
    disable var is set, so keying the guard on the disable vars would leave the
    body-outbox ``RuntimeError`` traceback live on the default path — hence the
    gate is keyed on ``sync_active()``. This is a gated early-return, NOT a
    ``try/except`` widen: when active, the real body path (and its genuine
    ``_require_project_destination`` error surfacing, C-003) is untouched.
    """
    if not sync_active():
        return None

    try:
        from specify_cli.core.paths import get_feature_target_branch
        from specify_cli.mission import get_mission_type
        from specify_cli.sync.namespace import NamespaceRef, resolve_manifest_version
        from specify_cli.identity.project import resolve_identity
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue
        from specify_cli.sync.project_store import ProjectSyncStore

        # Background dossier sync: resolve identity WITHOUT persisting (#2263,
        # FR-001/FR-003) — a fire-and-forget read path must not dirty config.yaml.
        identity = resolve_identity(repo_root)
        if identity.project_uuid is None:
            logger.warning("No project UUID; skipping dossier sync")
            return None

        target_branch = get_feature_target_branch(repo_root, mission_slug)
        resolved_mission = get_mission_type(feature_dir) or mission_type
        manifest_version = resolve_manifest_version(resolved_mission)

        namespace_ref = NamespaceRef.from_context(
            identity=identity,
            mission_slug=mission_slug,
            target_branch=target_branch,
            mission_type=resolved_mission,
            manifest_version=manifest_version,
        )

        # Use one verified project store and one short-lived UoW for local body
        # capture.  No transport happens here; WP08 drains the resulting task
        # later through the canonical body gate after revalidating context.
        store = ProjectSyncStore(str(identity.project_uuid))
        layout = store.layout_generation()
        with store.unit_of_work() as unit:
            context = store.create_context_from_unit(unit)
            body_queue = OfflineBodyUploadQueue(unit, layout)
            return sync_feature_dossier(
                feature_dir=feature_dir,
                namespace_ref=namespace_ref,
                body_queue=body_queue,
                mission_type=resolved_mission,
                step_id=step_id,
                repo_root=repo_root,
                project_identity=identity,
                project_context=context,
                project_unit=unit,
                project_layout=layout,
            )
    except Exception as e:
        logger.warning("Dossier sync failed for %s: %s", mission_slug, e)
        return None
