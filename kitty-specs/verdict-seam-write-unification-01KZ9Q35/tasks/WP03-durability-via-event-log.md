---
work_package_id: WP03
title: Durability via the event log — emit_status_transition authoritative write
dependencies:
- WP02
requirement_refs:
- FR-008
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/emit.py
create_intent:
- tests/status/test_emit_durability.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/emit.py
- tests/status/test_emit_durability.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Make `emit_status_transition` the **authoritative** durability write for a recorded verdict — an
append on `status.events.jsonl` (union-merge-driver protected), so concurrent verdicts union rather
than clobber. **Keep the `review-cycle-N.md` commit a hard-error here** — the demote to best-effort is
WP05 (D-PLAN-11), which lands with the reader flip. This closes the `p#3044/SC-004` lost-record defect
at its root: durability becomes an event append, not a bespoke per-file git commit.

## Context

- **Requirements**: FR-008 (durability via the event log; demote deferred to WP05); NFR-001 (**no
  inter-process lock across any `git` subprocess**), NFR-004 (exactly **one** authoritative durability
  call per verdict — the `.md` render commit excluded from the count), NFR-005 (verdict recording < 2 s);
  SC-003 (two concurrent distinct verdicts → two durable records or one explicit refusal).
- **Contract**: [contracts/verdict-durability-write.md](../contracts/verdict-durability-write.md) — G1
  single authoritative call, G2 concurrency (union), G3 no lock across git, G4 < 2 s.
- **FR-008 add-leg owner**: **this WP (T013)** is the sole authoritative-durability-write deliverable.
  WP02 no longer wires the recording path (squad F6); WP03 owns `emit.py` and makes the append the
  authoritative act. Note the append may already partially exist via the #3211 render path — verify and
  make it the *single authoritative* durable act, do not add a second.
- **Coordinate**: **`tests/integration/test_review_durability_matrix.py` is owned by WP05** — WP05
  re-points its SC-003/NFR-004 anchors to count **event** records not `.md` files (D-PLAN-13). Here,
  exercise durability through the new hermetic `test_emit_durability.py`; do not edit the WP05-owned
  matrix test.

## Subtasks

### T012 — Red-first: concurrency durability through `emit_status_transition`
- **Purpose**: SC-003 anchor at the emit seam. Two distinct verdicts appended concurrently must both be
  durable (union) or one explicitly refused — never a silent drop.
- **Steps**: In new `tests/status/test_emit_durability.py`, drive two `emit_status_transition`
  `review_result` appends for the same mission from separate processes (or a faithful concurrency
  harness); assert both slots survive in `read_events`/the reducer, or one raises an explicit refusal.
  Red-first against the pre-change per-file commit path.
- **Files**: `tests/status/test_emit_durability.py`.
- **Validation**: fails before T013; green after.

### T013 — Route verdict durability to the event-log append (authoritative)
- **Purpose**: FR-008 — make the append the single authoritative durable act.
- **Steps**: In `status/emit.py`, ensure the `review_result` transition persists via the append
  discipline (validate → persist → materialize → views), and that this append is the authoritative
  durability point. Reuse the canonical store/append machinery (C-001) — do not add a bespoke lock.
- **Files**: `src/specify_cli/status/emit.py`.
- **Validation**: T012 green; the reducer snapshot carries the verdict after the append alone.

### T014 — NFR-001 + NFR-004: no lock across git; exactly one authoritative call
- **Purpose**: Enforce the two durability NFRs structurally.
- **Steps**: Name the NFR-001 mechanism concretely (squad #13): in the test, **monkeypatch the lock
  context manager** used on the durability path and **`subprocess.run`** (and any `git` invoker), record
  the call order, and assert **no `git` subprocess is spawned while the lock is held** (the event-log
  append discipline is the serialization, not a spanning lock). Add an assertion that exactly **one**
  authoritative `emit_status_transition` append occurs per recorded verdict (NFR-004); the best-effort
  `.md` render commit is **excluded** from this count (still hard-error here, not the authoritative call).
- **Files**: `status/emit.py`, `tests/status/test_emit_durability.py`.
- **Validation**: the monkeypatched-order test asserts no `git` subprocess overlaps a held lock; append
  count == 1.

### T015 — NFR-005 responsiveness (< 2 s)
- **Purpose**: Keep verdict recording within the existing 2-second budget.
- **Steps**: Add / confirm a timing assertion for a single verdict record incl. durable persistence
  under 2 s. Coordinate with `tests/review/test_cycle.py` (the canonical perf surface named in the
  spec) — if the budget lives there, add the hermetic emit-level timing here and note the cycle-level
  budget is exercised by WP05's flip.
- **Files**: `tests/status/test_emit_durability.py`.
- **Validation**: `PWHEADLESS=1 pytest tests/status/test_emit_durability.py -q` green under budget.

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP03`. Serial in the census
chain by dependency (after WP02). Does **not** touch the census yaml. The SC-003 50×2-process matrix
runs serially (`-n0`) but is owned/re-pointed by WP05 — do not run it as your gate here.

## Definition of Done

- SC-003 at the emit seam: two concurrent distinct verdicts → two durable records or one explicit
  refusal (T012). NFR-001 (no lock across git), NFR-004 (one authoritative call), NFR-005 (< 2 s) each
  have a passing assertion.
- The `.md` commit remains **hard-error** (demote is WP05). Do not demote here.
- Gate: `PWHEADLESS=1 pytest tests/status/test_emit_durability.py tests/status/test_reducer.py -q`
  green; `ruff` + `mypy --strict src/specify_cli/status` clean (NFR-003).

## Risks

- **Premature demote** — if the `.md` hard-error is relaxed here, a best-effort render failure diverges
  the event log from the `.md` while WP05's readers still read the `.md`. Keep it hard-error.
- **Bespoke lock reintroduction** — the point is to *remove* the per-file-commit fragility; do not add a
  new inter-process lock (NFR-001).

## Reviewer guidance

Verify the authoritative durable act is the event append and that the `.md` commit is still hard-error.
Grep the durability path for lock-acquire around any `subprocess`/`git` call (NFR-001 — must be none).
Confirm you did not edit `tests/integration/test_review_durability_matrix.py` (WP05 owns the re-point).
