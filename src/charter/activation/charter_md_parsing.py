"""``charter.md`` prose parsing helpers (WP04 T020, #2532).

Relocated verbatim from ``charter.activation.context`` (single-owner, no-net-growth for
that file). Pure text-parsing over the ``charter.md`` content string — no
governance-decision logic lives here (see
``tests/charter/test_context_display_charter_md.py``'s ``INV-3`` static
proof: functions that decide *which* directives/tactics/paradigms apply must
never reference this prose-parsing surface).
"""

from __future__ import annotations

# ``_find_section_start`` de-exported after the context.py re-export shim
# retirement (doctrine-built-in-seam-consolidation WP06): it has no external
# ``src/`` importer left. It stays a module-internal helper used by
# ``_extract_policy_summary`` above.
__all__ = [
    "_extract_policy_summary",
]


def _extract_policy_summary(content: str) -> list[str]:
    lines = content.splitlines()
    start = _find_section_start(lines, "## Policy Summary")

    if start is None:
        # Fallback: return the first meaningful bullet points in the document.
        fallback = [line.strip().lstrip("- ").strip() for line in lines if line.strip().startswith("-")]
        return [item for item in fallback if item][:8]

    summary: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("-"):
            summary.append(stripped.lstrip("- ").strip())
    return summary


def _find_section_start(lines: list[str], heading: str) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None
