"""Reusable mission-creation logic extracted from the CLI command.

This module provides ``create_mission_core()`` -- the programmatic API
for creating a new mission directory with all scaffolding. The CLI
command ``create()`` is a thin wrapper around this function.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ulid import ULID

from specify_cli.core.git_ops import get_current_branch, is_git_repo
from specify_cli.core.paths import is_worktree_context, locate_project_root
from specify_cli.git import safe_commit
from specify_cli.lanes.branch_naming import mid8, strip_numeric_prefix
from specify_cli.mission_metadata import validate_purpose_summary
from specify_cli.sync.events import emit_mission_created

logger = logging.getLogger(__name__)


class MissionCreationError(RuntimeError):
    """Raised when mission creation fails."""


@dataclass(slots=True)
class MissionCreationResult:
    """Structured result from ``create_mission_core()``."""

    feature_dir: Path
    mission_slug: str
    mission_number: int | None  # None for pre-merge missions (FR-044)
    meta: dict[str, Any]
    target_branch: str
    current_branch: str
    created_files: list[Path] = field(default_factory=list)
    origin_binding_attempted: bool = False
    origin_binding_succeeded: bool = False
    origin_binding_error: str | None = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$")
# Note: Intentionally permissive — bare-digit slugs like "069" are accepted.
# create_mission_core() always prefixes the mission number, so "069" becomes "070-069" in practice.

TASKS_README_TEMPLATE = """\
# Tasks Directory

This directory contains work package (WP) prompt files.

## Directory Structure (v0.9.0+)

```
tasks/
\u251c\u2500\u2500 WP01-setup-infrastructure.md
\u251c\u2500\u2500 WP02-user-authentication.md
\u251c\u2500\u2500 WP03-api-endpoints.md
\u2514\u2500\u2500 README.md
```

All WP files are stored flat in `tasks/`. Status is tracked in `status.events.jsonl`, not in WP frontmatter.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
dependencies: []
planning_base_branch: "{planning_branch}"
merge_target_branch: "{planning_branch}"
branch_strategy: "Planning artifacts were generated on {planning_branch}; completed changes must merge back into {planning_branch}."
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 \u2013 Work Package Title

[Content follows...]
```

## Status Tracking

Status is tracked via the canonical event log (`status.events.jsonl`), not in WP frontmatter.
Use `spec-kitty agent tasks move-task` to change WP status:

```bash
spec-kitty agent tasks move-task <WPID> --to <lane>
```

Example:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
"""


def _default_mission_display_name(mission_slug: str) -> str:
    """Derive a human-readable mission title from a kebab-case slug."""
    parts = [part for part in str(mission_slug).strip().split("-") if part]
    if not parts:
        return "Mission"
    return " ".join(parts)


def _default_mission_purpose_context(display_name: str, target_branch: str) -> str:
    """Keep mission-create defaults aligned with MissionCreated sync payloads."""
    return f"This mission advances {display_name} on {target_branch} so stakeholders can track the work from mission creation onward."


def render_tasks_readme_content(planning_branch: str) -> str:
    """Render tasks/README.md with branch-aware example frontmatter."""
    return TASKS_README_TEMPLATE.format(planning_branch=planning_branch)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _commit_feature_file(
    file_path: Path,
    mission_slug: str,
    artifact_type: str,
    repo_root: Path,
) -> None:
    """Commit a single planning artifact to the current branch.

    This is a slim, typer-free version of the ``_commit_to_branch`` helper
    in the CLI module.  It raises on hard failures and silently succeeds
    when there is nothing to commit.
    """
    current_branch = get_current_branch(repo_root)
    if current_branch is None:
        raise MissionCreationError("Not in a git repository")

    commit_msg = f"Add {artifact_type} for feature {mission_slug}"
    success = safe_commit(
        repo_path=repo_root,
        files_to_commit=[file_path],
        commit_message=commit_msg,
        allow_empty=False,
    )
    if not success:
        raise RuntimeError(f"Failed to commit {artifact_type}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_mission_core(
    repo_root: Path | None,
    mission_slug: str,
    *,
    mission: str | None = None,
    target_branch: str | None = None,
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
) -> MissionCreationResult:
    """Create a new feature with all scaffolding.

    This is the programmatic API for feature creation.  Unlike the CLI
    command, it returns a structured result and raises domain exceptions
    instead of calling ``typer.Exit()``.

    Parameters
    ----------
    repo_root:
        Absolute path to the project root (must contain ``.kittify/`` and
        ``kitty-specs/``).  When *None*, ``locate_project_root()`` is called
        automatically.
    mission_slug:
        Bare slug such as ``"user-auth"`` or ``"068-feature"`` (kebab-case).
    mission:
        Optional mission key (e.g. ``"documentation"``, ``"software-dev"``).
        Defaults to ``"software-dev"`` when not provided.
    target_branch:
        Explicit target branch for the feature.  When *None* the current
        git branch is used.
    friendly_name:
        Optional mission title shown on operator-facing surfaces. When omitted,
        it is derived from ``mission_slug``.
    purpose_tldr:
        Optional one-line product/CXO summary for the mission. When omitted,
        it defaults to the resolved ``friendly_name``.
    purpose_context:
        Optional short paragraph explaining the mission in stakeholder terms.
        When omitted, it defaults to a branch-aware summary sentence.

    Returns
    -------
    MissionCreationResult
        Structured result with all paths and metadata.

    Raises
    ------
    MissionCreationError
        On any validation or creation failure.
    """
    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    if not KEBAB_CASE_PATTERN.match(mission_slug):
        raise MissionCreationError(
            f"Invalid feature slug '{mission_slug}'. "
            "Must be kebab-case (lowercase letters, numbers, hyphens only)."
            "\n\nValid examples:"
            "\n  - user-auth"
            "\n  - fix-bug-123"
            "\n  - 068-feature-name"
            "\n  - new-dashboard"
            "\n\nInvalid examples:"
            "\n  - User-Auth (uppercase)"
            "\n  - user_auth (underscores)"
        )

    friendly_name_was_provided = friendly_name is not None
    normalized_friendly_name = " ".join((friendly_name or "").split())
    if friendly_name_was_provided and not normalized_friendly_name:
        raise MissionCreationError("Mission creation requires a non-empty friendly_name.")

    # ------------------------------------------------------------------
    # 2. Context guards
    # ------------------------------------------------------------------
    cwd = Path.cwd().resolve()
    if is_worktree_context(cwd):
        raise MissionCreationError("Cannot create missions from inside a worktree. Run from the project root checkout.")

    resolved_root = repo_root
    if resolved_root is None:
        resolved_root = locate_project_root()
    if resolved_root is None:
        raise MissionCreationError("Could not locate project root. Run from within spec-kitty repository.")

    if not is_git_repo(resolved_root):
        raise MissionCreationError("Not in a git repository. Mission creation requires git.")

    current_branch = get_current_branch(resolved_root)
    if not current_branch or current_branch == "HEAD":
        raise MissionCreationError("Must be on a branch to create missions (detached HEAD detected).")

    # ------------------------------------------------------------------
    # 3. Resolve planning branch
    # ------------------------------------------------------------------
    planning_branch = target_branch if target_branch else current_branch
    if not normalized_friendly_name:
        normalized_friendly_name = _default_mission_display_name(mission_slug)

    normalized_purpose_tldr = " ".join((purpose_tldr or "").split()) if purpose_tldr is not None else normalized_friendly_name
    normalized_purpose_context = (
        " ".join((purpose_context or "").split()) if purpose_context is not None else _default_mission_purpose_context(normalized_friendly_name, planning_branch)
    )
    purpose_errors = validate_purpose_summary(normalized_purpose_tldr, normalized_purpose_context)
    if purpose_errors:
        raise MissionCreationError(" ".join(purpose_errors))

    # ------------------------------------------------------------------
    # 4. Directory creation — human-slug + mid8 format (FR-032, FR-044)
    #
    # Pre-merge missions are identified by mission_id (ULID) only.
    # No feature_number is allocated here; mission_number stays None
    # until merge time (single-writer context on main).
    # ------------------------------------------------------------------
    # Mint the ULID first so we can derive mid8 for the directory name.
    mission_id = str(ULID())
    human_slug = strip_numeric_prefix(mission_slug)
    mission_slug_formatted = f"{human_slug}-{mid8(mission_id)}"

    feature_dir = resolved_root / "kitty-specs" / mission_slug_formatted
    feature_dir.mkdir(parents=True, exist_ok=True)

    (feature_dir / "checklists").mkdir(exist_ok=True)
    (feature_dir / "research").mkdir(exist_ok=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    (tasks_dir / ".gitkeep").touch()

    # Initialize empty event log so the feature has canonical status from birth.
    (feature_dir / "status.events.jsonl").touch(exist_ok=True)

    # Tasks README
    tasks_readme = tasks_dir / "README.md"
    tasks_readme.write_text(
        render_tasks_readme_content(planning_branch),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # 5. Spec template
    # ------------------------------------------------------------------
    spec_file = feature_dir / "spec.md"
    if not spec_file.exists():
        spec_template_candidates = [
            resolved_root / ".kittify" / "templates" / "spec-template.md",
            resolved_root / "templates" / "spec-template.md",
        ]
        for template in spec_template_candidates:
            if template.exists():
                shutil.copy2(template, spec_file)
                break
        else:
            spec_file.touch()

    # NOTE: spec.md is intentionally NOT committed here (issue #846).
    # The empty scaffold remains on disk but untracked at create time.
    # The agent commits the populated spec.md from the /spec-kitty.specify
    # slash-template after writing substantive content. The substantive-content
    # gate at `setup-plan` entry (see specify_cli.missions._substantive) enforces
    # that spec.md is committed AND substantive before plan.md can be scaffolded.
    # See:
    #   kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md

    # ------------------------------------------------------------------
    # 6. meta.json
    # ------------------------------------------------------------------
    meta_file = feature_dir / "meta.json"
    meta: dict[str, Any] = {}
    if meta_file.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Mint canonical machine-facing identity. The ULID was already generated
    # above (needed for mid8 directory naming). The ULID is immutable after creation.
    # mission_number is null pre-merge; a dense display number is assigned only
    # at merge time (single-writer context on main). See FR-044.
    meta.setdefault("mission_id", mission_id)
    meta.setdefault("mission_number", None)  # JSON null — pre-merge missions have no number
    meta.setdefault("slug", mission_slug_formatted)
    meta.setdefault("mission_slug", mission_slug_formatted)
    meta.setdefault("friendly_name", normalized_friendly_name)
    meta.setdefault("purpose_tldr", normalized_purpose_tldr)
    meta.setdefault("purpose_context", normalized_purpose_context)
    meta.setdefault("mission_type", mission or "software-dev")
    meta.setdefault("target_branch", planning_branch)
    meta.setdefault("created_at", datetime.now(timezone.utc).isoformat())  # noqa: UP017

    from specify_cli.mission_metadata import set_documentation_state, write_meta

    write_meta(feature_dir, meta)
    with contextlib.suppress(Exception):
        _commit_feature_file(meta_file, mission_slug_formatted, "meta", resolved_root)

    # ------------------------------------------------------------------
    # 7. Documentation state (if applicable)
    # ------------------------------------------------------------------
    if mission == "documentation":
        meta.setdefault("mission_type", "documentation")
        if "documentation_state" not in meta:
            doc_state: dict[str, Any] = {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            }
            set_documentation_state(feature_dir, doc_state)
        with contextlib.suppress(Exception):
            _commit_feature_file(meta_file, mission_slug_formatted, "meta", resolved_root)

    # ------------------------------------------------------------------
    # 8. Event emission (fire-and-forget)
    # ------------------------------------------------------------------
    with contextlib.suppress(Exception):
        emit_mission_created(
            mission_slug=mission_slug_formatted,
            mission_number=None,  # no number pre-merge (FR-044)
            mission_type=str(meta.get("mission_type") or mission or "software-dev"),
            target_branch=planning_branch,
            wp_count=0,
            friendly_name=normalized_friendly_name,
            purpose_tldr=normalized_purpose_tldr,
            purpose_context=normalized_purpose_context,
            created_at=str(meta["created_at"]) if meta.get("created_at") else None,
            mission_id=meta.get("mission_id"),
        )

    # Dossier sync (fire-and-forget)
    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import (
            trigger_feature_dossier_sync_if_enabled,
        )

        trigger_feature_dossier_sync_if_enabled(
            feature_dir,
            mission_slug_formatted,
            resolved_root,
        )

    # ------------------------------------------------------------------
    # 9. Consume pending origin if present (ticket-first flow)
    # ------------------------------------------------------------------
    origin_binding_attempted = False
    origin_binding_succeeded = False
    origin_binding_error: str | None = None

    origin_binding_attempted, origin_binding_succeeded, origin_binding_error, meta = _consume_pending_origin_if_present(
        repo_root=resolved_root,
        feature_dir=feature_dir,
        meta=meta,
    )

    # ------------------------------------------------------------------
    # 10. Build result
    # ------------------------------------------------------------------
    created_files = [spec_file, meta_file, tasks_readme]

    return MissionCreationResult(
        feature_dir=feature_dir,
        mission_slug=mission_slug_formatted,
        mission_number=None,  # pre-merge: no display number assigned (FR-044)
        meta=meta,
        target_branch=planning_branch,
        current_branch=current_branch,
        created_files=created_files,
        origin_binding_attempted=origin_binding_attempted,
        origin_binding_succeeded=origin_binding_succeeded,
        origin_binding_error=origin_binding_error,
    )


def _consume_pending_origin_if_present(
    *,
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Bind a staged pending origin after mission creation, if present."""
    from specify_cli.tracker.origin import OriginBindingError, bind_mission_origin
    from specify_cli.tracker.origin_models import OriginCandidate
    from specify_cli.tracker.ticket_context import clear_pending_origin, read_pending_origin

    pending = read_pending_origin(repo_root)
    if not pending:
        return False, False, None, meta

    provider = str(pending.get("provider") or "").strip().lower()
    issue_id = str(pending.get("issue_id") or "").strip()
    issue_key = str(pending.get("issue_key") or "").strip()

    if not provider or not issue_id or not issue_key:
        return (
            True,
            False,
            "Pending origin is missing required provider/issue identifiers.",
            meta,
        )

    candidate = OriginCandidate(
        external_issue_id=issue_id,
        external_issue_key=issue_key,
        title=str(pending.get("title") or "").strip(),
        status=str(pending.get("status") or "").strip(),
        url=str(pending.get("url") or "").strip(),
        match_type="pending_origin",
        body=str(pending.get("body") or "").strip() or None,
    )

    try:
        updated_meta, _ = bind_mission_origin(
            feature_dir=feature_dir,
            candidate=candidate,
            provider=provider,
            resource_type=None,
            resource_id=None,
        )
    except OriginBindingError as exc:
        logger.warning("Pending origin bind failed for %s: %s", feature_dir, exc)
        return True, False, str(exc), meta
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pending origin bind failed unexpectedly for %s: %s", feature_dir, exc)
        return True, False, str(exc), meta

    clear_pending_origin(repo_root)
    return True, True, None, updated_meta
