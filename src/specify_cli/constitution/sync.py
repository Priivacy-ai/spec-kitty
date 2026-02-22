"""Constitution sync orchestrator.

Provides the main sync() function that orchestrates:
1. Read constitution.md
2. Check staleness (skip if unchanged, unless --force)
3. Parse and extract to YAML
4. Write governance/directives/metadata files
5. Update metadata with hash and timestamp
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.constitution.extractor import Extractor, write_extraction_result
from specify_cli.constitution.hasher import is_stale
from specify_cli.constitution.schemas import (
    DirectivesConfig,
    GovernanceConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a constitution sync operation."""

    synced: bool  # True if extraction ran
    stale_before: bool  # True if constitution was stale before sync
    files_written: list[str]  # List of YAML file names written
    extraction_mode: str  # "deterministic" | "hybrid"
    error: str | None = None  # Error message if sync failed


def sync(
    constitution_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> SyncResult:
    """Sync constitution.md to structured YAML config files.

    Args:
        constitution_path: Path to constitution.md
        output_dir: Directory for YAML output (default: same as constitution_path.parent)
        force: If True, extract even if not stale

    Returns:
        SyncResult with status and file paths
    """
    # Default output directory to same location as constitution
    if output_dir is None:
        output_dir = constitution_path.parent

    # Metadata path
    metadata_path = output_dir / "metadata.yaml"

    try:
        # Read constitution content once
        content = constitution_path.read_text("utf-8")

        # Check staleness using the content (eliminates TOCTOU race)
        stale, current_hash, stored_hash = is_stale(None, metadata_path, content=content)

        # Skip if not stale and not forced
        if not stale and not force:
            logger.info("Constitution unchanged, skipping sync")
            return SyncResult(
                synced=False,
                stale_before=False,
                files_written=[],
                extraction_mode="",
            )

        # Extract to structured configs (using same content)
        extractor = Extractor()
        result = extractor.extract(content)

        # Write YAML files
        write_extraction_result(result, output_dir)

        # List files written
        files_written = [
            "governance.yaml",
            "directives.yaml",
            "metadata.yaml",
        ]

        logger.info(f"Constitution synced successfully (mode: {result.metadata.extraction_mode})")

        return SyncResult(
            synced=True,
            stale_before=stale,
            files_written=files_written,
            extraction_mode=result.metadata.extraction_mode,
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return SyncResult(
            synced=False,
            stale_before=False,
            files_written=[],
            extraction_mode="",
            error=str(e),
        )


def post_save_hook(constitution_path: Path) -> None:
    """Auto-trigger sync after constitution write.

    Called synchronously after CLI writes to constitution.md.
    Failures are logged but don't propagate (FR-2.3).

    Args:
        constitution_path: Path to constitution.md
    """
    try:
        result = sync(constitution_path, force=True)
        if result.synced:
            logger.info(
                "Constitution synced: %d YAML files updated",
                len(result.files_written),
            )
        elif result.error:
            logger.warning("Constitution sync warning: %s", result.error)
    except Exception:
        logger.warning(
            "Constitution auto-sync failed. Run 'spec-kitty constitution sync' manually.",
            exc_info=True,
        )


def load_governance_config(repo_root: Path) -> GovernanceConfig:
    """Load governance config from .kittify/constitution/governance.yaml.

    Falls back to empty GovernanceConfig if file missing (FR-4.4).
    Checks staleness and logs warning if stale (FR-4.2).

    Performance: YAML loading only, no AI invocation (FR-4.5).

    Args:
        repo_root: Repository root directory

    Returns:
        GovernanceConfig instance (empty if file missing)
    """
    constitution_dir = repo_root / ".kittify" / "constitution"
    governance_path = constitution_dir / "governance.yaml"

    if not governance_path.exists():
        logger.warning("governance.yaml not found. Run 'spec-kitty constitution sync'.")
        return GovernanceConfig()

    # Check staleness
    constitution_path = constitution_dir / "constitution.md"
    metadata_path = constitution_dir / "metadata.yaml"
    if constitution_path.exists() and metadata_path.exists():
        stale, _, _ = is_stale(constitution_path, metadata_path)
        if stale:
            logger.warning("Constitution changed since last sync. Run 'spec-kitty constitution sync' to update.")

    # Load and validate
    yaml = YAML()
    data = yaml.load(governance_path)
    return GovernanceConfig.model_validate(data)


def load_directives_config(repo_root: Path) -> DirectivesConfig:
    """Load directives config from .kittify/constitution/directives.yaml.

    Falls back to empty DirectivesConfig if file missing.
    Checks staleness and logs warning if stale.

    Args:
        repo_root: Repository root directory

    Returns:
        DirectivesConfig instance (empty if file missing)
    """
    constitution_dir = repo_root / ".kittify" / "constitution"
    directives_path = constitution_dir / "directives.yaml"

    if not directives_path.exists():
        logger.warning("directives.yaml not found. Run 'spec-kitty constitution sync'.")
        return DirectivesConfig()

    constitution_path = constitution_dir / "constitution.md"
    metadata_path = constitution_dir / "metadata.yaml"
    if constitution_path.exists() and metadata_path.exists():
        stale, _, _ = is_stale(constitution_path, metadata_path)
        if stale:
            logger.warning("Constitution changed since last sync. Run 'spec-kitty constitution sync' to update.")

    yaml = YAML()
    data = yaml.load(directives_path)
    return DirectivesConfig.model_validate(data)
