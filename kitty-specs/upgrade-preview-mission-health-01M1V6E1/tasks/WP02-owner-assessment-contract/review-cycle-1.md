---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T15:04:10Z'
reviewer_agent: codex
wp_id: WP02
---

# WP02 Independent Review

Audience: parent orchestrator and implementing owner.
Updated: 2026-09-06.
Reviewer: Reviewer Renata, independent Codex reviewer; authored none of the reviewed source or tests.
Verdict: **REJECT**. Three P2 findings require correction before WP02 API handoff.

## Findings

### [P2] F1: Zero-expansion dispatch loses selected tool and definition context

Location: `src/specify_cli/tool_surface/repair.py:99`, `:114`, `:219`; input contract at `operations.py:257`.

The dispatcher iterates selected plans but discards `plan.tool_key`, retaining only definitions grouped by provider. Even those definitions are not passed to `provider.assess(inputs, statuses)`. When expansion returns no instances, the owner receives only the caller's unchanged root/projected inputs and an empty status tuple. Distinct selected tool sets or kind filters are therefore indistinguishable to the owner.

Independent control used the existing `run_tool_surfaces` entrypoint, real registry assembly, a minimal registered owner whose expansion returns [], and separate `tool_filter="codex"` / `tool_filter="vibe"` calls. Both invoked assessment, but the received inputs/statuses were identical. Required-provider presence is retained; the selected logical-owner context is not.

This blocks correct owner-local orphan pruning and shared-manifest accounting when there are zero expanded statuses. Reading project config cannot recover an invocation's narrower tool/kind selection. Having each caller duplicate that selection inside an undocumented opaque payload would bypass the registry's authority.

Expected correction: carry immutable selected tool/definition context from the existing plans into owner assessment, including empty expansions and the selected kind/policy. Preserve original statuses where present. Add a real-service regression with two differing selections and a zero-expansion pruning/selection witness.

Contract: T008 original owner context and registry-driven selection; T009 retention of every logical owner/manifest-sharing context; owner-operations.md's configured-agent scope and profile pruning beyond expanded statuses; FR-002/003, C-001.

### [P2] F2: Existing service bypasses the new inventory-failure assessment path

Location: `src/specify_cli/tool_surface/service.py:150` and `:153`; unused protection at `plan.py:94`.

`SurfacePlanBuilder.assess` converts expansion/probe OSError or ValueError into `complete=False / inventory_unreadable`. The production-connected `run_tool_surfaces(..., assessment_inputs=...)` instead calls `builder.build` and `collect` directly before reaching its assessment branch. A missing/unreadable required source therefore escapes as an exception instead of the advertised incomplete assessment. The new builder helper has no production call site; its focused failure test does not cover the actual service path.

Independent control registered the same owner raising `OSError("required source unreadable")` during expansion. Direct builder assessment returned `False, inventory_unreadable`; existing service assessment raised the OSError and returned no outcome. No writer was invoked.

Expected correction: connect the guarded inventory/assessment behavior to the existing service without duplicating inventory policy or changing ordinary reporting/repair semantics. Test expansion and probe failures through `run_tool_surfaces`, retaining explicit incomplete diagnostics.

Contract: T008/T010 existing-service integration; owner-operations.md requires unreadable inputs to report incomplete with owner/reason; FR-002, C-001. This is a new assessment-path gap, not a claim that legacy reporting previously promised this envelope.

### [P2] F3: Later recheck I/O failure discards already known application results

Location: `src/specify_cli/tool_surface/repair.py:136` and `:295`.

The dispatcher accumulates successful OwnerApplyResults only in a local list. An OSError entering a later owner's recheck context unwinds the whole call before that list is returned. The earlier owner may already have written and accurately returned its succeeded IDs, but the caller receives neither those IDs nor a structured failed/skipped result for the batch whose lock failed.

Independent controls used two batches with deterministic root order. The first owner returned success; the second recheck raised `OSError("lock unavailable")`. A separate disposable-filesystem witness verified first/a contained exact prepared bytes `b"T1"`, second/a remained absent, and the aggregate API raised without returning results. The first writer used the held recheck context and returned valid IDs; the failing second writer was never entered.

Expected correction: retain already reported results when a later batch cannot enter recheck, and report its pre-write failure explicitly. Do not infer success for unknown writes, retry, promise rollback, or replace concrete owners' responsibility to report partial writes inside apply. Cover later lock/recheck acquisition failure after a preceding success, beyond the current single-owner returned-partial-result test.

Contract: T009.9 and its "apply failure after one recorded success" validation; owner-operations.md truthful actual IDs on I/O failure; FR-003. This finding is specifically a pre-write recheck failure after another batch's known success, not a request to fabricate results for an owner that throws after unknown writes.

## Scope and Provenance

- Exact lane: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-b`.
- Authored baseline: `0ff8914f7b474824126323a681b8bc3c722cb68d`.
- RED: `5441be33d4b46545062565ecbe7074d25e1aab1f`.
- GREEN reviewed: `411cd2eb00b20c29837b1a08b6db0d8d4f5023d0`.
- Execution HEAD: `411390c383f2c5182904e5c1a9c1d91875425a4d`; later coordination merge only. `git diff --exit-code GREEN HEAD -- src/specify_cli/tool_surface tests/specify_cli/tool_surface` exited 0.
- Authored diff: exactly ten owned files, 1282 additions / 77 deletions. Recovery/support/coordination ancestors excluded.
- Read full generated review prompt `a502b605ac474031a2f20d2b1827fbc2.md`, actual lane AGENTS.md and charter.md, resolved and source Renata profile, explicit profile directive/tactic sources, mission spec/plan/data-model/research and all five mission contract files, external task-authoring brief, wp02-handoff.md, wp02-parent-preflight.md, policy, owned source/tests and provider registry/discovery.
- No .codegraph directory in lane; ordinary targeted source reads/searches used.
- Reviewed source/tests remain unchanged; final worktree status clean. Only this external review report was authored. No installs/resync, push, source fixes, repository-root/coordination writes, or runtime verdict calls.

## Applied Governance and Boundaries

The first two shell commands were exactly the requested profile resolution and review charter context, in the requested lane with sync=0.

Applied Renata initialization: quality/correctness/security/standards review; identify actionable defects, do not implement changes or make product/WP-management decisions. Handoff is to parent and implementing owner. Modes: code review, design-contract review and scoped security review.

Used `spk-doctrine-profile-load` and `spk-run-review-wp`. Parent's explicit instruction supersedes generated prompt/skill instructions to persist a verdict: this report is advisory input to canonical persistence; parent alone writes the runtime verdict.

**#3908 disclosed:** command success did not mean complete governance activation. The resolver returned empty directives/tactics/references and unavailable-directive diagnostics. Applied explicit source bindings instead:
- 001: canonical registry/provider authority, leaf-value imports and separation from concrete writers.
- 024: exact authored scope; no neighboring implementation or opportunistic source edits.
- 030: independent tests/static checks; distinguish worker evidence from reviewer execution.
- 032: tool surface means the generated tool-facing artifact; assessment means in-process owner preparation, not a replayable JSON token.
- 041: non-vacuous original-entrypoint RED, mutation controls, no weakened assertions/xfails.
- 051: dependency/install review conditional scope checked; no dependency changes or installs, so registry/freshness/Node-install checklist is not applicable.

Applied incremental intent-first review, language/domain checks, test-to-contract reconstruction/readability, test-scaffolding boundary scrutiny, preservation of meaningful assertions, and conditional supply-chain safety. The test reconstruction was a comparison during review, not a claimed blinded reverse-speccing experiment or numeric score.

Actual charter additionally binds ownership/custom-content preservation, reviewer/implementer separation, exact evidence and no fabricated lifecycle state. No charter generation/activation repair performed.

Known pre_review hook **NO_COVERAGE** uses the wrong coordination identity. It is neither green evidence nor an attributed WP02 code/test failure. Did not rerun it or treat it as approval.

## Independent Verification

Inspected external `wp02-policy/sitecustomize.py` before test use. It forces sync=0 on Python environment assignments and child Popen environments, and rejects Python non-loopback socket connections. Shared conftest remained active; no assertion bypass. This is not an OS firewall guarantee for arbitrary native descendants.

All tests/probes used direct warm lane binaries, `env -i`, isolated HOME/USERPROFILE/XDG/AppData/SPEC_KITTY_HOME under `/tmp/wp02-independent-home`, `PYTHONDONTWRITEBYTECODE=1`, `CI=true`, `GIT_OPTIONAL_LOCKS=0`, and policy plus lane src in PYTHONPATH. Temporary write witnesses were confined to newly allocated disposable directories. No live SaaS or install was attempted.

Exact pytest selection (from lane, with that environment):

```sh
.venv/bin/pytest tests/specify_cli/tool_surface/test_operations.py tests/specify_cli/tool_surface/test_plan.py tests/specify_cli/tool_surface/test_repair.py tests/specify_cli/tool_surface/test_registry.py tests/specify_cli/cli/commands/test_tool_surfaces_fail_closed.py tests/specify_cli/cli/commands/test_doctor_tool_surfaces_config_error.py tests/specify_cli/cli/commands/test_agent_config.py -q -p no:cacheprovider --tb=short
```

Result: **121 passed in 12.38s**, exit 0. Includes all four owned test modules and 22 legacy caller checks.

Independent Ruff: `.venv/bin/ruff check --no-cache`, all ten changed source/test files: **All checks passed!**
Independent mypy: `.venv/bin/mypy --strict --cache-dir=/tmp/wp02-independent-mypy`, same ten files: **Success: no issues found in 10 source files**.

Meaningful adversarial controls:
- Original required-definition assertion GREEN on current builder; same assertion RED with baseline plan.py loaded from the pinned Git object in memory: "A selected required definition vanished without an instance or diagnostic". This is scoped old-builder reproduction, not a fresh full baseline checkout run. Worker raw RED log independently read: 1 failed / 17 passed.
- Changed-precondition strict test GREEN on current dispatcher. Loaded an in-memory repair-module mutant changing only the diagnostic-refusal condition to false; unchanged strict test failed. Thus the dispatcher refusal, not merely direct fake-writer invocation, was challenged. No source file mutation.
- Concrete registry floor GREEN; removal of actual command_skills registration made the nonempty floor assertion fail. Restored process-local registry through patch context.
- F1/F2/F3 controls independently reproduced as described above, with these outputs:

```text
ZERO_EXPANSION: different selected tools, identical owner inputs/statuses = True
DIRECT_BUILDER_ERROR: False inventory_unreadable
EXISTING_SERVICE_ERROR: raises OSError required source unreadable instead of assessment
LATE_RECHECK_ERROR: first owner writes = 1 returned results = none; exception = lock unavailable
RECHECK_CONTROL: original green
RECHECK_CONTROL: dispatcher diagnostic bypass killed by unchanged strict assertion
BASELINE_CONTROL: original entrypoint RED: A selected required definition vanished without an instance or diagnostic
REGISTRY_CONTROL: actual required registration removal killed floor
PARTIAL_CONTROL: prior owner result exists inside dispatcher, then dropped by OSError: lock unavailable
DISK_PARTIAL_CONTROL: first/a=T1, second/a absent; no aggregate result; OSError: lock unavailable
```

Parent's 99 passed / 2.62s and worker's 624 subsystem / 22 caller / 1642 fast / 94 architecture results remain attributed evidence, not my reruns. Read retained RED, architecture and static logs and handoff. Did not repeat full subsystem/fast/architecture or run parent-owned full CORE/E2E/wheel gates.

## Contract Coverage and Limits

| Concern | Assessment |
| --- | --- |
| Immutable values | Frozen nested validation rejects live lists/dicts/callbacks; exact hashes, link targets, modes and mtime observations retained. No writer/discovery imports in operations. |
| Registry completeness | Required missing/unsupported owner survives zero instances; nonempty registration floor and deletion control pass. Selected tool/definition context still lost: F1. |
| Optional/disabled | Existing focused unsupported optional/research-gap/disabled cases preserve not_applicable dispositions. These passing cases do not establish every downstream owner's applicability policy. |
| Original context | Nonempty status/instance object identity and projected input identity retained. Empty-selection limitation: F1. |
| Existing callers | 22 caller checks plus owned legacy tests pass; pinned report JSON not extended. Assessment failure path disconnected: F2. |
| Coalesce/conflicts | Same destination equivalent effects combine logical owners/surface IDs/proofs; conflicting bytes/mode/owner/root ID rejected; no hostile-link resolution or synthetic writer. |
| Recheck/consent | Lock context held through apply; changed diagnostic prevents writer; diagnostic-bypass mutation killed. No automatic retry, drift-consent change requires reassessment. |
| Exact prepared data | Dispatcher retains payload/observations and does not sample clocks or normalize hashes. Concrete advancing-clock/format-writer proof remains downstream. |
| Idempotence | Empty effect batches skip recheck/writer; no dispatcher timestamp refresh. Concrete second-apply filesystem idempotence remains downstream. |
| Partial results | Returned partial/omitted/foreign IDs have checks. Later pre-write exception loses previous results: F3. |

Recording owners prove mechanical API behavior only. The disposable byte-writing owner proves the narrow aggregate failure witness, not any built-in provider's completed implementation. No generic VFS, public JSON replay endpoint, concrete provider fix, public upgrade acceptance or mission acceptance is claimed.

## Generated Prompt Checklist

| Item | Verdict / evidence |
| --- | --- |
| 1. Dead code | FAIL in production integration: new builder assessment/error-conversion helper has no production caller; existing service bypasses it (F2). Operations module itself has live model/plan/repair/service imports. Staged apply API is explicitly reserved for downstream composition. |
| 2. Synthetic-fixture test | PASS for stated WP02 mechanics: tests execute production values, builder, registry and dispatcher. They are not public product acceptance. |
| 3. Silent empty return | FAIL for selection fidelity: zero-expansion context is erased before the owner call (F1). No claim that every intentional empty disposition is erroneous. |
| 4. FR coverage | FAIL for full scoped contract: FR-002/C-001 error and selection gaps; FR-003 partial-result gap. Existing assertions do cover substantial mechanics and FR-004 empty-batch no-write behavior. |
| 5. Frozen surface | PASS for authored baseline-to-GREEN diff: only ten owned files; concrete providers/startup/status/conftest/contracts untouched. |
| 6. Locked decision | FAIL: F1-F3 violate selected-owner fidelity, explicit incompleteness and truthful partial-result requirements. No VFS/replay/dependency prohibition breach found. |
| 7. Shared-file ownership | PASS: ten owned source/tests; recovery and coordination ancestry excluded, no neighboring edits. |
| 8. Production fragility | FAIL: service expansion/probe exception and later recheck exception lack the required structured outcome at their new assessment boundary (F2/F3). |

Parent action: return findings to WP02 owner, obtain focused regression fixes and independent re-review, then persist the canonical verdict through the supported serialized workflow. This report does not change WP state.

