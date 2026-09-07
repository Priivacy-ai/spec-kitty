# Supporting Operation Reviews

## Local Shared-Package CI: Complete

Op `01M1XPKV2DYTY49TC3K0H8Y5M5` addresses the recurring #3979 failure on
PR #3923 head `e1ce3817fd92d8dde93dd55b4c102cb8367449b4`, CI run
34110105314/job101704189922. The validator reports four mismatches between
the current public CLI train and the retired SaaS repository's pins.
Evidence is attached to #3979 comment5569112104; no duplicate issue was filed.

Scope is the shared-package CI workflow and focused existing regression tests:
remove its retired-consumer fetch/comparison and secret-dependent skip while
preserving local range/lockfile/compatibility-manifest/retired-package validation,
trusted validation scripts, candidate artifacts and existing job identities.
Dependency pins, release publishing, secrets and other #3979 retirement work
remain outside this Op. No claim that the full issue is closed or CI passed.
RED-first tests, offline real-validator positive/negative controls, independent
review and parent integration precede closure. Dispatch retains the known #3908
unresolved-governance diagnostic, not an empty-governance approval.

The bounded correction is independently approved: RED
`54a6c3a424136f17d67c88d28613034db0061dd7`, GREEN
`c3c22c56f4a749badc14a4b30c63441e195ea538`. Author release selection:
146 passed, five existing dogfood opt-in skips; canonical fast: 1643 passed;
Ruff and strict mypy passed. Reviewer ran eight focused tests plus six independent
real BASE-validator controls, including invalid/missing candidate metadata,
retired runtime dependency and untrusted candidate-script refusal. Broad suites
were inspected, not repeated. No validator or dependency changes.

Parent verified the review seal, integrated the exact two-commit patch chain with
provenance as `aa547eb19` / `afd61036b`, and confirmed the delivered files and
validator/metadata inputs remain byte-identical. On the target checkout, eight
focused tests passed in 28.07 seconds, with real conftest and enforced isolated
home/network/sync boundaries. External evidence:
local-shared-package-ci-independent-review.md and
local-shared-package-ci-parent/invocations.jsonl. This closes only the bounded
CI Op, not all of #3979, hosted CI confirmation or mission acceptance.

## Managed Installation Provisioning Projection: Open

Op `01M1XKAK3SXPCAWP6PN9STTA20` addresses WP10's next concrete owner gap.
Legitimate WP09 provisioning updates legacy config, invalidating the retained
managed-skill installation. Paired global/project preflight correctly refuses
both owners before writes. The actual projected compiler result is currently
rejected as unsupported. Real-conftest reproduction: one failed, three passed
in 38.60 seconds; pointer and explicit-empty controls apply 315 effects.

The original managed-skill owner extended admission and exact-transition
checks in a separate worktree. Strict original paired preflight, retained bytes,
caller registry/selection, locks, consent and unrelated-change refusal remain
mandatory. The reviewed command supplier stays unchanged. Supplier and actual
WP10 consumer review precede closure. External request/reproduction: wp10-handoff.md
and wp10-evidence/test_managed_provisioning_composition.py.

WP10 also committed public JSON downgrade RED `dd83882a826190f42dea09d89acd611c731e3087`
and separate formatting-only `18aca7992798effddfeb7d249cfc9139e7c46ee0` on its
lane. No production composition or public GREEN is claimed yet.

Supplier RED `250662c11c3086925222200bb639f684adaa01a2` precedes candidate
`7bd158a2ed105e18f6e53a19ced2e23f1dad4eca`, changing only the managed installer,
provider and their two existing test files. Final frozen targeted verification:
51 passed, 83 deselected in 77.91 seconds; Ruff and strict mypy passed.
Intermediate failures remain recorded rather than relabeled as passing runs.
Command and global supplier dependencies remain byte-identical.

The actual compiler descriptor is admitted during preparation. The caller must
hold `preflight_installation(installation, consent)` across provisioning and
paired apply, aborting on original-state diagnostics before any write. The
provider accepts only the bounded exact expected transition afterward, retaining
the existing paired global locks and project lock. This is not a transaction,
rollback guarantee, cross-process project lock or causal-writer authentication.

Independent review approved this supplier after four actual consumer cases
(38.47 seconds) and four adjacent refusal/cleanup controls (30.62 seconds).
Each consumer matched all 315 physical skill effects and succeeded IDs, with
provisioning reported separately and repeat apply showing no churn. Existing
broad WP05 and author static/coverage evidence was reused, not freshly rerun.
Parent verified all 18 review seal entries and fast-forwarded the exact supplier
RED/GREEN chain into WP10. Actual WP10 composer review is still pending; the Op
remains open. Reported commits are lane-local until mission consolidation.
External report: managed-provisioning-projection-independent-review.md.

## Command Provisioning Projection: Open

Op `01M1XF4MQ2JPFAVDK15SYGVK8Q` addresses the concrete WP10 integration gap:
command assessment renders from live configuration and cannot consume retained
WP09 provisioning state. Applying required provisioning before command repair
correctly invalidates original observations. In the real-conftest reproduction,
legacy/pointer missing-key cases both refuse all 33 command effects; explicit
empty controls both succeed. Result: two failed, two passed in 30.24 seconds.

The original command owner is implementing a bounded immutable projected-input
extension in a separate worktree. Original preflight and unrelated-change
refusals, exact prepared bytes and finalizer ordering must remain intact.
No preview writes, post-write rerender or blanket observation bypass is allowed.
Supplier review and real WP10 consumer verification precede closure. External
reproduction and API request: wp10-handoff.md and wp10-evidence/. Tracked on
#3901 comment5567579677. WP10 made no product changes before reporting the gap.

Supplier extension `bc950c6af76f2d2a5238e5dc9c53dc037b6c4f5b` is independently
approved, preceded by RED `b349cc947389f841090ce18d66e0c040d66eed13`. Six existing
command-owner source/test files changed. Mission-type-only provisioning preserves
ordinary command bytes; no mission-to-command selection policy was introduced.
The API admits the actual immutable compiler result and requires strict original
preflight before provisioning, then validates only the exact supported completed
transition. Unrelated changes still refuse before command writes.

Independent review ran the unchanged four-cell consumer, 39 selected guard
tests and adversarial controls, with narrow static checks. One external sentinel
placement error was corrected and only its affected test rerun. The older
262-pass author run is invalid for final coverage mapping because source moved;
the final frozen 76-case gate and coverage are recorded separately. Parent
verified all 42 evidence seal hashes and fast-forwarded the exact RED/GREEN chain
into WP10. Report: command-provisioning-projection-independent-review.md.
Actual composer consumption is still unreviewed, so this Op remains open.

## WP09 YAML Preservation Arbitration: Complete

Op `01M1XCGBK5AFYA6T2AE7CBRB3X` records explicit user authorization to fix
both remaining WP09 defects after its third rejection: comments lost when the
same loaded YAML document is saved repeatedly, and the already-reproduced
YAML-directive compatibility failures. This supersedes the human-arbitration
pause, not the preservation contract or review requirements.

The original author resumed the existing lane through the canonical implement
command. Scope remains WP09-owned YAML I/O and tests, with genuine RED evidence
for both defects before the fix. Follow-up review is limited to these corrections
and immediate preservation risks; unchanged broader evidence is reused. No
automatic approval, broad review restart, dependency change or acceptance waiver.
The durable Op record is included in this PR. Closure requires the actual fix
commit and independent focused review evidence. WP10 integration, WP13 acceptance
matrices and all final mission gates remain pending.

The bounded correction is complete at `0eff16b1a8a1329363b21f8964bb188e59cf8054`,
preceded by RED `62cd04d9f61ec210bd93a8a57abea011e9130f1e` (eight failures,
eight passing controls). Author YAML suite: 136 passed. Independent review
replayed the exact saved reuse/directive/explicit-key cases, ran 25 targeted
tests and static checks, and approved both defect classes. Report and sealed
evidence: wp09-op-independent-review.md. Parent recorded WP09 approval
`01M1XE81YCJ0RNB0JA4800DTH3` and completed the Op with that fix/report.
These are lane-local results until consolidation, not public-preview or final
PR acceptance. No full review restart or acceptance waiver was used.

## Configured Bundle Source Tools: Complete

Op `01M1WM2PAB09HACQVJEDDR422H` addresses WP08's observed shared planner gap:
`build_plans_for_bundles` hardcodes four representative tool keys, while the
bundle contract requires caller-configured source tools. The bounded extension
will preserve the existing default and explicit-empty selection, with one
canonical registry/builder path. Scope: service.py and existing test_plan.py.
Independent supplier review and real WP08 consumer verification precede closure.
No dead-code exemption, dummy caller or approved-WP source edit is authorized.

WP08 reported 924 subsystem tests passing; required architecture yielded 85
passes and two failures, including this dead helper and unwired upgrade intent.
The latter remains WP10 work, not a waived gate. Exact reproduction and source
snapshot are retained externally in wp08-evidence/owner-api-request.md and
architecture.log. WP08 continues non-overlapping owned verification meanwhile.

Supplier `e35cdc494237f55ef73b36cb6f979e0c56772bfe` is independently approved:
six focused tests, three independent controls and static checks passed. The
complete RED/GREEN chain is integrated into WP08 with the two supplier files
unchanged. Actual configured/empty/duplicate consumer cases pass in author tests;
independent consumer review passed all three actual configured/empty/duplicate
controls with approved supplier bytes unchanged. Parent completed this Op with
consumer commit `9d78799b94f3c4df0f2e68d4ca8dda4ef3661801` and the separate
consumer verdict in wp08-independent-review.md. WP08 itself was rejected for an
unrelated supporting-directory mode regression; this Op closure does not approve
WP08, root wiring, or final integrated gates.

External Claude validation was recovered using only a pinned standalone 2.1.263
executable copied into the disposable workspace, with host-home and network
denial retained. The real marketplace initially failed strict validation; source
comparison shows the bad payload existed in the frozen baseline. WP08's owned
Claude-only correction now passes real strict plugin and marketplace validation,
while a malformed-name control fails. Original failures remain in the external
ledger and #3901 comment5563531342. No member-coverage claim is inferred from the
validator's empty contents list; independent effects/member tests are separate.

## Caller-Resolved Global Skill Inputs: Complete

Op `01M1W6MA0EWJ38MJDQG2D50ZJ3` supplies the missing WP03 input needed by
WP05's existing direct installers. Their caller-resolved registry, concrete
skill selection and skill-agent selection must remain authoritative; default
package/all-agent behavior must remain unchanged. One coordinated preparation,
retained observations/bytes/owners and existing WP02 guards remain mandatory.
Scoped runtime extension and independent review precede consumer integration.
External reproduction and scope: wp05-interface-request.md.

Independent verdict: APPROVE at `2b653bc511b81a1b4ccbf06d60f491b044831633`.
Full dependency chain: RED `6650023b2eed23889637d35ecc99fabf00fdc188`,
tidy `8a3f1b90207027d24cbedf75c0ffe41e150fae5d`, implementation
`ea1f12e182753555bba17b6b30606e742ff4a774`, then the final test commit.
Three changed paths: runtime agent_skills.py, asset_preparation.py and
test_upgrade_preview_bootstrap.py. Fresh review: 37 focused plus six independent
tests passed; Ruff, formatting and strict mypy passed. Actual coordinated
dispatch retained 167 exact effects and 460 observations across three families;
selected input does not authorize overwriting differing untracked content.
Unchanged WP03 locking and owner evidence reused, not broad-suite rerun.
Initial reviewer run had 37 setup errors from an external fixture-hook missing
return; corrected externally without relaxing sandbox, fixtures or assertions.
Original failure retained in global-skill-selection-independent-review.md.
WP05 full-chain integration is verified with approved supplier bytes unchanged.
The original consumer review rejected aggregate preflight and shared-owner
metadata; correction `a458fc01fae48d80946f450ce90ab09ab19e8f1c` passed focused
independent review: 11 targeted tests plus four independent controls, real
169-effect provider dispatch and changed-input zero-write refusal. Separate
consumer-seam verdict is closure-ready; parent completed this Op through the
canonical CLI with that commit and wp05-cycle2-independent-review.md as evidence.
This closes the owner/provider input extension, not WP10 root wiring or final
public acceptance. Original failures and intermediate fixes remain recorded.

Operator isolation incident F038 is disclosed in the external friction ledger
and #3900 comment5561980379: earlier governance/parent CLI calls inherited live
HOME; exact global changes are unknown without before snapshots. They are not
claimed isolated. Future parent calls use an externally verified isolated-home
wrapper with OS real-home and network denial. No blind rollback was attempted.

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

## Canonical Agent Config Shape Repair: Reviewed and Integrated

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3917.
- Supporting Op: `01M1VV3PYTR3HESCVHEXG9W7TQ`.
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
- Independent scoped verdict: APPROVE. Reviewer reproduced the original
  33-failure RED and passed 61 fresh tests plus 98 independent controls.
  Original RED/GREEN: f04dece22f66c4e79a33965f32556c8723bd6377 /
  59ee50ec05f6d68b5a8511a5c3f80ce151f4581a. Parent integration preserves that
  sequence as 4ab373e0e / eab71296f; both files match reviewed bytes exactly.
- Parent post-integration loader and doctor-envelope run: 61 passed in 47.44
  seconds, terminal exit 0. External independent report:
  agent-config-shape-independent-review.md beside this checkout.
- This completes only root/selected-section mapping validation. Existing nested
  roster-element TypeErrors for available: [1] and available: [{}] remain
  reported on #3917. The 64 hosted tracker test failures under required sync=0
  remain disclosed, not waived or represented as broad-suite green.
- WP07 must still verify real native/session consumers after dependency uptake
  and resolve its separate review findings. No WP07 or mission approval follows
  from this supporting operation's completion.

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
- Resolver implementation independently approved at 251c4a7f2dbe6d571cdc6a4d0d0ad6340521cdbc:
  29 focused, 13 adversarial, 499 integration and 1642 fast-tier tests passed.
  Parent integrated RED/GREEN as 79096a52a / 371bc7b83 and reran resolver plus
  activation-gate tests: 29 passed, one legacy-config warning, terminal exit 0
  in 57.61 seconds. WP06 consumer integration is running; Op remains open.

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
- Independent review APPROVE at 910940be0209d3115a0d1bf216e83e64a10cf0dc:
  complete real collection has 1536 unique nodes and a total, disjoint partition;
  exactly the 19 newly registered nodes change markers. Parent-map replay and
  duplicate-marker negative control both reject through the unchanged gate.
  Both formatted test modules independently passed 25 tests in 12 seconds,
  terminal exit 0; full AST equality and Ruff checks passed.
- Existing duplicate declaration for test_cli_guard_family.py is unchanged;
  actual collection remains single-assignment. No claim that the entire source
  registry is duplicate-free or that hosted CI/full architecture ran green.
  Evidence: supporting-test-integration-independent-review.md beside checkout.

## Init Command Rendering Order: Open

Independent corrective review now approves `e9907343ba82782a91cb940df7c027d60dbdee9a`
separately from WP04. Exact interrupted-save RED and normal/shared/edited-selector
recovery controls pass, with preserved config, unknown content and original test
prefix. Target integration and post-integration checks with WP04's command owner
remain pending; Op stays open. Report: `wp04-cycle2-independent-review.md`.
This is bounded command-delivery recovery, not full-init transactionality.

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3920.
- Op: `01M1VXP7D4P42AJRTXEWW7JB42`, open. Separate supporting correction,
  not a waiver of WP04's remaining subsystem failure.
- Actual unchanged init/truncate-manifest/upgrade witness expects fifteen
  entries but obtains ten. Init renders before final REASONS activation; later
  canonical bytes differ in five files after manifest ownership is truncated.
- Correct init composition while ownership is still authoritative. Preserve
  explicit deactivation, authored configuration, unknown content and the original
  public regression test. Do not adopt historical variants without proof or
  change counts to hide the defect. RED/GREEN and independent review required.

## Terminology Gate Path Boundary: Open

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3919.
- Op: `01M1VZW11T9T6YXGNKGZ5Q235W`, open. Existing gate matches excluded
  path fragments against the entire hit, allowing active prose to suppress
  violations merely by mentioning an excluded directory.
- Repair actual source-path parsing and path boundaries. Preserve positive
  historical exclusions and active-source negative controls, including content
  injection and lookalike paths. Exercise the real scanner as well as pure seams.
- Classify immutable recovery evidence narrowly without changing receipt bytes,
  adding a broad archive exemption, or exempting arbitrary active prose.
  RED-first regressions, independent review and postintegration verification
  are required before closing this Op. No gate waiver is authorized.
- Dispatch exited successfully; governance hash `da91c778426bd64d` still reports
  unresolved directives (#3908). This is not full governance-resolution success.

- Independent review rejected candidate `447b4864bf94bece5a66724f66b7af961127bfb5`:
  real Git skips staged leaf symlinks while byte checks follow their targets.
  All 79 existing tests pass despite three failing real-Git rejection controls,
  one per frozen evidence path. Enforce the regular-file/no-symlink boundary
  independently of source hits. Original author is correcting this one finding;
  follow-up review targets the corrective diff and adjacent path regressions.
  Report: `terminology-gate-independent-review.md`; #3919 comment5561704532.

### Terminology Correction Approved And Integrated

Independent cycle-two review approved `a00ab6aeb452a51de7b384d500c3a8a6867f9be7`:
21 independent controls and 12 targeted repository tests passed. The original
three real-Git symlink counterexamples fail on RED and pass GREEN. Frozen bytes,
original test ASTs, scanner policy and baseline remain unchanged.
Parent integrated all four RED/GREEN commits with provenance, ending at
`cf2eaf1b1`; the complete 88-test terminology module passed in 49.84s on the
target checkout. This closes the bounded #3919 repair, not mission acceptance.
External reports: `terminology-gate-cycle2-independent-review.md` and
`terminology-gate-evidence/parent-integration.log`. Exact isolated command:
`terminology-parent-integration.sh`. Op completion follows this evidence record.

## Moments Literal-Output Test: Open

- Issue: https://github.com/Priivacy-ai/spec-kitty/issues/3924.
- Op: `01M1W32WPQW15E6YQXZDG91ZFA`, open. Normal Rich wrapping splits
  the invalid-value diagnostic across lines under long isolated config paths;
  the test incorrectly requires a contiguous substring. The literal markup
  value and semantic diagnostic remain present in actual output.
- Scope: `tests/cli/commands/test_moments_command.py` only. Preserve the
  existing no-crash, diagnostic and literal-markup requirements. Add real
  wrapping coverage and negative controls for lost/interpreted content.
- No production changes, widened-console workaround, skip, xfail or assertion
  deletion. RED-first proof, scoped static/full affected tests, canonical fast
  verification and independent review are required before integration/closure.
- The prior 1641-pass/one-failure fast run remains red. Source diagnosis and
  evidence are retained externally in `moments-wrapping-issue.md` and
  `terminology-gate-evidence/moments-probe.json`. Governance degradation #3908
  remains explicit despite successful dispatch.

### Moments Repair Approved And Integrated

RED `5dc39d1880fafc052c9bafc7602d19f6412b6c9e`, GREEN
`1a4c441f0c28cf8aa79b5d937c82176bf7cef516`; only the permitted test changed.
Independent reviewer approved after 19 affected tests, static checks, real
wrapping and mutation controls. Author's single canonical fast run passed 1643
tests; reviewer inspected that receipt rather than rerunning it. Parent integrated
with provenance as `f0f843ae2` / `c938e1905` and independently ran all 19 affected
tests on the target checkout: 19 passed in 28.49s, terminal exit 0.
The original diagnostic, literal-markup and no-crash obligations are retained;
no production changes or widened-console workaround. Historical RED remains
historical, not retrospectively green. External evidence:
`moments-wrapping-independent-review.md`, `moments-parent-integration.sh`,
`terminology-gate-evidence/parent-moments-integration.log`.

### Org Diagnostics Consumer Follow-Through Complete

The previously approved and integrated #3918 supplier remains byte-identical.
Independent WP06 review verified actual consumer health handling before list
copying/truthiness; its separate corrective review closed all other WP06 findings
without changing the supplier or that consumer seam. WP06 approved event:
`01M1W5N34C35V1989GAREFJ5ZS`. This satisfies the pending consumer follow-through
for Op `01M1VW15S0RR4AC182V3KJSNBS`; full public integration remains pending.
