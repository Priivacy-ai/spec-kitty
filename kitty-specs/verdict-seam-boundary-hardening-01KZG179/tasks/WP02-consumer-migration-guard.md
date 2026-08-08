---
work_package_id: WP02
title: Consumer migration + dedup + boundary-guard widening
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundational
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-01b
agent_profile: python-pedro
authoritative_surface: src/specify_cli/post_merge/review_artifact_consistency.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/reducer.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- src/specify_cli/review/cycle.py
- src/specify_cli/proof/events.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/migration/verdict_provenance_backfill.py
- src/specify_cli/coordination/status_service.py
- src/specify_cli/merge/done_bookkeeping.py
- tests/architectural/test_status_module_boundary.py
- tests/post_merge/test_review_artifact_consistency.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3254'
---

# Work Package Prompt: WP02 – Consumer migration + dedup + guard widening

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

Close the single-authority boundary: migrate **every** `status.<submodule>`-object import to façade symbols (WP01 exported them), retire the duplicated `review_result` decode on the merge-blocking path, and widen the boundary guard so the bypass is actually caught. **Depends on WP01** (C-002 export-before-dedup).

## Subtasks

### T005 — Migrate the 8 verdict_vocab consumers to façade symbols
Replace `from specify_cli.status import verdict_vocab` + `verdict_vocab.X()` with `from specify_cli.status import X` + `X()` in:
- `review/cycle.py` (`emission_event_verdict`) · `proof/events.py` (`EventVerdict`, `event_verdicts`) · `sync/emitter.py` (`event_verdicts`, `emission_artifact_verdicts`) · `orchestrator_api/commands.py` (`event_verdicts`, in `_parse_review_result_json`) · `retrospective/generator.py` (`is_changes_requested`) · `post_merge/review_artifact_consistency.py` (`is_changes_requested`) · `cli/commands/agent/tasks_move_task.py` (`emission_event_verdict`, `APPROVED`, `REJECTED`) · `migration/verdict_provenance_backfill.py` (`CHANGES_REQUESTED`, `APPROVED`, `emission_event_verdict`, `is_changes_requested`).
- **`retrospective/generator.py:332`** uses a *function-scoped* import — verify it is not a deliberate import-cycle break before hoisting to module top; if it is, migrate in place (still function-scoped).

### T006 — Migrate the 4 collateral submodule-object imports
Operator decision: fully close the boundary (no exemption ledger). Migrate to façade symbols:
- `orchestrator_api/commands.py:1558` (`emit as status_emit`) · `coordination/status_service.py:290` and `:308` (`store as _store`) · `merge/done_bookkeeping.py:154` (`lane_reader as _lane_reader`).
- **`status_service.py`** uses function-scoped imports each carrying `# noqa: PLC0415` (deliberate lazy/cycle-avoidance) — preserve that pattern; do not trip the noqas. Confirm the façade exports the specific `store`/`emit`/`lane_reader` names each site calls.

### T007 — Campsite (same WP as the edit)
- `tasks_move_task.py::_mt_emit_runtime_state` is **cc=13** and constructs `ReviewOverride(...)` (~L2172). **Extract a helper** (e.g. `_build_claim_review_override`) *before* adding the migration change so the function does not cross the 15 ceiling.
  - **Objective gate (NFR-004 — do not skip):** record the cc before/after the extract (e.g. `ruff check --select C901 <file>` or a cognitive-complexity read) in the WP notes, and add a **focused unit test for `_build_claim_review_override`** exercising its output directly (adding the migration branch alone lands the function at ~cc14 — still under the ceiling, so a skipped extract would pass silently; this gate is what catches that).
- `merge/done_bookkeeping.py:119` hard-codes `verdict="approved"` in a `ReviewApproval` construction → route through the façade `APPROVED` constant.

### T008 — Retire the duplicated decode (merge-blocking path)
In `post_merge/review_artifact_consistency.py::_event_sourced_gate_verdict` (~L159-167) replace the inline `ReviewResult.from_dict(...)` + `(KeyError,TypeError,ValueError)` catch with a call to façade `review_result_from_state`, adapting the return type:
`event_verdict = str(lookup.result.verdict) if lookup.result is not None else None`.
Behavior must be **identical** across all 5 decode cases (absent slot / raw-None / non-Mapping / from_dict-raises / valid) — NFR-001.
- **Delete the now-false justification docstring** at ~L148-158 ("...not on that facade's `__all__`...") — it becomes actively wrong the moment WP01 exports the symbol. **Reconcile** the echoed rationale in `reducer.review_result_from_state`'s docstring (~L522-527).

### T009 — Widen the boundary guard (+ non-vacuity teeth)
In `tests/architectural/test_status_module_boundary.py`, widen the walk so `ast.ImportFrom` also inspects `alias.name` (not just `node.module`), flagging `from specify_cli.status import <submodule>`.
- **C-003 trap:** target submodule **names specifically** — resolve via `(status_dir / f"{name}.py").exists()` or an explicit submodule-name set. A bare `startswith("specify_cli.status")` on the imported name would flag 100+ legitimate façade-**symbol** imports. 
- Add a **synthetic-violation teeth test** (NFR-002): a fabricated `from specify_cli.status import verdict_vocab` AST must be flagged; a fabricated `from specify_cli.status import is_approved` must **not**.
- After widening, the repo must be green (all 12 migrations done). Do **not** add exemptions.

### T010 — Behavior-preservation tests for the dedup
In `tests/post_merge/test_review_artifact_consistency.py`, add focused tests exercising `_event_sourced_gate_verdict` across all 5 decode cases, proving parity with the retired inline decode (NFR-001).

## Do-NOT-touch complexity traps (edit region is elsewhere in these files)
- `orchestrator_api/commands.py::_execute_lane_merge` (cc=15) / `transition` (14) — keep the diff surgically inside `_parse_review_result_json`.
- `retrospective/generator.py::_build_findings` (cc=15) — keep the diff inside the ~L340 helper.

## Branch Strategy
Base: WP01's lane. Final merge target: `hardening/verdict-seam-facade-followup`. **Rebase watch:** confirm no fresh collision on the migrated files before pushing.

## Definition of Done
- `grep -rn "from specify_cli.status import" src/specify_cli | grep -E "import (verdict_vocab|emit|store|lane_reader)\b"` returns **nothing** in production code.
- The dedup delegates to `review_result_from_state`; the false docstring is gone; reducer docstring reconciled.
- Boundary guard flags the synthetic bypass and passes on the real tree; teeth test present.
- 5-case parity tests green. `ruff`/`mypy` clean, zero new suppressions. Full `tests/status/` + `tests/architectural/test_status_module_boundary.py` + `tests/post_merge/test_review_artifact_consistency.py` green.

## Reviewer Guidance
Verify the guard-widening is submodule-name-targeted (not a blanket startswith) via the two-way teeth test. Verify the dedup return-type adaptation preserves all 5 cases. Confirm the cc=13 extract landed before the migration branch and the three do-not-touch functions are untouched.
