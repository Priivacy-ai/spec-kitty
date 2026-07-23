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

from specify_cli.sync.history_import.identity import ImportIdentity, resolve_import_identity
from specify_cli.sync.history_import.scan import MissionScan, scan_missions
from specify_cli.sync.history_import.synthesize import synthesize_streams


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

    def event_type_counts(self) -> dict[str, int]:
        return dict(Counter(str(env["event_type"]) for env in self.envelopes))

    def mission_summaries(self) -> list[MissionSummary]:
        return [
            MissionSummary(
                mission_slug=scan.mission_slug,
                prefix_source=str(scan.prefix_source),
                wp_count=len(scan.work_packages),
                status_count=len(scan.lane_transitions),
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


def describe_plan(plan: ImportPlan) -> list[str]:
    """Render the dry-run preview as plain lines (no CLI dependency)."""
    if plan.is_empty or plan.identity is None:
        return ["No missions eligible for import."]

    identity_note = " (synthetic offline id — dry-run only)" if plan.identity.is_synthetic else ""
    lines = [
        f"Import plan for project {plan.identity.project_slug} [{plan.identity.project_uuid}]{identity_note}",
        f"{plan.mission_count} mission(s) → {plan.total_events} event(s):",
    ]
    for summary in plan.mission_summaries():
        lines.append(f"  • {summary.mission_slug}  [{summary.prefix_source}]  {summary.wp_count} WP, {summary.status_count} status")
    counts = plan.event_type_counts()
    breakdown = ", ".join(f"{count} {event_type}" for event_type, count in sorted(counts.items()))
    lines.append(f"events to materialize: {breakdown}")
    return lines
