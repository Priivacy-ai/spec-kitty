---
work_package_id: WP12
title: Evidence-bound archive preservation gate
dependencies:
- WP11
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-003
- NFR-004
- C-001
- C-006
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T060
- T061
- T062
- T063
- T064
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_archive_root_byte_identical.py
create_intent:
- tests/architectural/test_upgrade_recovery_preservation.py
- tests/upgrade/test_mission_corpus_recovery.py
execution_mode: code_change
owned_files:
- tests/architectural/test_archive_root_byte_identical.py
- tests/architectural/test_upgrade_recovery_preservation.py
- tests/upgrade/test_mission_corpus_recovery.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP12 - Evidence-bound archive preservation gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Correct the archive gate so exact, valid lifecycle appends and the independently
reviewed #3903 recovery can pass while historical evidence remains protected.
Require byte-prefix, kind/mode, canonical replay and exact relocation proofs;
retain rejection of every unrelated edit, forged recovery and baseline bypass.

## Context

Audience: Python implementer and independent preservation reviewer.
Approved reslice: plan D6 and corpus-slicing-adjudication.md transfer persistent
corpus regressions, not data ownership or acceptance authority, to WP12.
This prompt describes future work only. Its author has not changed gate code,
run product tests, committed, emitted status, dispatched an Op or advanced runtime.

Absolute repository root checkout:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`.
Absolute mission root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`.
The runtime resolves the later execution workspace; use that returned absolute
root for implementation commands. Do not invent a worktree or base branch.
Frontmatter ownership and Git paths remain repository-relative by schema.

Read these binding authorities after loading the assigned profile:

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/corpus-slicing-adjudication.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/AGENTS.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/task-authoring-brief.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/archive-freeze-remediation-design.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/archive-freeze-issue.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/archive-freeze-reproduction.log`.

Planner Priti resolved from builtin: planning/decomposition/sequencing only,
directive 003 (document decisions), no tactic references.
Resolved author profile source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`.
Directive source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/directives/003-decision-documentation-requirement.directive.yaml`.
Tasks context returned empty directives/tactics/references with unresolved
governance diagnostics: known #3908, not a successful empty-governance verdict.
The explicit charter above remains binding; do not activate or repair governance.
Load Pedro through the resolver and apply its actual initialization, boundaries,
directives and tactics. Preserve the project's supported Python floor.

### Dependency and Ownership Boundary

WP11 is the only manifest dependency, confined to planning data and receipt:
corpus restoration/relocation, snapshot application, archive index, rename spine,
and `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json`.
WP11 retains actual pre-data audit RED, no-churn/mutation and full-audit evidence;
WP12 owns persistent corpus regressions, not application of the recovery.
The receipt is planned, not present at author inspection. Consume its delivered
schema, exact verified values and independent review; do not fabricate delivery.
Parent owns diagnostic classification, issue tracking and independent review.
WP12 cannot approve its own admission predicates or WP11's receipt.
WP13 consumes final evidence later; do not start or author WP13 here.

WP12 implementation may edit exactly the three frontmatter test paths.
Both new test files are explicitly declared in create_intent.
No code WP owns kitty-specs; never hide Python in docs or mutate data to pass.
The existing gate file is the nonempty authoritative_surface; this test-only
code_change has no owned production source prefix. Do not invent src ownership
or derive an empty common prefix (#2446).
Keep helpers in the owned tests; no generic exemption registry or policy package.

Do not edit runtime/lifecycle writers, reducer, charter, shared conftest, markers,
architectural baselines, old M1 dossier, corpus data or receipt.
No blanket archive/root/snapshot/Op exemption, skipped product bugs, xfail,
version changes, resync, global assets, state fabrication or remote pushes.
Canonical status commands below are future instructions, not author actions.

### Existing Seams to Inspect

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/audit/test_audit_cli.py`: real doctor mission-state CLI and report assertions.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/audit/engine.py`: full discovery, findings and teamspace_blockers aggregation.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/cli/commands/_mission_state_doctor.py`: public audit/materialization routing, read-only dependency.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/architectural/test_archive_root_byte_identical.py`: existing gate.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/invocation/lifecycle.py`: exact path and append writer.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/invocation/record.py`: ProfileInvocationRecord.from_dict.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/status/reducer.py`: pure snapshot and JSON preparation.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/invocation/test_lifecycle_pairing.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/status/test_shared_reducer_materialization.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/scripts/docs/rename_reconcile.py`: navigation evidence only.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/docs/context/ops-vs-missions.md`: lifecycle versus per-Op distinction.

Current gate uses merge-base(HEAD, origin/main), root-scoped name-status,
line splitting and parts[-1]; it rejects every existing changed path except
the separate whole-path rename-spine exception. Do not copy that exception.
The existing nonempty-baseline test and no-import-time-skip guard must survive.
Read lifecycle bytes directly: read_lifecycle_records skips malformed rows.
Use the full materialize_snapshot plus materialize_to_json composition;
transition-only reduction misses annotations, identity and other projections.

### Subtask T060: Retain observed #3911 RED and original append-permitting authority

**Purpose**: Establish a truthful defect witness and bounded authority before
changing the gate, with all observed archive changes independently classified.

**Steps**:

1. Preserve the external reproduction: source baseline
   c0054153b9bce0778cf41a85d11ecd4e9650031d, reported planning HEAD
   6ada9613b8b8713809da4089bda11d9d35065a77, exit 1,
   1 failed / 2 passed in 1.30s. The reported assertion names
   `M\tkitty-ops/lifecycle.jsonl`; do not label this a fresh run.
2. Record current execution SHA, resolved origin/main merge-base, Git status
   and test/executable provenance before editing. Retain the original comparison
   semantics; do not shift refs, compare against HEAD only or hide dirty paths.
3. Recover the original operator decision read-only with:
   `git show 7afd572fc:kitty-specs/retire-doctrine-term-01M0JMK9/decisions/DM-01M0P6C8C7Q6SPBT412V39RPN0.md`.
   It explicitly says "runtime may keep appending new records."
   This permits supported appends, not edits/renames/deletes of old proof.
4. Reconcile M1's scoped byte-freeze with the enduring history rule.
   Keep the four-root coverage; update misleading universal M1 wording only
   in the owned gate, never in the archived authority or historical decisions.
5. Inspect touched gate helpers for focused tidy-first extraction.
   Separate byte-oriented Git reading, candidate observation and operation
   classification inside the existing test module; avoid a new framework.
6. First add a regression that invokes the pre-existing gate against a real
   disposable Git repository with a nonempty archive baseline and reachable
   origin/main. Produce a valid suffix through append_lifecycle_record.
   Require gate acceptance; witness the current assertion failure.
7. Call the real gate body with only its repository root rebound for isolation.
   Do not mock Git diff/blob reads, the parser, writer or validator.
   A new-helper import failure or forced assertion is not the defect witness.
8. In the governed execution workflow, commit the observed RED tests separately
   before the gate fix; retain exact command/output and red commit SHA.
   Then perform any behavior-preserving tidy-first extraction as a distinct step.
9. Obtain the parent's full changed-path diagnostic and classification.
   Preserve unrelated failures and return them to their owner; do not treat
   #3911 as permission to excuse all current archive changes.

**Files**: Existing archive gate plus new preservation test; approximately
50-90 regression/setup lines before the functional change.

**Validation**: The exact pre-existing gate fails on a genuine valid append,
while the nonempty-base and reachable-base controls execute.
A new-path addition control remains allowed under original policy.
Raw historical evidence is only read; fixtures and evidence are disposable.
Unclassified changes block acceptance, not the authoring of this prompt.

### Subtask T061: Exact lifecycle byte-prefix, kind, mode and new-row validation

**Purpose**: Replace one incorrect whole-file freeze with the owner's actual
append-only contract, without expanding any other runtime-history exception.

**Steps**:

1. Consume LIFECYCLE_LOG_RELATIVE_PATH from invocation.lifecycle.
   Match that exact repository-relative path; no kitty-ops/*.jsonl wildcard.
   Per-Op invocation files and ops-index use different contracts and remain
   outside this narrow correction, with future failures reported separately.
2. Read the baseline Git blob as bytes, retaining object ID and Git mode.
   Inspect candidate and every parent without following escaping symlinks.
   Require regular-file kind and unchanged tracked executable mode.
3. Reject deletion, rename, type/symlink replacement and mode change even when
   content would otherwise match. Check working-tree and staged candidate
   evidence consistently; do not accept a dirty worktree that disguises a
   different staged destination.
4. Accept unchanged bytes with unchanged kind/mode, or require candidate bytes
   to start with the entire baseline bytes exactly.
   Never decode/reserialize old rows before prefix comparison.
   Preserve spaces, line endings, ordering, legacy fields and historical tails.
5. For extension of a nonempty baseline require a complete record boundary.
   Reject an unterminated historical tail rather than silently repairing it.
   Require a nonempty suffix of complete UTF-8 JSONL records with final LF.
6. Parse each appended row as a JSON object and call
   ProfileInvocationRecord.from_dict on every row.
   Reject malformed UTF-8/JSON, truncated lines, blank non-record rows and
   canonical-model errors. Never use the skip-corrupt lifecycle reader.
7. Preserve canonical optional-field semantics; do not invent pairing, timestamp,
   cross-mission correlation or signature requirements.
   An orphan started record is a legitimate observable runtime state.
8. Explain the integrity limit precisely: prefix/model validation proves
   preservation and format, not authenticity of unsigned new records.
   A schema-valid invented appended row is not cryptographically detectable
   from a file diff; positive provenance comes from the writer/workflow/review.
9. Return explicit offending path/reason diagnostics; parsing or Git read errors
   fail closed rather than becoming empty success.
10. Keep default freeze for all other existing files and preserve non-vacuity.
    Leave the existing rename-spine exception unchanged unless separately
    authorized with its own evidence; it is not a pattern for new admissions.

**Files**: Existing gate helper/dispatch and focused new test cases;
approximately 50-100 helper lines plus table-driven tests.

**Validation**: Exact valid append and unchanged cases pass; old-byte rewrite,
old-row delete/reorder, prepend/truncation/newline conversion, invalid suffix,
mode/type change and escaping parent fail. Assert direct row-parser invocation
for the complete suffix using invalid middle-row controls, not reader counts.

### Subtask T062: Persist corpus regressions and admit exact reviewed recovery evidence

**Purpose**: Admit only WP11's verified recovery operations while keeping the
receipt subordinate to approved scope and independently checked provenance.

**Steps**:

1. Wait for actual WP11 delivery and independent review. Read its receipt and
   retained execution evidence without editing them. Record the reviewed receipt blob/digest
   and source/recovery commit identities in the gate's bounded test evidence.
   Do not trust a candidate "reviewed": true flag or its self-reported hashes.
2. Constrain receipt entries to the exact approved operations below.
   Reject missing, duplicate, extra, traversal, absolute or redirected paths.
   Bind expected input/output/mode values to reviewed evidence and original
   Git objects. A candidate receipt change cannot expand its own authority.
3. Author admission predicates in the existing gate; keep independent attack
   fixtures in the new preservation test and corpus regressions in the new
   upgrade test. Do not use a test asserting candidate equals
   its own freshly computed receipt as evidence of historical preservation.
4. Admit only the two status.json targets: doctrine-drg-silent-drop-boundary-
   01M0PE7E and symbolkey-source-module-01M0B0SF (full slugs below).
   Require unchanged identity/meta, raw events and all other reducer inputs,
   preserved modes, original snapshot blob/OID and reviewed input/output hashes.
5. Compute candidate expectation read-only as
   materialize_to_json(materialize_snapshot(resolved_mission_dir)).
   Encode identically and compare exact bytes, not selected fields.
   The gate must never call materialize(), save or CLI repair to fix its input.
6. Independently verify all five plus three done lanes, all eight complete
   review_result objects, transition identities, force/cancellation provenance
   and annotations against WP11's retained evidence.
   Current reducer agreement alone cannot authorize a new archived output.
7. Require BOTH the reviewed recovery result and current canonical replay.
   If the reducer changes later, a different output remains a failure needing
   new independent adjudication; do not regenerate pins to get green.
8. Relocation admits exactly commit-history-notes.md and deletion-manifest.md
   from kitty-specs/R2-T1-local-legacy-removal to
   docs/archive/program-evidence/R2-T1-local-legacy-removal.
   Require old source blob/mode, source absence, exact destination bytes/kind/
   mode, confinement and tracked candidate index/commit membership.
9. Use an unscoped NUL-delimited Git change view retaining both rename endpoints.
   Prove the same move for R100 and equivalent delete/add; never depend on
   similarity or parts[-1]. Validate outside-root destinations explicitly.
   An untracked-only copy, divergent collision or missing source proof fails.
10. The 31 original cyclic-mission restorations are additions under the original
    base, already permitted; they require no new freeze exemption.
    Verify WP11's receipt against source commit
    3442ca1afc20b1b83b27a7bc64fd7014050b12a1, all 31 blobs/modes, original ID
    01M0QCK4D9D65AVNC15HKWAQZ7 and surviving schema. Do not repair them here.
11. Consume the archive index and exact rename-spine navigation evidence.
    Neither a navigation row nor a directory-wide move declaration proves
    destination bytes. No third file receives relocation admission.
12. Maintain protection of the exact relocated destinations after landing.
    A later merge-base containing the recovery must pass unchanged data and
    reject later mutation/deletion/mode changes; do not demand a fresh move.
    Keep receipt/provenance checks active when the original diff disappears.
13. Transfer ALL persistent T054-T059 expectations from the original committed
    WP11 prompt into the upgrade test. Build original and corrupted counterfactual
    fixtures from pinned Git provenance, not only the already-recovered checkout.
    Use original baseline c0054153b9bce0778cf41a85d11ecd4e9650031d and restore
    source above; prove deletion against convergence
    2554bd13adc289d3457681308645fe52619bca0e and its first parent.
    Desired-health/preservation assertions must actually fail on original or
    independently corrupted inputs, then pass on recovered controls through
    public audit/replay seams. No import error, synthetic failure or mocked audit.
    Retain WP11's earlier actual audit RED; do not claim these tests predated data.
14. Require exact 31 restored paths/blobs/modes plus the retained schema, including
    hidden dossier files and zero-byte .gitkeep. Assert original ID, created and
    accepted timestamps, all 71 task rows and schema provenance from the contract.
    Metadata-only restoration, missing blob, changed ID/date or a forged matching
    receipt must fail. Independently inventory disk/Git, not receipt paths alone.
15. Assert exactly two R2 moves, no old directory/stub/meta/alias, exact source
    provenance and destination bytes/modes. Verify archive index classification,
    contextual links and exact two rename-spine additions while retaining prior
    rows/comments. Wrong path, attribution, index or parent symlink must fail.
16. Assert exactly two corrected snapshots and five plus three complete verdicts:
    reviewer/review references, done lanes, identities/order, annotations and
    force/cancellation provenance. Doctrine mission_type becomes software-dev;
    pinned events/meta remain byte-identical. Omitted verdict fields and
    canonical-looking but unreviewed output fail. Do not silently replay a third
    cyclic snapshot; report new drift for separately evidenced parent disposition.
17. Repeat real restore/move/replay in disposable copies using the evidenced
    operations; compare bytes, kind/mode and mtimes across the full affected set.
    Missing move source is success only with exact completed-destination proof.
    Reject same-bytes mtime churn, unknown actions, omitted/extra paths, forged
    receipt/history and unrelated archive edits. Each negative has a passing
    unmutated control. Fixtures copy historical facts, never invent runtime state.
18. Protect reviewed receipt, index, rename-spine recovery rows and all recovered
    results after landing, including when the original diff is no longer visible.
    Keep new-file restoration policy distinct from permission to rewrite history.

**Files**: All three owned tests; bounded gate predicates, preservation attacks
and local persistent corpus fixtures. Receipt/data corrections go to WP11.

**Validation**: Delivered unmodified receipt plus genuine canonical snapshots
and exact tracked moves pass; missing or forged evidence fails closed.
Run a read-only snapshot of gate inputs before/after evaluation to prove the
gate did not repair its own candidate.

Exact reference identities from the design, to verify against WP11 delivery:

| Target | Required raw-event SHA-256 |
| --- | --- |
| doctrine-drg-silent-drop-boundary-01M0PE7E | 518d572629a39d026341d0cc26f47cc1a87c5f3323e21c5b8759cd0a02477b20 |
| symbolkey-source-module-01M0B0SF | 7e0326d9d1a9af04f3d1ce353e0b97caba765aab298de01074df4b889a455aaf |

| Relocated filename | Required destination SHA-256 |
| --- | --- |
| commit-history-notes.md | 65f17f5e7790d15b7128ee0f9ce72fd4034aaf616a074720dddef6967fbdd714 |
| deletion-manifest.md | 434870d0fe56e7a7187e3a47cd8ad9339cceba7f7b18dda8831e45e69741eaa8 |

The design's old/canonical snapshot hashes are observations to reconcile with
the delivered reviewed receipt, never substitutes for canonical replay.

### Subtask T063: Mixed-diff, forged-history, escaping-link, wrong-output and post-landing controls

**Purpose**: Make every narrow admission fail when its preservation evidence
is invalid, and prove one accepted operation cannot conceal another violation.

**Steps**:

1. Use real disposable Git repos with concrete nonempty archived files and
   origin/main refs. Rebind only the test repository; retain real Git plumbing.
   Parameterize attacks independently so one early failure cannot mask others.
2. Lifecycle attacks: modify one old byte, remove/reorder an old row, prepend,
   truncate, change newline bytes, add malformed/truncated JSON or invalid UTF-8,
   replace with a symlink, change executable mode or replace a parent with a link.
   Assert the specific preservation diagnostic, not any exception/nonzero exit.
3. Mixed-diff attacks: a valid lifecycle append plus an unrelated archived spec
   edit/delete, raw-event edit, quarantine edit or retrospective change.
   Each must fail despite the permitted append; keep all four roots covered.
4. Snapshot attacks: forge a lane/review value, change raw history, change
   identity/meta, drop annotation/provenance, select the wrong mission or supply
   non-canonical JSON bytes. An unrelated status.json edit must fail.
5. Receipt attacks: change expected hashes to match forged candidate bytes,
   remove an operation, add a third path, duplicate an entry, change source
   commit/OID/mode or replace reviewed input hashes.
   Change receipt and candidate together; trusted provenance must still reject.
6. Simulate canonical reducer and snapshot changing together while the reviewed
   receipt stays fixed: reject the changed result. Do not weaken input pins or
   fabricate historical metadata just to make the reducer accept a fixture.
7. Relocation attacks: source deletion with no destination, wrong destination,
   one-byte corruption, untracked-only destination, wrong mode, escaping link,
   divergent pre-existing destination and undeclared third relocation.
   Include Git path names needing NUL parsing in ordinary-protection controls.
8. Test R100 and delete/add representations with identical approved endpoints.
   Both pass only with exact proof; rename into/out of the four roots must not
   evade ordinary historical protection.
9. Post-landing fixture: commit the genuine recovery, make that commit the
   fixture's origin/main baseline, then check unchanged recovered state passes.
   Mutate/delete each protected relocated document and each snapshot in turn;
   all fail. Also test a later canonical-looking rewrite and forged new receipt.
   Advancing the disposable ref simulates landing; never move real refs to hide RED.
10. Retain a missing-base CI=true failure and an empty-baseline failure.
    Strengthen the structural floor to require named gate tests actually exist;
    all(empty) and import-time skip removal must not silently reduce coverage.
11. After each attack prove an unmutated positive control passes.
    Mutation controls alter disposable copies only, never the shared checkout.
    Preserve failed assertion identities, candidate diff and source hashes.

**Files**: New preservation test and minimal exposed helpers in existing gate;
approximately 100-170 test lines using parameterization.

**Validation**: Every attack fails for its intended reason; all permitted
operations and the post-landing unchanged control pass.
No xfail/skip, generic pytest.raises(Exception), mocked success, empty receipt
or changed baseline substitutes for an executed preservation assertion.

### Subtask T064: Real owner witnesses, full-corpus zero controls and subsystem regressions

**Purpose**: Prove the delivered gate is wired into real behavior and survives
attempts to remove its checks, then obtain independent review.

**Steps**:

1. Execute a positive append through append_lifecycle_record in the disposable
   repo and feed its real Git delta to the actual gate.
   Preserve old bytes and parse every suffix row; no hand-built success report.
2. Exercise the existing public next lifecycle seam in an isolated initialized
   fixture. Satisfy actual requested actions before reporting success.
   Confirm real append bytes and successful command behavior; dispatch alone
   is not proof that the shared lifecycle writer ran.
3. Reuse the existing next lifecycle test's legitimate setup/identity seams.
   Do not copy its historical import-error RED claim as this WP's evidence.
   No patched lifecycle writer/parser or bypassed gate in the positive witness.
   Do not execute runtime actions against this planning mission.
4. Run gate self-mutations in disposable test-module copies:
   replace exact-prefix checking with unconditional path acceptance;
   remove destination tracking/hash checking; omit one ordinary archive root;
   accept candidate-controlled receipt hashes; remove a protected gate function.
   Each must make the corresponding independently asserted control fail.
5. Run all three focused files, then architecture, upgrade, audit, status,
   schema/doctor consumers and invocation/next regressions, and make test-fast.
   Record all counts and named assertions, not only an outer green exit.
6. Use direct warm binaries; no uv sync or dependency resync.
   Child HOME/USERPROFILE/XDG/APPDATA/LOCALAPPDATA/SPEC_KITTY_HOME and temp roots
   must resolve inside disposable fixtures. Clear escaping overrides; sync=0 last.
7. Establish effective sync-off fixture policy with the parent before execution:
   shared conftest may overwrite the outer value to 1.
   Do not disable conftest wholesale, weaken guards or call an outer env var proof.
   Require reachable comparison objects, pytestarch/formatting dependencies,
   literal CI=true and cleared inherited PYTEST_ADDOPTS for architecture.
8. Attribute pre-existing failures with exact output/base evidence and linked
   issue under charter policy; parent routes unrelated repairs.
   Missing objects/imports, platform limits and relevant skips remain unmet
   evidence, never blanket waivers or product acceptance.
9. Submit gate plus WP11 receipt/data evidence to an independent preservation
   reviewer. Neither producer approves its own exemption.
   Parent retains final corpus/terminal acceptance; WP12 must deliver persistent
   full-corpus zero-blocker controls, not delegate them back to WP11.
10. In the new upgrade test run the real public doctor mission-state audit over
    the entire recovered disposable corpus: exit 0 and
    repo_summary.teamspace_blockers == 0, complete stdout as one JSON object.
    Prove nonempty discovery, restored mission present, relocated directory absent;
    no hardcoded historical total (424), empty scanner, --fixture-dir,
    --include-fixtures, mission filter or four-directory substitute for this gate.
    Original provenance must expose the two identity and two snapshot-drift
    failures by finding code; corruption controls must fail the zero assertion.
    Repeat on the final recovered tree after parent landing; retain corpus
    membership and exact delta inventory independently of the receipt.
11. Preserve separate consent regressions through the real damaged-corpus upgrade
    seam: --yes alone cannot authorize mission-state repair or alter metadata,
    events/verdicts; explicit separate consent must reach the intended owner path.
    Assert actual owner effect/no-effect and filesystem evidence, not a startup
    crash or mocked plan/apply success. Use the existing successful human upgrade
    finalizer and independent consent owner, with a real TTY approval for the
    positive control; JSON or failed-upgrade early returns are not that witness.
    No new WP10 API is required and no WP10-owned file may be edited here.
    Isolate existing startup writes; WP13 T070 reruns against integrated WP10.
12. Record commands, SHAs, finding codes, raw evidence hashes and no-churn results.
    Additional blockers are failures to route, not reasons to lower thresholds.
    WP11 data approval never means #3911 is green; no backward dependency,
    waiver, producer self-approval or retroactively fabricated RED/receipt.

**Files**: Three owned tests only; keep fixture helpers local and bounded.
No edits to consumed writer/reducer/test seams or shared architectural config.

**Validation commands**, future execution only from resolved absolute workspace:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 CI=true PYTEST_ADDOPTS= PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -n0 tests/architectural/test_archive_root_byte_identical.py tests/architectural/test_upgrade_recovery_preservation.py tests/upgrade/test_mission_corpus_recovery.py -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 CI=true PYTEST_ADDOPTS= PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -n0 tests/architectural/ -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/specify_cli/invocation/test_lifecycle_pairing.py tests/specify_cli/next/test_next_invocation_lifecycle_seam.py tests/status/test_shared_reducer_materialization.py -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/upgrade/ tests/audit/ tests/status/ tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py tests/specify_cli/cli/commands/test_mission_state_doctor.py tests/cli/commands/test_doctor_mission_state.py -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PATH="$PWD/.venv/bin:$PATH" make test-fast
.venv/bin/ruff check tests/architectural/test_archive_root_byte_identical.py tests/architectural/test_upgrade_recovery_preservation.py tests/upgrade/test_mission_corpus_recovery.py
.venv/bin/mypy --strict tests/architectural/test_archive_root_byte_identical.py tests/architectural/test_upgrade_recovery_preservation.py tests/upgrade/test_mission_corpus_recovery.py
```

Full-corpus witness, future only from the isolated recovered absolute root:
`SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty doctor mission-state --audit --fail-on teamspace-blocker --json`.
Repeat after parent landing; never run mutation/repair on this authoring checkout.

Run every added/changed test and retain the full architectural sweep; no
make test-full. These are prescribed checks, not claimed results.
Gate evaluation itself must leave source/data/receipt/index/refs unchanged.
Record argv/cwd, resolved base/SHA, environment, collected/executed/pass/fail/
skip counts, stdout/stderr, RED/fix commits and independent reviewer evidence.

## Definition of Done

- T060 retains the original RED and fresh pre-fix behavioral evidence with
  separate test-before-fix commit identity and focused tidy-first record.
- T061 admits only exact lifecycle prefixes with valid new rows and preserved
  kind/mode/confinement; old bytes and ordinary archive coverage remain intact.
- T062 uses the exact independently reviewed WP11 receipt plus canonical replay,
  source provenance and tracked byte-identical relocation endpoints.
- T063 rejects forged receipt/history, mixed unrelated diffs and escaping links;
  genuine unchanged recovery remains protected after landing.
- T064 passes real writer/public lifecycle controls, self-mutations, focused
  regressions, full architectural subsystem and lint/types with honest outcomes.
- T062/T064 retain full 31/2/2/eight-verdict, no-churn, counterfactual and
  whole-corpus zero-blocker regression coverage from WP11 without acceptance waiver.
- Only three test paths changed; no receipt/data/runtime/governance modifications.
- Parent receives independent review and evidence; no fabricated completed gates.

Canonical implementation command, for later execution only:
`spec-kitty agent action implement WP12 --agent codex --mission upgrade-preview-mission-health-01M1V6E1`.
Use sync=0 and the resolved absolute warm executable. Runtime chooses the lane.
Do not execute this command while authoring the prompt.

Completion is event-sourced, not a checkbox or frontmatter lane.
After each subtask has its evidence, the future implementer records:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T060 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T061 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T062 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T063 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T064 --status done --mission upgrade-preview-mission-health-01M1V6E1
```

These are instructions only. Do not execute them during authoring or hand-edit
tasks.md, manifests, metadata, status snapshots/events or review verdicts.

## Risks

- Mutable receipt self-authorization: bind reviewed values to original objects
  and exact approved paths, including simultaneous receipt/candidate attacks.
- Reducer drift blessing rewritten history: require reviewed output AND replay.
- Root-scoped diff misses moved proof: inspect both endpoints and protect the
  exact destinations after landing.
- Tolerant lifecycle reader hides corrupt suffix: validate every new row directly.
- Valid unsigned rows mistaken for authentication: state the limit; preserve
  original history and require real writer/workflow provenance.
- Unrelated archive changes swept under #3911: default rejection remains.

## Reviewer Guidance

Reproduce actual old-gate RED and final GREEN; inspect fixture Git blobs, modes,
new-row parser, pure replay calls and protected relocation endpoints.
Verify the candidate cannot choose its trusted receipt or rewrite historical pins.
Check all negative controls, post-landing baseline and nonempty-root floor.
Reject path-only exemptions, shifted real refs, skip waivers and self-repairing gates.
Verify scope against all three manifest paths and exact five subtask IDs.
Return findings/evidence to the parent; do not self-approve or start WP13.
