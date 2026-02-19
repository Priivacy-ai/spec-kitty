"""Migration: reconstruct full event history from WP frontmatter.

Reads existing WP frontmatter history[] arrays from a feature's tasks/
directory and generates complete transition chains as StatusEvent records
in status.events.jsonl.

Key invariants:
- Full history reconstruction via ``build_transition_chain()`` from history_parser.
- All migration events use ``force=True`` with ``reason`` set.
- 3-layer idempotency: marker check, live-events skip, migration-actor-only replace.
- Atomic write per feature (temp file + os.replace).
- Backup creation before replace-once on migration-only path.
- Post-migration materialization (status.json).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ulid import ULID

from specify_cli.frontmatter import read_frontmatter
from specify_cli.status.history_parser import build_transition_chain
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import EVENTS_FILENAME, StoreError, read_events
from specify_cli.status.transitions import CANONICAL_LANES, resolve_lane_alias

logger = logging.getLogger(__name__)


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
    events_created: int = 0  # Number of events generated
    event_ids: list[str] = field(default_factory=list)  # All ULID event IDs
    history_entries: int = 0  # Raw history entry count
    has_evidence: bool = False  # DoneEvidence extracted?


@dataclass
class FeatureMigrationResult:
    """Per-feature migration outcome."""

    feature_slug: str
    status: str  # "migrated", "skipped", "failed"
    wp_details: list[WPMigrationDetail] = field(default_factory=list)
    error: str | None = None
    backup_path: str | None = None  # Path to .bak file if created
    was_replace: bool = False  # True if replaced legacy bootstrap


@dataclass
class MigrationResult:
    """Aggregate migration outcome across features."""

    features: list[FeatureMigrationResult] = field(default_factory=list)
    total_migrated: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    aliases_resolved: int = 0


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _write_events_atomic(feature_dir: Path, events: list[StatusEvent]) -> None:
    """Write events to status.events.jsonl atomically."""
    events_file = feature_dir / EVENTS_FILENAME
    tmp_file = feature_dir / f"{EVENTS_FILENAME}.tmp"
    try:
        feature_dir.mkdir(parents=True, exist_ok=True)
        with open(tmp_file, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        os.replace(str(tmp_file), str(events_file))
    finally:
        if tmp_file.exists():
            tmp_file.unlink()


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------


def _check_idempotency(feature_dir: Path) -> str:
    """Check idempotency state of a feature's event log.

    Returns:
        "no_events" - No events file exists (or empty)
        "has_marker" - Full-history migration already done (skip)
        "live_events" - Non-migration actors present (skip)
        "migration_only" - Only migration actors (backup + replace)
    """
    events_file = feature_dir / EVENTS_FILENAME
    if not events_file.exists():
        return "no_events"

    content = events_file.read_text(encoding="utf-8").strip()
    if not content:
        return "no_events"

    try:
        events = read_events(feature_dir)
    except StoreError:
        logger.warning("Corrupt events file in %s, treating as no_events", feature_dir)
        return "no_events"

    if not events:
        return "no_events"

    # Layer 1: Check for full-history migration marker
    for event in events:
        if event.reason and "historical_frontmatter_to_jsonl:v1" in event.reason:
            return "has_marker"

    # Layer 2: Check for non-migration actors (live events)
    for event in events:
        if not event.actor.startswith("migration"):
            return "live_events"

    # Layer 3: All events have migration actors
    return "migration_only"


# ---------------------------------------------------------------------------
# Backup helper
# ---------------------------------------------------------------------------


def _backup_events_file(feature_dir: Path) -> Path | None:
    """Backup existing events file. Returns backup path or None."""
    events_file = feature_dir / EVENTS_FILENAME
    if not events_file.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = feature_dir / f"{EVENTS_FILENAME}.bak.{timestamp}"
    shutil.copy2(str(events_file), str(backup_path))
    return backup_path


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------


def feature_requires_historical_migration(feature_dir: Path) -> bool:
    """Return True when a feature has at least one reconstructable transition.

    Features with only planned/no-op WPs do not require historical migration and
    should not trigger upgrade detect loops.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return False

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return False

    for wp_file in wp_files:
        try:
            frontmatter, _body = read_frontmatter(wp_file)
        except Exception:
            # Parsing issues still require attention from migration logic.
            return True

        wp_id = str(frontmatter.get("work_package_id", wp_file.stem.split("-")[0]))
        raw_lane = frontmatter.get("lane", "planned")
        if raw_lane is None or str(raw_lane).strip() == "":
            raw_lane = "planned"
        canonical_lane = resolve_lane_alias(str(raw_lane))
        if canonical_lane not in CANONICAL_LANES:
            return True

        chain = build_transition_chain(frontmatter, wp_id)
        if chain.transitions:
            return True

    return False


def migrate_feature(
    feature_dir: Path,
    *,
    actor: str = "migration",
    dry_run: bool = False,
) -> FeatureMigrationResult:
    """Reconstruct full event history from WP frontmatter.

    Uses build_transition_chain() to reconstruct N transitions per WP
    from frontmatter history[] arrays. All events use force=True with
    reason set.

    Args:
        feature_dir: Path to the feature directory (e.g. kitty-specs/099-test/).
        actor: Fallback actor name (used when history agent is "migration").
        dry_run: When True, compute results but do not write events.

    Returns:
        FeatureMigrationResult with per-WP details and overall status.
    """
    feature_slug = feature_dir.name

    # ------------------------------------------------------------------
    # 3-layer idempotency check
    # ------------------------------------------------------------------
    idem_state = _check_idempotency(feature_dir)

    if idem_state == "has_marker":
        return FeatureMigrationResult(
            feature_slug=feature_slug,
            status="skipped",
        )

    if idem_state == "live_events":
        return FeatureMigrationResult(
            feature_slug=feature_slug,
            status="skipped",
        )

    # ------------------------------------------------------------------
    # If migration-only, backup before replace
    # ------------------------------------------------------------------
    backup_path: Path | None = None
    was_replace = False
    if idem_state == "migration_only" and not dry_run:
        backup_path = _backup_events_file(feature_dir)
        was_replace = True

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
    # Scan WP files and build events via history reconstruction
    # ------------------------------------------------------------------
    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return FeatureMigrationResult(
            feature_slug=feature_slug,
            status="failed",
            error=f"No WP*.md files found in {tasks_dir}",
        )

    wp_details: list[WPMigrationDetail] = []
    wp_errors: list[str] = []
    all_events: list[StatusEvent] = []

    for wp_file in wp_files:
        try:
            frontmatter, _body = read_frontmatter(wp_file)
        except Exception as exc:
            logger.warning("Failed to read frontmatter from %s: %s", wp_file, exc)
            wp_errors.append(f"{wp_file.name}: unreadable frontmatter ({exc})")
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_file.stem.split("-")[0],
                    original_lane="<unreadable>",
                    canonical_lane="<unreadable>",
                    alias_resolved=False,
                )
            )
            continue

        wp_id = str(frontmatter.get("work_package_id", wp_file.stem.split("-")[0]))
        raw_lane = frontmatter.get("lane", "planned")

        # Resolve alias
        if raw_lane is None or str(raw_lane).strip() == "":
            raw_lane = "planned"
        raw_lane_str = str(raw_lane)
        canonical_lane = resolve_lane_alias(raw_lane_str)
        alias_was_resolved = raw_lane_str.strip().lower() != canonical_lane

        # Validate canonical lane
        if canonical_lane not in CANONICAL_LANES:
            wp_errors.append(
                f"{wp_file.name}: unrecognized lane '{raw_lane_str}'"
            )
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_id,
                    original_lane=raw_lane_str,
                    canonical_lane=canonical_lane,
                    alias_resolved=alias_was_resolved,
                )
            )
            continue

        # Build transition chain from history
        chain = build_transition_chain(frontmatter, wp_id)

        if not chain.transitions:
            # No transitions (e.g., WP still at planned)
            wp_details.append(
                WPMigrationDetail(
                    wp_id=wp_id,
                    original_lane=raw_lane_str,
                    canonical_lane=canonical_lane,
                    alias_resolved=alias_was_resolved,
                    history_entries=chain.history_entries,
                )
            )
            continue

        # Create StatusEvent for each transition
        wp_event_ids: list[str] = []
        for i, t in enumerate(chain.transitions):
            event_id = str(ULID())

            # First event per WP gets the marker reason
            if i == 0:
                reason = "historical_frontmatter_to_jsonl:v1"
            else:
                reason = "historical migration"

            # Actor resolution: use transition's actor unless it's "migration"
            event_actor = t.actor if t.actor != "migration" else actor

            try:
                event = StatusEvent(
                    event_id=event_id,
                    feature_slug=feature_slug,
                    wp_id=wp_id,
                    from_lane=Lane(t.from_lane),
                    to_lane=Lane(t.to_lane),
                    at=t.timestamp,
                    actor=event_actor,
                    force=True,
                    execution_mode="direct_repo",
                    reason=reason,
                    evidence=t.evidence,
                )
            except ValueError:
                wp_errors.append(
                    f"{wp_file.name}: invalid transition {t.from_lane}->{t.to_lane}"
                )
                continue

            all_events.append(event)
            wp_event_ids.append(event_id)

        wp_details.append(
            WPMigrationDetail(
                wp_id=wp_id,
                original_lane=raw_lane_str,
                canonical_lane=canonical_lane,
                alias_resolved=alias_was_resolved,
                events_created=len(wp_event_ids),
                event_ids=wp_event_ids,
                history_entries=chain.history_entries,
                has_evidence=chain.has_evidence,
            )
        )

    # ------------------------------------------------------------------
    # Write events atomically (unless dry_run)
    # ------------------------------------------------------------------
    if not dry_run and all_events:
        _write_events_atomic(feature_dir, all_events)

        # Verification: read back and confirm count
        persisted = read_events(feature_dir)
        if len(persisted) != len(all_events):
            raise RuntimeError(
                f"Migration verification failed: expected {len(all_events)} events, "
                f"found {len(persisted)} in {feature_dir / EVENTS_FILENAME}"
            )

    # ------------------------------------------------------------------
    # Post-migration materialization
    # ------------------------------------------------------------------
    if not dry_run and all_events:
        try:
            from specify_cli.status.reducer import materialize

            materialize(feature_dir)
        except Exception as exc:
            logger.warning(
                "Materialization failed for %s (non-fatal): %s", feature_slug, exc
            )

    status = "migrated" if all_events else "skipped"
    error_msg: str | None = None
    if wp_errors:
        status = "failed"
        sample = "; ".join(wp_errors[:3])
        if len(wp_errors) > 3:
            sample = f"{sample}; ... (+{len(wp_errors) - 3} more)"
        error_msg = sample

    return FeatureMigrationResult(
        feature_slug=feature_slug,
        status=status,
        wp_details=wp_details,
        error=error_msg,
        backup_path=str(backup_path) if backup_path else None,
        was_replace=was_replace,
    )
