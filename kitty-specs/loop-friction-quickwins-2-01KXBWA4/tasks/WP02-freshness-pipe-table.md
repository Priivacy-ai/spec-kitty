---
work_package_id: WP02
title: Analysis-report freshness normalizes pipe-table status cells
dependencies: []
requirement_refs:
- FR-002
- NFR-002
- NFR-005
tracker_refs:
- '2493'
- '1862'
- '1764'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: ce40165f826f5683865cea95053f33be9b903785
created_at: '2026-07-12T21:33:29.773722+00:00'
subtasks:
- T005
- T006
- T007
phase: Guards self-stable
agent: "claude"
shell_pid: '1481719'
shell_pid_created_at: '1783891999.06'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-02)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/analysis_report.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/analysis_report.py
- tests/specify_cli/test_analysis_report.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — Analysis-report freshness normalizes pipe-table status cells

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

`mark-status`'s pipe-table `[D]`/`[P]` status-cell churn must not re-stale the analysis-report, while a
substantive `tasks.md` row change still stales it.

- **SC (NFR-002)**: mark-status → implement claim on a pipe-table `tasks.md` yields 0 `stale_analysis_report`.
- **SC (true-positive, NFR-005)**: a change to a substantive `tasks.md` row's text still stales the report.

## Context & Constraints

Bug (#2493.1): `_normalize_tasks_md` (`src/specify_cli/analysis_report.py:147`) uses
`_CHECKBOX_RE = r"(?m)^(\s*[-*]\s*)\[[ xX]\]"` (:144) — **bullet-line-start only**, charclass `[ xX]`. The
#1764 fix covers bullet checkboxes; pipe-table status cells (` [D] `/` [P] `/`[x]`, written by
`tasks_materialization.py:218-249,276-304`) escape on BOTH axes (cell position + charclass), so they mutate
the freshness hash and falsely stale the report. #1862 is the open umbrella ticket for exactly this.

**KEEP**: the bullet-checkbox normalization behavior is preserved; a substantive row change still stales
(K-1/NFR-005). One carefully-anchored added regex — do not broaden so far that real content is normalized away.

Plan: IC-02. Research: R-02. Contract: C-A2.

## Branch Strategy

- **Planning base branch**: feat/loop-friction-quickwins-2
- **Merge target branch**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T005 — Extend `_normalize_tasks_md`

- **Purpose**: Canonicalize status markers wherever they appear as a standalone status cell, not only at bullet line-start.
- **Steps**: Add a second normalization that matches a status cell inside a pipe-table cell boundary
  (`| … [ ]/[x]/[X]/[D]/[P] … |`) and canonicalizes the marker to a fixed token, leaving surrounding row
  text intact. Keep `_CHECKBOX_RE` untouched. Anchor the new regex to a table-cell context so it cannot
  match prose or a substantive `[D]`-like token in a description.
- **Files**: `src/specify_cli/analysis_report.py`.

### Subtask T006 — Test: pipe-table + mixed churn stays current

- **Steps**: In `tests/specify_cli/test_analysis_report.py`, add a sibling to
  `test_analysis_report_survives_subtask_checkbox_churn`: a pipe-table `tasks.md` whose only change is
  `[ ]`→`[D]`/`[P]`/`[x]` cells → `check_analysis_report_current` returns current. Add a mixed case
  (bullet checkboxes AND pipe-table cells) asserting both normalize.
- **Files**: the test file.

### Subtask T007 — Test: substantive change still stales

- **Steps**: A change to a table row's DESCRIPTION text (not the status cell) → report is stale. Prevents an
  over-broad normalizer.
- **Files**: the test file.

## Definition of Done

- `_normalize_tasks_md` canonicalizes pipe-table status cells + bullet checkboxes; substantive change still stales.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/test_analysis_report.py -q` green; `ruff` + `mypy` clean.
- Add #1862 to the closes/advances linkage in the PR body.

## Risks & Reviewer Guidance

- **Risk**: over-broad regex normalizes real content → T007 guards it; reviewer confirms T007 fails if the regex is loosened.

## Activity Log

- 2026-07-12T21:48:15Z – claude – shell_pid=1481719 – reviewer-renata APPROVE
- 2026-07-12T21:51:02Z – claude – shell_pid=1481719 – reviewer-renata APPROVE
