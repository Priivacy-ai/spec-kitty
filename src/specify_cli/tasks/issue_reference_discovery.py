"""Multi-file issue-reference discovery (T028, FR-004, #1738).

Generalizes ``tasks.issue_matrix.detect_issue_references`` -- which reads
``spec.md`` **only** -- to every mission artifact that can legitimately carry
a load-bearing GH issue reference: ``spec.md``, ``plan.md``, ``research.md``,
``analysis-report.md``, plus every ``.md`` file directly under ``tasks/`` and
``contracts/``.

This module reuses the ONE canonical single-file detector
(:func:`specify_cli.tasks.issue_matrix.detect_issue_references`) per scanned
file -- same ``#NNNN`` regex, same canonicalization -- so there remains
exactly one issue-reference pattern definition in the codebase (WP08 risk:
"avoid a fourth definition"). This module owns only two concerns: *which*
files to scan, and how to merge/dedupe references discovered across them.

``detect_issue_references`` is NOT deleted or edited here (it is owned by
WP05): :func:`specify_cli.tasks.issue_matrix.scaffold_issue_matrix` still
calls it directly against ``spec.md`` alone for the initial-scaffold use case
(B3), so it remains a live building block. It IS superseded for
completeness/enforcement purposes -- the three enforcement sites
(``status.doctor.check_issue_matrix``,
``cli.commands.agent.tasks_parsing_validation._issue_matrix_evaluation`` /
``_issue_matrix_approval_blocker``) and the merge-time completeness gate
(``policy.merge_gates``) now call :func:`discover_issue_references` instead
(write-side-seam-matrix-tracer-01KYP3MH WP08, T029/T030).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.tasks.issue_matrix import IssueReference

# Single-file mission artifacts scanned in this fixed order (T028). Each is
# optional -- a mission without a ``research.md``/``analysis-report.md``
# simply contributes nothing from that slot. ``spec.md`` stays first so the
# existing single-file behavior (:func:`detect_issue_references` on
# ``spec.md`` alone) is a strict, order-preserving subset of this scan.
_SINGLE_FILE_ARTIFACTS: tuple[str, ...] = (
    "spec.md",
    "plan.md",
    "research.md",
    "analysis-report.md",
)

# Directories scanned non-recursively for ``.md`` files, in this fixed order,
# each sorted by filename for a deterministic scan.
_SCAN_DIRS: tuple[str, ...] = ("tasks", "contracts")


def _iter_scan_paths(feature_dir: Path) -> list[Path]:
    """Return every artifact path to scan, in deterministic order.

    Missing single-file artifacts and missing/empty scan directories are
    silently skipped -- discovery must not fail a mission that simply has
    not authored a given optional artifact yet.
    """
    paths: list[Path] = []
    for name in _SINGLE_FILE_ARTIFACTS:
        candidate = feature_dir / name
        if candidate.is_file():
            paths.append(candidate)
    for dirname in _SCAN_DIRS:
        dir_path = feature_dir / dirname
        if not dir_path.is_dir():
            continue
        paths.extend(sorted(p for p in dir_path.glob("*.md") if p.is_file()))
    return paths


def discover_issue_references(feature_dir: Path) -> list[IssueReference]:
    """Return the deduplicated, ordered list of GH issue refs across a mission.

    Scans ``spec.md``, ``plan.md``, ``research.md``, ``analysis-report.md``
    (each optional) plus every ``.md`` file directly under ``tasks/`` and
    ``contracts/`` (also optional directories), reusing the canonical
    single-file detector (:func:`~specify_cli.tasks.issue_matrix.
    detect_issue_references`) per file so there is one #NNNN pattern
    definition.

    Ordering is deterministic: the single-file artifacts in the fixed order
    above, then ``tasks/*.md`` sorted by filename, then ``contracts/*.md``
    sorted by filename. Within that scan order, the FIRST file+line a given
    issue number appears in wins both the ``first_line_context`` AND the
    ``source_file`` (WP06 / T028, #1738) -- matching the single-file
    function's existing first-occurrence contract, extended to provenance.

    Args:
        feature_dir: The mission's ``kitty-specs/<slug>/`` planning
            directory (or the caller's already topology-resolved read
            surface).

    Returns:
        Deduplicated :class:`~specify_cli.tasks.issue_matrix.IssueReference`
        list, ordered by first appearance across the scanned files. Empty
        list when no scanned file references a GH issue, or when
        ``feature_dir`` has none of the scanned artifacts.
    """
    # Deferred import (not a module-level ``from ... import``) so this stays
    # a live patch seam: callers/tests monkeypatch
    # ``specify_cli.tasks.issue_matrix.detect_issue_references`` and expect
    # every consumer -- this discovery module included -- to observe the
    # patched callable, the same contract the pre-WP08 single-file callers
    # relied on.
    from specify_cli.tasks.issue_matrix import IssueReference, detect_issue_references

    # T028 (#1738): keyed by number, valued by (first_line_context,
    # source_file) TOGETHER so the pair always travels from the same
    # first-occurrence file -- never independently re-derived, which could
    # otherwise mismatch context from one file against provenance from
    # another.
    seen: dict[int, tuple[str, str]] = {}
    for path in _iter_scan_paths(feature_dir):
        for ref in detect_issue_references(path):
            if ref.number not in seen:
                seen[ref.number] = (ref.first_line_context, ref.source_file)
    return [
        IssueReference(num, ctx, source_file) for num, (ctx, source_file) in seen.items()
    ]


__all__ = ["discover_issue_references"]
