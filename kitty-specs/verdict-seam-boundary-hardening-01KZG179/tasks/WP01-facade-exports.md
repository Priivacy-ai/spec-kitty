---
work_package_id: WP01
title: Façade exports — full verdict bridge onto status.__all__
dependencies: []
requirement_refs:
- FR-001
- FR-006
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundational
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-01a
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/__init__.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/__init__.py
- tests/status/test_reducer.py
- tests/specify_cli/coordination/test_status_facade_adoption_wp02.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3254'
---

# Work Package Prompt: WP01 – Façade exports

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

Promote the **full** verdict bridge onto the `specify_cli.status` public façade so that WP02 can migrate every consumer to façade symbols and retire the duplicated decode. This WP is **foundational**: it lands the exports *before* WP02's dedup (constraint **C-002** — the duplicated decode in the merge-blocking gate exists *only* because `review_result_from_state` is not yet exported).

## Why this WP exists

`status/verdict_vocab.py` has **10** public symbols but `status/__init__.__all__` promotes only 2 (`is_changes_requested`, `to_artifact_verdict`). Consumers reach the other 8 by importing the submodule object — the bypass WP02 will close. And `review_result_from_state` (the reducer-owned `review_result` decode) is imported into `__init__` but never exported, forcing `post_merge/review_artifact_consistency.py` to re-implement it. Export everything the consumers need, here, first.

## Subtasks

### T001 — Promote the full `verdict_vocab` public surface
Add to `status/__init__.py` imports **and** `__all__` (mirroring the existing per-symbol WP-provenance comment style — do not bare-append):
- 8 functions: `artifact_verdicts`, `event_verdicts`, `emission_artifact_verdicts`, `to_event_verdict`, `to_artifact_verdict` (already present), `emission_event_verdict`, `is_changes_requested` (already present), `is_approved`
- the `EventVerdict` type alias
- the constants `APPROVED`, `REJECTED`, `CHANGES_REQUESTED`

These are the symbols the WP02 consumers actually use (`proof/events.py` needs `EventVerdict`; `tasks_move_task.py`/`verdict_provenance_backfill.py` need the constants). Confirm the real surface with `python -c "import specify_cli.status.verdict_vocab as v; print([n for n in dir(v) if not n.startswith('_')])"` before editing.

### T002 — Export `review_result_from_state`
`reducer.review_result_from_state` is already imported in `status/__init__.py` (the reducer import block ~L34-43) — only the `__all__` entry is missing. Add it **beside** its sibling `event_sourced_review_result` (already exported ~L293) and mirror that block's provenance-comment style.

### T003 — (FR-006 campsite) Rename the two drifted reducer tests
In `tests/status/test_reducer.py`, the two tests whose **names/docstrings** contradict their bodies (they assert the frontmatter path is *not* consulted and does *not* refuse — the retired behavior):
- `test_forced_null_review_result_defers_to_frontmatter_and_still_refuses` (~L1167)
- `test_frontmatter_only_case_unchanged_when_no_event_sourced_verdict` (~L1204)

**Assertions are already correct** — rename the methods (and fix the misleading docstring fragments) to describe the *current* behavior, e.g. `test_forced_null_review_result_yields_no_findings`. Pure rename; change no assertion. *(NOTE: PR #3209 merged into base and shifted these line numbers — re-grep the exact names before editing.)*

### T004 — Assert the new exports
Extend `tests/specify_cli/coordination/test_status_facade_adoption_wp02.py` (or add a focused test there) to assert each newly-promoted symbol is importable from `specify_cli.status` and present in `__all__`.

## Branch Strategy

Planning/base branch: `hardening/verdict-seam-facade-followup`. Final merge target: same. Execution worktrees are allocated per computed lane from `lanes.json`. This is the foundational WP — **WP02 depends on it**.

## Definition of Done

- All 10 `verdict_vocab` symbols + `review_result_from_state` are on `status.__all__`, importable from `specify_cli.status`.
- The two reducer tests renamed; assertions unchanged; `pytest tests/status/test_reducer.py` green.
- Façade-adoption test asserts the new exports; green.
- `ruff check` + `mypy` clean on touched files, zero new suppressions.

## Reviewer Guidance

Confirm the export list matches the real `verdict_vocab` public surface (no omissions that would strand a WP02 consumer). Confirm the reducer-test rename changed no assertion (diff the bodies). Confirm `review_result_from_state` sits beside `event_sourced_review_result` with matching comment style.

## Risks

- Missing a symbol here strands a WP02 consumer on the submodule object — cross-check against the WP02 migration list.
- Do not touch `status/reducer.py` here (that is WP02's docstring reconcile) — this WP edits only `__init__.py` + the two test files.
