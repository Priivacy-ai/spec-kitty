"""Replace agent command files with thin 3-line shims.

Delegates all generation to :func:`~specify_cli.shims.generator.generate_all_shims`.
Also removes any stale command files in agent directories that are NOT part
of the newly generated shim set.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RewriteResult:
    """Summary of a :func:`rewrite_agent_shims` run.

    Attributes:
        agents_processed: Number of agent directories touched.
        files_written: Paths of shim files that were written (created or
            overwritten).
        files_deleted: Paths of stale command files that were removed.
        warnings: List of non-fatal warning messages.
    """

    agents_processed: int = 0
    files_written: list[Path] = field(default_factory=list)
    files_deleted: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def rewrite_agent_shims(repo_root: Path) -> RewriteResult:
    """Replace all agent command files with thin shims.

    Calls :func:`~specify_cli.shims.generator.generate_all_shims` to write
    the canonical 3-line shim for each (agent, skill) pair.  After generation,
    any ``spec-kitty.*.md`` files that remain in the agent command directories
    but were **not** in the generated set are deleted — they are stale workflow
    templates from the pre-canonical era.

    Only processes agent directories that are configured in
    ``.kittify/config.yaml`` (via
    :func:`~specify_cli.agent_utils.directories.get_agent_dirs_for_project`).

    Args:
        repo_root: Absolute path to the project root.

    Returns:
        :class:`RewriteResult` with counts of agents processed, files written,
        and files deleted.
    """
    from specify_cli.shims.generator import generate_all_shims
    from specify_cli.agent_utils.directories import get_agent_dirs_for_project

    result = RewriteResult()

    # Generate (and overwrite) all shims
    try:
        written = generate_all_shims(repo_root)
        result.files_written = list(written)
    except Exception as exc:
        msg = f"generate_all_shims failed: {exc}"
        logger.error(msg)
        result.warnings.append(msg)
        return result

    written_set: set[Path] = set(result.files_written)

    # Discover agent command directories to clean up stale files
    agent_dirs = get_agent_dirs_for_project(repo_root)
    seen_dirs: set[Path] = set()

    for agent_root, command_subdir in agent_dirs:
        agent_cmd_dir = repo_root / agent_root / command_subdir
        if not agent_cmd_dir.is_dir():
            continue

        if agent_cmd_dir in seen_dirs:
            continue
        seen_dirs.add(agent_cmd_dir)
        result.agents_processed += 1

        # Remove stale spec-kitty.*.md files not in the generated set
        for stale_file in sorted(agent_cmd_dir.glob("spec-kitty.*.md")):
            if stale_file not in written_set:
                try:
                    stale_file.unlink()
                    result.files_deleted.append(stale_file)
                    logger.info("Deleted stale shim file: %s", stale_file)
                except Exception as exc:
                    msg = f"Failed to delete stale file {stale_file}: {exc}"
                    logger.warning(msg)
                    result.warnings.append(msg)

    logger.info(
        "rewrite_agent_shims: %d agents, %d written, %d deleted",
        result.agents_processed,
        len(result.files_written),
        len(result.files_deleted),
    )
    return result
