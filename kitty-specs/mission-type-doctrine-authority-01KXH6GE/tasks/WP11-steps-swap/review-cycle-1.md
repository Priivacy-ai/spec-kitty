# WP11 Review — Cycle 1 (REJECT)

Reviewer: reviewer-renata (opus). Lane: lane-k. HEAD: `f27d08c5d`.

## Verdict: CHANGES REQUESTED — one blocking test failure

The core of WP11 is correct and well-executed (see "What passed" below). It is
rejected on a single, deterministic red test that WP11 introduced and left
unaddressed. This is a proof-trail miss: the implementer activity log claims
"3123 passed, 1 skipped", but `tests/charter` is red at HEAD.

---

## Blocking Issue 1 — WP11 leaves a stale, RED bundle-slot test

`tests/charter/test_resolved_mission_type_context.py::TestResolverHardFailPolicies::test_reserved_slots_are_unpopulated`
fails deterministically at HEAD (confirmed standalone and in a full `tests/charter`
run: **1 failed, 1538 passed, 1 skipped**):

```
tests/charter/test_resolved_mission_type_context.py:154: in test_reserved_slots_are_unpopulated
    assert bundle.step_contracts == []
E   AssertionError: assert ['implement', 'plan', 'review', 'specify', 'tasks'] == []
```

Root cause: WP03 authored this test (commit `b5b407c47`) when `step_contracts`
was a *reserved* (empty) slot; its docstring literally reads
`"...template_set + step_contracts (WP11) are reserved"` and it asserts
`bundle.step_contracts == []`. WP11's entire purpose is to **populate** that slot
from the doctrine artefact — which now correctly returns the five software-dev
step IDs. The production change is right; the test assertion is now stale and was
not updated in the same commit.

This is a valid-test-guarding-old-behaviour case per the failing-test
remediation framework: the assertion encoded the pre-WP11 contract, and WP11
changed the contract on purpose. Remediation is to re-pin the test, not to touch
production.

### Required fix (in `tests/charter/test_resolved_mission_type_context.py`)
1. Drop the `assert bundle.step_contracts == []` line from
   `test_reserved_slots_are_unpopulated` (lines 148–154).
2. Keep the two still-reserved slot assertions
   (`expected_artifacts is None`, `template_set is None`) — those remain reserved
   until WP10 / a later slice.
3. Update the docstring to remove `step_contracts (WP11)` from the "reserved"
   list (leave `expected_artifacts (WP10)` and `template_set`).
4. Add a positive assertion that the slot is now populated for software-dev,
   e.g. `assert set(bundle.step_contracts) == {"specify", "plan", "tasks",
   "implement", "review"}` (or split into a dedicated
   `test_step_contracts_slot_is_populated`), so the bundle-level wiring is pinned
   at the seam — not only in the doctrine-unit test.
5. Re-run `uv run pytest tests/charter tests/doctrine tests/runtime -q` and
   confirm green before moving back to review. Record the real result in the
   activity log (the previous "3123 passed" claim did not include this red).

Note: editing this WP03-authored test is within reasonable ownership leeway —
WP11 already (correctly) edits the charter seam
`src/charter/mission_type_profiles.py` outside its declared `owned_files`, and
updating the seam's own test to match the new contract is the same seam.

---

## What passed (for the re-review — do not redo)

- **FR-008 / bundle routing**: `_resolve_step_contracts_slot` in
  `mission_type_profiles.py` sources the slot from
  `doctrine.missions.step_contracts.resolve_step_contract_ids`, mirroring
  `_resolve_action_slot` exactly (same `is_registered` guard → `[]` for tolerated
  overrides). C-001 preserved: lazy `charter → doctrine` import, no `specify_cli`
  reach. Tolerant/strict policy intact.
- **Doctrine-native resolver**: `get_by_mission` + `resolve_step_contract_ids`
  are the single doctrine answer, action-ordered (NFR-007), with an injectable
  repository for tests. Live callers exist (charter seam), so not dead code.
- **SC-007 grep-0 (verified)**: no `specify_cli` module independently resolves a
  type's step set.
  `grep -rn "get_by_mission\|resolve_step_contract\|steps_for\|step_set\|resolve_steps" src/specify_cli/`
  → **0 hits**. Every `specify_cli` step-contract reference imports the canonical
  `doctrine.missions.step_contracts` (directly or via the pure re-export facade
  `charter.mission_steps`); none is a copy. The implementer's "no specify_cli
  COPY existed" claim holds.
- **C-002 parity scaffold deleted (verified)**: the transitional scaffold
  `tests/doctrine/mission_step_contracts/test_wp11_transitional_step_parity.py`
  is NOT tracked and NOT on disk (`git ls-files` → not tracked; `find` → absent).
  Only a git-ignored `__pycache__/*.pyc` remains, proving it ran then was
  removed within the working tree before the single WP11 commit. No surviving
  parity ratchet.
- **Gates on WP11's own code**: `ruff check` on all three files → clean.
  `mypy --strict` on WP11's new code (`step_contracts.py`,
  `_resolve_step_contracts_slot`) → clean. The two `no-any-return` errors at
  `mission_type_profiles.py:427,431` are **pre-existing WP03** (blamed to
  `b5b407c47`, untouched by WP11's `f27d08c5d`) — not WP11's responsibility.
- New doctrine unit tests
  (`tests/doctrine/mission_step_contracts/test_step_contract_resolution.py`)
  are non-vacuous and exercise the real production path (deterministic ordering,
  unknown-type-empty, default-repo shipped read).

Fix Issue 1 and re-run the three suites green; everything else is approvable.
