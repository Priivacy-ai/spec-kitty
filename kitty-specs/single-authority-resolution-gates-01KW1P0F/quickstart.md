# Quickstart — Validating Single-Authority Resolution Gates

Each scenario maps to a Success Criterion and is the acceptance proof for its IC.

## SC-001 — The implement/review loop is unblocked (#2154, IC-04)
1. On a mission under coordination topology, mark a WP's subtasks done: `spec-kitty agent tasks mark-status T001 T002 … --status done`.
2. Advance it: `spec-kitty agent tasks move-task WP## --to for_review`.
3. **Expect**: the WP advances. **Before the fix** it fails with phantom "unchecked subtasks" (the write landed in coord, the validator read primary).

## SC-002 — A status transition commits under coordination topology (#2155, IC-04)
1. Trigger a status transition that stages a coordination-owned status write from the repo root.
2. **Expect**: the commit succeeds. **Before the fix** it raises `SafeCommitPathPolicyError` (the `.worktrees/` blanket refusal). A deliberately wrong-surface write is still refused.

## SC-003 — A future bypass fails CI (IC-02 / IC-03 self-tests)
1. Run the gate suite: `pytest tests/architectural/test_resolution_authority_gates.py -q`.
2. The in-test self-mutation proofs inject a bypass and assert the gate goes RED, then revert and assert GREEN — for **both** discriminators (un-canonicalized handle → blind primitive; kind-blind mandated write).
3. **Expect**: green (the self-tests prove the gates are non-vacuous).

## SC-004 — Zero un-sanctioned bypassing sites
1. Run the gates against `src/`.
2. **Expect**: green — every one of the ~34 `primary_feature_dir_for_mission` bare-handle sites and the coord-authority write sites is either routed through the canonical authority or carries a rationale'd allowlist entry. The allowlist count is non-increasing vs the mission start (shrink-only).

## SC-005 — Convergence across handle forms (FR-006, IC-05)
1. Run the convergence test: `pytest tests/missions/test_*_convergence.py -q` (uv-run if events 6.1.0 matters).
2. **Expect**: for every handle form (full slug, `<slug>-<mid8>`, bare mid8, ULID, numeric) the read-seam dir equals every write/placement-seam dir; ambiguous handles raise `MissionSelectorAmbiguous`; cold-miss fails closed. Stub-driven — no live `kitty-specs/` fixtures.

## SC-006 — Test-hygiene folds (FR-007/008, IC-06)
1. `pytest tests/architectural/test_no_tmp_paths_in_tests.py -q` → green (no literal `/tmp/` in test files).
2. Confirm the mission-owned `contract` test files (`test_mark_status_input_shapes.py`, `test_mark_status_pipe_table.py`) carry a CI-selected marker and run in a fast shard.

## Full gate sanity (pre-merge)
```bash
PYTHONPATH=$PWD/src TERM=dumb NO_COLOR=1 pytest tests/architectural/ -q -p no:cacheprovider
```
The two new gates + the existing surface-resolution gates all green; the canonicalizer + coord-authority allowlists carry only live, rationale'd entries.
