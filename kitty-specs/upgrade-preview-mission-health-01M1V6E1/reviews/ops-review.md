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

## Planning Workspace Ancestry (#3912)

- Op: `01M1V9DJH0BQGR18AZ838K4VPZ`.
- Implementer: Mill under Python Pedro; independent reviewer: parent under
  Reviewer Renata. Reviewer did not edit the implementation or tests.
- Integrated red: `71a76f497` (original `86d535f60`); green: `be5a58f55`
  (original `0c9dfabe2be235854dd1de584b50de585091c993`).
- Planning self-heal now selects the canonical root workspace, preserves the
  existing ancestry predicate and merges only approved dependency refs.
  Protected/dirty roots refuse mutation; ordinary lane behavior is unchanged.
- Independent verdict: APPROVE. Ten focused tests passed before integration
  and again after integration (36.50s), including rollback and idempotence.
- Inspected implementer evidence: 406 passed/1 skipped, Ruff/mypy clean;
  real E2E lifecycle scenario passed in 333.98s with 97 child records.
- Worker stopped on workspace credits after producing the reviewed patch.
  Parent preserved red-first history and committed/integrated unchanged code.
  Full final mission gates remain pending.

## Real Contract-Drift Witness (E2E #411)

- Op: `01M1V9DM1GNCDPRJ9R9ADP1PCS`.
- Separate PR: https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing/pull/414
- Red commit: `5fbe20dfdb4b319f12b5a5de792e9a36630a933e`;
  final fix: `24a72c2b43c0e89c4b0a1e05bc2f23fb72663e2b` in that repository.
- Real locked events distribution replaces the incomplete synthetic package.
  Unmodified envelope/consumer contracts run green, then only Event.event_id's
  required default is mutated in an isolated installed copy. The witness
  requires the exact intended assertion failure and restores original bytes.
- Initial parent review found bootstrap still inherited host environment.
  Distinct implementer completed explicit UV/stdlib environment forwarding,
  isolated cache/config roots and exact interpreter binding. Parent did not
  author code/tests; independent final inspection resolved this finding.
- Changed-contract and helper blast-radius tests: 30 passed; independently
  rerun by parent in0.09s. Real installed scenario:1 passed in23.08s, control
  29 passed; drift exactly1 identified failure/28 passed/no errors or skips.
  Parent independently checked XML identities and restored source SHA256.
- Offline owning-subsystem gate:285 passed,2 failed,3 skipped,362 deselected
  in113.05s. Both unrelated failures reproduced on untouched E2E baseline:
  2 failed,2 passed in6.52s. Filed E2E#412 (inherited resolver environment)
  and E2E#413 (unbounded raw-path expectation versus provenance byte cap).
  No baseline green claim, skipped coverage claim or test weakening.
- Optional Ruff advisories disclosed; mypy unavailable. Full CI and the single
  programme squad review belong to the existing CI/merge agents after handoff.
  PR is ready-for-squad, not locally squad-approved or merged. The current
  core mission's final five-case E2E floor still requires integrated execution.

## Contract-Drift Pass-One Correction

- Correction Op: `01M1VEJSZMGHJAE5C6G4SD0RY7`.
- PR414 correction head: `50d47d634123e865033762fd676db66a2043b454`.
  The original operation above records its historical initial handoff, not
  approval of this later correction or programme merge.
- Programme pass one identified Git-locked events8.0.0 unavailable through
  the previous PyPI-only install, an unsupported provenance import, and two
  reproduction commands missing explicit pytest plugin-autoload isolation.
- Distinct implementer fixed immutable registry/Git source selection and
  PEP610 source/commit verification, limited provenance imports to the selected
  Event model, and preserved existing trusted system Git transport while
  isolating user/global Git configuration. No new proxy or dependency change.
- Parent independently reviewed the fixed diff and ran 42 focused tests
  (0.17s). Owning offline suite: 297 passed, 2 known baseline failures
  (#412/#413), 3 skipped, 362 deselected in130.95s. No full-green claim.
- Public source c3657a86a/events9.1.6: scenario1 passed23.11s. Actual CI source
  e4a083107/events8.0.0: parent final-patch scenario1 passed29.81s using
  authenticated-read exact-commit local mirrors, not the remote CI platform.
  Both runs preserve identical29 control identities, exactly the intended
  required-field assertion failure plus28 passes after mutation, no errors or
  skips, and exact original-model restoration. No credentials copied to tests.
- Parent published the corrected five-section PR body with both Op IDs,
  executable reproduction, evidence limits and deferred gates. Verified new
  head and open PR; programme review is running. Old ci:green is not evidence
  for this head. Programme pass two, remote CI and merge remain external.
- Separate nested-checkout fixture gap filed E2E#416. Source selection is
  explicitly bound in these witnesses; missing prerequisite skips never count
  as completing acceptance. Static advisories and missing mypy remain disclosed.
- External evidence: `drift-harness-evidence/parent-pass1-review.md`,
  `pass1-fix-handoff.md`, `parent-pass1-ci-final*`, and `pr-body-pass1.md`
  under the timestamped workspace's parent directory. This operation closes
  only the tested correction handoff, not core mission acceptance or merge.

### Programme Merge and CI Coverage Limitation

Programme merged PR414 as `cb6939eb700f05845a8adf48546e11ab897182c2` after
pass-two squad review and exact-head CI at50d47d6. Reported full CI:
737 passed,6 skipped,371 deselected in1467.00s. However, the scenario leg
explicitly skipped contract_drift_caught.py because source checkout discovery
failed (four passed,one skipped). This confirms E2E#416 in the actual runner.
The remote green label does not prove execution of this changed witness.
Local explicit-source control/mutation evidence above remains distinct.
Final core mission E2E acceptance must bind the source and execute every
required floor case rather than count a missing prerequisite as coverage.
Evidence and follow-up:
https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing/issues/416#issuecomment-5560076553.

## Pre-review Identity Partition Repair

- Supporting Op: `01M1VKFGEXZEZK9E4PRSGA8TJ2`; core issue #3915.
- Exact independent worker RED646f7c488 and GREENdac638afe integrated as
  402947d5a and ea6324cc8. Three-file scope; production changes only the
  metadata-read directory in `_mt_resolve_active_gate_bindings`.
- Identity reads use canonical PRIMARY_METADATA placement; COORD continues to
  own status. Owned effective_root and activation operation-root policy remain
  unchanged. No hardcoded software-dev fallback or activation bypass.
- Independent Renata/Darwin APPROVE: 65 fresh checks, plus exact-baseline replay
  with eight expected failures and five passing controls. Real declared failing
  subprocess executes through the selected binding. Four linked-owned-worktree
  controls retain correct identity; actual corrupt metadata keeps existing
  visible unverified-error behavior. Ruff clean. Two strict mypy diagnostics
  reproduce with byte-exact baseline shadow files; full-file mypy is not green.
- Parent integrated suite: 32 passed in45.52s. Actual mission binding probe
  resolves active/spec-kitty-pre-review despite absent coord metadata, using
  the canonical PRIMARY directory. Both status file hashes remain unchanged.
  This probe is resolution-only, not a live gate execution or transition.
- Tests use disposable real Git topology and real gate subprocesses, but the
  integration bookkeeping port records rather than persists transitions.
  Live work-package coverage must still be inspected at the next real handoff;
  previous NO_COVERAGE results are not retroactively converted to passes.
- External evidence: `pre-review-identity-handoff.md` and independent
  `pre-review-identity-independent-review.md` beside this checkout. Worker
  process-tree readiness timing failure remains disclosed, not represented as
  fresh reviewer reproduction. No source suppression or timeout extension.

## Canonical Agent Config Shape Repair: Open

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3917.
- Supporting Op: `01M1VV3PYTR3HESCVHEXG9W7TQ`, open; no fix or closure yet.
- WP07 identified load_agent_config using yaml.load(f) or {} before shape
  validation. Parent independently reproduced [], false, 0 and empty-string
  documents returning successful empty AgentConfig instead of AgentConfigError.
- This can make selected native/session assessment report complete/not_applicable
  rather than incomplete. Shared canonical loader is outside WP07/WP10 ownership;
  no provider-local schema or default change is authorized as a workaround.
- Required correction: typed canonical failure for malformed root/selected-section
  shapes, preserving absent/null/default mapping behavior and documented valid
  agents/tools precedence. Separate RED/GREEN and independent consumer checks
  remain required before the malformed-config contract is complete.

## Canonical Org Profile Diagnostics: Open

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3918.
- Supporting Op: `01M1VW15S0RR4AC182V3KJSNBS`, open; no fix or closure yet.
- Parent reproduced a real corrupt org sibling through the existing resolver
  fixture. The activation-aware repository reports an org SkippedProfile, while
  resolve_activated_org_profiles returns only admitted records without that
  diagnostic. Admission filtering remains correct; source-health evidence is lost.
- WP06 T030/T033 remain incomplete pending the canonical diagnostic seam and
  consumer integration. Preserve activation, provenance, deterministic results,
  list-caller compatibility and the no-org fast path. No raw-org admission or
  provider-local schema validation may substitute for canonical diagnostics.
- Require RED/GREEN controls and independent review before integration/closure.
  External reproduction: org-profile-diagnostic-probe.py beside this checkout.

## Supporting Test Integration: Open

- Supporting Op: `01M1VWE1HPYDDSHAAZ4Z1HYK83`; related #3910 and #3912.
- Parent reproduced the live next-shard completeness failure: all 19 artifact
  placement nodes lacked a shard marker, one failed gate in 54.89 seconds.
  Ruff also required formatting the artifact-placement and planning-self-heal
  test files. These are valid integration failures, not waived baseline debt.
- Correction registers the new runtime test in the existing next-shard map
  and formats only those two tests. Their complete location-independent ASTs
  remain identical to HEAD. No assertion, gate exemption or runtime change.
- Three-file Ruff, format and strict typing checks pass. Combined live next-shard
  completeness and both affected test files passed: 26 tests in 334.32 seconds,
  terminal exit 0. The process remained live briefly after printing its summary;
  the parent waited for its actual exit, without restart or termination.
- Independent review remains pending; operation stays open.
