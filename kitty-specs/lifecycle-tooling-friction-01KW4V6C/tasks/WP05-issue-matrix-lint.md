---
work_package_id: WP05
title: Issue-matrix finalize-tasks lint
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1781861"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/review/
create_intent:
- tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/review/_issue_matrix.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Issue-matrix finalize-tasks lint

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- `finalize-tasks` emits an **advisory, never-blocking** lint of `issue-matrix.md` (one-table / closed-verdict / deferred-needs-handle / mandatory-columns) reusing the **same** rule engine the approve gate uses — one engine, two callers.
- `validate_issue_matrix` is ALREADY exported (`review/__init__.py`) and used by the approve gate; the finalize call-site imports that existing symbol — no new export, no rule reimplementation, no drift. The completeness "row-for-every-`#ref`" scan (in `agent/tasks_parsing_validation.py::_issue_matrix_evaluation`) is OUT of scope.
- A malformed matrix is flagged at `finalize-tasks` (advisory); a valid one is silent. Finalize is never blocked by the lint.
- **SC-005** is satisfied. `ruff` + `mypy` clean.

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 5, FR-009, SC-005, Edge Cases (lint is advisory).
- Plan: [plan.md](../plan.md) — IC-05.
- Research: [research.md](../research.md) — `validate_issue_matrix` enforces one-table / closed-verdict / deferred-needs-handle / mandatory-columns only; errors are already structured (`:226`, `:342`). The "row for every `#NNNN`" rule does NOT exist here — it lives in the approve-gate spec-scan.
- **NFR-002 — ONE rule engine, TWO callers**: do NOT reimplement the rules in `mission_finalize.py`; import and call the existing engine.
- **debbie's note + research open question 2 (resolved: completeness OUT of scope)**: the "row-for-every-`#ref`" completeness rule is NOT in `validate_issue_matrix` — it lives in `agent/tasks_parsing_validation.py::_issue_matrix_evaluation` (private). This WP binds to `validate_issue_matrix` ONLY; do NOT cross-import the private completeness symbol. If completeness is later added to the finalize lint, `tasks_parsing_validation.py` must first be added to `owned_files` and the scan factored into a shared pure helper (no import cycle). Record this boundary in the PR.
- **C-006 — red-first** through `finalize-tasks` with a malformed matrix.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T013 – RED test: advisory lint at finalize, silent when valid

- **Purpose**: Reproduce #2223's "correct-but-late" gap through the pre-existing surface.
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py`.
  2. Seed a realistic mission with a malformed `issue-matrix.md` (e.g. two tables / open verdict / deferred without a handle); run `finalize-tasks`; assert a non-blocking advisory naming the violated rule is emitted AND finalize still succeeds (exit 0).
  3. Add a valid-matrix case; assert no advisory and finalize succeeds silently.
  4. Confirm RED against current code (no lint at finalize time).
- **Files**: `tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py` (new — in `owned_files` + `create_intent`).
- **Parallel?**: Parallel-safe with WP01/WP02/WP04/WP06.
- **DoD — prove "same engine" by CALL IDENTITY, not message strings**: spy/monkeypatch the existing `validate_issue_matrix` and assert the finalize path actually invokes that exact callable (e.g. patch it and assert it was called with the matrix). Do NOT prove engine-sharing by matching rendered message/identifier strings — string matching passes even for a copied rule set and is the drift-masking anti-pattern.

### Subtask T014 – Expose the engine + advisory call-site at finalize

- **Purpose**: Wire the existing engine into a second (advisory) caller.
- **Steps**:
  1. **No new export work**: `validate_issue_matrix` is ALREADY exported (`src/specify_cli/cli/commands/review/__init__.py`) and consumed by the approve gate. Import that existing symbol — do NOT add a new export or wrap it.
  2. In `src/specify_cli/cli/commands/agent/mission_finalize.py`, add an advisory lint call-site at `finalize-tasks` that imports and calls the existing `validate_issue_matrix` and surfaces findings WITHOUT raising/blocking (warn-level output only).
  3. Do NOT reimplement any rule; the finalize caller only invokes + renders.
- **Scope binding**: this WP covers **`validate_issue_matrix` only** — the stated tests (two-tables / open-verdict / deferred-without-handle / mandatory-columns) are fully covered by it. The completeness / "row-for-every-`#ref`" scan lives in `src/specify_cli/agent/tasks_parsing_validation.py::_issue_matrix_evaluation` (a private symbol) and is **OUT of scope**: do NOT cross-import it. If a later decision pulls completeness into the finalize lint, that file must first be added to this WP's `owned_files` — it is not in scope here.
- **Files**: `agent/mission_finalize.py` (the call-site). `review/_issue_matrix.py` remains owned for reference but needs no export change.
- **Parallel?**: After T013 red.
- **Notes**: Keep the finalize path's added branch ≤ 15 complexity. No completeness-scan factoring in this WP (see Scope binding); record that boundary in the PR (research open question 2).

## Test Strategy

- New test: `tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py`.
- Red-first via `finalize-tasks` with a malformed matrix.
- Assert advisory (exit 0, warning emitted) AND engine-sharing by CALL IDENTITY (spy/monkeypatch `validate_issue_matrix` and assert the finalize path invokes it), not by matching message strings.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py -q`.
- Realistic matrix fixtures (C-007).

## Risks & Mitigations

- **Rule drift**: import the existing engine; a copied rule set is the exact anti-pattern (NFR-002) — assert shared rule identity in the test.
- **Accidentally blocking finalize**: the lint must be advisory; assert finalize exits 0 even with a malformed matrix.
- **Import cycle** when factoring the completeness scan: extract a pure shared helper rather than cross-importing command modules; document the decision.

## Review Guidance

- Confirm the finalize lint calls the SAME already-exported `validate_issue_matrix` engine the approve gate uses, proven by call identity (spy/monkeypatch) — no new export, no duplication, completeness scan not cross-imported.
- Confirm the lint is advisory — finalize never blocks on it.
- Confirm the malformed-matrix case warns and the valid case is silent.
- Confirm the completeness-scan scoping decision is recorded if touched; `ruff`/`mypy` clean, complexity ≤ 15.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:23:52Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Assigned agent via action command
- 2026-06-27T16:36:14Z – user – shell_pid=1735250 – Claiming WP05 for finalize-tasks advisory lint
- 2026-06-27T16:36:25Z – user – shell_pid=1735250 – Implementing finalize-tasks advisory issue-matrix lint
- 2026-06-27T16:38:08Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Ready: finalize-tasks advisory-flags malformed matrix via existing engine (call-identity asserted); valid matrix silent; never blocks finalize
- 2026-06-27T16:39:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=1781861 – Started review via action command
- 2026-06-27T16:42:05Z – user – shell_pid=1781861 – Review APPROVE (reviewer-renata, isolated): advisory finalize-tasks lint reuses exported validate_issue_matrix (true call-identity), never blocks (incl. engine-raises test), no reinvention/re-export/cross-import; mypy errors pre-existing; one justified noqa:BLE001 advisory-never-blocks
