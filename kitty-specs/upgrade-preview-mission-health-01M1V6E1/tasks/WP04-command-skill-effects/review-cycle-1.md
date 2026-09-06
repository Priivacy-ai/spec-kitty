---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T19:22:13Z'
reviewer_agent: codex
wp_id: WP04
---

# Independent WP04 Review and Supporting Op #3920 Review

Date: 2026-09-06. Reviewer: canonical reviewer-renata, action=review.
Mode: source-readonly independent review, not implementation or canonical verdict submission.

## Findings

### F1 [P2] WP04: disabled selections acquire command ownership in a mixed batch

[command_skills.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/tool_surface/providers/command_skills.py:105) builds owners from every command-kind selection, ignoring activation policy. The real dispatcher avoids an all-disabled batch, but passes both selections when any selection is enabled. Registering ordinary codex plus the same registered command definition with vibe DISABLED, then running the actual SurfacePlanBuilder -> provider -> SurfaceRepairService apply, creates all 15 entries with owners `("codex", "vibe")`.

Expected: the disabled selection cannot acquire ownership or authorize writes. The all-disabled negative control correctly produces no effects; this is specifically the mixed-selection hole. Shared physical roots hide the error if tests only count physical writes or exercise enabled owners.

Evidence: [extended_checks.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/extended_checks.py) `mixed_disabled`; [extended-checks.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/extended-checks.log) records `MIXED_DISABLED_ACTUAL_OWNERS [('codex', 'vibe')]` and the strict assertion failure. No fake provider or dispatcher was used.

Contract: [owner-operations.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md:165) requires preservation of required/disabled/advisory policy and exact configured selection. This is a delivered assessment-contract defect; the original baseline lacks this new assessment API, so no claim is made that an existing public CLI exposed the same configuration or regressed in this exact way.

Routing: WP04 provider ownership. If normalization belongs in the shared dispatcher, coordinate explicitly with WP02; do not silently broaden the eleven-file scope. Require a mixed enabled/disabled production-dispatch witness plus both-enabled shared-root and all-disabled controls before approval.

### F2 [P2] WP04: cyclic config symlink raises instead of returning an incomplete assessment

[command_installer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/skills/command_installer.py:685) resolves each rendering input; the exception boundary at [command_installer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/skills/command_installer.py:706) does not include Python 3.11's `RuntimeError` for a symlink loop. With `.kittify/config.yaml -> config.yaml`, the actual planner/provider call escapes with `RuntimeError: Symlink loop from .../config.yaml` rather than returning `complete=False` and a diagnostic.

Evidence: [config-loop.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/config-loop.log); exact fixture and command in [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/commands.md). The traceback reaches the real plan, dispatcher, provider and owner, not an artificial new-API import failure. Ordinary malformed-config and malformed-manifest controls return incomplete assessments in [independent-checks.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/independent-checks.log).

Contract: [owner-operations.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md:172) requires unreadable/unprojectable inputs to produce explicit incomplete assessment. Scope is a new protocol error boundary, not an asserted historical CLI regression. The probe aborts before its final unchanged-snapshot assertion; it establishes the escaping exception, not a completed no-write assertion for this fixture.

Routing: WP04 rendering-input observation/error boundary. Add loop-specific coverage with diagnostics and zero-write proof, retaining missing, corrupt and valid-pointer controls; do not mask arbitrary programmer exceptions.

### F3 [P2] #3920: deferred installation widens the unrecoverable init interruption window

The real config persistence at [init.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/cli/commands/init.py:1170) now precedes the deferred command loop at [init.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/cli/commands/init.py:1179). The existing guard at [init.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/cli/commands/init.py:586) treats config existence as complete initialization. An interruption immediately after the real save leaves zero command skills; retry exits 0 with "Already initialized" and still zero skills.

Independent differential witness wraps only `save_agent_config`: call the actual function, then raise KeyboardInterrupt. Both runs use the actual CLI composition. Baseline loads the exact pre-Op init module from b27c733 in memory; final uses delivered init. All other code, environment and fault boundary are held constant.

| State | Pre-Op init b27c733 | Final init 234a2b4 |
| --- | ---: | ---: |
| First invocation exit | 130 | 130 |
| Real save/fault reached | yes | yes |
| Physical command files before retry | 15 | 0 |
| Retry exit / message | 0 / Already initialized | 0 / Already initialized |
| Physical command files after retry | 15 | 0 |

Evidence: [init_fault.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init_fault.py), [init-fault-comparison.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-comparison.log), [init-fault-baseline/first.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-baseline/first.log), [init-fault-baseline/retry.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-baseline/retry.log), [init-fault-final/first.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-final/first.log), [init-fault-final/retry.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-final/retry.log). The baseline already had an initialization-completeness limitation; this change demonstrably expands its impact to absence of the entire command delivery. It is not evidence that baseline interruption was fully transactional or generally resumable.

Routing: separately scoped #3920 init ordering/recovery. Preserve render-after-final-config and authored-config idempotency while providing an honest recovery boundary for newly interrupted initialization. Do not solve by priming upgrade, weakening the canonical count, overwriting authored deactivation, or moving config ahead of runtime-root protection. No generic cross-owner rollback system is demanded.

## Scoped Verdict: WP04

**REQUEST CHANGES.** F1 and F2 block independent approval of the nine-path WP04 delivery. T022 is not complete merely because 967 subsystem tests pass. Supporting #3920's F3 is reported separately, not attributed to WP04 author paths.

| Obligation | Review result |
| --- | --- |
| T018 existing-entry RED and seam tidy | Original six failing witnesses reproduced against pinned baseline; all six pass delivered code. Tidy commit retained in ancestry. |
| T019 complete prepared effects | Full 15-command physical batch, directories, raw manifest bytes and advancing-clock equality independently pass. Incomplete-input boundary fails F2. |
| T020 exact ownership/preservation | Arbitrary adoption, missing placeholders, unknown links, drift, pruning and shared-owner controls pass. Mixed disabled ownership fails F1. Ninth-file correction stays within explicit parent authorization. |
| T021 apply/rechecks | Actual owner/dispatcher checks reject source/config/manifest/destination/mode/mtime/temp changes before writes. Partial I/O remains explicit and retains truthful ownership; repeat operation has no effects or mtime churn. Bounded tests do not establish concurrent-writer atomicity. |
| T022 integration/gates | Full affected subsystem independently green; scoped static checks green except separately disclosed preexisting supporting-file formatting. Full fast invocation non-green. Broad CLI and full mission gates remain unresolved. |

Approval conditions: resolve F1/F2 with attributable RED/GREEN tests through real dispatch, retain the original existing-entry witnesses and all preservation controls, rerun the affected subsystem/static checks and canonical fast gate, and retain separately routed public-composition/full-mission failures. Parent alone submits the canonical verdict.

## Independent Review: Supporting Op #3920

Op: `01M1VXP7D4P42AJRTXEWW7JB42`; supporting governance hash `da91c778426bd64d`.
**REQUEST CHANGES / NOT READY FOR CLOSURE.** F3 blocks the independently reviewed supporting change. This section is evidence for parent integration and later Op closure, not self-closure.

The main ordering correction works on ordinary successful initialization:

- The original stale-manifest witness prefix is unchanged; actual init -> truncate all but one entry -> upgrade remains intact. No inserted priming upgrade or expected-count weakening.
- Independent pre-Op replay of that public sequence yields 10 instead of the original canonical 15: [original-op-red.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-op-red.log), [original-op-red/init.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-op-red/init.log), [original-op-red/upgrade.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-op-red/upgrade.log). Only pre-Op init is substituted; upgrade is the delivered real console entry point, intentionally isolating the supporting change.
- Final original witness and all six added parametrized supporting cases execute successfully within the fresh 967-test run, not merely the author report.
- `test_init_command_bytes_agree_with_final_config` covers codex, codex/vibe and vibe/codex: 15 distinct paths, exact canonical render and manifest digest, explicit REASONS text pin, both owners retained, exactly one temporary physical write and one replacement per command. Observer is installed before the actual CLI.
- Authored inline and pointer-based deactivation remain unchanged under the existing initialized-project guard. This covers authored existing config, not an invented fresh-init override interface.
- Unknown read-only command content remains byte/mode/mtime-identical without fabricated ownership, with a visible collision warning.
- A separately authored real-CLI control uses a foreign `.gitignore` symlink: runtime-root protection refuses before config exists, preserves link and target, and succeeds on retry after only the fixture obstruction is removed. Resumed project has all 15 commands and native Claude skills. [init_gate_check.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init_gate_check.py), [init-gate.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-gate.log), [init-gate/refused.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-gate/refused.log), [init-gate/resumed.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-gate/resumed.log).
- Native installation remains in its existing branch; deferred per-agent installation retains its nonfatal warning handler. The failure of resumability after config persistence is F3, not a claim that the earlier runtime-root gate moved or became ineffective.

Closure conditions after parent integration: resolve F3 without violating final-config rendering, authored idempotency, foreign-content preservation, runtime-root protection or shared-write counts; reproduce the exact public RED/GREEN witness and interruption controls; retain scoped provenance. Broad CLI failures must be routed with honest context attribution. Passing this Op later would still not certify WP04 or full mission acceptance.

## Independent Evidence Matrix

| Check | Fresh result / evidence |
| --- | --- |
| Original WP04 six witnesses, pinned baseline | 6 failed, 49 deselected; intended existing-entry assertions, [original-entry-red.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-entry-red.log) |
| Same exact original witnesses, delivery | 6 passed, 49 deselected, [original-entry-green.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-entry-green.log) |
| Independent ownership/bytes/rechecks/negative controls | 6 groups passed, [independent-checks.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/independent-checks.log) |
| Independent extended controls | 5 groups passed, 1 failed (F1), [extended-checks.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/extended-checks.log) |
| Config-cycle control | Escaping RuntimeError (F2), [config-loop.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/config-loop.log) |
| Original public init/truncate/upgrade pre-Op | Strict 15-vs-10 assertion fails, [original-op-red.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/original-op-red.log) |
| Real init fault differential | Baseline 15 -> 15; final 0 -> 0 after retry (F3), [init-fault-comparison.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-fault-comparison.log) |
| Real runtime-root refusal/resume + native skills | Pass, [init-gate.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/init-gate.log) |
| Entire skills + tool_surface trees | 967 passed, 4 warnings, 768.03s; [subsystems-v3.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/subsystems-v3.log), [subsystems-v3.xml](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/subsystems-v3.xml) |
| Canonical make test-fast, unchanged markers, two workers | 1641 passed, 1 failed, 3 teardown errors, 266.18s; [fast.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/fast.log), [fast.xml](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/fast.xml) |
| Four affected fast tests, isolated after harness correction | 4 passed, 3.77s; [fast-affected.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/fast-affected.log). Not a replacement full gate. |
| Five architecture guardrail files | 94 passed, 133.52s; [architecture.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/architecture.log), [architecture.xml](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/architecture.xml) |
| Ruff all eleven scoped files | Pass; [ruff.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/ruff.log) |
| Strict mypy all eleven, follow-imports=silent | Pass; [mypy.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/mypy.log). Project config still applies; not whole-repo type certification. |
| Scoped git diff --check | Pass; [scoped-diff-check.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/scoped-diff-check.log) |
| Full-file Ruff formatting | 9 unchanged, 2 supporting files would reformat; [format.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/format.log) |
| Same two full files at pre-Op b27c733 | Both already fail; [baseline-format-init.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/baseline-format-init.log), [baseline-format-wiring.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/baseline-format-wiring.log). Preexisting format debt, not a clean formatting gate or waiver. |

The first original-entry reproduction selected external byte-exact tests outside the canonical pytest.ini root, resulting in two unknown unit/fast marker warnings; no witness was skipped, xfailed or converted to collection failure. Shared conftest was loaded. The complete canonical subsystem run independently executes delivered tests under the repository configuration.

The three fast teardown errors came from the review-only guard invoking `Path.resolve` while fd-sharing tests intentionally make `Path.stat` raise. Only the external guard changed to `os.path.realpath/commonpath`; all three then pass without modifying their spies/assertions. The unrelated moments literal-output assertion also passes individually but its full-run context remains unresolved. Do not label it baseline, fixed, waived, or a scoped product regression from serial success alone.

### Raw Oracle and Adversarial Controls

[independent_checks.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/independent_checks.py) uses actual WP01 `snapshot`, `net_delta` and unchanged-state checks against the actual registered provider/planner/dispatcher. It compares full physical path/action/node-kind/hash/link-target/mode effects, including new supporting directories and the manifest, not command counts alone. For a single invocation, the clock advances before apply and the manifest must match retained prepared bytes exactly; no timestamp normalization is applied. Retained raw bytes: [full-batch-manifest.raw](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/full-batch-manifest.raw); snapshots/effects: [full-batch-snapshots.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/full-batch-snapshots.json).

Independent controls exercised:

- Exact manifestless canonical adoption for only the configured owner; manifest-only shared reuse; one-owner release retains physical bytes and the other owner; last proven owner removes; retired shared ownership and edited orphans survive inappropriate pruning.
- Actual normal repair preserves unknown canonical/custom bytes, dangling unknown links, read-only modes and managed drift while restoring an independent missing command.
- Exact manifest-owned package/leaf links convert to copy delivery without touching foreign targets; full physical delta remains equal to assessment.
- Whole-batch preconditions refuse changed config, manifest, parent, destination, mode, mtime, temporary occupants and source templates. The source-race fixture copies a real template and redirects only template resolution to that fixture; it does not replace renderer/provider/dispatcher behavior.
- Deliberately dropping the manifest effect breaks the WP01 equality oracle; deliberately bypassing owner recheck makes a forbidden write observable; deliberately resampling prepared manifest timestamps breaks raw equality.
- Python audit observer sees no transient assessment writes, while an intentional create/delete control is detected. No snapshot-only inference of transient purity.
- Injected second physical-write failure reports one success, one failure, skipped manifest effect and partial outcome, while salvage preserves surviving owners and existing read-only manifest mode.
- Pinned old normalization and prefix-link-cleanup functions demonstrably adopt arbitrary content/delete an unknown link; delivered existing entries preserve both. These counterfactual checks substitute only exact baseline function bodies in memory; no source checkout is rewritten.

These controls supplement, rather than replace, original-entry RED evidence. New API controls do not by themselves establish historical regressions.

## Scope and Provenance

Authoritative inputs read: full fresh canonical prompt, complete parent handoffs/investigation/routing files, actual PRIMARY WP04, spec/plan/research/data-model and required contracts, PRIMARY charter, AGENTS, canonical Renata profile and review tactics. PRIMARY and lane AGENTS compare byte-identically. No CodeGraph index was present.

Canonical prompt: [fresh WP04 prompt](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-prompts/spec-kitty-7aebe9a30bb5/upgrade-preview-mission-health-01M1V6E1/WP04/69dd030ad21642ea9180e839e3ddbe78.md).
Parent scope: [wp04-handoff.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-handoff.md), [init-command-ordering-handoff.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/init-command-ordering-handoff.md), [wp04-parent-correction-routing.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-parent-correction-routing.md), [wp04-init-ordering-investigation.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-init-ordering-investigation.md).

| Provenance | Commit |
| --- | --- |
| WP04 baseline | d95a61b97297c75e39ae56828fc7d63159a03b7a |
| Original WP04 RED | 248b48916d5f5380bda953d64021c3e3286d5183 |
| Seam tidy | e1300bd0be6ab4891ff30321fdb05bd6bf071d79 |
| WP04 GREEN | 8f1499826520f32b06dcff7b8d5c34de9e74b644 |
| Authorized ninth legacy-test correction | b27c733d66c4e89bff9467f8ece1b8eaab41474f |
| Supporting #3920 RED, test additions only | 36ac0c9e111a9cf01fd137d723c5c4542418d568 |
| Supporting #3920 GREEN, init only | 234a2b433a0c4bc621352ca55484cef3edc37f79 |
| Reviewed coordination HEAD | c26c1002a42ea27ddde59abb0c1bceacb8f9fc3d |

Ancestry and file-byte assertions independently pass: [verify_scope.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/verify_scope.py), [scope-provenance.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/scope-provenance.log), [scope-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/scope-final.log). Nine WP04 paths match b27c733; two supporting paths match 234a2b4. No later source/test/dependency changes between supporting GREEN and reviewed HEAD. Dependency/coordination receipts are not WP04 author code.

Exact eleven authored paths:

1. [src/specify_cli/skills/command_installer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/skills/command_installer.py)
2. [src/specify_cli/skills/command_renderer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/skills/command_renderer.py)
3. [src/specify_cli/skills/manifest_store.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/skills/manifest_store.py)
4. [src/specify_cli/tool_surface/providers/command_skills.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/tool_surface/providers/command_skills.py)
5. [tests/specify_cli/skills/test_command_installer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/skills/test_command_installer.py)
6. [tests/specify_cli/skills/test_command_renderer.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/skills/test_command_renderer.py)
7. [tests/specify_cli/skills/test_manifest_store.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/skills/test_manifest_store.py)
8. [tests/specify_cli/tool_surface/providers/test_command_skills.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/tool_surface/providers/test_command_skills.py)
9. [tests/specify_cli/skills/test_manifest_repair.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/skills/test_manifest_repair.py) (separately authorized ninth WP04 correction)
10. [src/specify_cli/cli/commands/init.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/src/specify_cli/cli/commands/init.py) (supporting #3920 only)
11. [tests/specify_cli/tool_surface/test_surface_repair_wiring.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/tool_surface/test_surface_repair_wiring.py) (supporting #3920 only)

Original wiring-test prefix: 8,521 bytes, SHA-256 `2e996030fd215bfe18d4013255e1b1c0f1abfe4194755f4db02b67f876aa5bbf`, byte-for-byte unchanged. Exact per-file SHA-256 values are in provenance logs. Original RED only changes the installer test; supporting RED only adds to wiring tests; supporting GREEN only changes init. No canonical-count, priming-sequence, stub/xfail or threshold waiver was introduced by this review.

## Required Anti-Pattern Checklist

| Item | WP04 | Supporting #3920 |
| --- | --- | --- |
| Dead code | PASS: new payloads/helpers have real owner/provider/dispatcher callers; [production-callers.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/production-callers.log); dead-module/symbol guardrails pass. No new module. | N/A new public symbols/modules; moved loop has live init callers. |
| Synthetic-fixture test | PASS: existing-entry witnesses and independent real-provider/CLI controls invoke actual producers. Intentional mutants test assertion sensitivity, not replacement product behavior. | PASS: actual pre-CLI observer and public sequence; fault wrapper calls real save. |
| Silent empty return | PASS: incomplete/error results carry diagnostics; preservation dispositions and nonfatal cleanup/warnings are intentional. F2 is an escaping exception, not a silently successful empty result. | PASS: per-agent and config exceptions retain visible nonfatal messages; F3 remains a recovery defect. |
| FR assertion presence | PASS for scoped FR-002/003/004, NFR-004 and C-001: full effects, exact apply, repeat unchanged, ownership/preservation and canonical real authority assertions exist. This is not complete mission satisfaction. | N/A standalone FR frontmatter; supporting ordering/preservation assertions exist, but interruption requirement fails. |
| Frozen surface | PASS within authored commits: original eight files plus explicit ninth and separate two-file Op; no schema/registry/dispatcher/shared-conftest implementation edits. | PASS: test-only RED, init-only GREEN, original prefix frozen. |
| Locked decisions | FAIL: F1 violates disabled-owner policy; F2 violates explicit incomplete-input reporting. | FAIL against requested preservation of resumability/failure behavior: F3. |
| Shared-file ownership | PASS: parent correction/routing and separate supporting handoff explicitly authorize the ninth path and isolate init/wiring ownership. Dependency/coord changes excluded. | PASS: separately identified Op, not disguised WP04 scope expansion. |

Any FAIL blocks approval. This review does not use checklist PASS cells to override the findings.

## Environment, Governance and Limitations

Profile resolved through the actual CLI: [profile.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/profile.log). Review action context: [charter-review.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/charter-review.log). **#3908 remains unresolved:** a successful command envelope does not resolve unavailable directives or empty tactics/styles/toolguide/reference arrays. Explicit charter, AGENTS, profile and review-intent/incremental/assertion-preservation/scaffolding doctrine were read; no claim of fully resolved governance.

Tests used the already-warm lane Python directly, no uv resync. Canonical make test-fast retains its existing `uv run --frozen` recipe with UV_NO_SYNC=1 and UV_OFFLINE=1. Python 3.11.15 on Darwin; spec-kitty-cli 3.2.7rc1, spec-kitty-events 9.1.6, pytest 9.0.3, xdist 3.8.0, Ruff 0.15.12, mypy 1.20.2; distribution/source bindings recorded in provenance logs.

External policy and canonical conftest/test-venv binding were inspected before tests. Launch is `env -i` with isolated HOME, USERPROFILE, XDG, APPDATA, tmp and caches; no inherited credentials/global user assets. External policy forces SaaS sync=0 through conftest mutation and explicit child environments. [environment.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/environment.log) checks parent and child binding. Shared warm test-venv is reused; its lock/state and wall-clock-scan cache are redirected outside lane without replacing dependency validation, scan logic or tests.

Python audit hooks deny non-loopback socket connect/address resolution. Offline flags prevent intentional dependency resolution. This is **not a native firewall**, not a native-process network confinement claim, and not universal filesystem-write enforcement; a Python read-only guard supplements exact source/status verification. No network operation or credential/global-asset access was intentionally requested. Loopback subprocess/test services remain allowed.

Harness-only startup/cleanup mistakes are retained: [subsystems.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/subsystems.log) failed before tests because benchmark storage defaulted inside lane; [subsystems-v2.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/subsystems-v2.log) was interrupted after a Darwin dir_fd path-resolution bug caused false read-only errors. Its 14 failures/826 passes/329 errors are invalid acceptance evidence, not product RED or accepted exceptions. External policy corrections only; source/test assertions untouched. Final valid subsystem run is v3. The later fast guard correction and isolated retest are separately recorded above.

Exact launch environment, argv, working directory, inline probes, baseline loading method and raw-log destinations: [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-independent-evidence/commands.md). Manual external harness/report edits used apply_patch only. Initial/final source scope checks are clean; no source, receipts, mission/status, COORD, Op completion, root lifecycle, commits, pushes or canonical review submissions were written. Only external evidence and this requested report were created.

Platform/format limitations: macOS/Python 3.11 source-bound execution, not Windows or Linux certification; no source-free installed-wheel run; exact per-invocation raw byte oracle is not serialized cross-process replay certification. Full-file formatting of both supporting files is preexisting non-green, not waived. No full repository typecheck, complete architecture/contract/E2E/corpus suite, or complete public preview/apply mission gate is claimed.

## Retained Broad CLI and Full Mission Gates

Author broad CLI raw log was inspected, not rerun independently: [init-op-init-callers.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp04-evidence/init-op-init-callers.log). Retained outcome: **3923 passed, 7 failed, 2 skipped, 2 xfailed**, 63 warnings. No waiver, threshold increase, stub or new xfail.

| Failures | Exact identities / impact |
| --- | --- |
| Four planner state failures | `test_project_migration_needed_planner_json`, `test_project_too_new_for_cli_project_state`, `test_project_not_initialized_planner_state`, `test_planner_json_too_new_project_has_exit_code_5_in_payload` in [test_upgrade_command.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/cli/commands/test_upgrade_command.py:461). Actual CORRUPT instead of STALE/TOO_NEW/NO_PROJECT. Compatibility/planner-owner gate remains non-green. |
| Two durability timing failures | `test_two_queued_rejections_preserve_each_exact_cycle_and_event[canonical]` and `[causal-mutation]`, [test_move_task_durability.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/cli/commands/agent/test_move_task_durability.py:853). 22.791834s and 16.510712s exceed unchanged 10s limit. Timing/contention attribution unresolved; do not increase limit. |
| One sync-policy conflict | `test_owned_preflight_refuses_before_effects[sync-OWNED_SYNC_UNSUPPORTED]`, [test_owned_checkout_move_task.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-d/tests/specify_cli/cli/commands/agent/test_owned_checkout_move_task.py:212). Test sets sync=1; required external policy forces 0, producing OWNED_TRANSITION_UNSUPPORTED rather than expected OWNED_SYNC_UNSUPPORTED. Route to parent gate/policy ownership, not sync enablement in this review. |

Pre-Op serial comparisons do **not** establish a baseline for the four context-sensitive planner and two timing failures. Their broad-run regression attribution remains open. The sync case has a specific environment-policy contradiction, not permission to waive its gate or enable sync.

Existing skips are the platform-gated safety/finalization cases identified in the handoff. Existing strict xfails are the two flattened-topology planning-placement finalization cases tied to #2802. They remain visible; no mission-wide green is inferred.

Parent-owned unresolved acceptance work:

- Full CORE contracts and full CORE architecture, not the 94-test scoped guardrail subset; canonical fast must also be re-established honestly.
- Full E2E current `scenarios/` with correct CORE/source/binary binding. The recorded five-case floor remains two failures/three passes, including #3912 dependent-WP ancestry and #411 contract-drift fixture failing at fake-events diary collection instead of the intended inner assertion. Require positive and negative controls at the intended assertion; no fixture stub or xfail acceptance.
- Original eight WP01 ordinary-public RED witnesses, including same-version/no-migration omitted-repair behavior; WP10/public composition and later acceptance owners must prove final GREEN. Infrastructure counts are not those product witnesses.
- Source public G0/G1/G5, target rejection, P0-P8 effects/clock/TTY/cold/no-bootstrap and aggregate envelope checks; source-free installed-wheel provenance matrices.
- Terminal issue matrix #3900-#3903, separate corpus full audit/recovery evidence and remaining governed mission completion requirements.
- Governance resolution limitation #3908 and all broad-run failures above, including the independent fast-run context failure.

These are outside this review's authorized implementation scope. Route them to parent/integration/gate owners; do not silently assign their fixes to WP04 or close the supporting Op. Parent serializes canonical verdict and any eventual integration/closure.
