---
work_package_id: WP04
title: Checkbox-parser canonicalization
dependencies: []
requirement_refs:
- FR-008
- FR-009
- NFR-003
tracker_refs: []
planning_base_branch: rework/coord-shadows-followups
merge_target_branch: rework/coord-shadows-followups
branch_strategy: Planning artifacts for this mission were generated on rework/coord-shadows-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/coord-shadows-followups unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
phase: Phase 4 - Checkbox authority
assignee: ''
agent: "claude"
shell_pid: "698445"
history:
- at: '2026-07-12T15:14:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/subtask_rows.py
create_intent:
- tests/specify_cli/acceptance/test_find_unchecked_tasks_canon.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/subtask_rows.py
- src/specify_cli/acceptance/gates_core.py
- tests/specify_cli/acceptance/test_find_unchecked_tasks_canon.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Checkbox-parser canonicalization

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role: implementer) before parsing the rest of this prompt.

## Objectives & Success Criteria

Closes **#2567**. Replace the acceptance gate's stray whole-file `[ ]` regex with a canonical fence-aware, T###-scoped whole-file iterator on `core/subtask_rows` — unifying checkbox semantics. The tightening is **ratified consciously** via a characterization test.

Done when:
- `iter_unchecked_subtask_rows(text) -> Iterator[str]` exists on `core/subtask_rows.py` (whole-file, fence-aware, T###-scoped, yields the offending line strings the gate needs).
- `acceptance/gates_core.py::_find_unchecked_tasks` consumes it; the stray `re.match(r"^\s*-\s*\[ \]")` is removed.
- A characterization test captures the old→new flagging (the T###/fence/indent tightening); terminal-mission normalization is preserved.
- Dead-code gate clean; `ruff` + `mypy` clean.

## Context & Constraints

- **D5 / semantics change (NOT mechanical):** the current parser is whole-file and flags ANY `- [ ]` (prose, fenced examples, indented). The canonical iterator narrows to T###-scoped + fence-aware. This LOOSENS what the gate flags — an intentional improvement that must be ratified by the characterization test (FR-009), not folded silently.
- `count_subtask_rows` returns counts only (drops the strings the gate needs); `_walk_wp_section`/`iter_wp_section_subtask_rows` are WP-scoped. Hence a NEW whole-file **string-yielding** iterator on the shared constants — do not force-fit the existing functions.
- Preserve the terminal-mission normalization at `gates_core.py:81-102` (`_normalized_unchecked_tasks` zeroes unchecked tasks when all WPs are terminal).
- `_find_unchecked_tasks` has one production caller (`acceptance/__init__.py:968`) + test monkeypatches.
- **C-003**: canonical `core/subtask_rows` only; no improvised parser.

## Subtasks

- [ ] T024 Add `iter_unchecked_subtask_rows(text) -> Iterator[str]` (whole-file, fence-aware, T###) on `core/subtask_rows.py`.
- [ ] T025 [P] Characterization test (`tests/specify_cli/acceptance/test_find_unchecked_tasks_canon.py`): old→new flagging on a mixed fixture (T### rows + prose `[ ]` + fenced examples) — ratifies the tightening.
- [ ] T026 Migrate `gates_core._find_unchecked_tasks` onto the iterator; remove the stray regex.
- [ ] T027 [P] Test: terminal-mission normalization preserved.
- [ ] T028 Dead-code gate + `ruff` + `mypy` clean.

## Campsite & Coverage Notes (post-tasks squad — fold into the listed subtasks)

- **Coverage (fold into T024/T025):** add a DIRECT `iter_unchecked_subtask_rows` unit test enumerating each new branch — T### unchecked → yielded; prose `- [ ]` → rejected; fenced (```` ``` ````) `- [ ]` → rejected; indented/anchored tightening. T025 (via the gate) + T027 (normalization) do not cover the iterator branches directly.
- **Reuse, no new literal (T024):** mirror `count_subtask_rows`'s existing fence-loop (`subtask_rows.py:56-71`) and reuse the two module constants (`UNCHECKED_SUBTASK_ROW` etc.) — do not introduce a new regex/literal.
- `_find_unchecked_tasks` simplifies to near-trivial after the migration (campsite win); preserve `_normalized_unchecked_tasks` (`gates_core.py:81-102`) verbatim (T027 pins it).

## Definition of Done

All 5 subtasks checked (T024/T025 include a direct iterator branch test); `pytest tests/specify_cli/acceptance/ tests/specify_cli/core/ -q` green; stray regex removed (dead-code clean); `ruff` + `mypy` clean.

## Dependencies

None.

## Activity Log

- 2026-07-12T15:29:17Z – claude – shell_pid=698445 – Assigned agent via action command
- 2026-07-12T15:52:02Z – claude – shell_pid=698445 – Ready: canonical iter_unchecked_subtask_rows + ratified tightening; 400 passed
- 2026-07-12T15:57:19Z – user – shell_pid=698445 – APPROVED by reviewer-renata (opus): 7/7 checks pass; tightening judged SAFE (unifies with guard/dashboard/writer)
