"""Charter path resolution helpers for dashboard features/API.

FR-003 (#3150): this module exposes two distinct readers over the same
canonical charter directory, per C-001 (``charter.yaml`` is the resolving
presence authority when both files exist; ``charter.md`` stays a readable
secondary, never an override):

* :func:`resolve_project_charter_presence` -- the presence probe. Reports
  present when EITHER ``charter.yaml`` OR ``charter.md`` exists (preferring
  ``charter.yaml`` when both are present), so it survives ``charter.md``
  deletion (#3150) *and* does not regress projects that have authored a
  ``charter.md`` but have not yet compiled ``charter.yaml`` (landing-fold
  fix, matching the yaml-or-md prose-presence gate in
  ``charter.activation.context`` and the md-only fallback in
  ``cli/commands/charter/_status_collectors.py``).
* :func:`resolve_project_charter_path` -- the prose body reader. Keys on
  ``charter.md`` (unchanged from pre-#3150 behaviour) for callers that
  serve/read the charter's prose content.

Do not collapse these two back into one reader -- that is the #3150 bug.
"""

from __future__ import annotations

import logging
from pathlib import Path

from charter.bundle import CHARTER_MD, CHARTER_YAML

logger = logging.getLogger(__name__)


def _log_resolver_unavailable(context: str, project_dir: Path, exc: Exception) -> None:
    """Log a resolver-failure warning shared by both charter-path resolvers.

    Both :func:`_resolve_canonical_root_loud` and
    :func:`resolve_project_charter_path` hit the same
    ``(NotInsideRepositoryError, GitCommonDirUnavailableError)`` failure
    shape from two different underlying resolvers and must stay loud per
    C-001 while still surfacing ``None`` (never re-raising -- re-raising
    would crash the scanner). ``context`` names which resolver failed so the
    two call sites keep their distinct, debuggable log messages.
    """
    logger.warning(
        "Dashboard charter probe: %s unavailable for %s: %s",
        context,
        project_dir,
        exc,
    )


def _resolve_canonical_root_loud(project_dir: Path) -> Path | None:
    """Resolve the canonical (main-checkout) project root, degrading to ``None``.

    Uses ``charter.resolution.resolve_canonical_repo_root`` directly rather
    than the ``charter.activation.sync.ensure_charter_bundle_fresh`` chokepoint: that
    chokepoint's own contract returns ``None`` whenever ``charter.md`` is
    absent (it exists to refresh bundle derivatives *from* ``charter.md``,
    so "nothing to refresh" is correct for its purpose) -- which would sink
    canonical-root resolution entirely before a ``charter.yaml``-only
    presence probe ever got a chance to look. The dashboard surface is
    read-only and runs against arbitrary user paths (including paths under
    ``.git/`` during scanner sweeps), so resolver failures are logged loudly
    per C-001 and surfaced as ``None`` rather than re-raised (re-raising
    would crash the scanner).
    """
    from charter.resolution import (
        GitCommonDirUnavailableError,
        NotInsideRepositoryError,
        resolve_canonical_repo_root,
    )

    try:
        # Explicit annotation: charter.resolution is under a follow_imports =
        # "skip" mypy override (pre-existing project-wide setting for
        # charter.*), so the imported callable's return type resolves to
        # Any at the call site without this local pin (NFR-002).
        canonical_root: Path = resolve_canonical_repo_root(Path(project_dir))
    except (NotInsideRepositoryError, GitCommonDirUnavailableError) as exc:
        _log_resolver_unavailable("canonical-root resolver", project_dir, exc)
        return None
    return canonical_root


def resolve_project_charter_presence(project_dir: Path) -> Path | None:
    """Resolve the project-level charter *presence* probe path (FR-003, #3150).

    Prefers ``charter.yaml`` -- the deterministic, schema-guarded governance
    authority (C-001) -- so the dashboard's "no charter" signal survives
    ``charter.md`` deletion. Falls back to ``charter.md`` when
    ``charter.yaml`` has not been compiled yet (a project that authored a
    charter but has not run ``charter sync``/compile), so presence does not
    regress that far more common case: this mirrors the yaml-or-md
    prose-presence gate in ``charter.activation.context`` (C-003) and the md-only
    fallback added to ``cli/commands/charter/_status_collectors.py`` in the
    same PR. Returns the absolute path to whichever file is present
    (``charter.yaml`` when both exist), ``None`` when neither exists. Does
    not fall back to legacy locations -- those must be migrated via
    ``spec-kitty upgrade``.

    This is a presence check only (file exists); it does not inspect the
    resolved file's contents.
    """
    canonical_root = _resolve_canonical_root_loud(Path(project_dir))
    if canonical_root is None:
        return None

    # Explicit annotation: charter.bundle is under a follow_imports = "skip"
    # mypy override (pre-existing project-wide setting for charter.*), so
    # CHARTER_YAML/CHARTER_MD resolve to Any at the call site without this
    # local pin (NFR-002).
    charter_yaml_path: Path = canonical_root / CHARTER_YAML
    if charter_yaml_path.exists():
        return charter_yaml_path

    charter_md_path: Path = canonical_root / CHARTER_MD
    if charter_md_path.exists():
        return charter_md_path

    return None


def resolve_project_charter_path(project_dir: Path) -> Path | None:
    """Resolve the project-level charter *prose body* file path.

    Routes through ``charter.activation.sync.ensure_charter_bundle_fresh`` (FR-004
    chokepoint) so the canonical-root resolver picks up the main checkout
    even when the dashboard scans a worktree path. The return value is the
    absolute path to ``<canonical_root>/.kittify/charter/charter.md`` when
    present, ``None`` otherwise. Does not fall back to legacy locations —
    those must be migrated via ``spec-kitty upgrade``.

    Per C-001, ``charter.md`` stays a readable secondary prose source and is
    never retargeted to ``charter.yaml`` -- callers that need a presence
    signal instead of prose content should use
    :func:`resolve_project_charter_presence`.
    """
    from charter.resolution import (
        GitCommonDirUnavailableError,
        NotInsideRepositoryError,
    )
    from charter.activation.sync import ensure_charter_bundle_fresh

    project_dir = Path(project_dir)

    # Resolver-failure path: we *must* stay loud per C-001, but the dashboard
    # surface is read-only and runs against arbitrary user paths (including
    # paths under .git/ during scanner sweeps). Re-raising would crash the
    # scanner. We log loudly and surface None ("no charter") which is the
    # exact same signal the chokepoint produces for "no charter file".
    try:
        sync_result = ensure_charter_bundle_fresh(project_dir)
    except (NotInsideRepositoryError, GitCommonDirUnavailableError) as exc:
        _log_resolver_unavailable("chokepoint resolver", project_dir, exc)
        return None

    if sync_result is None or sync_result.canonical_root is None:
        return None

    # Explicit annotation: charter.activation.sync/charter.bundle are under a
    # follow_imports = "skip" mypy override (pre-existing project-wide
    # setting for charter.*), so this expression resolves to Any at the
    # call site without this local pin (NFR-002).
    charter_path: Path = sync_result.canonical_root / CHARTER_MD
    if charter_path.exists():
        return charter_path
    return None
