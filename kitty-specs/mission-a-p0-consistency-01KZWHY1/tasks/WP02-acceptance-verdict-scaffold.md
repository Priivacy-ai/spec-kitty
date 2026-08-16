---
work_package_id: WP02
title: '#3231 — acceptance verdict special-cases only the empty scaffold placeholder'
dependencies: []
requirement_refs:
- FR-003
- FR-004
planning_base_branch: fix/mission-a-p0-consistency
merge_target_branch: fix/mission-a-p0-consistency
branch_strategy: Planning artifacts for this mission were generated on fix/mission-a-p0-consistency. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-a-p0-consistency unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
history:
- Created by /spec-kitty.tasks for mission-a-p0-consistency-01KZWHY1
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/matrix.py
create_intent:
- tests/acceptance/test_overall_verdict_scaffold.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/matrix.py
- tests/acceptance/test_overall_verdict_scaffold.py
- tests/regression/test_issue_3231_scaffold_pending_poisons_acceptance.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile: `/ad-hoc-profile-load python-pedro` (or
`spec-kitty agent profile show python-pedro`) and apply it. You are an **implementer**.

## Objective

`AcceptanceMatrix.overall_verdict` lets **any** `pending` row dominate, so a leftover
empty `finalize-tasks` scaffold placeholder blocks acceptance for a mission whose real
criteria all pass. Special-case **only the contentless empty placeholder** so it does
not block — while seeded-but-unauthored requirement rows and all-scaffold matrices
still stay `pending`.

## Context (root cause — verified against `main`)

- `src/specify_cli/acceptance/matrix.py::overall_verdict` (~:263): `if any(v == "pending" ...): return "pending"`.
- The scaffold builder writes the marker into **two** shapes:
  - empty placeholder: `criterion_id="AC-001"`, **`description == SCAFFOLD_TODO_MARKER`** (`matrix.py:531`), `pass_fail="pending"`.
  - seeded per-requirement rows: `criterion_id="FR-###"`, **real** `description="Verify FR-### is satisfied"`, marker only in **`notes`** (`matrix.py:517-520`), `pass_fail="pending"`.
- So `description == SCAFFOLD_TODO_MARKER` is the ONLY discriminator unique to the empty placeholder.

## Constraints

- **C-003**: discriminate on `description == SCAFFOLD_TODO_MARKER` — **never** on `notes == SCAFFOLD_TODO_MARKER` (would exempt real unauthored FR rows → false-accept through the accept gate) and **never** on `criterion_id == "AC-001"` (would exempt a genuine pending `AC-001`).
- `overall_verdict` stays a pure computed property (never persisted/merged).
- `SCAFFOLD_TODO_MARKER` becomes load-bearing in two directions (writer + verdict) — a future rename must touch both.

## Subtasks

### T005 — Scaffold-aware verdict

In `overall_verdict`, treat a criterion as an exempt empty placeholder iff
`description == SCAFFOLD_TODO_MARKER`. Exempt such rows from the pending-dominates
rule **only when at least one non-scaffold criterion exists**. If every criterion is
an empty placeholder (or there are no real criteria), the verdict stays `pending`.
Keep the existing `fail`/negative-invariant precedence unchanged (a `fail` still wins;
`still_present`/`verification_error` still `fail`; deferral logic untouched). Extract a
small `_is_empty_scaffold(criterion)` helper if it keeps complexity ≤ 15.

### T006 — Non-fakeable guard tests [P]

Add `tests/acceptance/test_overall_verdict_scaffold.py` driving `overall_verdict`
directly:
- real-all-pass + empty `AC-001` placeholder → **not** `pending`.
- **partial authoring**: 9 of 10 seeded FR rows `pending` (marker in `notes`, real `description`) + 1 `pass` → `pending`.
- **all-scaffold**: only seeded FR rows (marker in notes) → `pending`; and a single-row **empty-`AC-001`-only** matrix → `pending` (the "no non-scaffold criterion" branch).
- **real `AC-001`** (real `description`, `pending`, no marker) → `pending` (defeats a `criterion_id=="AC-001"` shortcut).

### T007 — Relocate the repro; canonicalize (NFR-005)

Move `tests/regression/test_issue_3231_scaffold_pending_poisons_acceptance.py` into
`tests/acceptance/`. Drop `@pytest.mark.regression`; add canonical marks from
`docs/context/testing-taxonomy.md`; rewrite the docstring as a permanent guard
(defect #3231 fixed; pins "scaffold placeholder does not poison a passing verdict").

### T008 — Touched-consumer check + gates

The verdict property auto-corrects all readers — run their suites, not just the fix's:
`gates_core.py`, `accept.py`, and **`cli/commands/agent/acceptance_verdict.py:285,350`**
(writes the computed verdict downstream). `ruff`/`mypy` clean. Targeted run:
`PWHEADLESS=1 .venv/bin/python -m pytest tests/acceptance/ -q` and the
acceptance-verdict command tests. **Mechanical regression-exit check** (the repro is *relocated*, so a dropped marker is the fakeable step): `pytest tests/ -m regression -k 3231` must select **nothing**.

## Branch Strategy

Planning base + merge target: `fix/mission-a-p0-consistency`. Worktree is per-lane from
`lanes.json`. Implement via `spec-kitty agent action implement WP02 --agent claude`.

## Definition of Done

- [ ] `overall_verdict` exempts only the empty placeholder (`description==MARKER`), guarded by "≥1 real criterion".
- [ ] All four guard cases pass (T006), incl. real-`AC-001`→pending and empty-only→pending.
- [ ] #3231 repro relocated to `tests/acceptance/`, marker dropped, canonical marks + guard docstring.
- [ ] `acceptance_verdict.py` + gate consumer suites green; `ruff`/`mypy` clean; no green `regression`-marked #3231 test.

## Risks / Reviewer guidance

- **Symmetric false-accept** is the danger — reviewer must confirm the discriminator is `description`, and that partial-authoring stays `pending`. A `notes`-based or `criterion_id`-based key is a rejection.
- Confirm the "≥1 non-scaffold criterion" guard: an all-scaffold matrix must never read `pass`.
