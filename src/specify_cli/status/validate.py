"""Validation engine for the canonical status model.

Provides schema validation, transition legality checks, done-evidence
completeness verification, materialization drift detection, and
derived-view drift comparison. Each function returns a list of
human-readable finding strings that reference specific event_ids.

This module is a library -- it reports problems but never modifies data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from specify_cli.spec_kitty_events import normalize_event_id

from .models import ULID_PATTERN
from .transitions import ALLOWED_TRANSITIONS, CANONICAL_LANES

STATUS_BLOCK_START = "<!-- status-model:start -->"
STATUS_BLOCK_END = "<!-- status-model:end -->"


@dataclass
class ValidationResult:
    """Aggregate result of all validation checks."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    phase_source: str = ""

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def validate_event_schema(event: dict) -> list[str]:
    """Validate a single event dict against the StatusEvent schema.

    Checks:
    - All required fields present: event_id, feature_slug, wp_id,
      from_lane, to_lane, at, actor, force, execution_mode
    - event_id is valid event ID (ULID Crockford base32, or UUID)
    - from_lane and to_lane are canonical lane values (never aliases)
    - at is valid ISO 8601 timestamp
    - force is boolean
    - execution_mode is "worktree" or "direct_repo"
    - If force=True, reason must be non-empty string
    - If from_lane=for_review and to_lane=in_progress, review_ref must be present

    Extra unknown fields are NOT flagged (forward-compatible).
    """
    findings: list[str] = []
    required_fields = [
        "event_id",
        "feature_slug",
        "wp_id",
        "from_lane",
        "to_lane",
        "at",
        "actor",
        "force",
        "execution_mode",
    ]
    for f in required_fields:
        if f not in event:
            findings.append(f"Missing required field: {f}")

    # ULID format check
    event_id = event.get("event_id", "")
    if event_id and not _is_valid_event_id(str(event_id)):
        findings.append(f"Invalid event ID format: {event_id}")

    # Canonical lane check (aliases like "doing" are NOT canonical)
    canonical_set = set(CANONICAL_LANES)
    for lane_field in ("from_lane", "to_lane"):
        val = event.get(lane_field)
        if val is not None and val not in canonical_set:
            findings.append(f"{lane_field} is not canonical: {val}")

    # ISO 8601 timestamp check
    at_val = event.get("at")
    if at_val is not None:
        if not _is_valid_iso8601(str(at_val)):
            findings.append(f"Event {event_id}: invalid ISO 8601 timestamp: {at_val}")

    # force must be boolean
    force_val = event.get("force")
    if force_val is not None and not isinstance(force_val, bool):
        findings.append(f"Event {event_id}: force must be boolean, got {type(force_val).__name__}")

    # execution_mode check
    exec_mode = event.get("execution_mode")
    if exec_mode is not None and exec_mode not in ("worktree", "direct_repo"):
        findings.append(
            f"Event {event_id}: execution_mode must be 'worktree' or 'direct_repo', got '{exec_mode}'"
        )

    # Force audit check: force=true requires reason
    if event.get("force") is True and not event.get("reason"):
        findings.append(f"Event {event_id}: force=true without reason")

    # Review ref check: for_review -> in_progress requires review_ref
    if (
        event.get("from_lane") == "for_review"
        and event.get("to_lane") == "in_progress"
    ):
        if not event.get("review_ref"):
            findings.append(
                f"Event {event_id}: for_review->in_progress without review_ref"
            )

    return findings


def validate_transition_legality(events: list[dict]) -> list[str]:
    """Replay events in order and check each transition is legal.

    Uses ALLOWED_TRANSITIONS from status/transitions.py.
    Force transitions are always legal (skipped).
    Events are sorted by (at, event_id) before checking.

    Missing from_lane or to_lane is skipped (caught by schema validator).
    """
    findings: list[str] = []

    # Sort by (at, event_id) to ensure correct replay order
    sorted_events = sorted(
        events, key=lambda e: (e.get("at", ""), e.get("event_id", ""))
    )

    for event in sorted_events:
        from_lane = event.get("from_lane")
        to_lane = event.get("to_lane")
        event_id = event.get("event_id", "unknown")
        force = event.get("force", False)

        # Skip events with missing lane fields (schema validator catches these)
        if from_lane is None or to_lane is None:
            continue

        if force:
            # Forced transitions are legal but noteworthy
            continue

        if (from_lane, to_lane) not in ALLOWED_TRANSITIONS:
            findings.append(
                f"Event {event_id}: illegal transition {from_lane} -> {to_lane}"
            )

    return findings


def validate_done_evidence(events: list[dict]) -> list[str]:
    """Check all done-transitions have evidence or force flag.

    Events not transitioning to done are skipped.
    Force-flagged done transitions bypass the evidence requirement.
    """
    findings: list[str] = []

    for event in events:
        if event.get("to_lane") != "done":
            continue

        event_id = event.get("event_id", "unknown")
        force = event.get("force", False)

        if force:
            continue  # Forced done transitions bypass evidence requirement

        evidence = event.get("evidence")
        if not evidence:
            findings.append(
                f"Event {event_id}: done without evidence (not forced)"
            )
            continue

        # Check evidence structure
        if not isinstance(evidence, dict):
            findings.append(
                f"Event {event_id}: done evidence is not a dict"
            )
            continue

        review = evidence.get("review")
        if not review:
            findings.append(
                f"Event {event_id}: done evidence missing review section"
            )
        elif not isinstance(review, dict):
            findings.append(
                f"Event {event_id}: done evidence review is not a dict"
            )
        else:
            if not review.get("reviewer"):
                findings.append(
                    f"Event {event_id}: done evidence missing reviewer identity"
                )
            if not review.get("verdict"):
                findings.append(
                    f"Event {event_id}: done evidence missing verdict"
                )
            if not review.get("reference"):
                findings.append(
                    f"Event {event_id}: done evidence missing approval reference"
                )

    return findings


def validate_materialization_drift(feature_dir: Path) -> list[str]:
    """Compare status.json on disk vs reducer output from the event log.

    Returns findings describing any drift detected. An empty list means
    no drift.
    """
    from .reducer import SNAPSHOT_FILENAME, reduce
    from .store import EVENTS_FILENAME, read_events

    findings: list[str] = []

    status_path = feature_dir / SNAPSHOT_FILENAME
    events_path = feature_dir / EVENTS_FILENAME

    if not events_path.exists():
        if status_path.exists():
            findings.append(
                "status.json exists but status.events.jsonl is missing"
            )
        return findings

    if not status_path.exists():
        findings.append(
            "status.events.jsonl exists but status.json is missing "
            "(run 'spec-kitty agent status materialize' to generate)"
        )
        return findings

    # Read on-disk snapshot
    disk_data = json.loads(status_path.read_text(encoding="utf-8"))

    # Compute expected snapshot from events
    events = read_events(feature_dir)
    expected_snapshot = reduce(events)

    # Compare work_packages and summary (skip materialized_at which is timestamp)
    disk_wps = disk_data.get("work_packages", {})
    expected_wps = expected_snapshot.work_packages

    if disk_wps != expected_wps:
        # Find specific differences
        all_wp_ids = set(disk_wps.keys()) | set(expected_wps.keys())
        for wp_id in sorted(all_wp_ids):
            disk_wp = disk_wps.get(wp_id)
            expected_wp = expected_wps.get(wp_id)

            if disk_wp is None:
                findings.append(
                    f"Materialization drift: {wp_id} missing from status.json "
                    f"(expected lane={expected_wp.get('lane', '?')})"
                )
            elif expected_wp is None:
                findings.append(
                    f"Materialization drift: {wp_id} in status.json but not in reducer output"
                )
            elif disk_wp.get("lane") != expected_wp.get("lane"):
                findings.append(
                    f"Materialization drift: {wp_id} lane={disk_wp.get('lane')} in status.json "
                    f"but reducer says lane={expected_wp.get('lane')}"
                )
            elif disk_wp != expected_wp:
                findings.append(
                    f"Materialization drift: {wp_id} state differs between status.json and reducer output"
                )

    # Also check event count and last_event_id
    if disk_data.get("event_count") != expected_snapshot.event_count:
        findings.append(
            f"Materialization drift: event_count={disk_data.get('event_count')} "
            f"in status.json but reducer counted {expected_snapshot.event_count}"
        )

    if disk_data.get("last_event_id") != expected_snapshot.last_event_id:
        findings.append(
            f"Materialization drift: last_event_id mismatch between "
            f"status.json and reducer output"
        )

    return findings


def validate_derived_views(
    feature_dir: Path,
    snapshot_wps: dict,
    phase: int,
) -> list[str]:
    """Compare frontmatter lanes with canonical snapshot work package states.

    Args:
        feature_dir: Path to the feature directory (kitty-specs/###-feature/).
        snapshot_wps: The work_packages dict from the StatusSnapshot
            (mapping wp_id -> state dict with at least a "lane" key).
        phase: Current status phase (1 or 2). Phase 1 drift is WARNING;
            Phase 2 drift is ERROR.

    Returns:
        List of finding strings. Empty means no drift.
    """
    severity = "ERROR" if phase >= 2 else "WARNING"
    findings: list[str] = []
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return findings

    for wp_id, wp_state in snapshot_wps.items():
        canonical_lane = wp_state.get("lane")

        # Find the corresponding WP file
        wp_files = list(tasks_dir.glob(f"{wp_id}-*.md")) + list(
            tasks_dir.glob(f"{wp_id}.md")
        )
        if not wp_files:
            findings.append(
                f"{wp_id}: no WP file found in tasks/ "
                f"(canonical state: {canonical_lane})"
            )
            continue

        wp_file = wp_files[0]
        content = wp_file.read_text(encoding="utf-8-sig")

        # Extract lane from frontmatter
        lane_match = re.search(
            r'^lane:\s*["\']?(\S+?)["\']?\s*$', content, re.MULTILINE
        )
        if not lane_match:
            findings.append(
                f"{wp_id}: no lane field in frontmatter "
                f"(canonical state: {canonical_lane})"
            )
            continue

        frontmatter_lane = lane_match.group(1)

        # Resolve alias for comparison (doing -> in_progress)
        if frontmatter_lane == "doing":
            frontmatter_lane = "in_progress"

        if frontmatter_lane != canonical_lane:
            findings.append(
                f"{severity}: {wp_id} frontmatter lane={frontmatter_lane} "
                f"but canonical state={canonical_lane}"
            )

    tasks_md = feature_dir / "tasks.md"
    if tasks_md.exists():
        status_lines = _extract_tasks_status_lines(tasks_md.read_text(encoding="utf-8"))
        if status_lines is None:
            findings.append(
                f"{severity}: tasks.md is missing generated canonical status block"
            )
        else:
            tasks_status: dict[str, str] = {}
            for line in status_lines:
                match = re.match(r"^- (WP\d{2}): ([a-z_]+)$", line.strip())
                if match is None:
                    findings.append(
                        f"{severity}: tasks.md status block has malformed line: {line.strip()}"
                    )
                    continue
                tasks_status[match.group(1)] = match.group(2)

            for wp_id, wp_state in snapshot_wps.items():
                canonical_lane = wp_state.get("lane")
                tasks_lane = tasks_status.get(wp_id)
                if tasks_lane is None:
                    findings.append(
                        f"{severity}: tasks.md status block missing {wp_id} "
                        f"(canonical state: {canonical_lane})"
                    )
                    continue
                if tasks_lane != canonical_lane:
                    findings.append(
                        f"{severity}: {wp_id} tasks.md lane={tasks_lane} "
                        f"but canonical state={canonical_lane}"
                    )

            for wp_id in sorted(tasks_status):
                if wp_id not in snapshot_wps:
                    findings.append(
                        f"{severity}: tasks.md status block includes unknown {wp_id}"
                    )

    return findings


def _extract_tasks_status_lines(content: str) -> list[str] | None:
    """Extract generated status lines from tasks.md status block markers."""
    start_idx = content.find(STATUS_BLOCK_START)
    if start_idx == -1:
        return None
    end_idx = content.find(STATUS_BLOCK_END, start_idx)
    if end_idx == -1:
        return None
    block = content[start_idx + len(STATUS_BLOCK_START):end_idx]
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    if not lines:
        return []
    # Strip optional heading line.
    if lines[0].startswith("## "):
        return lines[1:]
    return lines


def _is_valid_event_id(value: str) -> bool:
    """Check if a string is a valid event ID (ULID or UUID)."""
    try:
        normalize_event_id(value)
        return True
    except (ValueError, TypeError):
        return False


def _is_valid_iso8601(value: str) -> bool:
    """Check if a string looks like a valid ISO 8601 timestamp.

    Accepts common formats: YYYY-MM-DDTHH:MM:SSZ, YYYY-MM-DDTHH:MM:SS+00:00,
    and the output of datetime.isoformat().
    """
    try:
        # Python 3.11+ datetime.fromisoformat handles Z suffix
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False
