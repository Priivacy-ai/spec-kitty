"""Deterministic table renderers for :class:`FreshnessFinding` rows.

Two helpers are exposed:

- :func:`render_table_rich` returns a :class:`rich.table.Table` suitable for
  interactive terminals.
- :func:`render_table_plain` returns a deterministic tab-separated string,
  one finding per line, suitable for CI annotations.

Both helpers iterate findings in source order so that callers may pre-sort
to guarantee byte-identical output for identical inputs (per the
``version_leakage_check`` contract's determinism guarantee).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from rich.table import Table

__all__ = [
    "FINDING_COLUMNS",
    "FreshnessFinding",
    "render_table_plain",
    "render_table_rich",
]


Severity = Literal["error", "warning"]


@dataclass(slots=True, frozen=True)
class FreshnessFinding:
    """One row of the version-leakage check output.

    Mirrors :class:`FreshnessFinding` from ``data-model.md`` so the leakage
    tool's findings can be assembled into a ``FreshnessReport`` slice
    without translation.
    """

    rule_id: str
    severity: Severity
    location: str
    message: str
    suggested_action: str


FINDING_COLUMNS: Final[tuple[str, ...]] = (
    "rule_id",
    "severity",
    "location",
    "message",
    "suggested_action",
)


def render_table_rich(findings: list[FreshnessFinding]) -> Table:
    """Build a :class:`rich.table.Table` from ``findings``.

    Output order matches the order of ``findings`` for determinism.
    """
    table = Table(title="Version Leakage Findings", show_lines=False)
    for column in FINDING_COLUMNS:
        table.add_column(column, no_wrap=False, overflow="fold")
    for finding in findings:
        table.add_row(
            finding.rule_id,
            finding.severity,
            finding.location,
            finding.message,
            finding.suggested_action,
        )
    return table


def render_table_plain(findings: list[FreshnessFinding]) -> str:
    """Render ``findings`` as a tab-separated string.

    The first line is a header containing :data:`FINDING_COLUMNS`. Each
    subsequent line is one finding with tab-separated fields. The string
    always ends with a trailing newline (or is empty when there are no
    findings and no header is desired).

    For determinism, callers should pre-sort the findings list; this
    function preserves order.
    """
    lines = ["\t".join(FINDING_COLUMNS)]
    for finding in findings:
        lines.append(
            "\t".join(
                (
                    finding.rule_id,
                    finding.severity,
                    finding.location,
                    finding.message,
                    finding.suggested_action,
                )
            )
        )
    return "\n".join(lines) + "\n"
