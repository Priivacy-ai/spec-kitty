"""Legacy migration: bootstrap canonical event logs from frontmatter state.

Reads existing WP frontmatter lanes from a feature's tasks/ directory
and generates bootstrap StatusEvent records in status.events.jsonl.

Key invariants:
- Alias ``doing`` is ALWAYS resolved to ``in_progress`` before event creation.
- Idempotent: features with existing non-empty status.events.jsonl are skipped.
- Bootstrap events use ``from_lane=planned`` as sentinel (all WPs start there).
- WPs already at ``planned`` produce no events (no transition occurred).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ulid import ULID

from specify_cli.frontmatter import read_frontmatter
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import EVENTS_FILENAME, append_event, read_events
from specify_cli.status.transitions import CANONICAL_LANES, resolve_lane_alias


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WPMigrationDetail:
    """Per-WP migration outcome."""

    wp_id: str
    original_lane: str  # Raw value from frontmatter (may be alias)
    canonical_lane: str  # Resolved canonical value
    alias_resolved: bool  # True if original != canonical
    event_id: str  # ULID of bootstrap event ("" if skipped/errored)


@dataclass
class FeatureMigrationResult:
    """Per-feature migration outcome."""

    feature_slug: str
    status: str  # "migrated", "skipped", "failed"
    wp_details: list[WPMigrationDetail] = field(default_factory=list)
    error: str | None = None


@dataclass
class MigrationResult:
    """Aggregate migration outcome across features."""

    features: list[FeatureMigrationResult] = field(default_factory=list)
    total_migrated: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    aliases_resolved: int = 0


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------

def migrate_feature(
    feature_dir: Path,
    *,
    actor: str = "migration",
    dry_run: bool = False,
) -> FeatureMigrationResult:
    """Bootstrap canonical event log from existing frontmatter lanes.

    Args:
        feature_dir: Path to the feature directory (e.g. kitty-specs/099-test/).
        actor: Actor name recorded on bootstrap events.
        dry_run: When True, compute results but do not write events.

    Returns:
        FeatureMigrationResult with per-WP details and overall status.
    """
    feature_slug = feature_dir.name

    # ------------------------------------------------------------------
    # Idempotency check: skip if event log already exists and non-empty
    # ------------------------------------------------------------------
    events_file = feature_dir / EVENTS_FILENAME
    if events_file.exists():
        content = events_file.read_text(encoding="utf-8").strip()
        if content:
            return FeatureMigrationResult(
                feature_slug=feature_slug,
                status="skipped",
            )

    # ------------------------------------------------------------------
    # Validate tasks/ directory exists
    # ------------------------------------------------------------------
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return FeatureMigrationResult(
            feature_slug=feature_slug,
            status="failed",
            error=f"No tasks/ directory found in {feature_dir}",
        )

    # ------------------------------------------------------------------
    # Scan WP files and build bootstrap events
    # ------------------------------------------------------------------
    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return FeatureMigrationResult(
            feature_slug=feature_slug,
            status="failed",
            error=f"No WP*.md files found in {tasks_dir}",
        )

    wp_details: list[WPMigrationDetail] = []
    events_to_write: list[StatusEvent] = []
    has_errors = False

    for wp_file in wp_files:
        try:
            frontmatter, _body = read_frontmatter(wp_file)
        except Exception as exc:
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_file.stem.split("-")[0],
                    original_lane="<unreadable>",
                    canonical_lane="<unreadable>",
                    alias_resolved=False,
                    event_id="",
                )
            )
            has_errors = True
            continue

        wp_id = frontmatter.get("work_package_id", wp_file.stem.split("-")[0])
        raw_lane = frontmatter.get("lane", "planned")

        # Resolve alias (e.g. "doing" -> "in_progress")
        if raw_lane is None or str(raw_lane).strip() == "":
            raw_lane = "planned"
        raw_lane_str = str(raw_lane)
        canonical_lane = resolve_lane_alias(raw_lane_str)
        alias_was_resolved = raw_lane_str.strip().lower() != canonical_lane

        # Validate canonical lane
        if canonical_lane not in CANONICAL_LANES:
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_id,
                    original_lane=raw_lane_str,
                    canonical_lane=canonical_lane,
                    alias_resolved=alias_was_resolved,
                    event_id="",
                )
            )
            has_errors = True
            continue

        # Skip WPs already at planned (no transition occurred)
        if canonical_lane == "planned":
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_id,
                    original_lane=raw_lane_str,
                    canonical_lane=canonical_lane,
                    alias_resolved=alias_was_resolved,
                    event_id="",
                )
            )
            continue

        # Determine timestamp from frontmatter history or now
        timestamp = _extract_timestamp(frontmatter)

        event_id = str(ULID())
        event = StatusEvent(
            event_id=event_id,
            feature_slug=feature_slug,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(canonical_lane),
            at=timestamp,
            actor=actor,
            force=False,
            execution_mode="direct_repo",
        )

        events_to_write.append(event)
        wp_details.append(
            WPMigrationDetail(
                wp_id=wp_id,
                original_lane=raw_lane_str,
                canonical_lane=canonical_lane,
                alias_resolved=alias_was_resolved,
                event_id=event_id,
            )
        )

    # ------------------------------------------------------------------
    # Write events (unless dry_run)
    # ------------------------------------------------------------------
    if not dry_run:
        for event in events_to_write:
            append_event(feature_dir, event)

        # Verification: read back and confirm count
        persisted = read_events(feature_dir)
        if len(persisted) != len(events_to_write):
            raise RuntimeError(
                f"Migration verification failed: expected {len(events_to_write)} events, "
                f"found {len(persisted)} in {events_file}"
            )

    return FeatureMigrationResult(
        feature_slug=feature_slug,
        status="migrated",
        wp_details=wp_details,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_timestamp(frontmatter: dict) -> str:
    """Extract best-available timestamp from frontmatter history.

    Falls back to ``datetime.now(UTC)`` when history is absent.
    """
    history = frontmatter.get("history")
    if isinstance(history, list) and history:
        last_entry = history[-1]
        if isinstance(last_entry, dict):
            ts = last_entry.get("timestamp")
            if ts:
                return str(ts)
    return datetime.now(timezone.utc).isoformat()
