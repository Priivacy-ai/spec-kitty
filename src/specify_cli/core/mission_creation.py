"""Reusable feature-creation logic extracted from the CLI command.

This module provides ``create_feature_core()`` -- the programmatic API
for creating a new feature directory with all scaffolding.  The CLI
command ``create_feature()`` is a thin wrapper around this function.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.core.git_ops import get_current_branch, is_git_repo
from specify_cli.core.paths import is_worktree_context, locate_project_root
from specify_cli.core.worktree import get_next_feature_number
from specify_cli.git import safe_commit
from specify_cli.sync.events import emit_mission_created


class FeatureCreationError(RuntimeError):
    """Raised when feature creation fails."""


@dataclass(slots=True)
class FeatureCreationResult:
    """Structured result from ``create_feature_core()``."""

    feature_dir: Path
    feature_slug: str
    feature_number: str
    meta: dict[str, Any]
    target_branch: str
    current_branch: str
    created_files: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

TASKS_README_CONTENT = """\
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
planning_base_branch: "2.x"
merge_target_branch: "2.x"
branch_strategy: "Planning artifacts were generated on 2.x; completed changes must merge back into 2.x."
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _commit_feature_file(
    file_path: Path,
    feature_slug: str,
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
        raise FeatureCreationError("Not in a git repository")

    commit_msg = f"Add {artifact_type} for feature {feature_slug}"
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


def create_feature_core(
    repo_root: Path | None,
    feature_slug: str,
    *,
    mission: str | None = None,
    target_branch: str | None = None,
) -> FeatureCreationResult:
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
    feature_slug:
        Bare slug such as ``"user-auth"`` (kebab-case, no number prefix).
    mission:
        Optional mission key (e.g. ``"documentation"``, ``"software-dev"``).
        Defaults to ``"software-dev"`` when not provided.
    target_branch:
        Explicit target branch for the feature.  When *None* the current
        git branch is used.

    Returns
    -------
    FeatureCreationResult
        Structured result with all paths and metadata.

    Raises
    ------
    FeatureCreationError
        On any validation or creation failure.
    """
    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    if not KEBAB_CASE_PATTERN.match(feature_slug):
        raise FeatureCreationError(
            f"Invalid feature slug '{feature_slug}'. "
            "Must be kebab-case (lowercase letters, numbers, hyphens only)."
            "\n\nValid examples:"
            "\n  - user-auth"
            "\n  - fix-bug-123"
            "\n  - new-dashboard"
            "\n\nInvalid examples:"
            "\n  - User-Auth (uppercase)"
            "\n  - user_auth (underscores)"
            "\n  - 123-fix (starts with number)"
        )

    # ------------------------------------------------------------------
    # 2. Context guards
    # ------------------------------------------------------------------
    cwd = Path.cwd().resolve()
    if is_worktree_context(cwd):
        raise FeatureCreationError("Cannot create features from inside a worktree. Run from the project root checkout.")

    resolved_root = repo_root
    if resolved_root is None:
        resolved_root = locate_project_root()
    if resolved_root is None:
        raise FeatureCreationError("Could not locate project root. Run from within spec-kitty repository.")

    if not is_git_repo(resolved_root):
        raise FeatureCreationError("Not in a git repository. Feature creation requires git.")

    current_branch = get_current_branch(resolved_root)
    if not current_branch or current_branch == "HEAD":
        raise FeatureCreationError("Must be on a branch to create features (detached HEAD detected).")

    # ------------------------------------------------------------------
    # 3. Resolve planning branch
    # ------------------------------------------------------------------
    planning_branch = target_branch if target_branch else current_branch

    # ------------------------------------------------------------------
    # 4. Feature number allocation + directory creation
    # ------------------------------------------------------------------
    feature_number = get_next_feature_number(resolved_root)
    feature_slug_formatted = f"{feature_number:03d}-{feature_slug}"

    feature_dir = resolved_root / "kitty-specs" / feature_slug_formatted
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
    tasks_readme.write_text(TASKS_README_CONTENT, encoding="utf-8")

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

    # Commit spec.md (non-fatal)
    with contextlib.suppress(Exception):
        _commit_feature_file(spec_file, feature_slug_formatted, "spec", resolved_root)

    # ------------------------------------------------------------------
    # 6. meta.json
    # ------------------------------------------------------------------
    meta_file = feature_dir / "meta.json"
    meta: dict[str, Any] = {}
    if meta_file.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            meta = json.loads(meta_file.read_text(encoding="utf-8"))

    meta.setdefault("mission_number", f"{feature_number:03d}")
    meta.setdefault("slug", feature_slug_formatted)
    meta.setdefault("mission_slug", feature_slug_formatted)
    meta.setdefault("friendly_name", feature_slug.replace("-", " ").strip())
    meta.setdefault("mission_type", mission or "software-dev")
    meta.setdefault("target_branch", planning_branch)
    meta.setdefault("created_at", datetime.now(timezone.utc).isoformat())  # noqa: UP017

    from specify_cli.mission_metadata import set_documentation_state, write_meta

    write_meta(feature_dir, meta)
    with contextlib.suppress(Exception):
        _commit_feature_file(meta_file, feature_slug_formatted, "meta", resolved_root)

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
            _commit_feature_file(meta_file, feature_slug_formatted, "meta", resolved_root)

    # ------------------------------------------------------------------
    # 8. Event emission (fire-and-forget)
    # ------------------------------------------------------------------
    with contextlib.suppress(Exception):
        emit_mission_created(
            feature_slug=feature_slug_formatted,
            feature_number=f"{feature_number:03d}",
            target_branch=planning_branch,
            wp_count=0,
        )

    # Dossier sync (fire-and-forget)
    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import (
            trigger_feature_dossier_sync_if_enabled,
        )

        trigger_feature_dossier_sync_if_enabled(
            feature_dir,
            feature_slug_formatted,
            resolved_root,
        )

    # ------------------------------------------------------------------
    # 9. Build result
    # ------------------------------------------------------------------
    created_files = [spec_file, meta_file, tasks_readme]

    return FeatureCreationResult(
        feature_dir=feature_dir,
        feature_slug=feature_slug_formatted,
        feature_number=f"{feature_number:03d}",
        meta=meta,
        target_branch=planning_branch,
        current_branch=current_branch,
        created_files=created_files,
    )
