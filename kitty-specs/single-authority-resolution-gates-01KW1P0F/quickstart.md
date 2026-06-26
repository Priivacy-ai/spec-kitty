# Quickstart — Validating Single-Authority Resolution Gates

Each scenario maps to a Success Criterion and is the acceptance proof for its IC.

## SC-001 — The implement/review loop is unblocked (#2154, IC-04)
1. On a mission under coordination topology, mark a WP's subtasks done: `spec-kitty agent tasks mark-status T001 T002 … --status done`.
2. Advance it: `spec-kitty agent tasks move-task WP## --to for_review`.
3. **Expect**: the WP advances. **Before the fix** it fails with phantom "unchecked subtasks" (the write landed in coord, the validator read primary).

## SC-002 — Mixed-bundle auto-commit, no silent drop (#2155, IC-04b)
1. Under coordination topology + an **unprotected** target branch, run `move_task WP## --to <lane>` (and the `implement`/claim path) so it auto-commits a primary WP file bundled with coord-owned status artifacts.
2. **Expect**: coord status lands on the coord surface, the WP file on primary, **no swallowed `SafeCommitPathPolicyError`**, tree clean. **Before the fix** the commit is silently skipped ("Auto-commit skipped" warning) and the activity-log update is dropped (dirty tree). A deliberately wrong-surface `.worktrees/` write staged from primary is **still refused** by the unchanged guard (`git/commit_helpers.py:983-991`).

## SC-003 — A future bypass fails CI (IC-02 / IC-03 self-tests)
1. Run the gate suite: `pytest tests/architectural/test_resolution_authority_gates.py -q`.
2. The in-test self-mutation proofs inject a bypass and assert the gate goes RED, then revert and assert GREEN — for **both** discriminators (un-canonicalized handle → blind primitive; kind-blind mandated write).
3. **Expect**: green (the self-tests prove the gates are non-vacuous).

## SC-004 — Zero un-sanctioned bypassing sites (routed by default)
1. Run the gates against `src/`.
2. **Expect**: green — every one of the **38** `primary_feature_dir_for_mission` sites and the coord-authority write sites is **routed** (default) or carries a rationale'd already-canonical allowlist entry; **≥ the bare-handle census is routed, not allowlisted**; the allowlist count is ≤ the **pre-sweep baseline** (shrink-only, no inflate-then-freeze).

## SC-005 — Convergence across handle forms (FR-006, IC-05)
1. Run the convergence test: `pytest tests/missions/test_*_convergence.py -q` (uv-run if events 6.1.0 matters).
2. **Expect**: for every handle form (full slug, `<slug>-<mid8>`, bare mid8, ULID, numeric) the read-seam dir equals every write/placement-seam dir; the stub returns **distinguishable** per-form outputs (a constant-return stub is rejected); ambiguous handles raise `MissionSelectorAmbiguous`; cold-miss fails closed; a **negative-control** form (divergent under pre-fix code) proves the test is red-first. Stub-driven — no live `kitty-specs/` fixtures.

## SC-006 — Test-hygiene folds (FR-007/008, IC-06)
1. `pytest tests/architectural/test_no_tmp_paths_in_tests.py -q` → green; injecting a **new** `/tmp/` literal in a test file turns it RED (frozen-baseline ratchet, ~82 baseline; the full litter sweep is out of scope).
2. FR-008: a before/after `pytest --collect-only -m <shard>` diff confirms the mission-owned target files are collected. **If the originally-named files already run (audit indicates they do), this is satisfied-by-verification — no redundant marker added.**

## Full gate sanity (pre-merge)
```bash
PYTHONPATH=$PWD/src TERM=dumb NO_COLOR=1 pytest tests/architectural/ -q -p no:cacheprovider
```
The two new gates + the existing surface-resolution gates all green; the canonicalizer + coord-authority allowlists carry only live, rationale'd entries.
