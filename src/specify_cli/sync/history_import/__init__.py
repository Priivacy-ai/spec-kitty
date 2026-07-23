"""Historical-import pipeline for ``spec-kitty sync import-history`` (#2262).

A first sync registers a remote project/build but leaves it with zero
materialized missions — the SaaS materializer refuses to fabricate a
WorkPackage from a status event with no prior create. This package emits the
missing ``MissionCreated → WPCreated[] → WPStatusChanged[]`` prefix so
historical local work populates the projection.

Stages (see issue #2262 §3.3):

* WP-Y2 — :mod:`.scan`: the hybrid SCAN — read the on-disk lifecycle prefix
  where present, synthesize it from ``meta.json`` + ``tasks/WP*.md`` where
  absent, and drop local-only lifecycle events.
* WP-Y3 — :mod:`.synthesize`: turn a :class:`MissionScan` into the ordered,
  deterministic ``MissionCreated → WPCreated[] → WPStatusChanged[]`` envelope
  stream (INV-3 / INV-4).
* WP-Y4 — :mod:`.identity`: resolve the ``(project_uuid, project_slug,
  repo_slug)`` trio — real persisted UUID on ``--apply`` (INV-5), synthetic
  offline UUID for dry-run, never persisting on the read path (INV-2).
* :mod:`.pipeline`: ``build_import_plan`` runs SELECT → AUDIT → SCAN →
  IDENTITY → SYNTHESIZE and returns the :class:`ImportPlan` both ``--dry-run``
  and ``--apply`` consume.

Later slices add PROVENANCE, PREFLIGHT, UPLOAD, and REPORT.
"""

from __future__ import annotations

from specify_cli.sync.history_import.identity import (
    ImportIdentity,
    ImportIdentityError,
    resolve_import_identity,
)
from specify_cli.sync.history_import.pipeline import (
    ApplyResult,
    ImportAuditBlocked,
    ImportPlan,
    apply_import,
    build_import_plan,
    describe_plan,
)
from specify_cli.sync.history_import.upload import (
    PreflightRejected,
    ImportProvenanceEntry,
    UploadReport,
    build_provenance_manifest,
    run_import_upload,
    run_server_preflight,
    upload_envelopes,
)
from specify_cli.sync.history_import.scan import (
    MissionScan,
    MissionScanError,
    PrefixSource,
    ScannedWorkPackage,
    scan_mission,
    scan_missions,
)
from specify_cli.sync.history_import.synthesize import (
    dry_run_project_uuid,
    synthesize_mission_stream,
    synthesize_streams,
)

__all__ = [
    "ApplyResult",
    "ImportAuditBlocked",
    "ImportIdentity",
    "ImportIdentityError",
    "ImportPlan",
    "MissionScan",
    "MissionScanError",
    "PrefixSource",
    "PreflightRejected",
    "ImportProvenanceEntry",
    "ScannedWorkPackage",
    "UploadReport",
    "apply_import",
    "build_import_plan",
    "build_provenance_manifest",
    "describe_plan",
    "dry_run_project_uuid",
    "resolve_import_identity",
    "run_import_upload",
    "run_server_preflight",
    "scan_mission",
    "scan_missions",
    "synthesize_mission_stream",
    "synthesize_streams",
    "upload_envelopes",
]
