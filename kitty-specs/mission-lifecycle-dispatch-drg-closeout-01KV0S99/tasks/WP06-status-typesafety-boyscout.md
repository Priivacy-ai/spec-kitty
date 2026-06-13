---
work_package_id: WP06
title: 'Type-safety boyscout: status/ package mypy --strict clean'
dependencies: []
requirement_refs:
- NFR-002
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2880737"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (boyscout IC-11 added post-review)
agent_profile: ''
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/status/__init__.py
- src/specify_cli/status/progress.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Type-safety boyscout: status/ package mypy --strict clean

## ⚡ Do This First: Load Agent Profile

Load your assigned implementer profile (recommended `python-pedro`) via the profile-load skill —
governed context, not a bare name — before reading further.

## Objectives & Success Criteria

Clear the pre-existing `mypy --strict` debt on the un-owned `status/` files so the whole package is
strict-clean (SC-6), **behavior-preserving**.

- After this WP (+ WP01's `lifecycle_events.py` and WP02's `views.py` fixes), `mypy --strict
  src/specify_cli/status/` exits 0.
- No logic/behavior change — type annotations, casts, narrow guards, removing unused ignores only.
- The existing `status/` test suite stays green (no test weakened or deleted).

## Context & Constraints

- Read: `plan.md` (IC-11), `spec.md` (SC-6, NFR-002).
- **Surface scan (2026-06-13) found 17 strict errors on these files:** `emit.py` (10), `aggregate.py`
  (4), `status/__init__.py` (2), `progress.py` (1). `invocation/` is already clean (0).
- **Ownership:** do NOT touch `lifecycle_events.py` (WP01) or `views.py` (WP02) — they clear their
  own strict errors under NFR-002. This WP owns only the four files above.
- **`emit.py` is critical-path** (the status-event emit pipeline: validate → persist → materialize →
  views → SaaS). Fixes MUST be type-only and behavior-preserving. Do NOT change control flow, error
  handling, or the emit contract. If a "fix" would require a logic change, STOP and flag it rather
  than alter behavior.
- **Scope discipline:** bounded to `status/`. Do NOT expand into the project-wide charter/doctrine
  mypy debt (out of scope). No blanket `# type: ignore` / per-file ignore additions to pass the gate
  (CLAUDE.md) — fix the code; narrowly-scoped justified ignores only when the checker is genuinely wrong.

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T024 – Baseline
- Run the `status/` test suite (`pytest tests/specify_cli/status/`) — confirm green BEFORE changes.
- Enumerate the 17 errors: `mypy --strict src/specify_cli/status/emit.py src/specify_cli/status/aggregate.py src/specify_cli/status/__init__.py src/specify_cli/status/progress.py`.

### T025 – emit.py (10 errors)
- Fix each strict error type-only (annotations, return types, `cast`, narrowing). Common shapes:
  `no-any-return`, `arg-type` (e.g. str vs datetime|None — coerce/annotate at the boundary, do not
  change what is persisted), unused-ignore removal. Behavior-preserving — verify against the emit
  pipeline contract.

### T026 – aggregate.py + __init__.py + progress.py (7 errors)
- Same approach: type-only fixes. For `status/__init__.py` (re-export surface) ensure `__all__` /
  typed re-exports are correct without changing the public API.

### T027 – Verify SC-6
- Run `mypy --strict src/specify_cli/status/` → expect 0 errors (your four files clean; the WP01/WP02
  files clean in their lanes — if those lanes haven't merged yet, confirm your four files contribute 0
  and note the residual is WP01/WP02's). Re-run `pytest tests/specify_cli/status/` → green. Paste both
  commands + exit codes into the handoff note.

## Test Strategy

- No new feature tests (behavior-preserving). The pin is: existing `status/` suite stays green AND
  `mypy --strict` on the four files = 0. Diff-scoped `ruff check` on touched files (exit 0).

## Definition of Done

- The four files are `mypy --strict` clean; status suite green; zero behavior change; no weakened
  tests; no blanket ignores added. (Whole-package SC-6 completes once WP01/WP02 also land.)

## Risks

- Changing `emit.py` behavior while "fixing types" (forbidden — type-only). Scope creep beyond
  `status/`. Masking an error with `# type: ignore` instead of fixing it.

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Verify every change is type-only/behavior-preserving (especially
  `emit.py`), the status suite is unchanged-and-green, no blanket ignores were added, and scope stayed
  within the four owned files.

## Activity Log

- 2026-06-13T16:57:38Z – claude:sonnet:python-pedro:implementer – shell_pid=2767258 – Assigned agent via action command
- 2026-06-13T17:09:14Z – user – shell_pid=2767258 – Moved to claimed
- 2026-06-13T17:09:19Z – user – shell_pid=2767258 – Moved to in_progress
- 2026-06-13T17:10:52Z – user – shell_pid=2767258 – Moved to claimed
- 2026-06-13T17:10:56Z – user – shell_pid=2767258 – Moved to in_progress
- 2026-06-13T17:11:22Z – claude:sonnet:python-pedro:implementer – shell_pid=2767258 – DONE: mypy --strict 0 errors on 4 files; 318 tests green (exit 0); ruff clean (exit 0). Behavior-preserving cast() at follow_imports=skip boundaries. No logic change in emit.py critical path.
- 2026-06-13T17:14:27Z – claude:sonnet:python-pedro:implementer – shell_pid=2767258 – Ready: 4 status/ files mypy --strict clean via rationale-backed casts (follow_imports=skip boundary); status suite 318 green; behavior-preserving
- 2026-06-13T17:15:10Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2835611 – Started review via action command
- 2026-06-13T17:19:55Z – user – shell_pid=2835611 – Moved to planned
- 2026-06-13T17:23:10Z – claude:sonnet:python-pedro:implementer – shell_pid=2864175 – Started implementation via action command
- 2026-06-13T17:25:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2864175 – cycle1: emit.py cast rationale comments added; gates green
- 2026-06-13T17:26:15Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2880737 – Started review via action command
- 2026-06-13T17:27:48Z – user – shell_pid=2880737 – cycle1 verified (re-review cycle2): emit.py cast rationale comment added (comment-only, 4 insertions 0 deletions); mypy --strict 4 files exit 0; pytest 318 passed exit 0; ruff exit 0. Cycle-1 sole blocker resolved.
