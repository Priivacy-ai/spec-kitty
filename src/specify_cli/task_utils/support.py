#!/usr/bin/env python3
"""Shared utilities for manipulating Spec Kitty work package prompts and frontmatter."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from specify_cli.core.paths import get_main_repo_root, locate_project_root
from specify_cli.mission_metadata import load_meta as _load_meta_canonical

# Canonical lane tuple — imported from the leaf module to avoid pulling in the
# full status orchestration package during cold command imports.
from specify_cli.status_lanes import CANONICAL_LANES

if TYPE_CHECKING:
    from specify_cli.status import EventStream
    from specify_cli.status.wp_view import WPView

LANES: tuple[str, ...] = CANONICAL_LANES
LANE_ALIASES: dict[str, str] = {"doing": "in_progress"}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskCliError(RuntimeError):
    """Raised when task operations cannot be completed safely."""


def find_repo_root(start: Path | None = None) -> Path:
    """Find the MAIN repository root, even when inside a worktree.

    This function correctly handles git worktrees by detecting when .git is a
    file (worktree pointer) vs a directory (main repo), and following the
    pointer back to the main repository.

    Args:
        start: Starting directory for search (defaults to cwd)

    Returns:
        Path to the main repository root

    Raises:
        TaskCliError: If repository root cannot be found
    """
    current = (start or Path.cwd()).resolve()

    detected_root = locate_project_root(current)
    if detected_root is not None:
        # cast: follow_imports=skip erases get_main_repo_root's -> Path signature
        # at this specify_cli.* boundary; type-only, no behaviour change.
        return cast(Path, get_main_repo_root(detected_root))

    # Fallback: support plain git repositories that do not contain .kittify yet.
    for candidate in [current, *current.parents]:
        git_path = candidate / ".git"

        if git_path.is_dir():
            return cast(Path, get_main_repo_root(candidate))

        if git_path.is_file():
            resolved = cast(Path, get_main_repo_root(candidate))
            if resolved != candidate:
                return resolved

    raise TaskCliError("Unable to locate repository root (missing .git or .kittify).")


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command inside the repository."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=check,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise TaskCliError("git is not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        if check:
            message = exc.stderr.strip() or exc.stdout.strip() or "Unknown git error"
            raise TaskCliError(message) from exc
        return subprocess.CompletedProcess(
            args=exc.cmd,
            returncode=exc.returncode,
            stdout=exc.stdout,
            stderr=exc.stderr,
        )


def ensure_lane(value: str) -> str:
    lane = value.strip().lower()
    # Resolve aliases (e.g., "doing" -> "in_progress")
    lane = LANE_ALIASES.get(lane, lane)
    if lane not in LANES:
        raise TaskCliError(f"Invalid lane '{value}'. Expected one of {', '.join(LANES)}.")
    return lane


def now_utc() -> str:
    return datetime.now(UTC).strftime(TIMESTAMP_FORMAT)


def git_status_lines(repo_root: Path) -> list[str]:
    result = run_git(["status", "--porcelain"], cwd=repo_root, check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def normalize_note(note: str | None, target_lane: str) -> str:
    default = f"Moved to {target_lane}"
    cleaned = (note or default).strip()
    return cleaned or default


def detect_conflicting_wp_status(status_lines: list[str], feature: str, old_path: Path, new_path: Path) -> list[str]:
    """Return staged work-package entries unrelated to the requested move."""
    prefix = f"kitty-specs/{feature}/tasks/"
    allowed = {
        str(old_path).lstrip("./"),
        str(new_path).lstrip("./"),
    }
    conflicts = []
    for line in status_lines:
        path = line[3:] if len(line) > 3 else ""
        if not path.startswith(prefix):
            continue
        clean = path.strip()
        if clean not in allowed:
            conflicts.append(line)
    return conflicts


def match_frontmatter_line(frontmatter: str, key: str) -> re.Match[str] | None:
    pattern = re.compile(
        rf"^({re.escape(key)}:\s*)(\".*?\"|'.*?'|[^#\n]*)(.*)$",
        flags=re.MULTILINE,
    )
    return pattern.search(frontmatter)


def extract_scalar(frontmatter: str, key: str) -> str | None:
    match = match_frontmatter_line(frontmatter, key)
    if not match:
        return None
    raw_value = match.group(2).strip()
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value[1:-1]
    if raw_value.startswith("'") and raw_value.endswith("'"):
        return raw_value[1:-1]
    return raw_value.strip() or None


def delete_scalar(frontmatter: str, key: str) -> str:
    """Remove a scalar key-value line from frontmatter, if present.

    Removes the entire line (including its trailing newline) without
    disturbing surrounding content or comment lines.  Returns frontmatter
    unchanged when the key is absent.
    """
    match = match_frontmatter_line(frontmatter, key)
    if not match:
        return frontmatter
    line_end = match.end()
    if line_end < len(frontmatter) and frontmatter[line_end] == "\n":
        line_end += 1  # consume the trailing newline so no blank line is left
    return frontmatter[: match.start()] + frontmatter[line_end:]


def set_scalar(frontmatter: str, key: str, value: str) -> str:
    """Replace or insert a scalar value while preserving trailing comments."""
    match = match_frontmatter_line(frontmatter, key)
    replacement_line = f'{key}: "{value}"'
    if match:
        prefix = match.group(1)
        comment = match.group(3)
        comment_suffix = f"{comment}" if comment else ""
        return frontmatter[: match.start()] + f'{prefix}"{value}"{comment_suffix}' + frontmatter[match.end() :]

    insertion = f"{replacement_line}\n"
    history_match = re.search(r"^\s*history:\s*$", frontmatter, flags=re.MULTILINE)
    if history_match:
        idx = history_match.start()
        return frontmatter[:idx] + insertion + frontmatter[idx:]

    if frontmatter and not frontmatter.endswith("\n"):
        frontmatter += "\n"
    return frontmatter + insertion


def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (frontmatter, body, padding) while preserving spacing after frontmatter."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized, ""

    closing_idx = normalized.find("\n---", 4)
    if closing_idx == -1:
        return "", normalized, ""

    front = normalized[4:closing_idx]
    tail = normalized[closing_idx + 4 :]
    padding = ""
    while tail.startswith("\n"):
        padding += "\n"
        tail = tail[1:]
    return front, tail, padding


def build_document(frontmatter: str, body: str, padding: str) -> str:
    frontmatter = frontmatter.rstrip("\n")
    doc = f"---\n{frontmatter}\n---"
    if padding or body:
        doc += padding or "\n"
    doc += body
    if not doc.endswith("\n"):
        doc += "\n"
    return doc


def append_activity_log(body: str, entry: str) -> str:
    header = "## Activity Log"
    if header not in body:
        block = f"{header}\n\n{entry}\n"
        if body and not body.endswith("\n\n"):
            return body.rstrip() + "\n\n" + block
        return body + "\n" + block if body else block

    pattern = re.compile(r"(## Activity Log.*?)(?=\n## |\Z)", flags=re.DOTALL)
    match = pattern.search(body)
    if not match:
        return body + ("\n" if not body.endswith("\n") else "") + entry + "\n"

    section = match.group(1).rstrip()
    if not section.endswith("\n"):
        section += "\n"
    section += f"{entry}\n"
    return body[: match.start(1)] + section + body[match.end(1) :]


def _parse_activity_entries_from_body(body: str) -> list[dict[str, str]]:
    """Parse ``## Activity Log`` rows out of a WP-file body (the legacy source).

    Pre-FR-005 sole implementation of :func:`activity_entries`; retained
    verbatim and always run unconditionally -- the body-parsed rows are never
    gated, they are folded in addition to the snapshot's event-sourced rows
    when *feature_dir*/*wp_id* are supplied (SC-004 "no content loss").
    """
    # Match both en-dash (–) and hyphen (-) as separators
    # Agent names can contain hyphens (e.g., "cursor-agent", "claude-reviewer")
    # Use \S+ to match non-whitespace including hyphens within the agent name
    pattern = re.compile(
        r"^\s*-\s*"
        r"(?P<timestamp>[0-9T:-]+Z)\s+[–-]\s+"
        r"(?P<agent>\S+(?:\s+\S+)*?)\s+[–-]\s+"
        r"(?:shell_pid=(?P<shell>\S*)\s+[–-]\s+)?"
        r"lane=(?P<lane>[a-z_]+)\s+[–-]\s+"
        r"(?P<note>.*)$",
        flags=re.MULTILINE,
    )
    entries: list[dict[str, str]] = []
    for match in pattern.finditer(body):
        entries.append(
            {
                "timestamp": match.group("timestamp").strip(),
                "agent": match.group("agent").strip(),
                "lane": match.group("lane").strip(),
                "note": match.group("note").strip(),
                "shell_pid": (match.group("shell") or "").strip(),
            }
        )
    return entries


def _snapshot_activity_entries(stream: EventStream, wp_id: str) -> list[dict[str, str]]:
    """Fold event-sourced transition + note history into activity-log rows (SC-004).

    Draws directly from the same annotation-aware read seam
    (``status.store.read_event_stream``) the reducer folds through — not a
    second parser (#2093 / FR-013). Produces one row per lane transition for
    *wp_id* (``lane=<to_lane>``, ``note=<reason or "Moved to <to_lane>">``) and
    one row per note annotation (the annotation's own note text), each
    carrying its own event timestamp/actor for per-entry fidelity, sorted
    chronologically by occurrence time.
    """
    # ``actor`` is ``str | dict`` (FR-015 / IC-09): a resolved-binding transition
    # may carry a ``{role, profile, tool, model}`` dict. The activity-log "agent"
    # cell is a display string, so project the structured actor to its string
    # identity (the dict binding is surfaced via the resolved-binding slots, not
    # this row).
    from specify_cli.status import actor_identity_str  # noqa: PLC0415

    rows: list[tuple[str, dict[str, str]]] = []
    for event in stream.transitions:
        if event.wp_id != wp_id:
            continue
        rows.append(
            (
                event.at,
                {
                    "timestamp": event.at,
                    "agent": actor_identity_str(event.actor),
                    "lane": str(event.to_lane),
                    "note": event.reason or f"Moved to {event.to_lane}",
                    "shell_pid": "",
                },
            )
        )
    for annotation in stream.annotations:
        if annotation.wp_id != wp_id or annotation.delta.note is None:
            continue
        rows.append(
            (
                annotation.at,
                {
                    "timestamp": annotation.at,
                    "agent": actor_identity_str(annotation.actor),
                    "lane": "",
                    "note": annotation.delta.note,
                    "shell_pid": "",
                },
            )
        )
    rows.sort(key=lambda item: item[0])
    return [entry for _at, entry in rows]


def activity_entries(
    body: str,
    *,
    feature_dir: Path | None = None,
    wp_id: str | None = None,
) -> list[dict[str, str]]:
    """Return the WP's activity-log rows as ``{timestamp, agent, lane, note, shell_pid}`` dicts.

    Parses the ``## Activity Log`` section out of *body* (the pre-FR-005
    behavior; see :func:`_parse_activity_entries_from_body`). This is always
    computed and always included in the result — it is the tolerated
    migration-window fallback (a WP whose legacy entries have not yet been
    migrated must not lose them, SC-004 "no content loss").

    SC-004: when *feature_dir* and *wp_id* are BOTH supplied, the reduced
    snapshot's event-sourced transition history and ``note`` annotations for
    *wp_id* are folded in ADDITION to the body-parsed rows above — never in
    place of them (:func:`_snapshot_activity_entries`). Omitting
    *feature_dir*/*wp_id* reproduces the body-only output.
    """
    entries = _parse_activity_entries_from_body(body)
    if feature_dir is None or wp_id is None:
        return entries

    from specify_cli.status import read_event_stream  # noqa: PLC0415

    stream = read_event_stream(feature_dir)
    return entries + _snapshot_activity_entries(stream, wp_id)


@dataclass
class WorkPackage:
    feature: str
    path: Path
    current_lane: str
    relative_subpath: Path
    frontmatter: str
    body: str
    padding: str
    # Planning artifacts always live on the primary partition, while mutable
    # status may live on the coordination partition.  Carry the canonical
    # status directory separately so a coord-topology WorkPackage never reads
    # a stale primary event log merely because its Markdown file lives there.
    status_dir: Path | None = None
    # Per-instance reconstructed-view cache (FR-005 / IC-07): populated lazily by
    # ``_resolved_view`` on first access so ``assignee``/``agent``/``shell_pid``
    # and the resolved-binding ``role``/``agent_profile``/``model`` share a single
    # reconstruction per WorkPackage instance rather than one per property access.
    # Excluded from ``__init__``/``__eq__``/``repr`` -- pure memoization, not part
    # of the value's identity.
    _resolved_view_cache: WPView | None = field(default=None, init=False, repr=False, compare=False)
    _resolved_view_loaded: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def work_package_id(self) -> str | None:
        return extract_scalar(self.frontmatter, "work_package_id")

    @property
    def title(self) -> str | None:
        return extract_scalar(self.frontmatter, "title")

    def _resolved_view(self) -> WPView | None:
        """Return the reconstructed WP view through the ONE canonical reader (SC-007).

        Routes the snapshot read through
        :func:`specify_cli.status.reconstruct_wp_view` (SC-007) instead of
        hand-rolling the ``read_event_stream -> reduce -> get(wp_id)`` idiom.
        The reduced snapshot is the unconditional authority for this WP's
        runtime slots (#2093/IC-03): an absent resolved slot is a valid
        authoritative empty result ("no runtime state yet"), never a signal to
        fall back to frontmatter (C-001 -- the phase-1 dual-write flag and its
        frontmatter fallback are retired with the unconditional cutover).

        Memoized per instance (one reconstruction per ``WorkPackage``, not one
        per property read) -- correctness is unaffected since a ``WorkPackage``
        is a point-in-time read, never mutated in place after construction.
        """
        if self._resolved_view_loaded:
            return self._resolved_view_cache

        from specify_cli.status import (  # noqa: PLC0415
            CanonicalStatusNotFoundError,
            has_event_log,
            reconstruct_wp_view,
        )

        # WP files are primary-partition planning artifacts; mutable state may
        # instead live on the coordination partition.
        feature_dir = self.status_dir or self.path.parent.parent
        if not has_event_log(feature_dir):
            raise CanonicalStatusNotFoundError(
                f"Canonical status not found for feature '{self.feature}'. "
                f"Run 'spec-kitty agent mission finalize-tasks --mission "
                f"{self.feature}' to bootstrap the event log."
            )
        wp_id = extract_scalar(self.frontmatter, "work_package_id") or self.path.stem.split("-")[0]
        view = reconstruct_wp_view(feature_dir, wp_id)

        self._resolved_view_loaded = True
        self._resolved_view_cache = view
        return view

    @property
    def assignee(self) -> str | None:
        # Snapshot-sourced via the one reconstruction reader (C-001): an absent
        # resolved slot is authoritative empty, never a frontmatter fallback.
        view = self._resolved_view()
        return view.resolved.assignee if view is not None else None

    @property
    def agent(self) -> str | None:
        # Snapshot-sourced via the one reconstruction reader (C-001): an absent
        # resolved slot is authoritative empty, never a frontmatter fallback.
        view = self._resolved_view()
        return view.resolved.agent if view is not None else None

    @property
    def shell_pid(self) -> str | None:
        # Snapshot-sourced via the one reconstruction reader (C-001): an absent
        # resolved slot is authoritative empty, never a frontmatter fallback.
        view = self._resolved_view()
        return view.resolved.shell_pid if view is not None else None

    @property
    def shell_pid_created_at(self) -> str | None:
        view = self._resolved_view()
        return view.resolved.shell_pid_created_at if view is not None else None

    @property
    def subtasks(self) -> Mapping[str, str]:
        view = self._resolved_view()
        return view.resolved.subtasks if view is not None else {}

    @property
    def review(self) -> Mapping[str, Any] | None:
        view = self._resolved_view()
        return view.resolved.review if view is not None else None

    @property
    def role(self) -> str | None:
        """Resolved *actual* role that ran (event-sourced); ``None`` when the WP
        was never bound. Authored recommendation: :attr:`authored_role`."""
        view = self._resolved_view()
        return view.resolved.role if view is not None else None

    @property
    def agent_profile(self) -> str | None:
        """Resolved *actual* agent profile (event-sourced); ``None`` when the WP
        was never bound. Authored recommendation:
        :attr:`authored_agent_profile` (C-008 -- never conflate the two)."""
        view = self._resolved_view()
        return view.resolved.agent_profile if view is not None else None

    @property
    def agent_profile_version(self) -> str | None:
        view = self._resolved_view()
        return view.resolved.agent_profile_version if view is not None else None

    @property
    def model(self) -> str | None:
        """Resolved *actual* model (event-sourced); ``None`` when the WP was
        never bound. Authored recommendation: :attr:`authored_model`."""
        view = self._resolved_view()
        return view.resolved.model if view is not None else None

    @property
    def provider(self) -> str | None:
        view = self._resolved_view()
        return view.resolved.provider if view is not None else None

    @property
    def authored_role(self) -> str | None:
        """Authored (frontmatter) role recommendation -- the design intent,
        distinct from the resolved actual :attr:`role` (C-008)."""
        return extract_scalar(self.frontmatter, "role")

    @property
    def authored_agent_profile(self) -> str | None:
        """Authored (frontmatter) agent-profile recommendation -- distinct from the
        resolved actual :attr:`agent_profile` (C-008)."""
        return extract_scalar(self.frontmatter, "agent_profile")

    @property
    def authored_model(self) -> str | None:
        """Authored (frontmatter) model recommendation -- distinct from the resolved
        actual :attr:`model` (C-008)."""
        return extract_scalar(self.frontmatter, "model")

    @property
    def lane(self) -> str | None:
        view = self._resolved_view()
        if view is None or view.resolved.lane is None:
            return "uninitialized"
        return str(view.resolved.lane)


def locate_work_package(repo_root: Path, feature: str, wp_id: str) -> WorkPackage:
    """Locate a work package by ID, supporting both legacy and new formats.

    Always uses main repo's kitty-specs/ regardless of current directory.
    Main branch is authoritative for planning artifacts.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    from mission_runtime import MissionArtifactKind
    from specify_cli.coordination import resolve_status_surface
    from specify_cli.core.paths import get_main_repo_root
    from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
    from specify_cli.status import reconstruct_wp_view

    # Always use main repo's kitty-specs - it's the source of truth.
    # Route through the seam (WORK_PACKAGE_TASK) so tasks/ reads resolve to the
    # primary checkout under coord topology (coord husk carries STATUS only).
    main_root = get_main_repo_root(repo_root)
    feature_path = resolve_planning_read_dir(
        main_root, feature, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    status_dir = resolve_status_surface(main_root, feature).parent

    tasks_root = feature_path / "tasks"
    if not tasks_root.exists():
        raise TaskCliError(f"Feature '{feature}' has no tasks directory at {tasks_root}.")

    # Use exact WP ID matching with word boundary to avoid WP04 matching WP04b
    # Matches: WP04.md, WP04-something.md, WP04_something.md
    # Does NOT match: WP04b.md, WP04b-something.md
    wp_pattern = re.compile(rf"^{re.escape(wp_id)}(?:[-_.]|\.md$)")

    candidates = []

    # Flat-layout only: search flat tasks/ directory (lane from frontmatter).
    # The boundary guard (WP02) prevents pre-3.0 projects from reaching here.
    for path in tasks_root.glob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        if wp_pattern.match(path.name):
            # Mutable lane state is authoritative on the resolved status
            # partition, which may differ from the planning-file partition.
            lane = reconstruct_wp_view(status_dir, wp_id).resolved.lane or "uninitialized"
            candidates.append((lane, path, tasks_root))

    if not candidates:
        raise TaskCliError(f"Work package '{wp_id}' not found under kitty-specs/{feature}/tasks.")
    if len(candidates) > 1:
        joined = "\n".join(str(item[1].relative_to(repo_root)) for item in candidates)
        raise TaskCliError(f"Multiple files matched '{wp_id}'. Refine the ID or clean duplicates:\n{joined}")

    lane, path, base_dir = candidates[0]
    text = path.read_text(encoding="utf-8-sig")
    front, body, padding = split_frontmatter(text)
    relative = path.relative_to(base_dir)
    return WorkPackage(
        feature=feature,
        path=path,
        current_lane=lane,
        relative_subpath=relative,
        frontmatter=front,
        body=body,
        padding=padding,
        status_dir=status_dir,
    )


def load_meta(meta_path: Path) -> dict[str, Any]:
    """Load ``meta.json`` from *meta_path* (path-signature adapter; NOT canonical).

    The CANONICAL meta-reader authority is
    :func:`specify_cli.mission_metadata.load_meta` (imported here as
    ``_load_meta_canonical``).  This function is a thin **adapter** retained only
    for its distinct calling convention -- it takes the ``meta.json`` *file path*
    (not the parent dir) and translates the canonical
    :class:`FileNotFoundError` into a :class:`TaskCliError` for the task CLI.  It
    delegates entirely to the canonical reader and adds no parallel contract
    (FR-009 / SC-004: the canonical authority is unambiguous -- this is an
    adapter, not a fork).

    Preserves the original contract: missing → :class:`TaskCliError`,
    malformed JSON → :class:`ValueError` (behavior-neutral; original raised
    ``json.JSONDecodeError``, which ``ValueError`` wraps via the canonical reader).
    BOM-tolerant (``utf-8-sig`` encoding).

    Args:
        meta_path: Path to the ``meta.json`` file (not the parent directory).

    Raises:
        TaskCliError: When ``meta_path`` does not exist.
        ValueError: When ``meta_path`` contains malformed JSON or a non-object
            top level.
    """
    try:
        result = _load_meta_canonical(
            meta_path.parent,
            allow_missing=False,
            on_malformed="raise",
            encoding="utf-8-sig",
        )
    except FileNotFoundError as exc:
        raise TaskCliError(f"Meta file not found at {meta_path}") from exc
    # allow_missing=False raises on missing; on_malformed="raise" raises on bad
    # JSON — so result is always a dict here.  ``or {}`` narrows ``| None`` for
    # the type checker without an assert that ``-O`` would strip.
    return result or {}


def get_lane_from_frontmatter(wp_path: Path, warn_on_missing: bool = True) -> str:  # noqa: ARG001
    """Return canonical lane for a WP from the event log.

    Reads exclusively from the canonical event log via ``get_wp_lane()``.
    Raises ``CanonicalStatusNotFoundError`` when the event log is absent.

    Args:
        wp_path: Path to the work package markdown file
        warn_on_missing: Unused; retained for call-site compatibility

    Returns:
        Lane value from event log, or ``"uninitialized"`` when WP has no events.
    """
    # Derive feature_dir: WP files live at kitty-specs/<slug>/tasks/WP01.md
    feature_dir = wp_path.parent.parent

    text = wp_path.read_text(encoding="utf-8-sig")
    frontmatter, _body, _padding = split_frontmatter(text)
    wp_id = extract_scalar(frontmatter, "work_package_id")
    if not wp_id:
        stem = wp_path.stem
        wp_id_match = re.match(r"^(WP\d+)(?=$|[-_.])", stem, re.IGNORECASE)
        wp_id = wp_id_match.group(1).upper() if wp_id_match else stem

    from specify_cli.status import get_wp_lane

    # cast: get_wp_lane's -> str return is erased to Any at the specify_cli.*
    # follow_imports=skip boundary; type-only, no behaviour change.
    return cast(str, get_wp_lane(feature_dir, wp_id))


__all__ = [
    "LANES",
    "LANE_ALIASES",
    "TIMESTAMP_FORMAT",
    "TaskCliError",
    "WorkPackage",
    "append_activity_log",
    "activity_entries",
    "build_document",
    "detect_conflicting_wp_status",
    "ensure_lane",
    "extract_scalar",
    "find_repo_root",
    "get_lane_from_frontmatter",
    "git_status_lines",
    # Path-signature adapter over the canonical mission_metadata.load_meta
    # (FR-009 / SC-004) -- not a parallel authority; see its docstring.
    "load_meta",
    "locate_work_package",
    "match_frontmatter_line",
    "normalize_note",
    "now_utc",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]
