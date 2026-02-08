"""Legacy bridge -- backward compatibility views from canonical StatusSnapshot.

Generates human-readable views (WP frontmatter `lane` fields and tasks.md
status sections) from the canonical `status.json` snapshot. These views are
never authoritative; they are compatibility caches that existing tools
(agents, dashboards, slash commands) read.

Phase behavior:
  - Phase 0: No-op (no event log yet, frontmatter is still the authority)
  - Phase 1: Update views on every emit (dual-write mode)
  - Phase 2: Views are generated after materialize only, never read as authority
"""

from __future__ import annotations

import logging
from pathlib import Path

from specify_cli.frontmatter import FrontmatterManager
from specify_cli.status.models import StatusSnapshot
from specify_cli.status.phase import resolve_phase

logger = logging.getLogger(__name__)


def update_frontmatter_views(
    feature_dir: Path,
    snapshot: StatusSnapshot,
) -> None:
    """Update WP frontmatter lane fields from StatusSnapshot.

    For each WP in the snapshot, finds the corresponding
    tasks/WP##-*.md file and updates its 'lane' field.

    Skips writes when the lane already matches to avoid unnecessary diffs.
    Logs warnings for missing WP files but does not error.
    Propagates write errors without catching them.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        logger.warning("Tasks directory not found: %s", tasks_dir)
        return

    fm = FrontmatterManager()

    for wp_id, wp_state in snapshot.work_packages.items():
        lane_value = wp_state.get("lane")
        if lane_value is None:
            continue

        # Find the WP file by glob pattern
        wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
        if not wp_files:
            logger.warning(
                "No task file found for %s in %s", wp_id, tasks_dir
            )
            continue
        if len(wp_files) > 1:
            logger.warning(
                "Multiple task files for %s: %s (using first)",
                wp_id, wp_files,
            )

        wp_file = wp_files[0]

        frontmatter, body = fm.read(wp_file)
        current_lane = frontmatter.get("lane")

        if current_lane == lane_value:
            # Already in sync, skip write
            continue

        frontmatter["lane"] = lane_value
        fm.write(wp_file, frontmatter, body)
        logger.debug(
            "Updated %s lane: %s -> %s",
            wp_id, current_lane, lane_value,
        )


def update_tasks_md_views(
    feature_dir: Path,
    snapshot: StatusSnapshot,
) -> None:
    """Update tasks.md status sections from StatusSnapshot.

    Updates WP section headers or status metadata to reflect
    canonical lane values. Does NOT modify subtask checkboxes
    (those are for subtask tracking, separate from lane status).

    Current implementation is a lightweight pass-through because
    tasks.md does not contain lane status fields that need updating.
    The WP sections in tasks.md have subtask checkboxes and descriptive
    text, not frontmatter-style lane fields. The authoritative lane
    display is in the individual WP files' frontmatter.
    """
    tasks_md = feature_dir / "tasks.md"
    if not tasks_md.exists():
        logger.debug("tasks.md not found: %s", tasks_md)
        return

    content = tasks_md.read_text(encoding="utf-8")
    updated = _update_wp_status_in_tasks_md(content, snapshot)

    if updated != content:
        tasks_md.write_text(updated, encoding="utf-8")
        logger.debug("Updated tasks.md status sections")


def _update_wp_status_in_tasks_md(
    content: str,
    snapshot: StatusSnapshot,
) -> str:
    """Update WP status references in tasks.md content.

    Strategy: Find WP section headers and update any inline
    status indicators. Preserves all other content unchanged.

    Does NOT modify:
    - Subtask checkboxes ([ ] or [x])
    - Non-WP sections
    - Content within WP sections (only headers/metadata)

    Currently a pass-through. The status is tracked in the individual
    WP files, not in tasks.md section content. If future requirements
    add lane indicators to tasks.md, this function will be extended.
    """
    return content


def update_all_views(
    feature_dir: Path,
    snapshot: StatusSnapshot,
    *,
    repo_root: Path | None = None,
) -> None:
    """Update all compatibility views from the canonical snapshot.

    Checks the current phase and adjusts behavior:
    - Phase 0: No-op (no event log, frontmatter is still authority)
    - Phase 1: Update views (dual-write mode)
    - Phase 2: Update views (views are generated-only)

    Args:
        feature_dir: Path to the feature directory (kitty-specs/<feature>/)
        snapshot: The StatusSnapshot to generate views from
        repo_root: Repository root for phase resolution. If None, derived
                   from feature_dir (assumes kitty-specs/<slug>/ structure).
    """
    if repo_root is None:
        # Derive repo_root: feature_dir is typically kitty-specs/<slug>/
        repo_root = feature_dir.parent.parent

    phase, source = resolve_phase(repo_root, snapshot.feature_slug)

    if phase == 0:
        logger.debug(
            "Phase 0 (%s): legacy bridge is no-op", source
        )
        return

    # Phase 1 and Phase 2: update views
    update_frontmatter_views(feature_dir, snapshot)
    update_tasks_md_views(feature_dir, snapshot)

    logger.debug(
        "Legacy views updated for %s (phase %d: %s)",
        snapshot.feature_slug, phase, source,
    )
