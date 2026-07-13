"""Stage the repo-global charter-lint decay report into a mission dossier.

The charter-lint engine writes a single repo-global report at
``<repo_root>/.kittify/lint-report.json`` (see
``specify_cli.charter_runtime.lint.findings.DecayReport``). The dossier
indexer only scans a mission's ``feature_dir``, so the report has to be
copied in before indexing for the downstream Teamspace SaaS dossier indexer
to surface it (issue #2481, unblocks saas #392).

Staging is scoped: the report is copied into the mission dossier only when it
was produced for THIS mission (its ``feature_scope`` equals the mission
slug). Repo-global / unscoped runs (``feature_scope`` is null) and reports
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

from specify_cli.core.paths import locate_project_root

logger = logging.getLogger(__name__)

LINT_REPORT_FILENAME = "lint-report.json"


def stage_charter_lint_report(feature_dir: Path, mission_slug: str) -> bool:
    """Copy the repo-global charter-lint report into a mission dossier if scoped to it.

    Locates ``<repo_root>/.kittify/lint-report.json`` (repo root derived from
    ``feature_dir`` via the canonical :func:`locate_project_root`), parses it,
    and — only when its ``feature_scope`` matches ``mission_slug`` — writes a
    non-hidden ``lint-report.json`` into ``feature_dir`` so the existing dossier
    indexer scan picks it up.

    Never raises: a missing repo root, missing/unreadable report, unparseable
    JSON, a non-matching ``feature_scope`` (including the null repo-global
    case), or an unwritable ``feature_dir`` are all quiet no-ops.

    Returns True only when the report was staged, False otherwise.
    """
    repo_root = locate_project_root(feature_dir)
    if repo_root is None:
        return False

    report_path = repo_root / ".kittify" / LINT_REPORT_FILENAME
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

    # Only stage a report explicitly scoped to THIS mission. A null
    # feature_scope (repo-global lint run) or a mismatched slug is skipped.
    if report.get("feature_scope") != mission_slug:
        return False

    try:
        (feature_dir / LINT_REPORT_FILENAME).write_text(raw, encoding="utf-8")
    except OSError as e:
        logger.warning(
            "Failed to stage charter-lint report into %s: %s", feature_dir, e,
        )
        return False

    return True
