"""Runtime bootstrap: ensure_runtime() and related functions.

On every CLI startup, ``ensure_runtime()`` guarantees that
``~/.kittify/`` contains up-to-date package assets. It uses a
version.lock file for fast-path detection and file locking for
concurrency safety across parallel CLI invocations.

Also provides version pin detection and warning for projects that set
``runtime.pin_version`` in their ``.kittify/config.yaml``.
"""

from __future__ import annotations

import logging
import shutil
import sys
import warnings
from pathlib import Path
from typing import IO

import yaml

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.asset_preparation import _GlobalAssetPreparation
from specify_cli.tool_surface.operations import ApplyConsent, OwnerAssessment, OwnerApplyResult

logger = logging.getLogger(__name__)


def _get_cli_version() -> str:
    """Return the current CLI version string.

    Defensive: when the package's ``__version__`` is missing or ``None``
    (e.g. during partial installs, broken editable layouts, or import
    cycles during bootstrap), fall back to ``"0.0.0-dev"`` rather than
    crashing the entire CLI with a ``TypeError`` on later
    ``write_text`` / string-compare paths (issue #1070).
    """
    fallback = "0.0.0-dev"
    try:
        from specify_cli import __version__ as _version
    except Exception:  # noqa: BLE001
        logger.warning(
            "Could not import specify_cli.__version__ during runtime bootstrap; falling back to %s",
            fallback,
        )
        return fallback
    if not isinstance(_version, str) or not _version:
        logger.warning(
            "specify_cli.__version__ resolved to %r during runtime bootstrap; falling back to %s",
            _version,
            fallback,
        )
        return fallback
    return _version


def _lock_exclusive(fd: IO[str] | int) -> None:
    """Acquire an exclusive file lock, blocking if another process holds it.

    On Unix: uses ``fcntl.flock`` with a non-blocking attempt first.
    If another process holds the lock, falls back to a blocking wait.

    On Windows: uses ``msvcrt.locking`` with ``LK_LOCK`` (blocking).

    Args:
        fd: An open file object whose underlying descriptor will be locked.
    """
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd if isinstance(fd, int) else fd.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another process is updating -- wait for it
            fcntl.flock(fd, fcntl.LOCK_EX)


def populate_from_package(
    target: Path,
    *,
    assessment: OwnerAssessment | None = None,
    consent: ApplyConsent = ApplyConsent(),
) -> OwnerApplyResult | None:
    """Copy all package-bundled assets to *target* directory.

    Creates a complete asset tree matching the ``~/.kittify/`` layout:

    - ``missions/`` -- copied from ``get_package_asset_root()``
    - ``scripts/``  -- copied from the package's ``scripts/`` directory
    - ``AGENTS.md`` -- copied from the package root

    Args:
        target: Destination directory (typically a temporary staging area).
        assessment: Optional retained package batch. When supplied, never
            recollect or copy source trees; delegate its exact bytes to merge.
        consent: Explicit consent for a supplied retained batch.
    """
    if assessment is not None:
        # Checked apply supplies retained bytes. Assessment never calls this
        # mutating entry point or stages package assets to discover effects.
        from specify_cli.runtime.merge import merge_package_assets

        return merge_package_assets(assessment, target, consent=consent)

    # Mission doctrine-consumer-surface-missions-extraction-01KZ6G6H (FR-005,
    # N-03) relocated the missions data to packs/built-in/missions;
    # asset_root (via get_package_asset_root(), R-09) now resolves there
    # correctly, so missions_src below needs no separate repoint. The
    # scripts_src/agents_src ".parent"-derived candidates below were,
    # independent of this move, ALREADY never satisfied in a real
    # installed/editable layout -- neither src/charter/offering/scripts nor
    # src/charter/offering/AGENTS.md exist for real (the actual shipped scripts/ tree
    # is packaged from src/specify_cli/scripts/, per pyproject.toml's wheel
    # "artifacts" list, and the real AGENTS.md lives at
    # src/charter/offering/templates/AGENTS.md) -- confirmed by checking both
    # directories directly. Only the SPEC_KITTY_TEMPLATE_ROOT-driven test
    # fixture (tests/runtime/test_bootstrap_unit.py's fake_assets, a
    # synthetic sibling layout) ever exercises these two branches
    # successfully; this is a pre-existing gap, unrelated to and not
    # worsened by this WP's relocation, recorded here rather than expanded
    # into this WP's scope.
    asset_root = get_package_asset_root()
    target.mkdir(parents=True, exist_ok=True)

    # Copy all missions
    missions_src = asset_root
    missions_dst = target / "missions"
    if missions_src.is_dir():
        shutil.copytree(missions_src, missions_dst)

    # Copy scripts if they exist
    scripts_src = asset_root.parent / "scripts"
    if scripts_src.is_dir():
        shutil.copytree(scripts_src, target / "scripts")

    # Copy AGENTS.md if it exists
    agents_src = asset_root.parent / "AGENTS.md"
    if agents_src.is_file():
        shutil.copy2(agents_src, target / "AGENTS.md")
    return None


def _cleanup_orphaned_update_dirs(parent: Path) -> None:
    """Report legacy staging candidates; their names do not prove ownership."""
    if not parent.is_dir():
        return
    for entry in parent.iterdir():
        if entry.is_dir() and entry.name.startswith(".kittify_update_"):
            logger.warning("Preserving unproven orphan staging directory: %s", entry)


def assess_runtime(*, consent: ApplyConsent = ApplyConsent(), _batch: _GlobalAssetPreparation | None = None) -> OwnerAssessment:
    """Prepare managed package assets directly, without staging or bootstrap."""
    from specify_cli.runtime.asset_preparation import AssetPreparation, global_asset_root, incomplete
    from specify_cli.runtime.merge import MANAGED_DIRS, MANAGED_FILES

    home = get_kittify_home()
    root = global_asset_root("runtime_bootstrap", (home,))
    try:
        prepared = AssetPreparation("runtime_bootstrap", root, home / "cache", ".update.lock", consent)
        assets = get_package_asset_root()
        if prepared.observe(assets, members=True).kind != "directory":
            raise ValueError(f"Required package assets unavailable: {assets}")
        for relative in MANAGED_DIRS:
            source = assets / relative.removeprefix("missions/") if relative.startswith("missions/") else assets.parent / relative
            state = prepared.observe(source)
            if state.kind == "absent":
                continue  # Existing populate/merge policy: optional absent trees.
            prepared.tree(source, home / relative, managed_tree=True)
            prepared.prune_missing(home / relative)
        for relative in MANAGED_FILES:
            source = assets.parent / relative
            state = prepared.observe(source)
            if state.kind != "absent":
                prepared.asset(home / relative, prepared.source(source), state.mode or 0o644, managed_tree=True)
        if home.parent.is_dir():
            for candidate in home.parent.iterdir():
                if candidate.name.startswith(".kittify_update_"):
                    prepared.preserve(candidate, "Unproven orphan staging directory; preserved")
        assessment = prepared.finish(home / "cache/version.lock", _get_cli_version())
        if _batch is not None:
            _batch.include(prepared, assessment.effects)
        return assessment
    except (OSError, ValueError) as exc:
        return incomplete("runtime_bootstrap", root, exc)


def ensure_runtime() -> None:
    """Repair actual managed health; a version stamp alone is insufficient."""
    from specify_cli.runtime.asset_preparation import apply_assets, recheck_assets

    assessment = assess_runtime()
    if not assessment.complete:
        raise RuntimeError("; ".join(d.message for d in assessment.diagnostics))
    if not assessment.effects:
        return
    with recheck_assets(assessment) as diagnostics:
        if diagnostics:
            raise RuntimeError("; ".join(d.message for d in diagnostics))
        result = apply_assets(assessment, ApplyConsent(automatic=True))
    if result.outcome != "applied":
        raise RuntimeError("; ".join(d.message for d in result.diagnostics))


def check_version_pin(project_dir: Path) -> None:
    """Check for runtime.pin_version in project config and warn if present.

    Version pinning is not yet supported.  When a pin is detected the
    function emits both a ``logging.warning`` and a ``UserWarning`` so
    that CI pipelines and interactive users alike are notified.  The
    pinned version is **never** silently honored -- the latest global
    assets are always used.

    Args:
        project_dir: Project root containing ``.kittify/``.
    """
    config_path = project_dir / ".kittify" / "config.yaml"
    if not config_path.exists():
        return

    try:
        config = yaml.safe_load(config_path.read_text())
    except Exception:
        # Config parsing failure handled elsewhere
        return

    if not config or not isinstance(config, dict):
        return

    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        return

    if "pin_version" not in runtime:
        return

    pin = runtime["pin_version"]
    msg = (
        f"runtime.pin_version={pin} found in .kittify/config.yaml. "
        f"Version pinning is not yet supported. Using latest global assets. "
        f"The pin will NOT be silently honored."
    )
    logger.warning(msg)
    warnings.warn(msg, UserWarning, stacklevel=2)
