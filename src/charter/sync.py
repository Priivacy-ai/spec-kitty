"""Charter sync orchestrator.

Provides the main sync() function that orchestrates:
1. Read charter.md
2. Check staleness (skip if unchanged, unless --force)
3. Parse and extract to YAML
4. Write governance/directives/metadata files
5. Update metadata with hash and timestamp
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from charter.extractor import Extractor, write_extraction_result
from charter.hasher import is_stale
from charter.schemas import (
    DirectivesConfig,
    GovernanceConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a charter sync operation."""

    synced: bool  # True if extraction ran
    stale_before: bool  # True if charter was stale before sync
    files_written: list[str]  # List of YAML file names written
    extraction_mode: str  # "deterministic" | "hybrid"
    error: str | None = None  # Error message if sync failed


def ensure_charter_bundle_fresh(repo_root: Path) -> SyncResult | None:
    """Auto-refresh extracted charter artifacts when charter.md exists."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_path = charter_dir / "charter.md"
    if not charter_path.exists():
        return None

    metadata_path = charter_dir / "metadata.yaml"
    expected_paths = (
        charter_dir / "governance.yaml",
        charter_dir / "directives.yaml",
        metadata_path,
    )
    missing_files = [path.name for path in expected_paths if not path.exists()]
    should_force = bool(missing_files)
    stale = False

    if not should_force:
        try:
            stale, _, _ = is_stale(charter_path, metadata_path)
        except Exception as exc:
            logger.warning("Failed to evaluate charter bundle freshness: %s", exc)
            should_force = True

    if not should_force and not stale:
        return SyncResult(
            synced=False,
            stale_before=False,
            files_written=[],
            extraction_mode="",
        )

    if missing_files:
        logger.info("Charter bundle incomplete (%s). Attempting auto-sync.", ", ".join(missing_files))
    else:
        logger.info("Charter bundle stale. Attempting auto-sync.")

    result = sync(charter_path, charter_dir, force=should_force)
    if result.error:
        logger.warning("Charter auto-sync failed while refreshing extracted artifacts: %s", result.error)
    return result


def sync(
    charter_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> SyncResult:
    """Sync charter.md to structured YAML config files.

    Args:
        charter_path: Path to charter.md
        output_dir: Directory for YAML output (default: same as charter_path.parent)
        force: If True, extract even if not stale

    Returns:
        SyncResult with status and file paths
    """
    # Default output directory to same location as charter
    if output_dir is None:
        output_dir = charter_path.parent

    # Metadata path
    metadata_path = output_dir / "metadata.yaml"

    try:
        # Read charter content once
        content = charter_path.read_text("utf-8")

        # Check staleness using the content (eliminates TOCTOU race)
        stale, _, _ = is_stale(None, metadata_path, content=content)

        # Skip if not stale and not forced
        if not stale and not force:
            logger.info("Charter unchanged, skipping sync")
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

        logger.info(f"Charter synced successfully (mode: {result.metadata.extraction_mode})")

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


def post_save_hook(charter_path: Path) -> None:
    """Auto-trigger sync after charter write.

    Called synchronously after CLI writes to charter.md.
    Failures are logged but don't propagate (FR-2.3).

    Args:
        charter_path: Path to charter.md
    """
    try:
        result = sync(charter_path, force=True)
        if result.synced:
            logger.info(
                "Charter synced: %d YAML files updated",
                len(result.files_written),
            )
        elif result.error:
            logger.warning("Charter sync warning: %s", result.error)
    except Exception:
        logger.warning(
            "Charter auto-sync failed. Run 'spec-kitty charter sync' manually.",
            exc_info=True,
        )


def load_governance_config(repo_root: Path) -> GovernanceConfig:
    """Load governance config from .kittify/charter/governance.yaml.

    Falls back to empty GovernanceConfig if file missing (FR-4.4).
    Checks staleness and logs warning if stale (FR-4.2).

    Performance: YAML loading only, no AI invocation (FR-4.5).

    Args:
        repo_root: Repository root directory

    Returns:
        GovernanceConfig instance (empty if file missing)
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_path = charter_dir / "charter.md"
    governance_path = charter_dir / "governance.yaml"
    refresh_result = ensure_charter_bundle_fresh(repo_root)

    if not governance_path.exists():
        if charter_path.exists():
            logger.warning("governance.yaml unavailable after charter auto-sync. Using empty governance config.")
        else:
            logger.warning("governance.yaml not found and charter.md is absent. Using empty governance config.")
        return GovernanceConfig()

    # Check staleness
    metadata_path = charter_dir / "metadata.yaml"
    if charter_path.exists() and metadata_path.exists():
        stale, _, _ = is_stale(charter_path, metadata_path)
        if stale:
            if refresh_result and refresh_result.error:
                logger.warning("Charter bundle is stale after auto-sync failure. Using last synced governance config.")
            else:
                logger.warning("Charter bundle remains stale. Using last synced governance config.")

    # Load and validate
    yaml = YAML()
    data = yaml.load(governance_path)
    return GovernanceConfig.model_validate(data)


def load_directives_config(repo_root: Path) -> DirectivesConfig:
    """Load directives config from .kittify/charter/directives.yaml.

    Falls back to empty DirectivesConfig if file missing.
    Checks staleness and logs warning if stale.

    Args:
        repo_root: Repository root directory

    Returns:
        DirectivesConfig instance (empty if file missing)
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_path = charter_dir / "charter.md"
    directives_path = charter_dir / "directives.yaml"
    refresh_result = ensure_charter_bundle_fresh(repo_root)

    if not directives_path.exists():
        if charter_path.exists():
            logger.warning("directives.yaml unavailable after charter auto-sync. Using empty directives config.")
        else:
            logger.warning("directives.yaml not found and charter.md is absent. Using empty directives config.")
        return DirectivesConfig()

    metadata_path = charter_dir / "metadata.yaml"
    if charter_path.exists() and metadata_path.exists():
        stale, _, _ = is_stale(charter_path, metadata_path)
        if stale:
            if refresh_result and refresh_result.error:
                logger.warning("Charter bundle is stale after auto-sync failure. Using last synced directives config.")
            else:
                logger.warning("Charter bundle remains stale. Using last synced directives config.")

    yaml = YAML()
    data = yaml.load(directives_path)
    return DirectivesConfig.model_validate(data)
