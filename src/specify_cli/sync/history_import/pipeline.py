"""Import-history orchestration (#2262).

`build_import_plan` runs the read-only half of the pipeline end to end —
SELECT → AUDIT (fail-closed) → SCAN → IDENTITY → SYNTHESIZE — and returns an
:class:`ImportPlan`: the resolved identity, the per-mission scans, and the full
ordered envelope stream that *would* be uploaded.

Both surfaces share this core: ``--dry-run`` builds the plan and reports it
(no upload); ``--apply`` builds the plan and hands the envelopes to the upload
stage (WP-Y5). Keeping the orchestration here keeps the CLI command thin and
lets the whole plan be tested without the CLI.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.delivery.receivers import DeliveryReceiver, HttpPoster, _requests_post
from specify_cli.sync.history_import.identity import ImportIdentity, resolve_import_identity
from specify_cli.sync.history_import.scan import MissionScan, scan_missions
from specify_cli.sync.history_import.synthesize import synthesize_streams
from specify_cli.sync.history_import.upload import (
    ImportProvenanceEntry,
    UploadReport,
    build_provenance_manifest,
    run_import_upload,
)


class ImportAuditBlocked(RuntimeError):
    """Raised when the fail-closed TeamSpace audit finds blocking findings.

    Carries the blocker records (each a dict with at least ``mission_slug`` and
    ``message``) so the caller can name them without re-running the audit.
    """

    def __init__(self, blockers: list[dict[str, object]]) -> None:
        self.blockers = blockers
        super().__init__(f"{len(blockers)} audit finding(s) must be resolved before import")


@dataclass(frozen=True)
class MissionSummary:
    """One row of the dry-run preview."""

    mission_slug: str
    prefix_source: str
    wp_count: int
    status_count: int
    # Malformed-frontmatter WP files the scan skipped (fail-loud, B3/#2884):
    # these MUST render in the report so skips never read as clean success.
    skipped_wp_files: tuple[str, ...] = ()

    @property
    def skipped_wp_count(self) -> int:
        return len(self.skipped_wp_files)


@dataclass(frozen=True)
class ImportPlan:
    """The read-only import plan: identity, scans, and the envelope stream.

    ``identity`` is ``None`` only for the empty plan (no eligible missions).
    """

    identity: ImportIdentity | None
    scans: tuple[MissionScan, ...]
    envelopes: tuple[dict[str, Any], ...]

    @property
    def is_empty(self) -> bool:
        return not self.scans

    @property
    def mission_count(self) -> int:
        return len(self.scans)

    @property
    def total_events(self) -> int:
        return len(self.envelopes)

    @property
    def skipped_wp_total(self) -> int:
        """Total malformed-frontmatter WP files skipped across all scans."""
        return sum(len(scan.skipped_wp_files) for scan in self.scans)

    def event_type_counts(self) -> dict[str, int]:
        return dict(Counter(str(env["event_type"]) for env in self.envelopes))

    def mission_summaries(self) -> list[MissionSummary]:
        return [
            MissionSummary(
                mission_slug=scan.mission_slug,
                prefix_source=str(scan.prefix_source),
                wp_count=len(scan.work_packages),
                status_count=len(scan.lane_transitions),
                skipped_wp_files=scan.skipped_wp_files,
            )
            for scan in self.scans
        ]


def build_import_plan(repo_root: Path, *, mission: str | None, apply: bool) -> ImportPlan:
    """SELECT → AUDIT → SCAN → IDENTITY → SYNTHESIZE for the selected missions.

    Raises :class:`ImportAuditBlocked` when the fail-closed audit finds blockers,
    and propagates ``MissionStateRepairError`` from selection. Returns an empty
    plan (no identity resolved) when nothing is eligible.
    """
    # Local import: the migration helpers pull a heavy dependency graph, and
    # keeping the bind lazy lets tests patch the seams on the source module.
    from specify_cli.migration.mission_state import _select_mission_dirs, _teamspace_audit_blockers

    mission_dirs = _select_mission_dirs(repo_root, scan_root=None, mission=mission)
    if not mission_dirs:
        return ImportPlan(identity=None, scans=(), envelopes=())

    blockers = _teamspace_audit_blockers(repo_root, scan_root=None, mission_dirs=mission_dirs)
    if blockers:
        raise ImportAuditBlocked(blockers)

    scans = tuple(scan_missions(mission_dirs))
    identity = resolve_import_identity(repo_root, [scan.mission_slug for scan in scans], apply=apply)
    envelopes = tuple(
        synthesize_streams(
            scans,
            project_uuid=identity.project_uuid,
            project_slug=identity.project_slug,
            repo_slug=identity.repo_slug,
        )
    )
    return ImportPlan(identity=identity, scans=scans, envelopes=envelopes)


@dataclass(frozen=True)
class ApplyResult:
    """The outcome of an ``--apply`` run: the plan, its provenance, the upload."""

    plan: ImportPlan
    manifest: list[ImportProvenanceEntry]
    report: UploadReport


def apply_import(
    repo_root: Path,
    *,
    mission: str | None,
    receiver: DeliveryReceiver,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = _requests_post,
    chunk_size: int | None = None,
) -> ApplyResult:
    """Materialize: build the plan (real identity), then preflight + upload.

    Raises :class:`ImportAuditBlocked` / ``MissionStateRepairError`` /
    ``ImportIdentityError`` (from the plan) or ``PreflightRejected`` (from the
    server preflight) — all fail-closed before or without a partial upload.
    """
    plan = build_import_plan(repo_root, mission=mission, apply=True)
    if plan.is_empty:
        return ApplyResult(plan=plan, manifest=[], report=UploadReport())

    manifest = build_provenance_manifest(plan.envelopes)
    upload_kwargs: dict[str, Any] = {"receiver": receiver, "server_url": server_url, "auth_token": auth_token, "poster": poster}
    if chunk_size is not None:
        upload_kwargs["chunk_size"] = chunk_size
    report = run_import_upload(plan.envelopes, **upload_kwargs)
    return ApplyResult(plan=plan, manifest=manifest, report=report)


def describe_plan(plan: ImportPlan) -> list[str]:
    """Render the dry-run preview as plain lines (no CLI dependency)."""
    if plan.is_empty or plan.identity is None:
        return ["No missions eligible for import."]

    identity_note = " (synthetic offline id — dry-run only)" if plan.identity.is_synthetic else ""
    # Skips must be impossible to read past: they mark the summary line itself,
    # not just a footnote (fail-loud, B3/#2884).
    skipped_note = f" · {plan.skipped_wp_total} WP file(s) SKIPPED" if plan.skipped_wp_total else ""
    lines = [
        f"Import plan for project {plan.identity.project_slug} [{plan.identity.project_uuid}]{identity_note}",
        f"{plan.mission_count} mission(s) → {plan.total_events} event(s){skipped_note}:",
    ]
    for summary in plan.mission_summaries():
        row = f"  • {summary.mission_slug}  [{summary.prefix_source}]  {summary.wp_count} WP, {summary.status_count} status"
        if summary.skipped_wp_count:
            row += f" · {summary.skipped_wp_count} WPs SKIPPED (malformed frontmatter: {', '.join(summary.skipped_wp_files)})"
        lines.append(row)
    counts = plan.event_type_counts()
    breakdown = ", ".join(f"{count} {event_type}" for event_type, count in sorted(counts.items()))
    lines.append(f"events to materialize: {breakdown}")
    return lines
