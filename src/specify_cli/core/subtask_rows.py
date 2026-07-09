"""Canonical work-package subtask row patterns — single definition (#2504).

A WP's subtasks are the checkbox rows of the form ``- [ ] T001 <desc>`` /
``- [x] T001 <desc>`` in ``tasks.md`` and the WP prompt body. The
lane-transition guard blocks on unchecked rows; the dashboard reports
done/total progress. Both consume THESE patterns — do not re-derive them
locally (canonical-sources rule).

Semantics (mirrors the guard, ``_check_unchecked_subtasks``):

* A ``T`` id of at least three digits is mandatory (``\\d{3,}`` so ids past
  T999 still match).
* Only implementation rows count: validation/procedure command rows
  (``- [ ] swift test``), prose checkboxes, and anything inside fenced code
  blocks are not work-package subtasks.
"""

from __future__ import annotations

from collections.abc import Iterator

from kernel._safe_re import re

#: Unchecked canonical subtask row: ``- [ ] T001 ...`` (blocks lane transitions).
UNCHECKED_SUBTASK_ROW = re.compile(r"^-\s*\[\s*\]\s*(T\d{3,})\b")

#: Checked canonical subtask row: ``- [x] T001 ...``.
CHECKED_SUBTASK_ROW = re.compile(r"^-\s*\[[xX]\]\s*(T\d{3,})\b")


def count_subtask_rows(text: str) -> tuple[int, int]:
    """Return ``(done, total)`` canonical subtask rows in *text*.

    Rows inside fenced code blocks (``` or ~~~) are ignored — task-like
    example lines in implementation notes are not real subtasks, matching the
    guard's fence handling.
    """
    done = 0
    total = 0
    in_code_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if CHECKED_SUBTASK_ROW.match(stripped):
            done += 1
            total += 1
        elif UNCHECKED_SUBTASK_ROW.match(stripped):
            total += 1
    return done, total


def iter_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> Iterator[tuple[str, bool]]:
    """Yield ``(task_id, checked)`` for canonical rows in *wp_id*'s tasks.md section.

    The standard convention keeps the checkable ``- [ ] T### …`` rows in
    ``tasks.md``, grouped under per-WP headings — the source the
    lane-transition guard blocks on. Section semantics mirror the guard
    exactly:

    * a heading (``##``–``####``) belongs to the WP named by its FIRST
      ``WPxx`` token, NOT any mention — so ``### WP03 … (depends: WP01)``
      does not re-enter WP01's section (#2346 / #2324);
    * entering a different WP's heading ends the section;
    * fenced code blocks are ignored.
    """
    in_wp_section = False
    in_code_fence = False
    for line in tasks_md_text.split("\n"):
        stripped = line.strip()

        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        heading_wp: str | None = None
        if re.match(r"^#{2,4}[^#]", line):
            wp_tokens = re.findall(r"\bWP\d{2,}\b", line)
            heading_wp = wp_tokens[0] if wp_tokens else None
        if heading_wp == wp_id:
            in_wp_section = True
            continue
        if in_wp_section and heading_wp is not None and heading_wp != wp_id:
            break  # entered a different WP's section

        if not in_wp_section:
            continue

        checked_match = CHECKED_SUBTASK_ROW.match(stripped)
        if checked_match:
            yield checked_match.group(1), True
            continue
        unchecked_match = UNCHECKED_SUBTASK_ROW.match(stripped)
        if unchecked_match:
            yield unchecked_match.group(1), False


def count_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> tuple[int, int]:
    """Return ``(done, total)`` canonical rows in *wp_id*'s tasks.md section."""
    done = 0
    total = 0
    for _task_id, checked in iter_wp_section_subtask_rows(tasks_md_text, wp_id):
        total += 1
        if checked:
            done += 1
    return done, total
