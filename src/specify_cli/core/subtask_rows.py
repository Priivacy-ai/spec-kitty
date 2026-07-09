"""Work-package subtask row utilities for tasks.md manipulation (#2513).

Provides text-level transformations on the canonical ``- [ ] T### …`` /
``- [x] T### …`` rows that live in ``tasks.md`` WP sections. Section and
fence semantics mirror those in ``_check_unchecked_subtasks`` (#2346 /
#2324 heading rule) — a WP section is bounded by the heading whose FIRST
``WPxx`` token matches the target WP id.

Note: PR #2505 introduces additional read-only utilities to this module
(``iter_wp_section_subtask_rows``, ``count_wp_section_subtask_rows``).
When both PRs land, the section-traversal logic here and in #2505 should
be unified — one canonical walk shared by all callers.
"""

from __future__ import annotations

from kernel._safe_re import re

#: Checked canonical subtask row: ``- [x] T001 ...``.
_CHECKED_SUBTASK_ROW = re.compile(r"^-\s*\[[xX]\]\s*(T\d{3,})\b")


def uncheck_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> str:
    """Return *tasks_md_text* with all checked T### rows in *wp_id*'s section unchecked.

    Applies the same section and fence semantics as the lane-transition guard:

    * a heading (``##``–``####``) belongs to the WP named by its FIRST
      ``WPxx`` token — ``### WP03 … (depends: WP01)`` does not re-enter
      WP01's section (#2346 / #2324);
    * entering a different WP's heading ends the section;
    * rows inside fenced code blocks are ignored.

    Returns the original text unchanged when the section has no checked rows
    (no allocation, no write).  Used by ``move-task --to planned`` to reset
    subtask state on WP rollback (#2513): a rolled-back WP must be
    re-implemented, so leaving its subtasks checked would be a lie.
    """
    lines = tasks_md_text.split("\n")
    in_wp_section = False
    in_code_fence = False
    changed = False
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            result.append(line)
            continue
        if in_code_fence:
            result.append(line)
            continue
        heading_wp: str | None = None
        if re.match(r"^#{2,4}[^#]", line):
            wp_tokens = re.findall(r"\bWP\d{2,}\b", line)
            heading_wp = wp_tokens[0] if wp_tokens else None
        if heading_wp == wp_id:
            in_wp_section = True
            result.append(line)
            continue
        if in_wp_section and heading_wp is not None and heading_wp != wp_id:
            in_wp_section = False
            result.append(line)
            continue
        if in_wp_section and _CHECKED_SUBTASK_ROW.match(stripped):
            new_line = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
            if new_line != line:
                changed = True
            result.append(new_line)
        else:
            result.append(line)
    return "\n".join(result) if changed else tasks_md_text
