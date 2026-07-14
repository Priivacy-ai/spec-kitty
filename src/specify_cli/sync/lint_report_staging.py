"""Stage the repo-global charter-lint decay report into a mission dossier.

The charter-lint engine writes a single repo-global report at
``<repo_root>/.kittify/lint-report.json`` (see
``specify_cli.charter_runtime.lint.findings.DecayReport``). The dossier
indexer only scans a mission's ``feature_dir``, so the report has to be
copied in before indexing for the downstream Teamspace SaaS dossier indexer
to surface it (issue #2481, unblocks saas #392).

Staging is scoped: the report is copied into the mission dossier only when it
was produced for THIS mission. The producer (``charter lint --mission <X>``)
stores whatever handle the operator typed as ``feature_scope`` **verbatim**
(bare mid8, numeric prefix, or slug), while the dossier-sync consumer keys the
namespace by the canonical directory name (``feature_dir.name``). So a plain
``feature_scope == mission_slug`` compare would silently miss whenever the two
identity forms differ. Instead we match ``feature_scope`` against the mission's
full alias set — ``mission_id`` / ``mid8`` / ``mission_slug`` / directory name
(resolved via :func:`resolve_mission_identity`) — so any accepted handle form
fires. Repo-global / unscoped runs (``feature_scope`` is null) and reports
scoped to a different mission are intentionally NOT staged — surfacing
unscoped lint runs is out of scope for this change.

This module lives in the ``sync`` package on purpose: ``sync`` may import
``dossier``, but ``dossier`` must never import ``sync`` (enforced by
``tests/architectural/test_dossier_sync_boundary.py``). Staging is a sync-time
concern, so it belongs here.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from specify_cli.core.paths import (
    LINT_REPORT_FILENAME,
    lint_report_path,
    locate_project_root,
)

logger = logging.getLogger(__name__)

# Re-exported from core.paths so callers/tests that import it from this module
# keep working; the canonical definition lives in core.constants (#2628 SSOT).
__all__ = ["LINT_REPORT_FILENAME", "stage_charter_lint_report"]

_MID8_LEN = 8


def _mission_alias_set(feature_dir: Path, mission_slug: str) -> set[str]:
    """Return the identity handles that all denote the mission at *feature_dir*.

    Combines the caller-supplied ``mission_slug`` (already the canonical
    directory name in the load-bearing sync paths) with the mission's own
    identity — ``mission_id``, its ``mid8`` prefix, the meta ``mission_slug``,
    and ``feature_dir.name`` — so a ``feature_scope`` recorded under any accepted
    ``--mission`` handle form matches. Best-effort: if identity cannot be
    resolved (e.g. no ``meta.json``), the set degrades to the directory-derived
    handles, which is exactly the pre-existing behaviour.
    """
    aliases = {mission_slug, feature_dir.name}
    try:
        from specify_cli.mission_metadata import resolve_mission_identity

        identity = resolve_mission_identity(feature_dir)
        aliases.add(identity.mission_slug)
        if identity.mission_id:
            aliases.add(identity.mission_id)
            aliases.add(identity.mission_id[:_MID8_LEN])
    except Exception as exc:  # best-effort — never let identity resolution break staging
        logger.debug("Could not resolve mission identity for %s: %s", feature_dir, exc)
    return {alias for alias in aliases if alias}


def stage_charter_lint_report(feature_dir: Path, mission_slug: str) -> bool:
    """Copy the repo-global charter-lint report into a mission dossier if scoped to it.

    Locates ``<repo_root>/.kittify/lint-report.json`` (repo root derived from
    ``feature_dir`` via the canonical :func:`locate_project_root`), parses it,
    and — only when its ``feature_scope`` matches one of the mission's identity
    handles (see :func:`_mission_alias_set`) — writes a non-hidden
    ``lint-report.json`` into ``feature_dir`` so the existing dossier indexer
    scan picks it up.

    Never raises: a missing repo root, missing/unreadable report, unparseable
    JSON, a ``feature_scope`` matching no mission handle (including the null
    repo-global case), or an unwritable ``feature_dir`` are all quiet no-ops.

    Returns True only when the report was staged, False otherwise.
    """
    repo_root = locate_project_root(feature_dir)
    if repo_root is None:
        return False

    report_path = lint_report_path(repo_root)
    try:
        raw = report_path.read_text(encoding="utf-8")
    except OSError:
        # Missing or unreadable report — nothing to stage.
        return False

    try:
        report = json.loads(raw)
    except ValueError:
        logger.warning("charter-lint report at %s is not valid JSON", report_path)
        return False

    if not isinstance(report, dict):
        logger.warning("charter-lint report at %s is not a JSON object", report_path)
        return False

    # Only stage a report explicitly scoped to THIS mission. A null / non-string
    # feature_scope (repo-global lint run) or a scope that matches none of the
    # mission's identity handles is skipped.
    feature_scope = report.get("feature_scope")
    if (
        not isinstance(feature_scope, str)
        or feature_scope not in _mission_alias_set(feature_dir, mission_slug)
    ):
        return False

    try:
        (feature_dir / LINT_REPORT_FILENAME).write_text(raw, encoding="utf-8")
    except OSError as e:
        logger.warning(
            "Failed to stage charter-lint report into %s: %s", feature_dir, e,
        )
        return False

    return True
