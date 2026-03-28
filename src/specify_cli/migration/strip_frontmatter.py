"""Remove mutable status fields from all WP frontmatter.

Mutable fields (``lane``, ``review_status``, ``reviewed_by``,
``review_feedback``, ``progress``, ``shell_pid``, ``assignee``, ``agent``)
are runtime state that must not live in the immutable WP definition once the
canonical status event-log takes over.

IMPORTANT: This step records ``lane`` values *before* stripping them.  The
caller (or the orchestrating migration runner) must persist these lane records
for use by the state-rebuild step (WP13 / T065) **before** this function is
called — or use the ``lane_records`` returned in :class:`StripResult`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Fields that carry runtime mutable state and must be removed.
MUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "lane",
        "review_status",
        "reviewed_by",
        "review_feedback",
        "progress",
        "shell_pid",
        "assignee",
        "agent",
    }
)

# Fields that are part of the immutable WP definition and must be preserved.
STATIC_FIELDS: frozenset[str] = frozenset(
    {
        "work_package_id",
        "wp_code",
        "mission_id",
        "title",
        "dependencies",
        "requirement_refs",
        "execution_mode",
        "owned_files",
        "authoritative_surface",
        "subtasks",
        "phase",
        "planning_base_branch",
        "merge_target_branch",
        "branch_strategy",
        "base_branch",
        "base_commit",
        "created_at",
        "history",
    }
)


@dataclass
class StripResult:
    """Summary of a :func:`strip_mutable_fields` run.

    Attributes:
        wps_processed: Number of WP files processed.
        fields_stripped: Total number of field instances removed across all WPs.
        lane_records: Mapping of ``wp_code → lane`` recorded *before* stripping,
            so the lane values are available for state reconstruction in WP13.
        warnings: List of non-fatal warning messages.
    """

    wps_processed: int = 0
    fields_stripped: int = 0
    lane_records: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def strip_mutable_fields(feature_dir: Path) -> StripResult:
    """Remove mutable fields from all WP frontmatter in *feature_dir*.

    For each ``tasks/WP*.md`` file:

    1. Reads the current frontmatter.
    2. Records the ``lane`` value (if present) in :attr:`StripResult.lane_records`.
    3. Removes all keys listed in :data:`MUTABLE_FIELDS`.
    4. Writes back using :class:`~specify_cli.frontmatter.FrontmatterManager`
       (ruamel.yaml round-trip, body content preserved byte-for-byte).

    Also inspects the top-level ``tasks.md`` if it exists and strips any
    status-like blocks from its frontmatter.

    Args:
        feature_dir: Path to the feature directory (e.g. ``kitty-specs/057-…``).

    Returns:
        :class:`StripResult` with counts and the pre-strip lane records.
    """
    from specify_cli.frontmatter import FrontmatterManager

    result = StripResult()
    tasks_dir = feature_dir / "tasks"

    if not tasks_dir.is_dir():
        logger.debug("No tasks/ directory in %s — skipping frontmatter strip", feature_dir.name)
        return result

    manager = FrontmatterManager()

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            frontmatter, body = manager.read(wp_file)
        except Exception as exc:
            msg = f"Cannot read {wp_file.name}: {exc} — skipping"
            logger.warning(msg)
            result.warnings.append(msg)
            continue

        # Derive wp_code for the lane_records key
        import re
        m = re.match(r"^(WP\d+)", wp_file.stem)
        wp_code = m.group(1) if m else wp_file.stem

        # Record lane BEFORE stripping
        if "lane" in frontmatter:
            result.lane_records[wp_code] = str(frontmatter["lane"])

        # Count and remove mutable fields
        stripped_count = 0
        for mf in MUTABLE_FIELDS:
            if mf in frontmatter:
                del frontmatter[mf]
                stripped_count += 1

        if stripped_count > 0:
            manager.write(wp_file, frontmatter, body)
            logger.info(
                "Stripped %d mutable field(s) from %s",
                stripped_count,
                wp_file.name,
            )

        result.wps_processed += 1
        result.fields_stripped += stripped_count

    # Also strip frontmatter from tasks.md if it has status-like blocks
    tasks_md = feature_dir / "tasks.md"
    if tasks_md.exists():
        try:
            frontmatter, body = manager.read(tasks_md)
            stripped_count = 0
            for mf in MUTABLE_FIELDS:
                if mf in frontmatter:
                    del frontmatter[mf]
                    stripped_count += 1
            if stripped_count > 0:
                manager.write(tasks_md, frontmatter, body)
                logger.info(
                    "Stripped %d mutable field(s) from tasks.md in %s",
                    stripped_count,
                    feature_dir.name,
                )
                result.fields_stripped += stripped_count
        except Exception as exc:
            # tasks.md may not have frontmatter at all — that's fine
            logger.debug("tasks.md in %s has no frontmatter or could not be read: %s", feature_dir.name, exc)

    return result
