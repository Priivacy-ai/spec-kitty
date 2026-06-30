"""Frontmatter/file persistence and markdown-row mutation helpers.

WP03 (#2058): cohesive seam extracted from the ``tasks`` god-module. These
helpers persist status to disk (review-cycle artifacts, ``tasks.md`` rows) and
mutate markdown rows in the three supported task-row formats (checkbox,
pipe-table, inline ``Subtasks:`` references).

Import direction is one-way: this module may import from ``tasks_outline``
(seam↔seam is allowed) but MUST NOT import from ``tasks`` (the god-module that
re-exports these names back for existing call sites).
"""

from __future__ import annotations

from datetime import datetime, UTC
from kernel._safe_re import re
from pathlib import Path

from specify_cli.core.utils import write_text_within_directory
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
from specify_cli.status import EVENTS_FILENAME, SNAPSHOT_FILENAME
from specify_cli.task_utils import (
    build_document,
    set_scalar,
    split_frontmatter,
)

# WP02 (#2058): the shared result vocabulary, the inline-subtasks regex, and the
# pipe-table row parsers live in the ``tasks_outline`` seam. Imported here so
# the materialization helpers keep their exact prior behavior.
from specify_cli.cli.commands.agent.tasks_outline import (
    TASKS_MD_FILENAME,
    TaskIdResolutionFormat,
    TaskIdResolutionOutcome,
    TaskIdResult,
    _INLINE_SUBTASKS_RE,
    _is_pipe_table_task_row,
    _parse_pipe_table_header,
)

# Mirror of the timestamp format defined in ``tasks``. Hoisted as a module-local
# constant so this seam has no back-import to the god-module.
UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _persist_review_artifact_override(
    artifact_path: Path,
    *,
    repo_root: Path,
    wp_id: str,
    actor: str,
    reason: str,
) -> None:
    """Record durable evidence that a rejected latest review was superseded."""
    text = artifact_path.read_text(encoding="utf-8-sig")
    frontmatter, body, padding = split_frontmatter(text)
    timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_at", timestamp)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_actor", actor)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_wp_id", wp_id)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_reason", reason)
    write_text_within_directory(
        artifact_path,
        build_document(frontmatter, body, padding),
        root=repo_root,
        encoding="utf-8",
    )


def _persist_review_artifact_override_in_coord(
    primary_artifact_path: Path,
    *,
    coord_feature_dir: Path,
    wp_id: str,
    actor: str,
    reason: str,
) -> bool:
    """Stamp the approval override onto the matching coord-worktree review artifact.

    The merge gate reads review artifacts from the coord worktree via
    ``find_rejected_review_artifact_conflicts(coord_feature_dir)`` →
    ``_artifact_dirs_for_wp(coord_feature_dir, wp_id)``.  When the approval
    handler stamps an override on the primary/lane artifact only, the coord
    copy is unchanged (``verdict: rejected``, no override block) — falsely
    blocking the gate (#2275 / FR-008).

    This helper resolves the coord artifact via the SAME ``_artifact_dirs_for_wp``
    path that the gate uses, guaranteeing byte-for-byte read/write symmetry.
    The existing ``has_complete_override`` check in ``artifacts.py`` (#1924) is
    honored: if the coord artifact already carries a complete override block the
    gate would not have fired, so no duplicate write is needed.

    ``primary_artifact_path`` supplies the artifact filename (``review-cycle-N.md``)
    and the sub-directory name (``WP01-slug``), which are identical in both the
    primary and coord worktrees.  Only the feature-dir root changes.

    Returns True when the coord artifact was found and stamped; False when no
    matching coord artifact exists (no-op — the gate would not block on it either).

    Args:
        primary_artifact_path: Path to the primary/lane review artifact (provides
            the filename and sub-directory name for the coord lookup).
        coord_feature_dir: The coord worktree's mission feature_dir, resolved via
            ``candidate_feature_dir_for_mission`` (the write-side resolver) by
            the caller.  Must be the same root the merge gate passes to
            ``find_rejected_review_artifact_conflicts``.
        wp_id: Canonical work-package identifier (e.g. ``"WP01"``).
        actor: Identity of the approver (operator or agent name).
        reason: Human-readable rationale for the override (required by the
            approval gate; must be non-empty before reaching this call).
    """
    # The artifact sub-directory name (e.g. "WP01-slug") and the artifact
    # filename (e.g. "review-cycle-1.md") are structurally identical in primary
    # and coord.  Derive both from primary_artifact_path so this is not a
    # hand-built path.
    artifact_subdir_name = primary_artifact_path.parent.name
    coord_artifact_path = (
        coord_feature_dir / "tasks" / artifact_subdir_name / primary_artifact_path.name
    )
    if not coord_artifact_path.exists():
        return False
    text = coord_artifact_path.read_text(encoding="utf-8-sig")
    frontmatter, body, padding = split_frontmatter(text)
    timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_at", timestamp)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_actor", actor)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_wp_id", wp_id)
    frontmatter = set_scalar(frontmatter, "review_artifact_override_reason", reason)
    write_text_within_directory(
        coord_artifact_path,
        build_document(frontmatter, body, padding),
        root=coord_feature_dir,
        encoding="utf-8",
    )
    return True


def _collect_status_artifacts(feature_dir: Path) -> list[Path]:
    """Return paths to all deterministic status artifacts that exist on disk.

    These files are generated by the emit pipeline (events.jsonl, status.json)
    and by task management (tasks.md).  Including them in a single commit
    alongside the WP file ensures the working tree stays clean after every
    ``move_task`` or ``workflow review`` transition.

    Args:
        feature_dir: Absolute path to the kitty-specs mission directory.

    Returns:
        List of existing artifact paths (may be empty).
    """
    candidates = [
        feature_dir / EVENTS_FILENAME,
        feature_dir / SNAPSHOT_FILENAME,
        feature_dir / TASKS_MD_FILENAME,
    ]
    return [p for p in candidates if p.exists()]


def _resolve_wp_slug(main_repo_root: Path, mission_slug: str, task_id: str) -> str:
    """Resolve the WP slug (e.g. 'WP01-some-title') from a task ID.

    Looks for a file named '{task_id}-*.md' in kitty-specs/<mission>/tasks/.
    Falls back to bare task_id if no matching file is found.
    """
    # WP04 / FR-006: ``tasks/WP*.md`` is a WORK_PACKAGE_TASK (primary-partition)
    # artifact — author+read on PRIMARY (INV-5). Route the read through the
    # kind-aware seam so a coord-topology mission's stale ``-coord`` husk cannot
    # shadow the real primary WP files (#2062 read-side close).
    from mission_runtime import MissionArtifactKind

    tasks_dir = (
        resolve_planning_read_dir(
            main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        / "tasks"
    )
    if tasks_dir.exists():
        for p in tasks_dir.iterdir():
            if p.stem.startswith(f"{task_id}-") or p.stem == task_id:
                # Narrow ``str()`` coercion: when this seam is type-checked in
                # isolation, mypy resolves the cross-package ``resolve_planning_read_dir``
                # result as ``Any`` (follow-imports narrowing), so ``p.stem`` is
                # inferred ``Any``. The coercion restores ``str`` without a suppression.
                return str(p.stem)
    return task_id


def _persist_review_feedback(
    *,
    main_repo_root: Path,
    mission_slug: str,
    task_id: str,
    feedback_source: Path,
    reviewer_agent: str = "unknown",
    affected_files: list[dict[str, str]] | None = None,
) -> tuple[Path, str]:
    """Persist review feedback through the shared review-cycle boundary.

    Returns the created artifact path and canonical ``review-cycle://`` URI.
    """
    from specify_cli.review.cycle import create_rejected_review_cycle

    wp_slug = _resolve_wp_slug(main_repo_root, mission_slug, task_id)
    cycle = create_rejected_review_cycle(
        main_repo_root=main_repo_root,
        mission_slug=mission_slug,
        wp_id=task_id,
        wp_slug=wp_slug,
        feedback_source=feedback_source,
        reviewer_agent=reviewer_agent,
        affected_files=affected_files,
    )
    return cycle.artifact_path, cycle.pointer


def _update_pipe_table_status(line: str, status: str, header_map: dict[str, int]) -> str:
    """Update the status marker in a pipe-table row without corrupting other columns.

    Strategy (in priority order):
    1. If a "status" column exists in *header_map* -> update only that cell.
    2. If a "parallel" column exists -> do NOT touch it; append a new status cell.
    3. If the last cell already looks like a status marker ([P]/[D]/[ ]/[x]) ->
       replace it in place.
    4. Otherwise -> append a new status cell.
    """
    # Split on '|'; cells[0] and cells[-1] are empty strings outside the row.
    cells = line.split("|")
    inner_cells = cells[1:-1]

    done_marker = " [D] "
    pending_marker = " [ ] "
    new_marker = done_marker if status == "done" else pending_marker

    status_col = header_map.get("status")
    parallel_col = header_map.get("parallel")

    if status_col is not None and status_col < len(inner_cells):
        # Update the designated status column only
        inner_cells[status_col] = new_marker
    elif parallel_col is not None:
        # Parallel column exists — do NOT corrupt it; append status instead
        inner_cells.append(new_marker)
    else:
        # No header guidance — check if the last cell looks like a status marker
        if inner_cells and re.match(r"\s*\[\s*[PDx ]\s*\]\s*$", inner_cells[-1]):
            inner_cells[-1] = new_marker
        else:
            inner_cells.append(new_marker)

    return "|" + "|".join(inner_cells) + "|"


def _resolve_checkbox(
    task_id: str,
    lines: list[str],
    status: str,
) -> TaskIdResult | None:
    """Resolve and mutate checkbox rows for *task_id*."""
    new_checkbox = "[x]" if status == "done" else "[ ]"
    found = False
    for i, line in enumerate(lines):
        if re.search(rf"-\s*\[[ x]\]\s*{re.escape(task_id)}\b", line, re.IGNORECASE):
            lines[i] = re.sub(r"-\s*\[[ x]\]", f"- {new_checkbox}", line)
            found = True
    if not found:
        return None
    return TaskIdResult(
        id=task_id,
        outcome=TaskIdResolutionOutcome.UPDATED,
        format=TaskIdResolutionFormat.CHECKBOX,
        message=f"Marked {task_id} as {status} (checkbox row updated).",
    )


def _resolve_pipe_table(
    task_id: str,
    lines: list[str],
    status: str,
) -> TaskIdResult | None:
    """Resolve and mutate pipe-table rows for *task_id*."""
    found = False
    for i, line in enumerate(lines):
        if _is_pipe_table_task_row(line, task_id):
            header_map = _parse_pipe_table_header(lines, i)
            lines[i] = _update_pipe_table_status(line, status, header_map)
            found = True
    if not found:
        return None
    return TaskIdResult(
        id=task_id,
        outcome=TaskIdResolutionOutcome.UPDATED,
        format=TaskIdResolutionFormat.PIPE_TABLE,
        message=f"Marked {task_id} as {status} (pipe-table row updated).",
    )


def _materialize_inline_subtask_status(
    task_id: str,
    tasks_content: str,
    status: str,
) -> tuple[str, bool]:
    """Insert a checkbox row next to a matching inline Subtasks reference."""
    new_checkbox = "[x]" if status == "done" else "[ ]"
    normalized_task_id = task_id.upper()
    lines = tasks_content.split("\n")

    for line_idx, line in enumerate(lines):
        match = _INLINE_SUBTASKS_RE.search(line)
        if not match:
            continue
        ids = [value.strip().upper() for value in str(match.group("ids")).split(",")]
        if normalized_task_id not in ids:
            continue

        for existing_idx, existing_line in enumerate(lines):
            if re.search(
                rf"-\s*\[[ x]\]\s*{re.escape(task_id)}\b",
                existing_line,
                re.IGNORECASE,
            ):
                lines[existing_idx] = re.sub(
                    r"-\s*\[[ x]\]",
                    f"- {new_checkbox}",
                    existing_line,
                )
                return "\n".join(lines), True

        insert_at = line_idx + 1
        while insert_at < len(lines) and re.match(r"\s*-\s*\[[ x]\]\s*(?:T|WP)\d+\b", lines[insert_at], re.IGNORECASE):
            insert_at += 1
        lines.insert(insert_at, f"- {new_checkbox} {task_id}")
        return "\n".join(lines), True

    return tasks_content, False


def _persist_inline_subtask_status(
    task_id: str,
    status: str,
    feature_dir: Path,
    tasks_content: str | None = None,
) -> bool:
    """Persist an inline Subtasks match by materializing a checkbox row."""
    tasks_path = feature_dir / TASKS_MD_FILENAME
    if tasks_content is None:
        if not tasks_path.exists():
            return False
        tasks_content = tasks_path.read_text(encoding="utf-8")

    updated_content, persisted = _materialize_inline_subtask_status(task_id, tasks_content, status)
    if not persisted:
        return False
    tasks_path.write_text(updated_content, encoding="utf-8")
    return True
