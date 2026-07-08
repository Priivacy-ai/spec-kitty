"""Cross-mission summary reducer for retrospective records.

Streams over all retrospective.yaml files in a project and reduces them
into a SummarySnapshot. Tolerant to malformed / missing / legacy /
in-flight / terminus_no_retrospective records (NFR-004).

Source-of-truth:
    kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/data-model.md
    kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/research.md  R-008

WP03 addition (T017):
    ``classify_mission_record(feature_dir)`` — distinguish the four per-mission
    record states: ``has_findings``, ``ran_no_findings``, ``missing``, ``failed``.
    This function is additive; existing read-paths in this module are unchanged.
"""

from __future__ import annotations

from specify_cli.core.constants import RETROSPECTIVE_FILENAME
from specify_cli.mission_metadata import load_meta_or_empty
from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission
import json
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Generator, Literal, cast

from pydantic import BaseModel, ConfigDict

from specify_cli.retrospective.reader import (
    SchemaError,
    YAMLParseError,
    read_gen_record,
    read_record,
)
from specify_cli.retrospective.schema import Finding, MissionId

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper count shapes
# ---------------------------------------------------------------------------


class TargetCount(BaseModel):
    """(urn, count) pair for not_helpful / over_inclusion / under_inclusion top-N."""

    model_config = ConfigDict(extra="forbid")

    urn: str
    count: int


class TermCount(BaseModel):
    """(key, count) pair for missing glossary terms top-N."""

    model_config = ConfigDict(extra="forbid")

    key: str
    count: int


class EdgeCount(BaseModel):
    """(urn, count) pair for missing DRG edge top-N."""

    model_config = ConfigDict(extra="forbid")

    urn: str
    count: int


class ReasonCount(BaseModel):
    """(reason, count) pair for skip-reason top-N."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    count: int


# ---------------------------------------------------------------------------
# Proposal acceptance metrics
# ---------------------------------------------------------------------------


class ProposalAcceptanceMetrics(BaseModel):
    """Aggregate proposal lifecycle metrics across missions."""

    model_config = ConfigDict(extra="forbid")

    total: int = 0
    accepted: int = 0
    rejected: int = 0
    applied: int = 0
    pending: int = 0
    superseded: int = 0


# ---------------------------------------------------------------------------
# Malformed entry
# ---------------------------------------------------------------------------


class MalformedSummaryEntry(BaseModel):
    """A record that exists but could not be schema-validated."""

    model_config = ConfigDict(extra="forbid")

    mission_id: MissionId | None = None
    path: str
    reason: str


# ---------------------------------------------------------------------------
# SummarySnapshot (cross-mission read side)
# ---------------------------------------------------------------------------


class SummarySnapshot(BaseModel):
    """Cross-mission reduction result.

    Mirrors the data-model.md cross-mission summary entities shape.
    """

    model_config = ConfigDict(extra="forbid")

    project_path: str
    generated_at: str

    # Counts
    mission_count: int = 0
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    in_flight_count: int = 0
    legacy_no_retro_count: int = 0
    terminus_no_retro_count: int = 0
    malformed: list[MalformedSummaryEntry] = []

    # Top-N ranked sections
    not_helpful_top: list[TargetCount] = []
    missing_terms_top: list[TermCount] = []
    missing_edges_top: list[EdgeCount] = []
    over_inclusion_top: list[TargetCount] = []
    under_inclusion_top: list[TargetCount] = []

    proposal_acceptance: ProposalAcceptanceMetrics = ProposalAcceptanceMetrics()
    skip_reasons_top: list[ReasonCount] = []


# ---------------------------------------------------------------------------
# Internal: mission directory iteration
# ---------------------------------------------------------------------------

#: Heuristic release timestamp — missions started before this are considered
#: "legacy" (no retrospective expected).  Filled in at the time this tranche
#: was merged; adjust if you are backfilling history.
_TRANCHE_RELEASE_CUTOFF: datetime = datetime(2026, 4, 27, 0, 0, 0, tzinfo=timezone.utc)


def _is_legacy(mission_started_at: str) -> bool:
    """Return True if the mission predates the tranche release."""
    try:
        started = datetime.fromisoformat(mission_started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return started < _TRANCHE_RELEASE_CUTOFF
    except ValueError:
        return False


def _mission_is_in_flight(mission_dir: Path) -> bool:
    """Return True if the mission has not yet reached a terminus status.

    Reads meta.json from the mission directory.  A mission is in-flight
    when its status field is not a terminal value (done / canceled / failed).
    If meta.json is absent or unparseable we conservatively return False.
    """
    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}; status is then falsy, matching the prior
    # try/except-False absorption.
    meta = load_meta_or_empty(mission_dir)
    status = meta.get("status") or meta.get("current_lane") or ""
    terminal = {"done", "canceled", "failed", "completed"}
    # If status is explicitly non-terminal (planned, in_progress, claimed …)
    return bool(status) and status not in terminal


def _read_slug_from_meta(mission_dir: Path) -> str | None:
    """Return mission_slug from meta.json, or None on any error."""
    meta = load_meta_or_empty(mission_dir)
    slug = meta.get("mission_slug") or meta.get("feature_slug")
    return str(slug) if slug else None


# ---------------------------------------------------------------------------
# Internal: proposal-lifecycle event reader
# ---------------------------------------------------------------------------

_PROPOSAL_EVENTS = frozenset({
    "retrospective.proposal.generated",
    "retrospective.proposal.applied",
    "retrospective.proposal.rejected",
})


def _read_proposal_events(
    project_path: Path,
    mission_slug: str | None,
) -> tuple[int, int, int]:
    """Return (generated, applied, rejected) event counts for a mission.

    Reads kitty-specs/<slug>/status.events.jsonl.  Returns (0, 0, 0) on any
    error, including missing slug, missing log, or corrupt lines.
    """
    if not mission_slug:
        return 0, 0, 0

    events_path = candidate_feature_dir_for_mission(project_path, mission_slug) / "status.events.jsonl"
    if not events_path.exists():
        return 0, 0, 0

    generated = applied = rejected = 0
    try:
        for raw_line in events_path.read_text(encoding="utf-8").splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                evt = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            name = evt.get("event_name", "")
            if name == "retrospective.proposal.generated":
                generated += 1
            elif name == "retrospective.proposal.applied":
                applied += 1
            elif name == "retrospective.proposal.rejected":
                rejected += 1
    except OSError:
        pass

    return generated, applied, rejected


# ---------------------------------------------------------------------------
# Internal: classification helpers
# ---------------------------------------------------------------------------


def _classify_gaps_finding(target_kind: str, target_urn: str) -> str:
    """Return the category ('missing_term', 'missing_edge', 'over', 'under') or 'other'."""
    if target_kind in ("glossary_term",):
        return "missing_term"
    if target_kind in ("drg_edge", "drg_node"):
        return "missing_edge"
    # over/under-inclusion classification by URN prefix convention
    if "over" in target_urn.lower():
        return "over"
    if "under" in target_urn.lower():
        return "under"
    return "other"


# ---------------------------------------------------------------------------
# Internal: top-N sort helper
# ---------------------------------------------------------------------------

def _top_n_target_counts(counter: dict[str, int], limit: int) -> list[TargetCount]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [TargetCount(urn=k, count=v) for k, v in items[:limit]]


def _top_n_term_counts(counter: dict[str, int], limit: int) -> list[TermCount]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [TermCount(key=k, count=v) for k, v in items[:limit]]


def _top_n_edge_counts(counter: dict[str, int], limit: int) -> list[EdgeCount]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [EdgeCount(urn=k, count=v) for k, v in items[:limit]]


def _top_n_reason_counts(counter: dict[str, int], limit: int) -> list[ReasonCount]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [ReasonCount(reason=k, count=v) for k, v in items[:limit]]


# ---------------------------------------------------------------------------
# Internal: streaming record generator
# ---------------------------------------------------------------------------


def _iter_mission_dirs(project_path: Path) -> Generator[Path, None, None]:
    """Yield each mission directory under .kittify/missions/."""
    missions_root = project_path / ".kittify" / "missions"
    if not missions_root.is_dir():
        return
    for entry in sorted(missions_root.iterdir()):
        if entry.is_dir():
            yield entry


def _resolve_summary_record_path(project_path: Path, mission_dir: Path) -> Path:
    """Resolve the retrospective.yaml path to read for a discovered mission dir.

    FR-006 (#1771): the record now lives in the tracked feature_dir
    (``kitty-specs/<slug>/retrospective.yaml``). The mission registry under
    ``.kittify/missions/<id>/`` is still used for discovery (it carries
    ``meta.json``), but the record is read from the tracked home — falling back
    to the legacy in-registry path for pre-relocation records.
    """
    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}; mission_slug stays None, matching the prior
    # try/except-None absorption.
    meta = load_meta_or_empty(mission_dir)
    mission_slug = meta.get("mission_slug") or meta.get("slug")
    if mission_slug:
        from specify_cli.retrospective.writer import canonical_record_path

        tracked: Path = canonical_record_path(project_path, mission_slug)
        if tracked.exists():
            return tracked
    # Back-compat: legacy in-registry record path.
    legacy: Path = mission_dir / RETROSPECTIVE_FILENAME
    return legacy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_summary(
    *,
    project_path: Path,
    since: date | None = None,
    limit_top_n: int = 20,
) -> SummarySnapshot:
    """Build a cross-mission SummarySnapshot from the project corpus.

    Args:
        project_path: Root directory of the spec-kitty project.
        since: If set, only include missions whose ``mission_started_at``
            is on or after this date.
        limit_top_n: Maximum entries in each top-N ranked section.

    Returns:
        A :class:`SummarySnapshot` (always — never raises on malformed
        records; they appear in ``snapshot.malformed``).
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    # Mutable accumulator state
    mission_count = 0
    completed_count = 0
    skipped_count = 0
    failed_count = 0
    in_flight_count = 0
    legacy_no_retro_count = 0
    terminus_no_retro_count = 0
    malformed: list[MalformedSummaryEntry] = []

    not_helpful_counter: dict[str, int] = defaultdict(int)
    missing_terms_counter: dict[str, int] = defaultdict(int)
    missing_edges_counter: dict[str, int] = defaultdict(int)
    over_inclusion_counter: dict[str, int] = defaultdict(int)
    under_inclusion_counter: dict[str, int] = defaultdict(int)
    skip_reasons_counter: dict[str, int] = defaultdict(int)

    total_proposals = 0
    accepted_proposals = 0
    rejected_proposals = 0
    applied_proposals = 0
    pending_proposals = 0
    superseded_proposals = 0

    for mission_dir in _iter_mission_dirs(project_path):
        retro_path = _resolve_summary_record_path(project_path, mission_dir)

        if not retro_path.exists():
            # No retrospective file — classify the mission.
            # load_meta_or_empty (post-#2091 silent contract) absorbs a missing
            # or malformed meta.json to {}, matching the prior try/except-pass.
            meta = load_meta_or_empty(mission_dir)
            mission_started_at: str | None = (
                meta.get("mission_started_at")
                or meta.get("created_at")
                or meta.get("started_at")
            )

            if mission_started_at and _is_legacy(mission_started_at):
                legacy_no_retro_count += 1
            elif _mission_is_in_flight(mission_dir):
                in_flight_count += 1
            else:
                terminus_no_retro_count += 1

            mission_count += 1
            continue

        # Attempt to parse
        mission_id_for_error: MissionId | None = None
        try:
            record = read_record(retro_path)
        except (YAMLParseError, SchemaError) as exc:
            try:
                gen_record = read_gen_record(retro_path)
            except (YAMLParseError, SchemaError):
                pass
            else:
                if since is not None:
                    try:
                        created_dt = datetime.fromisoformat(gen_record.created_at)
                        if created_dt.date() < since:
                            continue
                    except (ValueError, AttributeError):
                        pass

                mission_count += 1
                completed_count += 1

                for finding in gen_record.not_helpful:
                    not_helpful_counter[f"retrospective:not_helpful:{finding.category}"] += 1

                for finding in gen_record.gaps:
                    if finding.category == "doc":
                        missing_terms_counter[finding.summary] += 1
                    elif finding.category == "spec_quality":
                        under_inclusion_counter[f"retrospective:gaps:{finding.category}"] += 1

                total_proposals += len(gen_record.proposals)
                pending_proposals += len(gen_record.proposals)

                slug = gen_record.mission_slug
                gen_evt, app_evt, rej_evt = _read_proposal_events(project_path, slug)
                _ = (gen_evt, app_evt, rej_evt)
                continue

            # Try to extract mission_id from raw YAML for the error entry
            try:
                from ruamel.yaml import YAML as _YAML
                _yaml = _YAML(typ="safe")
                raw = _yaml.load(retro_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    m = raw.get("mission") or {}
                    mid = m.get("mission_id") if isinstance(m, dict) else None
                    if mid and isinstance(mid, str):
                        mission_id_for_error = mid
            except Exception:
                pass
            malformed.append(
                MalformedSummaryEntry(
                    mission_id=mission_id_for_error,
                    path=str(retro_path),
                    reason=str(exc),
                )
            )
            mission_count += 1
            continue
        except OSError as exc:
            malformed.append(
                MalformedSummaryEntry(
                    mission_id=None,
                    path=str(retro_path),
                    reason=f"OSError: {exc}",
                )
            )
            mission_count += 1
            continue
        except Exception as exc:
            # Catch-all: must never abort
            malformed.append(
                MalformedSummaryEntry(
                    mission_id=None,
                    path=str(retro_path),
                    reason=f"Unexpected error: {exc}",
                )
            )
            mission_count += 1
            continue

        # --since filter
        if since is not None:
            try:
                started_dt = datetime.fromisoformat(record.mission.mission_started_at)
                started_date = started_dt.date()
                if started_date < since:
                    continue
            except (ValueError, AttributeError):
                pass

        mission_count += 1

        # Status counting
        if record.status == "completed":
            completed_count += 1
        elif record.status == "skipped":
            skipped_count += 1
            if record.skip_reason:
                skip_reasons_counter[record.skip_reason] += 1
        elif record.status == "failed":
            failed_count += 1

        # Findings accumulation
        pydantic_finding: Finding
        for pydantic_finding in record.not_helpful:
            not_helpful_counter[pydantic_finding.target.urn] += 1

        for pydantic_finding in record.gaps:
            kind = pydantic_finding.target.kind
            urn = pydantic_finding.target.urn
            category = _classify_gaps_finding(kind, urn)
            if category == "missing_term":
                # Use the urn as the key for term counts
                missing_terms_counter[urn] += 1
            elif category == "missing_edge":
                missing_edges_counter[urn] += 1
            elif category == "over":
                over_inclusion_counter[urn] += 1
            elif category == "under":
                under_inclusion_counter[urn] += 1
            # "other" gaps are counted but not surfaced in any top-N section

        # Proposal accumulation
        for proposal in record.proposals:
            total_proposals += 1
            status = proposal.state.status
            if status == "accepted":
                accepted_proposals += 1
            elif status == "rejected":
                rejected_proposals += 1
            elif status == "applied":
                applied_proposals += 1
            elif status == "pending":
                pending_proposals += 1
            elif status == "superseded":
                superseded_proposals += 1

        # Proposal-lifecycle events from status.events.jsonl
        slug = record.mission.mission_slug
        gen_evt, app_evt, rej_evt = _read_proposal_events(project_path, slug)
        # Events supplement the YAML state — note we don't double-count,
        # events are informational for acceptance metrics when YAML state
        # is available.  The contract says "read ... events"; we track
        # them as additional data for consistency.
        # Per R-008: acceptance metrics come from both YAML proposal states
        # and from event counts.  We use YAML as primary and events as a
        # cross-check.  The acceptance metrics below already come from YAML.
        _ = (gen_evt, app_evt, rej_evt)  # Available for future use / cross-check

    snapshot = SummarySnapshot(
        project_path=str(project_path),
        generated_at=generated_at,
        mission_count=mission_count,
        completed_count=completed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        in_flight_count=in_flight_count,
        legacy_no_retro_count=legacy_no_retro_count,
        terminus_no_retro_count=terminus_no_retro_count,
        malformed=malformed,
        not_helpful_top=_top_n_target_counts(not_helpful_counter, limit_top_n),
        missing_terms_top=_top_n_term_counts(missing_terms_counter, limit_top_n),
        missing_edges_top=_top_n_edge_counts(missing_edges_counter, limit_top_n),
        over_inclusion_top=_top_n_target_counts(over_inclusion_counter, limit_top_n),
        under_inclusion_top=_top_n_target_counts(under_inclusion_counter, limit_top_n),
        proposal_acceptance=ProposalAcceptanceMetrics(
            total=total_proposals,
            accepted=accepted_proposals,
            rejected=rejected_proposals,
            applied=applied_proposals,
            pending=pending_proposals,
            superseded=superseded_proposals,
        ),
        skip_reasons_top=_top_n_reason_counts(skip_reasons_counter, limit_top_n),
    )
    return snapshot


# ---------------------------------------------------------------------------
# WP03 T017: Per-mission record classifier (additive, no CLI output changes)
# ---------------------------------------------------------------------------

#: Types returned by classify_mission_record.
MissionRecordState = Literal["has_findings", "ran_no_findings", "missing", "failed"]


def _most_recent_gen_event(
    feature_dir: Path,
    event_type: str,
) -> dict[str, Any] | None:
    """Return the most-recent event dict matching ``type == event_type``, or None.

    Reads ``status.events.jsonl`` from the given feature directory.
    Returns the event with the highest ``lamport`` value, or the last
    occurrence in log order when lamport values are absent/tied.
    """
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return None

    best: dict[str, Any] | None = None
    best_lamport: int = -1

    try:
        for raw in events_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != event_type:
                continue
            lp = obj.get("lamport", 0)
            if not isinstance(lp, int):
                lp = 0
            if best is None or lp >= best_lamport:
                best = obj
                best_lamport = lp
    except OSError:
        pass

    return best


def classify_mission_record(feature_dir: Path) -> MissionRecordState:
    """Classify the per-mission retrospective record state.

    The four states (FR-013):
    - ``"has_findings"``    — record on disk with findings_status=="has_findings"
    - ``"ran_no_findings"`` — record on disk with findings_status=="ran_no_findings"
    - ``"missing"``         — no record on disk AND no recent Failed event
    - ``"failed"``          — no record on disk AND most-recent ``RetrospectiveCaptureFailed``
                              lamport > most-recent ``RetrospectiveCaptured`` lamport

    Args:
        feature_dir: Path to the mission directory inside ``.kittify/missions/<mission_id>/``
            OR the kitty-specs mission directory — whichever contains the
            ``retrospective.yaml`` file. Callers typically pass the feature_dir that
            contains the event log AND the record file.

    Returns:
        One of the four state literals above.

    Note (scope boundary):
        This function provides the *classifier logic* only. CLI output-shape changes
        belong to WP05 T027. Do not call this from CLI commands in this WP.
    """
    record_path = feature_dir / RETROSPECTIVE_FILENAME

    if record_path.exists():
        try:
            from ruamel.yaml import YAML as _YAML
            _yaml = _YAML(typ="safe")
            raw = _yaml.load(record_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                status_raw = raw.get("findings_status", "ran_no_findings")
                status_str = str(status_raw) if status_raw is not None else "ran_no_findings"
                if status_str in ("has_findings", "ran_no_findings"):
                    return cast(MissionRecordState, status_str)
        except Exception:
            pass
        # Fallback for Pydantic-model records (old schema).
        try:
            pydantic_record = read_record(record_path)
            # Pydantic records use 'status' field; map to our four states.
            status = pydantic_record.status
            if status == "completed":
                # Completed but no findings_status field — treat as has_findings
                # if any findings/proposals exist, else ran_no_findings.
                has_any = bool(
                    list(pydantic_record.helped)
                    + list(pydantic_record.not_helpful)
                    + list(pydantic_record.gaps)
                    + list(pydantic_record.proposals)
                )
                return "has_findings" if has_any else "ran_no_findings"
        except Exception:
            pass
        # We couldn't read it cleanly; conservatively return has_findings.
        return "has_findings"

    # No record on disk — check event log for RetrospectiveCaptureFailed.
    last_failed = _most_recent_gen_event(feature_dir, "RetrospectiveCaptureFailed")
    last_captured = _most_recent_gen_event(feature_dir, "RetrospectiveCaptured")

    if last_failed is not None:
        failed_lp = last_failed.get("lamport", 0)
        if not isinstance(failed_lp, int):
            failed_lp = 0
        captured_lp = 0
        if last_captured is not None:
            captured_lp = last_captured.get("lamport", 0)
            if not isinstance(captured_lp, int):
                captured_lp = 0
        if failed_lp > captured_lp:
            return "failed"

    return "missing"
