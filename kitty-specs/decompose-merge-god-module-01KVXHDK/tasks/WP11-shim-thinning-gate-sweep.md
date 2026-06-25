---
work_package_id: WP11
title: Shim thinning +
dependencies:
- WP10
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/merge.py
role: implementer
tags: []
task_type: implement
shell_pid: "3793737"
---

# Work Package Prompt: WP11 – Shim thinning + #2057 pointer comment + full gate sweep

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Decompose the `merge` command (CC71) into `_dispatch_abort`/`_dispatch_resume`/`_dispatch_dry_run`/`_run_real_merge` (each ≤15 CC); install the top-of-file #2057 decomposition pointer comment (FR-002, #2056/#1623 convention); finalize re-exports + `__all__` byte-stability; run the full gate sweep. SOLE owner of `cli/commands/merge.py`.

- Requirement refs: FR-001, FR-002, FR-005, FR-006, NFR-001, NFR-002, NFR-003.

## Context & Constraints

- Plan IC-11. By now every seam is relocated (WP02–WP10); `merge.py` should contain only the command + re-exports. Target ~120 LOC, maxCC ≤15. Pointer comment mirrors #2056/#1623.
- Strictly-linear chain: this WP depends only on its predecessor WP10.
- Ownership: this WP owns ONLY `src/specify_cli/cli/commands/merge.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T047 – Decompose the command
- **Steps**: Split the `merge` command body into `_dispatch_abort` / `_dispatch_resume` / `_dispatch_dry_run` / `_run_real_merge` helpers, each ≤15 CC (FR-005). The command becomes a thin dispatcher.

### Subtask T048 – Pointer comment
- **Steps**: Install the top-of-file decomposition pointer comment referencing #2057 (match the #2056/#1623 convention), listing the seam map and the shim's role (FR-002).

### Subtask T049 – Finalize re-exports
- **Steps**: Confirm all relocated symbols are re-exported and assert `__all__` ordering is byte-stable (FR-006/INV-4).

### Subtask T050 – Full gate sweep
- **Steps**: Run quickstart.md steps 0–6: golden test byte-identical, radon `-n B` shows ≤15 everywhere, ruff clean, mypy --strict clean, coverage ≥90% (NFR-001/002/003).

### Subtask T051 – Importer verification
- **Steps**: Verify the 3 src consumers (orchestrator_api/commands.py, agent/mission.py, doctor.py) + the ~41 importing test files pass with ZERO import edits (FR-006).

## Definition of Done

- `cli/commands/merge.py` ~120 LOC, maxCC ≤15, with the #2057 pointer comment.
- Golden test byte-identical; `__all__` ordering stable.
- radon ≤15 across shim + all seams; ruff + mypy --strict clean; coverage ≥90%.
- All importers green with zero edits.

## Risks & Mitigations

- `__all__` drift → assert exact ordering; the golden test is the final byte-identity gate.

## Reviewer Guidance

- Diff `__all__` against pre-refactor.
- Confirm the pointer comment matches the #2056/#1623 format.
- Run the full `-k merge` suite + architectural boundary tests.

## Activity Log

- 2026-06-24T23:59:09Z – claude:opus:randy-reducer:implementer – shell_pid=3762132 – Assigned agent via action command
- 2026-06-25T00:06:22Z – claude:opus:randy-reducer:implementer – shell_pid=3762132 – Shim thinning + gate sweep: merge command decomposed into thin dispatcher + _dispatch_abort/_dispatch_resume/_run_real_merge (+2 helpers), all <=15 CC (merge=15); #2057 pointer comment installed (FR-002, #2056/#1623 convention) with seam map; __all__ finalized byte-stable for contract symbols; merge.py 3383->559 LOC, maxCC<=15; golden CLI byte-identical; 3 src consumers + importers zero-edit green; 562 merge suite green; ruff C901 + mypy --strict clean.
- 2026-06-25T00:06:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=3793737 – Started review via action command
- 2026-06-25T00:06:41Z – user – shell_pid=3793737 – Review passed: merge command thinned to a dispatcher + abort/resume/real-merge helpers (all <=15 CC); abort/resume/real-merge moved verbatim (golden byte-identical, 562 suite green); #2057 pointer comment + seam map installed (FR-002); __all__ keeps contract symbols + seam re-exports (3 src consumers + importers zero-edit green); merge.py 3383->559 LOC, maxCC<=15; ruff C901 + mypy strict clean.
