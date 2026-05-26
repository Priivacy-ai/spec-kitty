"""Scaffold ``issue-matrix.md`` from GitHub-issue references in a mission spec.

Per FR-009 of the test-stabilization-and-debt-pass mission. Closes #1163.

The matrix schema mirrors the Gate-4 contract from the
``spec-kitty-mission-review`` skill: columns ``Issue``, ``Title``,
``Verdict``, ``Evidence ref``. The scaffold is created during the
``/spec-kitty.tasks`` flow (specifically
``spec-kitty agent mission finalize-tasks``) when ``spec.md`` references
one or more GitHub issues such as ``#1298`` or ``#1163``.

The scaffold is **idempotent**: an existing ``issue-matrix.md`` is never
overwritten, so operator edits survive re-runs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

# Match ``#NNNN`` GH issue references with 2-6 digits, requiring a non-word
# leading boundary (start-of-line, whitespace, ``(``, ``[``) and a non-word
# trailing boundary (whitespace, ``)``, ``]``, ``,``, ``;``, ``.``, EOL).
#
# This deliberately rejects:
#   * markdown anchor links like ``#section-name`` (alphabetical, not 2-6 digits)
#   * heading markers like ``# Title`` (no digits)
#   * tiny one-digit refs like ``#1`` (too few digits)
#   * runs of seven-plus digits (out of GitHub's typical issue-number range)
_GH_ISSUE_PATTERN = re.compile(
    r"(?:^|\s|\(|\[)#(\d{2,6})(?=\s|\)|\]|,|;|\.|$)",
    re.MULTILINE,
)


class IssueReference(NamedTuple):
    """A single GH issue reference detected in a mission spec.

    Attributes:
        number: Issue number, e.g. ``1163``.
        first_line_context: The first line in ``spec.md`` where the issue
            appears, stripped of leading and trailing whitespace. Useful for
            generating evidence hints in the matrix.
    """

    number: int
    first_line_context: str


def detect_issue_references(spec_md_path: Path) -> list[IssueReference]:
    """Return the unique list of GH issue refs in spec.md, ordered by first appearance.

    Skips refs that look like markdown anchor links (``#section-name``) and
    requires the number to be 2-6 digits to avoid matching markdown headings
    or trivial single-digit numerics.

    Args:
        spec_md_path: Filesystem path to the mission's ``spec.md`` file.

    Returns:
        Ordered list of :class:`IssueReference` entries with no duplicates.
        Empty list if ``spec_md_path`` contains no GH issue references.
    """
    text = spec_md_path.read_text(encoding="utf-8")
    seen: dict[int, str] = {}
    for line in text.splitlines():
        for match in _GH_ISSUE_PATTERN.finditer(line):
            num = int(match.group(1))
            if num not in seen:
                seen[num] = line.strip()
    return [IssueReference(num, ctx) for num, ctx in seen.items()]


def scaffold_issue_matrix(
    feature_dir: Path,
    spec_md_path: Path,
) -> Path | None:
    """Author ``feature_dir/issue-matrix.md`` from detected GH issue refs.

    The scaffold is **idempotent**: if ``issue-matrix.md`` already exists
    in ``feature_dir``, this function returns that path unchanged without
    overwriting operator-curated content.

    Args:
        feature_dir: The ``kitty-specs/<slug>/`` directory for the mission.
        spec_md_path: The mission's ``spec.md`` (used to detect issue refs).

    Returns:
        Path to the scaffolded (or pre-existing) ``issue-matrix.md``, or
        ``None`` when ``spec.md`` references no GH issues — in which case
        no file is created.
    """
    out_path = feature_dir / "issue-matrix.md"
    if out_path.exists():
        # Respect existing operator-curated file. Idempotent re-runs are a hard
        # requirement: the WP09 reviewer guidance explicitly checks this.
        return out_path
    refs = detect_issue_references(spec_md_path)
    if not refs:
        return None
    lines = [
        f"# Issue matrix — {feature_dir.name}",
        "",
        (
            "Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row "
            "per issue referenced in spec.md."
        ),
        "",
        "| Issue | Title | Verdict | Evidence ref |",
        "|-------|-------|---------|--------------|",
    ]
    for ref in refs:
        lines.append(
            f"| #{ref.number} | <fill at WP-implementation time> | unknown | <link or commit> |"
        )
    lines.append("")
    lines.append(
        "Valid `Verdict` values: `fixed`, `verified-already-fixed`, "
        "`deferred-with-followup`."
    )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
