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
