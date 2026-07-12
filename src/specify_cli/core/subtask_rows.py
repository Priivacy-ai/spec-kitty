"""Canonical work-package subtask row patterns — single definition (#2504 / #2513).

A WP's subtasks are the checkbox rows of the form ``- [ ] T001 <desc>`` /
``- [x] T001 <desc>`` in ``tasks.md`` and the WP prompt body. The
lane-transition guard blocks on unchecked rows; the dashboard reports
done/total progress; ``move-task --to planned`` unchecks them on rollback.
All three consume THESE patterns — do not re-derive them locally
(canonical-sources rule).

Semantics (mirrors the guard, ``_check_unchecked_subtasks``):

* A ``T`` id of at least three digits is mandatory (``\\d{3,}`` so ids past
  T999 still match).
* Only implementation rows count: validation/procedure command rows
  (``- [ ] swift test``), prose checkboxes, and anything inside fenced code
  blocks are not work-package subtasks.
* Section semantics (#2346 / #2324): a heading (``##``–``####``) belongs to
  the WP named by its FIRST ``WPxx`` token, NOT any mention — so
  ``### WP03 … (depends: WP01)`` does not re-enter WP01's section.
* Section semantics (NFR-005): once a *different* WP's heading is seen, the
  section is closed for the rest of the document — a later re-appearing
  ``## WPxx`` heading for the same WP does not reopen it. This is a
  deliberate correction of the writer's pre-unification behavior, which used
  to re-enter such a heading; the guard/read side always had this right.

All three callers (lane-transition guard, dashboard progress, rollback
writer) are driven by the single private ``_walk_wp_section`` generator
below — it is the only place the heading rule, fence skipping, and
section-exit semantics are encoded.
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

    This counts across the whole document, not a single WP's section, so it
    does not consume ``_walk_wp_section`` (which is WP-scoped) — it keeps its
    own minimal fence-aware loop but shares the two row-pattern constants.
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


def _heading_wp_token(line: str) -> str | None:
    """Return the FIRST ``WPxx`` token in *line* if it is a ``##``-``####`` heading."""
    if not re.match(r"^#{2,4}[^#]", line):
        return None
    wp_tokens = re.findall(r"\bWP\d{2,}\b", line)
    return wp_tokens[0] if wp_tokens else None


def _walk_wp_section(lines: list[str], wp_id: str) -> Iterator[tuple[int, str, bool]]:
    """Yield ``(index, raw_line, checked)`` for canonical rows in *wp_id*'s section.

    The single, canonical definition of "what counts as a WP subtask row",
    consumed identically by the lane-transition guard, the dashboard, and the
    rollback writer. Encodes, once:

    * **First-``WPxx``-token heading rule** (#2346/#2324): a heading
      (``##``-``####``) belongs to the WP named by the *first* ``WPxx`` token
      found in it, not any mention — ``### WP03 … (depends: WP01)`` belongs
      to WP03, not WP01.
    * **Fenced-code skipping**: lines between a matching ``` `/`~~~` pair are
      never yielded as rows, even if they look like subtask rows.
    * **Break-on-section-exit**: once a *different* WP's heading is seen
      after the target section opened, the section is closed for the rest of
      the document — a later re-appearing ``## wp_id`` heading does not
      reopen it.

    Only rows matching ``CHECKED_SUBTASK_ROW``/``UNCHECKED_SUBTASK_ROW`` are
    yielded; the *index* is the position in *lines* so a caller can either
    read-count (ignore the index) or mutate in place (index back into
    *lines*) without a second parallel walk.
    """
    in_wp_section = False
    in_code_fence = False
    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        heading_wp = _heading_wp_token(line)
        if heading_wp == wp_id:
            in_wp_section = True
            continue
        if in_wp_section and heading_wp is not None and heading_wp != wp_id:
            break  # entered a different WP's section — closed for the rest of the doc

        if not in_wp_section:
            continue

        checked_match = CHECKED_SUBTASK_ROW.match(stripped)
        if checked_match:
            yield index, line, True
            continue
        unchecked_match = UNCHECKED_SUBTASK_ROW.match(stripped)
        if unchecked_match:
            yield index, line, False


def iter_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> Iterator[tuple[str, bool]]:
    """Yield ``(task_id, checked)`` for canonical rows in *wp_id*'s tasks.md section.

    The standard convention keeps the checkable ``- [ ] T### …`` rows in
    ``tasks.md``, grouped under per-WP headings — the source the
    lane-transition guard blocks on. Section semantics are driven by
    ``_walk_wp_section`` (see its docstring for the exact rules).
    """
    lines = tasks_md_text.split("\n")
    for _index, line, checked in _walk_wp_section(lines, wp_id):
        stripped = line.strip()
        pattern = CHECKED_SUBTASK_ROW if checked else UNCHECKED_SUBTASK_ROW
        match = pattern.match(stripped)
        if match:
            yield match.group(1), checked


def count_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> tuple[int, int]:
    """Return ``(done, total)`` canonical rows in *wp_id*'s tasks.md section."""
    done = 0
    total = 0
    for _task_id, checked in iter_wp_section_subtask_rows(tasks_md_text, wp_id):
        total += 1
        if checked:
            done += 1
    return done, total


def uncheck_wp_section_subtask_rows(tasks_md_text: str, wp_id: str) -> str:
    """Return *tasks_md_text* with all checked T### rows in *wp_id*'s section unchecked.

    Applies the same section and fence semantics as the lane-transition guard
    and the dashboard counter, via ``_walk_wp_section`` — including the
    break-on-section-exit rule: a re-appearing ``## wp_id`` heading later in
    the document is NOT re-entered, so only the *first* section's checked
    rows are ever flipped (NFR-005 correction — the writer previously
    re-entered such a heading; the guard/dashboard never did).

    Returns the original text unchanged when the section has no checked rows
    (no allocation, no write). Used by ``move-task --to planned`` to reset
    subtask state on WP rollback (#2513): a rolled-back WP must be
    re-implemented, so leaving its subtasks checked would be a lie.
    """
    lines = tasks_md_text.split("\n")
    flip_indices = {index for index, _line, checked in _walk_wp_section(lines, wp_id) if checked}
    if not flip_indices:
        return tasks_md_text

    changed = False
    result: list[str] = []
    for index, line in enumerate(lines):
        if index not in flip_indices:
            result.append(line)
            continue
        new_line = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
        if new_line != line:
            changed = True
        result.append(new_line)
    return "\n".join(result) if changed else tasks_md_text
