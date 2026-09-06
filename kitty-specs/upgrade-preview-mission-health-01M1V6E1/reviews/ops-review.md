# Supporting Operation Reviews

Audience: agentic-framework-core-team. Updated: 2026-09-06.
These are bounded workflow/test repairs, not completion of #3900-#3903.
Detailed friction and raw command logs remain in the operator's external ledger.

## Runtime Artifact Authority (#3910)

- Op: `01M1V7FE092RMCWE96F6191SF3`.
- Implementer: Python Pedro; independent reviewer: Debugger Debbie.
- Initial red commit: `f223fd6ab`; initial fix: `163f0f000`.
- First review rejected an owned-checkout false approval using root-only decoys.
- Owned-checkout red commit: `7d6f22658`; corrected fix: `158e62aa9`.
- Source/test scope: `src/runtime/next/runtime_bridge_io.py` and
  `tests/runtime/test_artifact_presence_placement.py`.
- Final independent verdict: APPROVE. Nineteen focused cases passed; separate
  real-worktree probes rejected root-only spec/plan decoys through both guards
  and accepted owned-only artifacts. Normal coord authority remains unchanged.
- Implementer reported 137 focused follow-up passes and clean Ruff/mypy.
- Parent integrated with cherry-pick provenance. Original supported
  `next --agent codex --mission upgrade-preview-mission-health-01M1V6E1
  --result success --json` retry exited 0, returned `kind: step`, `step_id: plan`,
  and an empty guard_failures list. No artifact copying or status fabrication.

## Pair-Arity Classification (#3458 Recurrence)

- Op: `01M1V8WKCPN7KZT629FP57NA2X`.
- Implementer: parent under Python Pedro; independent reviewer: Mill under
  Reviewer Renata (distinct from the implementing parent).
- Commit: `c3657a86a`, preserving original `78ad0b6a` provenance.
- Scope: two comment lines in `tests/architectural/test_ratchet_baselines.py`.
  Tuple arity remains asserted; the existing documented cardinality-contract
  annotation prevents misclassification as an enumerable-domain count.
- Original full golden-count gate was RED (15 sites versus ceiling 14);
  isolated pre-edit witness: one failure. No new artificial regression needed.
- Green: both affected test files, 33 passed in 58.28s; Ruff/mypy clean.
- Independent verdict: APPROVE. Executable AST and baseline files unchanged;
  original pair growth/shrink cases passed and six malformed-pair controls
  still rejected invalid shapes. Broader classifier-policy issue #3458 remains
  open; this operation does not choose its deferred policy redesign.

## Integrated Verification

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 CI=true PYTEST_ADDOPTS= PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/pytest -q -n0 \
  tests/runtime/test_artifact_presence_placement.py \
  tests/architectural/test_golden_count_ban.py \
  tests/architectural/test_ratchet_baselines.py -p no:cacheprovider
```

Exit 0: **52 passed in 57.81s**, at `c3657a86a`.
The full pre-integration architecture sweep had two reported failures, not a
green baseline. Archive preservation #3911 remains unresolved; final mission
gates must execute on the eventual integrated implementation.

## Open Prerequisite Operations

- `01M1V9DJH0BQGR18AZ838K4VPZ`: #3912 planning-artifact ancestry correction,
  isolated implementation and independent review pending.
- `01M1V9DM1GNCDPRJ9R9ADP1PCS`: E2E repository #411 contract-drift harness,
  isolated cross-repository implementation and independent review pending.

Neither is claimed complete or passing. Their final evidence and separate E2E
PR link must be included in the publication handoff.
