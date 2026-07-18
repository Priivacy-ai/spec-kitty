"""Charter sync orchestrator.

IC-04 (consolidate-charter-bundle / WP04): the prose->triad scrape this
module used to perform -- parsing ``charter.md`` and writing
``governance.yaml`` / ``directives.yaml`` / ``metadata.yaml`` -- is RETIRED.
``governance`` and ``directives`` are now hand-authored sections directly
inside the git-tracked ``charter.yaml`` (``charter.schemas.CharterYaml``);
:func:`load_governance_config` / :func:`load_directives_config` read those
sections straight off disk (INV-3: no governance/directives DECISION reads
``charter.md`` prose or the retired triad files any more).

``sync()`` / ``ensure_charter_bundle_fresh()`` are RETAINED -- signatures and
``SyncResult`` contract unchanged -- because other charter-layer modules
(``context.py``, ``specify_cli.charter_runtime.freshness.computer``, the
``charter sync`` CLI command, the dashboard, and the bundle-migration
upgrader) still call them for canonical-root resolution and the
``charter.md`` staleness check. ``sync()`` no longer extracts or writes
anything; it always reports ``synced=False`` / ``files_written=[]``.
"""

import logging
from dataclasses import dataclass, field, replace
from pathlib import Path

from charter._io import load_charter_file
from charter.bundle import CANONICAL_MANIFEST, CHARTER_YAML
from charter.charter_yaml_io import load_charter_yaml
from charter.hasher import is_stale
from charter.resolution import resolve_canonical_repo_root
from charter.schemas import (
    DirectivesConfig,
    GovernanceConfig,
)

__all__ = [
    "SyncResult",
    "ensure_charter_bundle_fresh",
    "load_directives_config",
    "load_governance_config",
    "sync",
]


logger = logging.getLogger(__name__)

_KITTIFY_DIRNAME = ".kittify"
_CHARTER_DIRNAME = "charter"
_CHARTER_FILENAME = "charter.md"
_METADATA_FILENAME = "metadata.yaml"


@dataclass
class SyncResult:
    """Result of a charter sync operation.

    ``files_written`` entries are file names relative to the canonical
    charter directory (``canonical_root / .kittify/charter/``). To
    reconstruct an absolute path for a written file, anchor against
    ``canonical_root``: ``canonical_root / .kittify/charter / files_written[i]``.

    ``canonical_root`` is the main-checkout project root resolved via
    ``charter.resolution.resolve_canonical_repo_root``. It is ``None`` only
    on transient ``SyncResult`` objects produced by direct ``sync()`` calls
    that haven't been routed through the chokepoint; the chokepoint
    (``ensure_charter_bundle_fresh``) always patches a real path in via
    ``dataclasses.replace`` before returning.
    """

    synced: bool  # True if extraction ran
    stale_before: bool  # True if charter was stale before sync
    files_written: list[str]  # File names; anchored at canonical_root / .kittify/charter
    extraction_mode: str  # "deterministic" | "hybrid"
    error: str | None = None  # Error message if sync failed
    canonical_root: Path | None = None  # NEW (WP02): main-checkout root
    warnings: list[str] = field(default_factory=list)


def ensure_charter_bundle_fresh(repo_root: Path) -> SyncResult | None:
    """Auto-refresh extracted charter artifacts when ``charter.md`` exists.

    Resolves ``repo_root`` to the canonical (main-checkout) root via
    ``resolve_canonical_repo_root`` and consults
    ``CharterBundleManifest.CANONICAL_MANIFEST`` for the set of files that
    must exist under the canonical root. If any required derived file is
    missing or the bundle is stale (``is_stale`` hash comparison), ``sync()``
    is invoked to regenerate the derivatives.

    The returned ``SyncResult`` always carries ``canonical_root`` (patched
    via ``dataclasses.replace`` onto whatever ``sync()`` returned).
    Exceptions from the resolver (``NotInsideRepositoryError``,
    ``GitCommonDirUnavailableError``) propagate unchanged per C-001.

    Returns ``None`` when ``charter.md`` is absent under the canonical
    root — there is no charter to refresh.
    """
    canonical_root = resolve_canonical_repo_root(repo_root)
    charter_dir = canonical_root / _KITTIFY_DIRNAME / _CHARTER_DIRNAME
    charter_path = charter_dir / _CHARTER_FILENAME
    if not charter_path.exists():
        return None

    metadata_path = charter_dir / _METADATA_FILENAME
    # Manifest is authoritative for "what files must exist" (FR-006).
    expected_paths = [canonical_root / p for p in CANONICAL_MANIFEST.derived_files]
    missing_files = [p.name for p in expected_paths if not p.exists()]
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
            canonical_root=canonical_root,
        )

    if missing_files:
        logger.info("Charter bundle incomplete (%s). Attempting auto-sync.", ", ".join(missing_files))
    else:
        logger.info("Charter bundle stale. Attempting auto-sync.")

    result = sync(charter_path, charter_dir, force=should_force)
    # Patch canonical_root onto the SyncResult returned by sync(); sync()
    # itself doesn't know which checkout the caller invoked it from.
    result = replace(result, canonical_root=canonical_root)
    if result.error:
        logger.warning("Charter auto-sync failed while refreshing extracted artifacts: %s", result.error)
    return result


def sync(
    charter_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
    unsafe: bool = False,
) -> SyncResult:
    """Report ``charter.md`` staleness; no longer extracts or writes anything.

    IC-04 retirement: this function used to parse ``charter.md`` and write
    ``governance.yaml`` / ``directives.yaml`` / ``metadata.yaml`` (the
    prose->triad scrape). That scrape is retired -- ``governance`` and
    ``directives`` are hand-authored directly in ``charter.yaml`` now (see
    :func:`load_governance_config` / :func:`load_directives_config`).

    Retained for its callers' contract (``ensure_charter_bundle_fresh``, the
    ``charter sync`` CLI command): it still performs the staleness check
    against ``charter.md`` and reports ``stale_before`` accurately, but
    ``synced`` is now always ``False`` and ``files_written`` always empty --
    there is nothing left for this function to produce.

    Args:
        charter_path: Path to charter.md
        output_dir: Directory containing metadata.yaml for the staleness
            check (default: same as charter_path.parent)
        force: Accepted for backward compatibility with existing callers;
            no longer changes behavior (there is no extraction to force).
        unsafe: when True, bypass CHARTER_ENCODING_AMBIGUOUS by accepting the
            highest-confidence decode candidate and logging bypass_used=True in
            provenance.  Use only when you have inspected the file and accept
            the operational risk; the bypass is recorded in
            ``.encoding-provenance.jsonl``.

    Returns:
        SyncResult with ``synced=False`` and the staleness verdict.
    """
    _ = force  # no longer changes behavior; kept for signature stability.

    # Default output directory to same location as charter
    if output_dir is None:
        output_dir = charter_path.parent

    # Metadata path
    metadata_path = output_dir / _METADATA_FILENAME

    try:
        # Read charter content once — route through encoding chokepoint (FR-016)
        content = load_charter_file(charter_path, unsafe=unsafe).text

        # Check staleness using the content (eliminates TOCTOU race)
        stale, _, _ = is_stale(None, metadata_path, content=content)

        return SyncResult(
            synced=False,
            stale_before=stale,
            files_written=[],
            extraction_mode="",
        )

    except Exception as e:
        logger.debug("Sync failed: %s", e, exc_info=True)
        return SyncResult(
            synced=False,
            stale_before=False,
            files_written=[],
            extraction_mode="",
            error=str(e),
        )


def _load_charter_yaml_section(repo_root: Path, section: str) -> object | None:
    """Return the named top-level ``charter.yaml`` section, or ``None``.

    Anchors path resolution on the canonical (main-checkout) root via
    :func:`charter.resolution.resolve_canonical_repo_root` so worktree
    callers read the same ``charter.yaml`` the main checkout tracks
    (FR-010) -- mirrors the worktree-transparency contract the retired
    ``ensure_charter_bundle_fresh``-routed loaders used to provide, without
    invoking the (now-inert) sync chokepoint.

    Returns ``None`` when ``charter.yaml`` itself is absent, or when it
    exists but does not carry *section* as a top-level key -- both are the
    caller's "use an empty config" signal, logged at different verbosity by
    the two public loaders below.
    """
    canonical_root = resolve_canonical_repo_root(repo_root)
    charter_yaml_path = canonical_root / CHARTER_YAML
    if not charter_yaml_path.exists():
        return None
    document = load_charter_yaml(charter_yaml_path)
    if not isinstance(document, dict):
        return None
    return document.get(section)


def load_governance_config(repo_root: Path) -> GovernanceConfig:
    """Load governance config from ``charter.yaml``'s ``governance:`` section.

    IC-04 (INV-3): the prose->triad scrape is retired -- ``governance`` is a
    hand-authored section directly inside the git-tracked ``charter.yaml``
    (``charter.schemas.CharterYaml``), not a derived ``governance.yaml``.
    Falls back to an empty ``GovernanceConfig`` when ``charter.yaml`` is
    absent, or present without a ``governance`` section.

    Args:
        repo_root: Repository root directory (may be a worktree path).

    Returns:
        GovernanceConfig instance (empty if charter.yaml/section missing)
    """
    governance_data = _load_charter_yaml_section(repo_root, "governance")
    if governance_data is None:
        logger.info("charter.yaml governance section not found. Using empty governance config.")
        return GovernanceConfig()
    return GovernanceConfig.model_validate(governance_data)


def load_directives_config(repo_root: Path) -> DirectivesConfig:
    """Load directives config from ``charter.yaml``'s ``directives:`` section.

    IC-04 (INV-3): the prose->triad scrape is retired -- ``directives`` is a
    hand-authored section directly inside the git-tracked ``charter.yaml``
    (``charter.schemas.CharterYaml``), not a derived ``directives.yaml``.
    Falls back to an empty ``DirectivesConfig`` when ``charter.yaml`` is
    absent, or present without a ``directives`` section.

    Args:
        repo_root: Repository root directory (may be a worktree path).

    Returns:
        DirectivesConfig instance (empty if charter.yaml/section missing)
    """
    directives_data = _load_charter_yaml_section(repo_root, "directives")
    if directives_data is None:
        logger.info("charter.yaml directives section not found. Using empty directives config.")
        return DirectivesConfig()
    return DirectivesConfig.model_validate(directives_data)
