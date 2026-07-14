---
work_package_id: WP07
title: Lane-enum golden count → exact frozenset (flagship exemplar)
dependencies: []
requirement_refs:
- FR-006
- FR-016
- NFR-002
tracker_refs:
- '2076'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/status/test_models.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/status/test_models.py
role: implementer
tags: []
shell_pid: "2954148"
shell_pid_created_at: "1783952615.6"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-006 +
[data-model.md](../data-model.md) E-04, and [plan.md](../plan.md) §IC-05. This WP is the **exemplar
pattern** WP11 (and its batches WP12–WP14) reference — get the shape right.

## Objective

Replace the stale golden-count `len(Lane) == N` in `tests/status/test_models.py` with an assertion on the
**exact frozenset of `Lane` member names**, and rename the test off its "…nine_values" name. Adding or
removing a lane must force a content edit, not a silent count bump.

## Context

- The 9-lane state machine is the canonical model (see project status-model docs): `planned → claimed →
  in_progress → for_review → in_review → approved → done`, plus `blocked` and `canceled`.
- `len(Lane) == 9` is brittle: a rename that preserves cardinality passes silently; a real add/remove only
  moves a number with no name-level record. The frozenset assertion pins the *contract* (the exact names).

## Subtask guidance

- **T029 — frozenset assertion.** Replace `len(Lane) == N` with
  `frozenset(m.name for m in Lane) == { ...exact names... }` (or the `.value`s if the value is the
  contract — assert names as the canonical identity). Import the exact expected set as a literal in the
  test so a lane change forces this line to change.
- **T030 — rename.** Rename the test function off "…nine_values" to a content-describing name
  (e.g. `test_lane_member_names_exact`). Update any `-k` selectors/refs if present.
- **T031 — green.** `.venv/bin/python -m pytest tests/status/test_models.py -q`.
- **T032 — gates + tracer.** `ruff`/`mypy` clean; append the tracer row and note this is the exemplar
  pattern for WP11.

## Branch Strategy

Lane A root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`. **Precedes/anchors WP11** — WP11 declares a dependency on this WP so
the exemplar pattern exists before the sweep.

## Definition of Done (non-fakeable — NFR-002)

- [ ] `tests/status/test_models.py` asserts the exact `Lane` member-name frozenset (no `len(Lane) == N`).
- [ ] The test is renamed off "…nine_values".
- [ ] Adding/removing a lane forces a content edit to the expected set (demonstrated by reasoning in the
      review, not a live mutation).
- [ ] `tests/status/test_models.py` green.
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for this golden-count→content conversion (the exemplar) +
      friction log.

## Risks

- **Asserting the wrong identity** — assert on member *names* (stable canonical identity), not on ordering
  or a re-derived count.

## Reviewer guidance

- Confirm the assertion is an exact frozenset (not a superset/subset) and the "nine" naming is gone.
- Confirm this shape is clean enough to be the WP11 exemplar.

## Activity Log

- 2026-07-13T14:12:40Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:23:01Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Ready for review: Lane enum golden-count -> exact member-name frozenset (exemplar for WP11 sweep)
- 2026-07-13T14:23:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=2954148 – Started review via action command
- 2026-07-13T14:36:42Z – user – shell_pid=2954148 – Review passed on merits
