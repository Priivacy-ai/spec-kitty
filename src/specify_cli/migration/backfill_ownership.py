"""Infer and backfill ownership fields for legacy work packages.

Calls the inference functions from :mod:`specify_cli.ownership.inference`
to derive ``execution_mode``, ``owned_files``, and ``authoritative_surface``
for each WP that does not already have these fields.

Additionally attempts a best-effort git-diff to discover actually-changed
files when a WP branch exists.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from specify_cli.ownership.inference import (
    infer_authoritative_surface,
    infer_execution_mode,
    infer_owned_files,
)
from specify_cli.ownership.validation import validate_all

logger = logging.getLogger(__name__)


def _git_diff_files(repo_root: Path, base_branch: str, wp_branch: str) -> list[str]:
    """Return file paths changed between *base_branch* and *wp_branch*.

    Returns an empty list on any error (branch not found, git not available).

    Args:
        repo_root: Root directory of the git repository.
        base_branch: The base/target branch (e.g. ``"main"``).
        wp_branch: The WP's feature branch.

    Returns:
        Sorted list of relative file paths touched by the WP branch.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_branch}..{wp_branch}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        if result.returncode == 0:
            files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            logger.debug("git diff %s..%s: %d files", base_branch, wp_branch, len(files))
            return sorted(files)
    except Exception as exc:
        logger.debug("git diff failed for branch %s: %s", wp_branch, exc)
    return []


def backfill_ownership(feature_dir: Path, feature_slug: str) -> None:
    """Infer and write ownership fields for all WPs in *feature_dir*.

    For each ``tasks/WP*.md`` file:

    1. Reads the WP body content.
    2. Optionally gathers actually-changed files via ``git diff`` if the WP
       has a ``base_branch`` and ``wp_branch`` in its frontmatter.
    3. Calls inference functions to derive ``execution_mode``, ``owned_files``,
       and ``authoritative_surface``.
    4. Writes inferred values only when the field is **absent** from frontmatter
       (never overwrites existing values).

    After processing all WPs, runs :func:`~specify_cli.ownership.validation.validate_all`
    and logs any warnings — validation failures do NOT abort the migration.

    Args:
        feature_dir: Path to the feature directory (e.g. ``kitty-specs/057-…``).
        feature_slug: Slug of the feature (e.g. ``"057-canonical-context-architecture-cleanup"``).
    """
    from specify_cli.frontmatter import FrontmatterManager

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        logger.debug("No tasks/ directory in %s — skipping ownership backfill", feature_dir.name)
        return

    manager = FrontmatterManager()
    manifests: dict = {}  # wp_code → OwnershipManifest

    # Locate repo root: walk up until we find a .git directory
    repo_root: Path | None = None
    candidate = feature_dir
    for _ in range(10):
        if (candidate / ".git").exists():
            repo_root = candidate
            break
        candidate = candidate.parent

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            frontmatter, body = manager.read(wp_file)
        except Exception as exc:
            logger.warning("Cannot read %s: %s — skipping ownership backfill", wp_file.name, exc)
            continue

        # Derive wp_code for manifests key
        _m_code = re.match(r"^(WP\d+)", wp_file.stem)
        _wp_code_key = _m_code.group(1) if _m_code else wp_file.stem

        # Skip if all three ownership fields already present
        has_mode = "execution_mode" in frontmatter
        has_files = "owned_files" in frontmatter
        has_surface = "authoritative_surface" in frontmatter
        if has_mode and has_files and has_surface:
            logger.debug("Ownership already present for %s — skipping", wp_file.name)
            # Still gather for validation
            try:
                from specify_cli.ownership.models import OwnershipManifest as _OM
                manifests[_wp_code_key] = _OM.from_frontmatter(frontmatter)
            except Exception:
                pass
            continue

        # Full WP content for inference
        full_content = body

        # Best-effort: try to get actually-changed files from git diff
        git_files: list[str] = []
        if repo_root is not None:
            base_branch = frontmatter.get("base_branch") or frontmatter.get("planning_base_branch") or ""
            # Build a candidate WP branch name
            wp_code = frontmatter.get("wp_code", "")
            if not wp_code:
                # Try to parse from filename
                m_code = re.match(r"^(WP\d+)", wp_file.stem)
                wp_code = m_code.group(1) if m_code else ""

            if base_branch and wp_code:
                wp_branch = f"{feature_slug}-{wp_code}"
                git_files = _git_diff_files(repo_root, base_branch, wp_branch)

        updates: dict = {}

        if not has_mode:
            mode = infer_execution_mode(full_content, git_files)
            updates["execution_mode"] = str(mode)

        if not has_files:
            owned = infer_owned_files(full_content, feature_slug)
            # Prefer git-diff files if available and execution_mode is code_change
            if git_files and updates.get("execution_mode") == "code_change":
                owned = git_files
            updates["owned_files"] = owned

        if not has_surface:
            current_files = updates.get("owned_files") or frontmatter.get("owned_files") or []
            surface = infer_authoritative_surface(current_files)
            updates["authoritative_surface"] = surface

        if updates:
            frontmatter.update(updates)
            manager.write(wp_file, frontmatter, body)
            logger.info(
                "Backfilled ownership for %s: execution_mode=%s",
                wp_file.name,
                frontmatter.get("execution_mode"),
            )

        # Gather manifest for cross-WP validation
        try:
            from specify_cli.ownership.models import OwnershipManifest
            manifests[_wp_code_key] = OwnershipManifest.from_frontmatter(frontmatter)
        except Exception as exc:
            logger.debug("Could not build OwnershipManifest for %s: %s", wp_file.name, exc)

    # Cross-WP validation — warnings only, never fail
    if manifests:
        result = validate_all(manifests)
        for warning in result.warnings:
            logger.warning("Ownership validation warning: %s", warning)
        for error in result.errors:
            logger.warning("Ownership validation error (non-fatal): %s", error)
