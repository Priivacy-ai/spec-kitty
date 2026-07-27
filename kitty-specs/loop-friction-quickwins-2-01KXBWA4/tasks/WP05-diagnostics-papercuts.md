---
work_package_id: WP05
title: Diagnostics papercuts — issue-matrix error + bulk-edit inference
dependencies: []
requirement_refs:
- FR-007
- FR-008
- NFR-005
- NFR-006
tracker_refs:
- '2555'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: cf4e743947eac5ddd06bb478fd0c571e771a29d4
created_at: '2026-07-12T21:35:02.396335+00:00'
subtasks:
- T017
- T018
- T019
- T020
phase: Diagnostics
agent: "claude"
shell_pid: '1484725'
shell_pid_created_at: '1783892074.19'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-05)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/cli/commands/review/_issue_matrix.py
- src/specify_cli/bulk_edit/inference.py
- tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py
- tests/specify_cli/bulk_edit/test_inference.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 — Diagnostics papercuts

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

Two independent single-purpose fixes:
1. The issue-matrix approval blocker names the schema-drift/offending column when a header is malformed (FR-007).
2. Bulk-edit inference stops blocking on ordinary refactor verbs while genuine bulk edits — including a
   single-HIGH-phrase edit — still trip (FR-008).

- **SC (FR-007)**: a malformed mandatory column → the blocker names the offending/normalized column, not a "Missing rows: #A, #B…" list.
- **SC (FR-008)**: `refactor`+`update`+`change`+single `rename` → `triggered is False`; genuine bulk → `True`.

## Context & Constraints

- **FR-007 (#2555.5)**: `tasks_parsing_validation.py:206` emits `"Missing rows: …"`. When a mandatory column
  header is non-canonical, `review/_issue_matrix.py:262-287` early-returns with zero rows (its
  `ISSUE_MATRIX_SCHEMA_DRIFT` diagnostic carries a `detail` naming the found/normalized columns), so every
  referenced issue looks "missing". The detail exists but is never surfaced.
- **FR-008 (#2555.3)**: `bulk_edit/inference.py` — `LOW_WEIGHT_KEYWORDS` (update/change/modify/refactor, 1pt)
  are appended into the `triggered` sum (:119) with `INFERENCE_THRESHOLD = 4` (:51). Ordinary refactor prose
  reaches 4 and blocks.

**KEEP invariant (NFR-005, renata F10):** with threshold 4, dropping the low-weight `+1` lets a
**single-HIGH-phrase** bulk edit (score 3) escape. You MUST add a single-HIGH-phrase regression that still
trips; if it cannot pass at threshold 4, adopt the R-08 fallback (require a HIGH phrase OR a scale qualifier
like "across the codebase"/"replace all" to co-occur) rather than lowering detection.

Plan: IC-05. Research: R-07/R-08. Contract: C-C2/C-C3.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T017 — Schema-drift-first blocker message (via the existing diagnostic helper — complexity guard)

- **COMPLEXITY GUARD (pedro)**: `_issue_matrix_approval_blocker` (`def` @ `tasks_parsing_validation.py:129`)
  is already at cyclomatic **13** — adding the branch inline breaches the 15 ceiling. Instead, surface the
  drift in the EXISTING `_issue_matrix_diagnostic_lines` helper (@ `:114`), which today reads only
  `diagnostic.get("message")` and drops `diagnostic.get("detail")` (the found/normalized columns) — extend it
  to surface the `detail`, and gate the "Missing rows: …" line (@ `:206`) to only emit when rows actually
  parsed. Keep the blocker flat.
- **S1192 (pedro)**: the `"ERROR: issue-matrix.md …"` prefix and `"before approving"` each recur 3× (:160/:180/:204);
  this WP adds a 4th ERROR line → hoist `_ISSUE_MATRIX_ERROR_PREFIX` / `_FILL_VERDICTS_HINT` constants.
- **Files**: `tasks_parsing_validation.py` (`review/_issue_matrix.py` owned as a hedge — likely not edited; the
  diagnostic dict already carries `detail`).

### Subtask T018 — Test: malformed column named + preservation branch

- **Steps**: In `test_tasks_parsing_validation.py`: (a) a matrix whose `issue`/mandatory column is spelled
  non-canonically → the blocker names the column/schema drift and does NOT list all referenced issues as
  "Missing rows"; **(b) a genuinely row-incomplete matrix (rows parsed, some referenced issue missing) STILL
  emits "Missing rows"** — pins the "keep only when rows parsed" preservation branch.
- **Files**: the test file.

### Subtask T019 — Bulk-edit: drop low-weight verbs from `triggered`

- **Steps**: In `inference.py`, exclude `LOW_WEIGHT_KEYWORDS` from the `triggered` sum (keep them in
  `matched_phrases` for display). Verify genuine bulk still trips via HIGH ("rename all occurrences") or two
  MEDIUMs ("rename" + "across the codebase"). If the single-HIGH case (T020) fails at threshold 4, implement
  the co-occurrence fallback instead of lowering the threshold.
- **Files**: `bulk_edit/inference.py`.

### Subtask T020 — Test: inference scoring cases

- **Steps**: In `test_inference.py`: (a) `refactor`+`update`+`change`+single `rename` non-bulk → `triggered is False`;
  (b) "rename all occurrences …" / "rename … across the codebase" → `True`; (c) a SINGLE-HIGH-phrase bulk
  spec → `True` (the true-positive at risk).
- **Files**: `tests/specify_cli/bulk_edit/test_inference.py`.

## Definition of Done

- Issue-matrix blocker names the drift column; bulk-edit no longer trips on ordinary refactor verbs; all three inference cases pass.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py tests/specify_cli/bulk_edit/test_inference.py -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk (highest)**: FR-008 under-detects a genuine single-HIGH bulk edit — reviewer confirms T020(c) fails on a naive drop-the-verbs implementation and passes only with the guard/fallback.

## Activity Log

- 2026-07-12T21:55:58Z – claude – shell_pid=1484725 – reviewer-renata APPROVE: FR-007 complexity-safe via diagnostic-lines helper; FR-008 scope-fallback calibrated; 3 test flips design-justified
- 2026-07-12T21:56:14Z – claude – shell_pid=1484725 – reviewer-renata APPROVE
