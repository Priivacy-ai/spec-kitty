---
work_package_id: WP13
title: Integrated preview acceptance and architecture witness
dependencies:
- WP01
- WP10
- WP11
- WP12
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-002
- C-003
- C-004
- C-005
- C-006
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T065
- T066
- T067
- T068
- T069
- T070
- T071
history: []
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/upgrade/test_upgrade_preview_acceptance.py
- tests/architectural/test_upgrade_assessment_boundary.py
- tests/upgrade/test_upgrade_installed_wheel.py
execution_mode: code_change
owned_files:
- tests/upgrade/test_upgrade_preview_acceptance.py
- tests/architectural/test_upgrade_assessment_boundary.py
- tests/upgrade/test_upgrade_installed_wheel.py
role: implementer
tags: []
tracker_refs: []
---

# WP13: Integrated Preview Acceptance and Architecture Witness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

Legacy alias maps to canonical `spk-doctrine-profile-load`.
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty charter context --action implement --json
```
Apply initialization/boundaries/directives/tactics and independent handoff.
Read AGENTS.md and .kittify/charter/charter.md explicitly.
If #3908 yields empty structured governance despite success, disclose degraded
resolution and read explicit binding charter/resolved profile sources.
Do not invent activation, change governance or claim complete resolution.
Use warm direct binaries, no uv resync or model override.

---

## Objective

Demonstrate the integrated upgrade behavior through real public processes,
independent snapshots, source-free wheel execution and non-vacuous architecture
controls. Supply attributable evidence for parent final gates without claiming
approval from a narrow passing count or an unrelated expected failure.

## Context

Read the mission's spec.md, plan.md, research.md, data-model.md, wps.yaml and
all contracts before implementing these tests. contracts/acceptance.md is the
matrix authority; upgrade-cli.md is the exact flag/payload/process authority.
owner-operations.md fixes physical normalization, prepared bytes and ownership.
corpus-recovery.md fixes historical identity, event hashes and eight verdicts.
External task-authoring-brief.md assigns exactly T065-T071.

WP01's oracle is independently owned; consume preview_support without edits.
Do not copy production effect-building helpers into the oracle or fork a harness.
WP10 supplies integrated CLI/root/owner behavior, including upstream WPs.
WP11 supplies recovered corpus/receipt; WP12 supplies preservation-gate evidence.
Dependencies must be reviewed handoffs, not logs left by interrupted workers.

Only the three listed test files are writable in this implementation package.
Route product fixes to their real source owners with witnessed public red.
No source patch, shared conftest change, corpus edit, receipt rewrite or gate waiver.
Transient instrumentation is supplementary; unwrapped real CLI remains primary.
No replacement Typer app, mocked provider/installer, suppressed root callback,
prewarmed cold home or fixture setting that bypasses target validation.
New tests must fail for the intended regression, not unavailable APIs/setup.

Implementation entry after parent dispatch:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP13 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T065: Execute the Complete G0-G7 Public Purity Matrix

**Purpose:** Prove healthy previews are read-only from process entry.

**Steps:**
1. Create test_upgrade_preview_acceptance.py consuming the delivered WP01 harness.
2. Resolve actual source .venv/bin/spec-kitty absolutely before changing child HOME.
3. Capture source/distribution/module/version provenance and complete stdout/stderr.
4. Prepare project assets in a separate setup home before attaching measured cold
   home. No init/profile/doctor may warm a measured G0 fixture.
5. Instantiate all eight states from contracts/acceptance.md:
   G0 absent runtime/global roots; G1 all stale; G2 runtime-only stale;
   G3 global-skills stale; G4 commands stale; G5 healthy/current;
   G6 current markers with missing/stale command; G7 owned retired cleanup.
6. For every state run human --dry-run --verbose and legacy --dry-run --json,
   with and without --project, all --no-worktrees: 32 independent cells.
7. Add --plan-json for G0/G1/G5/G6/G7: five full-plan cells.
8. Require successful intended assessment and output, not purity from a crash.
9. Require actual pending global work disclosure for cold/stale human/full output;
   legacy summary must disclose work and the full-plan hint.
10. Repeat relevant non-CI/TTY/cache-present cells so CI/no-nag is not the reason
    preview avoids network/preferences/persistence.

**Files:** test_upgrade_preview_acceptance.py only; no preview_support edits.

**Validation:**
- Independent lstat observes ignored/untracked files, empty directories, links,
  bytes, modes, mtimes, manifests, cache and supporting assets.
- Git HEAD/refs/index are checked separately; no broad .git/.kittify exclusion.
- Pair snapshots with WP01's real-process transient-write observer/control.
- Unsupported syscall coverage is disclosed, not called zero filesystem writes.
- Every legacy stdout parses as one entire pinned-schema JSON value.

### Subtask T066: Execute Target, Schema and Effective-Flag Contracts

**Purpose:** Prove target validity independently of compatibility and process exit.

**Steps:**
1. Pin supported schema/current metadata 3.2.7rc1 rather than installed coincidence.
2. Run six targets: 3.2.6, 3.2.7rc0, 3.2.7rc1, 3.2.7rc2, 3.2.7, 3.2.8.
3. Cross each with human/legacy and with/without --project: 24 cells.
4. Add six full-plan cells and malformed empty/not-a-version/control-character
   targets across human/legacy/full; no traceback or silent ALLOW.
5. Add omitted target, unknown current and malformed known metadata.
6. Pair lower/higher with stale, too-new and corrupt schema; preserve both reasons.
7. Assert exact target-only legacy flags decision/case none/semantic 2 and
   pending_migrations []; compatible project state remains truthful.
8. Assert legacy dry-run process 0 does not erase semantic rejection.
   Human target rejection is 1; full target rejection is 2.
9. Non-dry --project --json remains planner-only; actual default --json normally
   returns outcome, but too-new schema returns full legacy planner/process 5.
10. Full-plan too-new keeps full envelope/process 5; standalone actual invalid
    target retains its distinct existing error outcome/process 1.
11. Exercise implicit --project --json plus hidden choice/check/latest separately,
    explicit --cli guidance conflicts and default guidance conflicts.
12. Standalone hidden operations remain positive controls in disposable homes.
13. Exercise redundant full/json/dry flags, --cli conflicts, target=value,
    reordered flags and help/version/parser errors without startup writes.

**Files:** test_upgrade_preview_acceptance.py; consume approved schemas as data.

**Validation:** Local-only schema registry, unchanged strict legacy schema/hash.
No extra repair keys/fake migrations or latest_source relabeling.
Higher target cannot imply shipped future migrations or bypass schema blockers.
No environment override can replace the real version validator.
Require raw output/exit, asserted intended result and unchanged asset observations.

### Subtask T067: Execute P0-P8 Plan/Apply/Repeat and Preservation

**Purpose:** Every physical effect agrees with application and second apply is quiet.

**Steps:**
1. Instantiate P0 repaired, P1 missing commands, P2 missing skills, P3 profiles,
   P4 missing manifests with retained files, P5 stale/truncated manifest/config,
   P6 combined command/skill/profile/manifest defects, P7 missing activations,
   and P8 mixed missing/drift/custom/link sentinels as specified in acceptance.md.
2. Repeat P6 with G0/G1: eleven variants total, not an arbitrary reduced sample.
3. Each variant uses independent human/legacy/full previews, real
   upgrade --yes --no-worktrees, then three repeated previews and second apply.
   Eight processes per variant, 88 total excluding setup.
4. Compare independent net physical deltas to declared full-plan effects:
   roots/paths/actions/kinds/modes and supporting manifests/directories/backups.
5. Require nonempty P1/P2/P3/P6 witnesses; logical surface counts are not file counts.
6. P8 permits independent repair while drift/custom bytes remain unchanged and
   existing noninteractive failure is visible; no second-run new churn.
7. Exercise both legacy config and pointer-charter P7 with preserved comments/
   unrelated sections; explicit empty remains empty and dangling pointer refuses.
8. Include disabled/advisory agents, shared codex/vibe root, Amazon Q exception,
   owned orphan pruning, native mixed sections and staged bundle members.
9. Include corrupt config/manifest/missing source: explicit blocked/incomplete,
   never all-agents fallback or complete no-work.
10. Exercise ownership/source/parent-link changes between preparation and apply
    through a focused seam in addition to ordinary unwrapped public runs.

**Clock/backup rules:**
- Per-invocation prepared bytes/hashes are exact even with advancing clock.
- Across independent runs normalize only owner-declared newly assigned
  installed_at/updated_at/last_upgraded_at fields, retaining raw JSON pointers.
- Sole additional exception: root /created_at of .kittify/skills-manifest.json
  newly created from absence in BOTH baselines.
- Existing manifest created_at and mission-meta created_at must remain exact.
- Mutation of either prohibited creation time must fail.
- Keep raw bytes/hashes and baseline absence proof; no whole-manifest masking.
- Backup paths are state-derived, never normalized away or treated as transient.
- Occupied candidates/legacy backups survive; racing allocation cannot clobber,
  merge or silently choose an unreported destination.
- Second apply retains bytes and mtimes, including already-current manifests.

**Files:** test_upgrade_preview_acceptance.py only.
Use WP01's independent oracle, not the production serializer as expected output.

### Subtask T068: Build Concrete Assessment Boundary and Mutation Witness

**Purpose:** A gate that catches regression cannot pass because its coverage shrank.

**Steps:**
1. Create test_upgrade_assessment_boundary.py using actual integrated source.
2. Enumerate a nonempty expected floor covering root CLI integration, composer,
   core dispatch and every selected built-in concrete assessment owner.
3. Derive discovery through the real registry but assert required owners/kinds
   independently; deleting one registration must not lower the expected floor.
4. Check assessment functions for forbidden writer/ensure/persistence calls and
   the required separate owner apply boundary.
5. Keep operations leaf imports independent from CLI/provider/writer graph.
6. In disposable source copies restore unconditional root ensure and insert a
   manifest save into an assessment; both mutations must make the gate fail.
7. Omit a required owner from scanning; floor must fail.
8. Pair syntactic checks with real public snapshots and transient-write controls.
   AST scanning alone cannot certify transitive I/O safety.
9. Record mutation identity/assertion and restore only disposable copies.

**Files:** test_upgrade_assessment_boundary.py only.
No edits to production, other architectural gates or shared conftest.

**Validation:** Healthy gate covers real code, not stub examples.
Forbidden-call mutations fail intended assertions, not import/setup errors.
No empty allowlist, blanket path exemption, skip decorator or fake source module.
Architecture changes require full architectural suite under parent gate policy.

### Subtask T069: Execute a Source-Free Installed-Wheel Witness

**Purpose:** Detect editable/source/template overrides hiding packaging failures.

**Steps:**
1. Create test_upgrade_installed_wheel.py using existing build tooling.
2. Build the ordinary project wheel in a disposable workspace/environment.
3. Install that artifact into an isolated test environment, never a global tool.
4. Record wheel SHA, build/source SHA, interpreter and dependency provenance.
5. Resolve installed console executable, distribution and module paths.
6. Clear PYTHONPATH, editable paths and source/template overrides injected by
   fixtures; run from disposable projects outside the source tree.
7. Assert imported package paths resolve to installed artifact, not CORE/src.
8. Replay required minimum: G0/G1/G5 previews, lower/equal/higher/malformed
   legacy/full target cells, P6 plan/apply/repeat and separate-consent control.
9. Keep actual owner/validator execution; no wheel test replacing services.
10. Record complete output, physical observations and process/payload distinctions.

**Files:** test_upgrade_installed_wheel.py only; consume WP01 helpers.

**Validation:** An editable install or missing-library fallback is not a wheel pass.
Parent-authorized package installations stay in disposable environments/caches;
retain package sources/warnings, do not call download runs network-free.
No production dependency change, resync, host credentials or live hosted traffic.
Source-free failures remain red; route fixes to the actual packaging/source owner.

### Subtask T070: Integrated Consent, Corpus and Performance Evidence

**Purpose:** Test preservation across integration rather than only local helpers.

**Steps:**
1. Preview/upgrade --yes against a blocked mission fixture; identity/events/
   snapshots/verdicts remain untouched without separate mission-repair consent.
2. Retain explicit positive consent demonstrating supported repair remains reachable.
3. Consume WP11's reviewed receipt and WP12 gate evidence without rewriting either.
4. Independently assert original recovered identity, 31 pinned restored blobs,
   surviving schema, exact two-document relocation and raw event hashes.
5. Verify eight complete review_result objects/done lanes and canonical snapshot
   output; second materialization retains bytes/mtime.
6. Run or consume parent-scheduled full corpus audit with exact source/executable
   provenance, exit 0 and zero TeamSpace blockers; four fixed names alone is not enough.
7. Preserve negative unknown/custom/backup/source-race controls from owner evidence.
8. Measure cold/warm preview p50/p95 against charter typical <2s budget.
9. Separate fixture/wheel construction from measured CLI process time; retain baseline.
10. Record Linux/macOS/Windows evidence and capability limitations, especially links.
    A platform skip needs explicit review and a capable-platform witness.

**Files:** test_upgrade_preview_acceptance.py for integrated assertions.
Synthetic fixtures cannot substitute for canonical corpus replay/history proof.
No corpus changes, blanket doctor --fix or invented status events in this package.

**Validation:** Raw history hashes and creation identity are never normalized.
A preserved warning is not a waiver of a required blocker.
Timing overruns and unsupported checks are recorded, not silently excluded.

### Subtask T071: Furnish Exact Parent Final-Gate Evidence

**Purpose:** Parent can assess full readiness without inferring it from narrow counts.

**Steps:**
1. Run three owned test files and full affected upgrade/architectural subsystems
   under the approved isolated fixture policy; record exact selection/results.
2. Run changed-file Ruff/mypy and calibrated final fast checks required by repo policy.
3. Link #3900-3903 to original public red, integrated green, actual source/data
   commits, snapshots/hashes and independent review records.
4. Supply the parent final gate table below; no runtime review PASS substitution.
5. Preserve argv/cwd, source/wheel SHA/dirty state, runner versions, effective flags,
   start/end/exit, collected/executed/deselected/skipped counts/reasons and JUnit.
6. Include nested drift stdout/stderr and intended assertion identity, not outer exit alone.
7. Report all tracked baseline failures with owners/dispositions; no xfail-to-green.
8. Obtain independent review; parent owns terminal issue matrix and final acceptance.

**Parent-owned final selections:**
- Final calibrated fast suite: retain its actual selection/count/exit; not full gates.
- CORE full tests/contract/: direct pytest -c pytest.ini, no marker narrowing.
- CORE full tests/architectural/: direct pytest -c pytest.ini, literal CI=true;
  required Git history/formatter/dependencies available, #3911 preservation intact.
- Full corpus: doctor mission-state --audit --fail-on teamspace-blocker --json;
  require exit 0/zero blockers and provenance, not a filtered four-case count.
- E2E full scenarios/: compatible E2E runner/config and explicit consistent CORE
  repo/bin/python bindings; all five surviving floor identities must execute.
- Terminal #3900-3903 issue matrix: fixed/verified-already-fixed/explicitly accepted
  deferred-with-followup plus evidence; pending/in-mission is not completion.

**Five E2E floor identities under scenarios/:**
- dependent_wp_planning_lane.py::test_dependent_wp_planning_lane_lifecycle_smoke.
- uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[specify].
- uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[plan].
- uninitialized_repo_fail_loud.py::test_uninitialized_repo_fails_loud[tasks].
- contract_drift_caught.py::test_contract_drift_caught.

Known recorded baseline: 2 failed/3 passed/0 skipped, not full-gate approval.
CORE #3912 planning ancestry and E2E
spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing#411 missing diary fake-package
collection failure require current tracked resolution/evidence.
Collection failure is not intended drift detection: require executed intended
envelope assertion AND unmutated green control.
SaaS scenario is retired by E2E e59564bd8b82f7912b8db67087712ec84fc47cf8 and
accepted CORE retirement ADR, not skipped/PASS; do not recreate transport.
Follow contracts/acceptance.md's full prerequisite/provenance table.

Shell sync=0 alone is not proof of effective fixture policy: shared conftest
can override it. Parent must establish isolation without disabling conftest
wholesale; flag=1 alone is not evidence of live SaaS transport.
No host/global writes, live credentials/endpoints or production network.
Relevant skips/exits remain visible and independently adjudicated.
No full-gate approval follows from narrow golden/owner test counts.

## Definition of Done

- T065-T071 each has exact executable evidence and canonical completion records.
- Full specified G/B/P matrices ran without fixture masks or missing-owner shrinkage.
- Source-free wheel subset ran against verified installed artifact.
- Oracle and architecture mutation controls failed for intended reasons.
- Clock/backup/path/identity preservation rules remain exact and independently checked.
- Actual subprocess failures route to source owners, not assertion weakening.
- Full-gate handoff includes exits/skips and unresolved prerequisites honestly.
- No source, harness, manifest, corpus, status or other WP files changed here.
- Independent reviewer approves implementation evidence; parent decides final mission gate.

Canonical event recording only after each subtask truly completes:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T065 --status done --mission upgrade-preview-mission-health-01M1V6E1
```
Repeat for T066-T071 with actual evidence. Never hand-edit tasks.md/status or
fabricate review/runtime completion. Author ran no implementation or gate commands.

## Risks

- False purity from early crashes: require healthy semantics plus unchanged snapshots.
- Reused setup homes: cold-state isolation must precede every measured process.
- Shared oracle edits: route corrections to WP01, never fork expected-value logic.
- Clock masking: exact owner/path exception only, raw/per-invocation evidence retained.
- Collection failure greenwash: require actual intended assertion and green control.
- Installed source leakage: record sys.path/module provenance and clear overrides.
- Scope creep: tests only; source owners fix witnessed product defects.
- Credits/interrupted workers: preserved logs alone are not complete handoffs.

## Reviewer Guidance

Review scenario selection and physical oracle before considering aggregate counts.
Check independent nonempty floors, ignored/link/mode/mtime controls and no source mocks.
Require every requested representation and actual too-new JSON exception.
Inspect installed artifact provenance and wrong-validator masking controls.
Demand exact protected history/backup/created_at handling and separate consent.
Confirm every architecture mutation reaches its intended assertion.
Reject xfail/skip waivers, narrowed full gates and optimistic pending-baseline summaries.
All listed tests/gates are implementation obligations, not author-executed results.
