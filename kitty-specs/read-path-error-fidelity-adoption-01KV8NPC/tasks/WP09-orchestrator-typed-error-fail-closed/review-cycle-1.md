# WP09 Review — Cycle 1 (reviewer-renata)

## Verdict: REJECT — one blocking finding (incomplete contract edit breaks the contract-sync gate)

The M2/M3 code fix is **correct and well-executed** (see "Verified correct" below). The single
blocker is that the out-of-owned-files contract edit (item 4) was applied to **only one of the two
copies** the repo keeps in sync, so it introduces a NEW test regression. DoD requires "Full suite
green"; it is not.

---

## BLOCKER 1 — `upstream_contract.json` edit not propagated to the authoritative planning artifact

WP09 added `STATUS_READ_PATH_NOT_FOUND` to the **vendored** contract
`src/specify_cli/core/upstream_contract.json` (`orchestrator_api.allowed_error_codes`). That is the
right code and the right list — but the vendored file is a **synced copy** of an authoritative
planning artifact, and a contract gate asserts the two are byte-equal (after `json.loads`):

- `tests/specify_cli/core/test_contract_gate.py::test_vendored_contract_matches_planning_artifact`
  compares the vendored `upstream_contract.json` against
  `kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json`.

WP09 edited the vendored copy but did NOT edit the planning artifact, so the test now FAILS:

```
FAILED tests/specify_cli/core/test_contract_gate.py::test_vendored_contract_matches_planning_artifact
  Differing items: allowed_error_codes ... 'MISSION_NOT_FOUND', 'STATUS_READ_PATH_NOT_FOUND' (vendored)
                                    !=     ... 'MISSION_NOT_FOUND', 'WP_NOT_FOUND'            (planning artifact)
```

Attribution is unambiguous (this is NOT pre-existing):
- On base (`9a5e6ffc8^`): vendored copy has 0 hits of the code, planning artifact has 0 -> match -> PASS.
- On the lane: vendored copy has the code, planning artifact still has 0 -> mismatch -> FAIL.

This also contradicts the Activity Log's "suites green (1684 passed)" claim — the contract-gate test
was not in that run (or pre-dated the contract edit). Re-run the full suite before declaring green.

### Fix (minimal, ~1 line)
Add `"STATUS_READ_PATH_NOT_FOUND"` to `orchestrator_api.allowed_error_codes` in
`kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json` (line 34),
in the **same position** as the vendored copy — immediately AFTER `"MISSION_NOT_FOUND"` (array equality
is order-sensitive; `json.loads` of two lists must match element-for-element). The planning artifact
is single-line-array format; preserve that format (the byte/format difference is fine — the test
compares parsed JSON, so only ordering+content matter).

Then re-run:
`python -m pytest tests/specify_cli/core/test_contract_gate.py tests/contract/test_orchestrator_api.py -q`

---

## Verified correct (no further action needed on these)

- **M2 (FR-001), 8 endpoints, single seam:** the `StatusReadPathNotFound -> return None` flatten is
  removed; all 8 endpoints (mission_state, list_ready, start_implementation, start_review, transition,
  append_history, accept_mission, merge_mission) now route through the new `_resolve_mission_dir_or_fail`
  seam, surfacing the typed `error_code` + `coord_candidate`/`primary_candidate` while preserving the
  external envelope shape. Genuine not-found still emits `MISSION_NOT_FOUND` (regression-guarded by
  `test_genuine_not_found_still_emits_mission_not_found`, verified RED-then-GREEN).
- **M3 (FR-011) fail-closed SAFETY:** the empty-mid8 seed `resolve_mid8(slug, mission_id=None)` is gone;
  the real `mission_id` is read from primary `meta.json` via `_read_primary_meta` (the
  decision.py/context.py primitive, using the sanctioned `primary_feature_dir_for_mission`) and threaded
  so the `bool(mid8)` gate at `_read_path_resolver.py:352` arms.
- **Captured-red verified against base `commands.py`** (I re-ran the new tests with the base file):
  T041 = `DID NOT RAISE` (suppressed guard returned stale primary), T039 = `assert True is False`
  (endpoint returned `success:True` reading the stale primary on a coord topology — the exact M3 safety
  defect). Both genuinely RED on base, GREEN on the lane. T041 is pinned to the gate via
  `assert exc.mid8 == _MID8` (proves the guard fired on the REAL derived mid8, not the empty seed).
- **M5 caveat handled:** coord-declared topology with unprovable identity (empty mid8) raises
  `StatusReadPathNotFound` with correct kwargs — does NOT silently seed empty.
- **Legacy seeds untouched:** the only `mission_id=None` line removed in the WP09 commit is the M3
  status-read seed; the legacy `{slug}-{lane}` `_wt_path(..., mission_id=None, lane_id=...)` seeds (now
  at :590/:877) are absent from the diff entirely — byte-unchanged.
- **Refuted comment corrected** (not just deleted): the old "byte-identical / safe" rationalization is
  replaced with an accurate docstring explaining the `bool(mid8)` gate.
- **Topology-true fixture:** full 26-char ULID, real primary meta declaring `coordination_branch`,
  materialized coord worktree (via real `CoordinationWorkspace.worktree_path`) with empty mission dir.
- **ruff + mypy clean** on `commands.py` and the test module; no suppressions; complexity within ceiling.

## Anti-pattern checklist
1. Dead code: PASS (`_resolve_mission_dir_or_fail` + `_read_primary_meta` have 8 / 1 live callers).
2. Synthetic-fixture test: PASS (drives the real endpoint + seam; verified RED on base).
3. Silent empty return: PASS (M5 path fails closed with a typed raise, not a silent None).
4. FR coverage: PASS (FR-001 + FR-011 each have asserting tests).
5. Frozen surface: PASS.
6. Locked decision: PASS (no new resolver/authority/error type — C-001 honored).
7. Shared-file ownership: **FAIL** — the shared/synced contract was edited in only one of its two
   tracked locations, breaking the sync gate (Blocker 1).
8. Production fragility: PASS (the new `raise StatusReadPathNotFound` is the intended fail-closed path).
