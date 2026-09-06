---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T22:03:25Z'
reviewer_agent: codex
wp_id: WP05
---

---
audience: agentic-framework-core-team
type: reference
updated: 2026-09-07
---

# WP05 First Independent Review

**WP05: REJECT. Consumer integration for Op 01M1W6MA0EWJ38MJDQG2D50ZJ3: REJECT / not ready for closure.**

Reviewer Renata; readonly reviewer, not author. Parent owns event capture, lifecycle and Op closure. No source fixes, commits, status/COORD changes, push or merge performed.

## Findings

### F1 [P1] Provider dispatch writes global assets before checking the paired project

Owned anchor: [managed_skills.py:457](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-e/src/specify_cli/tool_surface/providers/managed_skills.py:457), specifically its independent global recheck/apply delegation at 457-465.

The advertised `SurfaceRepairService([GlobalSkillAssetsProvider(), ManagedSkillsProvider(...)])` route does not preserve the paired preflight in [installer.py:871](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-e/src/specify_cli/skills/installer.py:871). The global adapter retains only its global assessment. Approved WP02 dispatch applies each independent owner in sequence; it does not promise an aggregate global/project preflight.

Fresh reproduction uses the actual registry, owner preparation, both actual WP05 providers and actual WP02 dispatcher. Prepare a cold selected-skill installation, then change existing project `.kittify/config.yaml` before calling apply. Both preparations were complete and nonempty.

- Direct `apply_skill_installation`: both results `precondition_changed`, zero persistent changes.
- Advertised provider dispatch: global result `applied`, **8 succeeded IDs and 8 persistent creations**; project result `precondition_changed`, all 5 project IDs skipped.
- Created global paths include selected `SKILL.md`, its directories, inventory, cache directories and persistent lock.
- No concurrent process or hostile race is needed: the config change exists before dispatch starts.

Evidence: [independent-consumer.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/independent-consumer.log), [provider result/delta](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/changed-project-provider.json), [direct control](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/changed-project-direct.json), [test:86](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/test_consumer_independent.py:86).

This violates the requested operation-wide refusal before any write and contradicts the handoff's assertion that both routes hold whole global/project prechecks. It is a WP05 consumer-composition defect, not grounds to reopen approved WP02's per-owner semantics or modify frozen supplier code. The supported provider composition needs the paired guarded boundary, with an independent changed-project control proving zero global writes. Removing that contract or treating the resulting writes as an acceptable partial I/O failure would not resolve it.

### F2 [P2] Existing owners suppress newly added shared consumers in effects

Owned anchor: [installer.py:643](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-e/src/specify_cli/skills/installer.py:643).

`effect_owners = owners or tuple(new_owners)` selects only prior manifest owners whenever any exist. Example: a shared skill is recorded for codex; canonical content changes while the next installation selects codex and copilot. The update and retained backup effects carry codex only, while lines 653-654 add both agents to the prepared manifest. `write()` derives both logical owners and surface IDs solely from the supplied owner tuple.

The physical update therefore omits an affected selected consumer despite the required complete owner/surface set. Initial shared installation tests cover the empty-prior-owner branch; they do not cover this transition. Preserve prior ownership proof while representing all affected logical consumers.

**Evidence level:** source-level finding, not an independently executed reproduction. Identified during the initial source pass; no additional probe launched after F1 was established.

## Scope and Identity

Reviewed complete WP05 authored comparison from `e5698583e3d60a25e480e78eb8777c7bfa4b6802` through frozen author source `5f271f07fde9d6efeb16661c00e2205a04816a13`, using the cumulative diff, final owned production sources and changed test bodies. This includes original RED `61521de`, tidy `417087`, clock `48a80a`, slice `2b6314`, repair RED `3c1a84`, supplier chain and final integration. It is not a latest-commit-only review.

Actual execution HEAD: `a246ad860d4902589697f404f10b9e96ecbea154`. The author commit is its ancestor. Later differences are five mission status/review artifacts; product, tests, dependencies, .kittify and AGENTS bytes match the frozen author source. Initial exact-HEAD assertion failed honestly; retained in `provenance.stderr` and reconstructed original `provenance-first-attempt.py`. Revised check verifies ancestry and unchanged product scope rather than silently replacing the source identity.

[provenance-verified.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/provenance-verified.json) independently verifies all twelve owned SHA-256 values, author evidence hashes, direct interpreter/module identity, Python 3.11.15, pytest 9.0.3 and events 9.1.6. The receipt lists exact owned paths. Ten owned paths changed; `retired.py` and `test_manifest_repair.py` remain unchanged. [complete-wp05.diff](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/complete-wp05.diff) preserves the cumulative owned diff.

The three approved supplier files compare byte-for-byte to `2b653bc511b81a1b4ccbf06d60f491b044831633`: runtime/asset_preparation.py, runtime/agent_skills.py and tests/runtime/test_upgrade_preview_bootstrap.py. No supplier implementation or supplier tests were rerun. Reused [supplier approval](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/global-skill-selection-independent-review.md), [WP02 approval](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp02-cycle2-independent-review.md), and [WP03 approval](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp03-cycle2-independent-review.md) within their stated boundaries. Original differing untracked supplier content was untouched.

Final `git status --porcelain` and frozen-product `git diff --exit-code` both returned 0 with empty output. Files: `final-status.log`, `final-product-diff.log`.

## Independent Verification

All commands used the separate [isolated.sh](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/isolated.sh), cwd lane-e, direct warm binaries. [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/commands.md) records expanded paths and exact test commands. [invocations.jsonl](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/invocations.jsonl) records actual argv, UTC start/end, terminal status and per-invocation isolation checks.

| Execution | Actual result |
| --- | --- |
| Canonical reviewer-renata profile | Exit 0; builtin reviewer, no warnings |
| Canonical review charter context | Exit 0; #3908 degraded, zero resolved references |
| First provenance assertion | Exit 1; lifecycle HEAD differs from frozen author commit |
| Revised provenance validation | Exit 0; ancestry, product identity and supplier equality established |
| Focused author tests | Exit 1; **13 passed, 1 failed, 129 deselected**, pytest 31.09s |
| Independent consumer controls | Exit 1; **2 passed, 1 failed**, pytest 32.39s; stopped at F1 |
| Final source integrity | Exit 0; clean status, no frozen-product diff |

Independent positive control passed through actual WP02 dispatch with runtime, commands and the caller-selected skill in one global assessment: **164 global + 5 project effects**, exactly equal to independent filesystem net delta including hashes/kinds/modes/targets; every effect ID reported succeeded. Assessment left snapshots unchanged. Direct changed-project control passed with zero writes. Provider changed-project control failed as F1 describes.

Focused author passes cover actual selected-registry direct installation, preservation of a differing untracked global sentinel, direct skills-only and three-family exact delta, direct project preflight refusal, retained manifest bytes/time, manifest preconditions, operation-wide backups, partial succeeded IDs and verifier consent/link conversion. They are author-authored controls freshly executed here, not independent blanket coverage.

The one author failure is `test_coordinated_provider_dispatch_keeps_both_owner_batches`: it changes HOME but not the wrapper's external SPEC_KITTY_HOME. The global inventory remains under the external harness home, outside that test's tmp_path; its `relative_to(tmp_path)` oracle raises ValueError. All writes remained inside reviewer evidence. This is a fixture/environment mismatch, retained unmodified in [author-targeted.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp05-independent-evidence-renata/author-targeted.log); it is neither a product preflight reproduction nor a passing result. The separate independent fixture explicitly binds all home selectors and reaches the genuine F1 assertion.

No source or shared fixture was changed to make tests pass. No retries to green, xfails/skips, policy relaxation, supplier suite, broad architecture/subsystem/fast/public matrix or fresh static suite. Author 161-test/Ruff/mypy success logs were inspected and hash-verified as historical author evidence; not claimed independently repeated.

## Complete Criteria Disposition

PASS below means the stated bounded evidence supports that criterion; it does not certify unexecuted combinations.

| Criterion | Disposition |
| --- | --- |
| T023: real RED / tidy / clock witnesses | Historical commits/receipts retained and inspected; no fresh historical RED replay. Canonical completion remains parent-owned. |
| T024: pure project preparation / global delegation | PASS bounded purity and one selected global batch; FAIL complete logical owners, F2. |
| T025: deterministic operation-wide backups | PASS source/author evidence and fresh retained-clock/backup control; collision/exclusive-allocation controls inspected, not all freshly rerun. |
| T026: retained manifest bytes/time and zero churn | PASS bounded direct/manifest controls; FAIL aggregate provider precheck, F1. |
| T027: custom/link/consent/retired handling and existing callers | Existing direct install, provider repair and verifier paths inspected; fresh consent/link/direct sentinel controls pass. Shared-owner effects FAIL F2. Remaining retirement/custom permutations retain author evidence only. |
| T028: exact effects and integration evidence | Positive three-family real dispatch PASS; changed-project dispatch FAIL. Broad final gates remain mandatory later. |
| FR-002 complete visibility | FAIL F2; exact initial physical effects corroborated independently. |
| FR-003 plan/apply agreement | FAIL required paired preflight F1; positive unchanged-fixture exact effects pass. |
| FR-004 idempotence | Bounded direct no-churn control passes; not recertified across every provider/error/retirement combination. |
| NFR-004 preservation | Direct unknown sentinel and verifier consent/link controls pass; all-logical-owner completeness fails F2. No claim that F1 destroyed user content. |
| C-001 canonical authority | One delegated global writer retained; consumer coordination FAIL F1. Existing WP02/WP03 authority remains approved. |
| Source/config/manifest/destination inputs | Retained observations and owner-local checks inspected; targeted manifest checks and changed-config control executed. Aggregate provider handling FAIL. |
| Empty/retired catalog safety | Absent required catalog fails; explicit empty avoids retirement in source/author tests. No independent exhaustive malformed-catalog certification. |
| Partial results | Fresh author partial-I/O control passes; F1 records actual global successes/project skips, not fabricated rollback. |
| Public/root and final compliance | PENDING WP10/WP13 and parent gates. Eight public RED are not this WP's claimed root fix; no waiver. |

Generated prompt anti-pattern checklist:

| Item | Verdict |
| --- | --- |
| Dead code | FAIL / pending production wiring for new `GlobalSkillAssetsProvider`: only its declaration occurs in src; tests instantiate it. Existing direct assessment/apply APIs have real production callers. Test integration is not a production caller or completion of the downstream gate. |
| Synthetic fixtures | PASS for examined behavioral controls: real owners/registry/dispatcher and independent physical deltas; no fabricated literal success. |
| Silent empty returns | PASS bounded review: owner input failures become incomplete diagnostics; preserve/empty paths have explicit policy. Not exhaustive negative coverage. |
| FR coverage | FAIL overall: F1/F2 and pending final integration prevent acceptance. Existing positive assertions remain useful. |
| Frozen surfaces | PASS: twelve-path owner boundary plus three explicitly approved supplier cherry-pick files; no manual supplier edits. |
| Locked decisions | FAIL: operation-wide preflight and all-consumer effect obligations remain unmet. |
| Shared-file ownership | PASS authored file scope; supplier integration explicitly coordinated. Effect-level sharing fails separately in F2. |
| Production fragility | FAIL provider composition F1; owner-local refusal/partial handling otherwise has bounded evidence. |

## Governance and Isolation

Read full canonical review prompt and full original WP05 prompt, handoff first 230 lines, provenance/integration recipes, actual AGENTS, explicit binding charter, spec/plan and relevant owner/acceptance/CLI/corpus contracts. Applied canonical profile-load and WP-review skills plus resolved Renata initialization: correctness, quality and standards review; no implementation, product decisions or WP management. Generated lifecycle directions are superseded by the user's parent-only instruction.

Charter CLI returned success with empty references and unavailable-directive diagnostics (#3908). Explicit charter/profile rules remain binding; no empty-governance inference or activation repair.

Before tests inspected WP05 wrapper, WP02 sitecustomize, parent_frozen_policy, relevant shared conftest and external cache policies. Shared conftest remained active, explicitly loaded for external independent tests. Frozen venv hook both assigns cached_result and **returns its value**. Reviewer policy redirects only the existing scanner cache and asserts fixture sync=0.

OS policy denies all network; denies read/write under both /Users/robert and /System/Volumes/Data/Users/robert; denies writes outside this reviewer evidence dir except /dev/null. Checkout/shared Git and supplier worktree are therefore readonly. Every wrapped command first tests denied noncreating/nontruncating O_RDONLY/O_WRONLY opens on the known skill path for both aliases, denied checkout/shared-Git write opens, and denied socket bind; parent and child attempts to set sync=1 clamp to 0. env-i binds external HOME/USERPROFILE/XDG/AppData/tmp/cache. No resync/install, live-home inventory, credentials, rollback or historical F038 isolation claim.

The initial raw provenance failure and author test failure remain retained. Read-only path lookup failures before testing (root conftest.py absent; optional historical selection_policy.py absent) are recorded in commands.md. No policy bypass occurred.

Evidence is macOS/Python 3.11.15. The project guard is an in-process RLock; this report makes no cross-process project-lock, rollback, hostile-race-immunity, Windows execution, or universal Python-firewall claim.

## Parent Handoff

Capture **REJECT WP05**. Consumer seam disposition for supporting Op: **REJECT / closure not established**, despite positive selected-catalog and three-family integration. Correct F1 and F2, then independently review the bounded corrections; preserve original failed logs and approved supplier bytes.

No further probes were launched after the actionable F1 reproduction; only report/integrity work followed. All launched command handles are terminal. Parent's canonical review handle 9719 exit 0 is supplied dispatch context, not product approval. Full final contracts/architecture/current E2E/issue-matrix gates remain mandatory.
