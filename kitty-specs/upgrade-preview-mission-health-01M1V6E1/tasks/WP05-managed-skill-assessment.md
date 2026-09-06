---
work_package_id: WP05
title: Managed skill assessment and deterministic backups
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-002
- FR-003
- FR-004
- NFR-004
- C-001
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/skills/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/skills/installer.py
- src/specify_cli/skills/manifest.py
- src/specify_cli/skills/paths.py
- src/specify_cli/skills/registry.py
- src/specify_cli/skills/verifier.py
- src/specify_cli/skills/retired.py
- src/specify_cli/tool_surface/providers/managed_skills.py
- tests/specify_cli/skills/test_installer.py
- tests/specify_cli/skills/test_manifest.py
- tests/specify_cli/skills/test_manifest_repair.py
- tests/specify_cli/skills/test_verifier.py
- tests/specify_cli/tool_surface/providers/test_managed_skills.py
role: implementer
tags: []
tracker_refs: []
---

# WP05: Managed Skill Assessment and Deterministic Backups

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

The legacy alias maps to canonical `spk-doctrine-profile-load`.
Run resolver-backed profile and action context with sync disabled:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty charter context --action implement --json
```
Apply initialization, boundaries, directives, tactics and independent handoff.
Read AGENTS.md and .kittify/charter/charter.md before implementation.
If #3908 returns empty governance despite success, disclose the degraded result
and read explicit binding charter/resolved profile sources. No activation fix.
Warm venv: direct binaries only; never resync or add a model override.

---

## Objective

Prepare complete managed-skill effects without writing, then apply exact prepared
bytes with owner rechecks. Preserve custom content, shared ownership and old
backups while eliminating clock-dependent backup paths and no-op manifest churn.

## Context

Read the approved spec, plan, data-model, research, wps.yaml and contracts in:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`.
Read exact T023-T028 in the external brief:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/task-authoring-brief.md`.
These authoring paths do not authorize implementation in the shared root;
use the canonical workspace assigned by runtime when parent dispatches.

owner-operations.md fixes preparation, backup allocation and clock semantics.
acceptance.md fixes independent snapshots and real process witnesses.
upgrade-cli.md/schema fix report meaning; this WP does not render CLI envelopes.
corpus-recovery.md pins historical identity timestamps, which are never normalized.

WP01 supplies green independent oracle infrastructure, not product acceptance.
WP02 supplies immutable assessment/operation values and dispatch.
WP03 supplies pure intent and global preparation/apply APIs.
Consume global preparation through WP03 rather than keeping a second global writer.
WP03 leaves public root behavior unchanged; WP10 alone wires startup suppression
and validated apply. WP08 consumes skill output; WP13 owns integrated acceptance.
Do not edit those WPs' files or interpret interrupted-worker logs as handoffs.

Source abbreviations installer.py, manifest.py, paths.py, registry.py,
verifier.py and retired.py mean src/specify_cli/skills/.
Provider means src/specify_cli/tool_surface/providers/managed_skills.py.
Only the exact frontmatter files are writable by this implementation package.
All currently exist; create_intent is empty.
Keep command_installer.py, command_renderer.py, manifest_store.py and vibe_config.py
with their respective owners, despite sharing the skills directory.
No runtime, charter, CLI, production dependency or corpus-state changes here.

After parent dispatch, use:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP05 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T023: Witness Managed-Skill Defects and Tidy Owners

**Purpose:** Establish failing-first behavior before extracting preparation.

**Steps:**
1. Read installer projection/global-sync/backup paths and manifest load/save.
2. Trace registry discovery, configured agent paths and provider repair.
3. Inspect existing five owned test modules and WP01's baseline witnesses.
4. Prepare realistic project/global fixtures, then inject missing/stale skills,
   managed drift, missing manifest and pre-existing backups.
5. Record old same-version public omission through the real CLI, with independent
   before/after snapshots and source/executable identity.
6. Reproduce advancing-clock backup path divergence through the existing installer.
7. Reproduce save-time updated_at mutation through the existing manifest saver.
8. Characterize missing versus malformed manifest handling; load_manifest currently
   returns None for malformed JSON as well as absence, which must not authorize
   an empty-success owner assessment.
9. Make a separate, behavior-preserving tidy-first change limited to touched seams.
10. Commit real owned regression tests red before functional correction.

**Files:** installer.py, manifest.py, provider and existing owned tests.
Inspect remaining owned helpers; do not rewrite them solely because allowed.

**Validation:** Red witnesses fail relevant path/hash/preservation assertions.
A missing new API or fake provider is not evidence of the existing defect.
Keep raw output, clock values, hashes, modes and exact assertion identities.
No live home writes; all fixture creation precedes measured snapshots.
Product red is not package completion or an expected-failure waiver.

### Subtask T024: Prepare Projection and Delegate Global Work

**Purpose:** One managed-skill inventory and pure owner preparation.

**Steps:**
1. Consume WP02's prepared assessment protocol without a new catalog.
2. Resolve existing SkillRegistry and activation policy once per selected root.
3. Accept projected activation inputs from later composition; do not provision
   charter or infer empty activation means missing.
4. Enumerate complete project copy/member/manifest effects, not missing IDs only.
5. Carry original provider status/source/manifest context into preparation.
6. Replace duplicate global sync decisions with consumption of WP03's owner API.
   Global writes have one physical owner retaining every logical consumer.
7. Do not bootstrap a cold home to discover sources; use canonical package
   resolution and the global owner's prepared inputs.
8. Include directory creation, copy modes, safe pruning and backup effects.
9. Distinguish unknown preserve, managed drift/consent and required input failure.
10. Missing/corrupt config/source/manifest must not select all agents or emit
    complete empty success. Preserve optional/disabled applicability policy.
11. Keep direct install and provider repair routed through the same owner logic.

**Files:** installer.py, registry.py/paths.py only as required, provider,
manifest.py and corresponding tests. No WP03 runtime edits.

**Validation:** Assessment snapshots are unchanged, including mtimes and links.
Selected skill/member sets match existing registry policy.
A shared-root fixture has one physical operation and all logical owner entries.
Corrupt state is distinguishable from a legitimately absent manifest.
Known independent work can be reported without authorizing an incomplete batch.
Prepared data must not contain mutable live manifests or writer callbacks.

### Subtask T025: Allocate State-Derived No-Clobber Backups

**Purpose:** Persistent backup identity agrees across preview/apply clocks.

**Steps:**
1. Replace timestamp path selection in _ensure_backup_root with the approved
   owner-local state-derived allocation; no shared allocation framework.
2. Retain the existing .kittify/.migration-backup/agent-skills parent.
3. Use a versioned state- name containing SHA-256 of canonical sorted replacement
   records: relative paths, observed kind/hash/literal link target/mode and
   desired stable content/kind/mode.
4. Exclude absolute fixture root, current clock, mtime and new manifest timestamps
   from allocation identity; retain original relative layout inside the backup.
5. If the candidate exists, preserve it regardless of content and choose the
   first absent numeric suffix in ascending order.
6. Include occupied candidates and selected absence in batch preconditions.
7. Create exclusively/no-clobber. A racing occupant causes conflict/reassessment;
   never overwrite, merge or silently choose a different unreported name.
8. Leave all historical timestamp-named backups and occupied state backups intact.
9. Report backup directories, descendants and modes as persistent effects.
   Retained backups are not transient execution artifacts.
10. Apply only to ownership-proven, consent-permitted replacements; backups
    do not authorize archiving unknown custom content or overriding drift.
11. Preserve explicit caller-provided backup destinations only under the same
    confinement, collision and exact-effect rules; no hidden alternate allocator.

**Files:** installer.py and test_installer.py; provider adapter only if needed.
Keep existing archive/projection functions as the concrete writer authority.

**Validation:** Equivalent fixtures at T1/T2 choose identical paths/actions.
Occupied candidate and multiple suffix fixtures preserve every old backup.
A race at exclusive creation refuses without clobbering or fallback.
Unknown/custom sentinels cannot become authorized replacements by backup policy.
Clock-name mutation and omitted-backup-effect mutation must fail controls.
Never normalize persistent backup paths to make the equality assertion pass.

### Subtask T026: Prepare Time Once and Preserve Current Manifests

**Purpose:** Exact per-invocation bytes and second-run zero churn.

**Steps:**
1. Sample operation time once during preparation for genuinely new/changed fields.
2. Preserve existing entry installed_at and manifest created_at where unchanged.
3. Prepare final manifest bytes/hash before apply; save_manifest must consume
   them rather than resample updated_at during serialization.
4. Existing non-upgrade callers may prepare immediately before saving through
   the same owner seam; do not break their public entrypoint contracts.
5. Missing managed manifest gets root created_at from prepared time.
6. Already-current manifests are not rewritten, even with identical bytes;
   their updated_at, created_at, installed_at and mtime remain unchanged.
7. Preserve exact source/entry/agent identity and delivery metadata.
8. At apply, recheck source/config/manifest/destination observations for the
   whole owner batch under existing locks before its first write.
9. A changed precondition refuses; no rerender/time substitution or --yes bypass.
10. On partial I/O error, return actual succeeded/failed/skipped effects and
    persist only truthful valid manifest state; no global rollback claim.

**Files:** manifest.py, installer.py, provider; test_manifest.py,
test_manifest_repair.py and test_installer.py.

**Exact comparison rule:**
- Within one assessment/apply invocation: no normalization whatsoever.
- Across independent runs: normalize only owner-declared newly assigned
  installed_at/updated_at/last_upgraded_at fields permitted by the contract.
- Additional exception: root /created_at ONLY in a newly created
  .kittify/skills-manifest.json absent in BOTH baselines.
- Keep raw bytes/hashes, exact JSON pointers and baseline-absence evidence.
- Never normalize existing manifest created_at or mission-meta created_at.
- No arbitrary nested created_at ignore, whole-manifest masking or path masking.

**Validation:** T1 assessment/T2 apply writes exact prepared bytes.
New-manifest cross-run test uses the precise root exception above.
Changing existing manifest creation time or historical identity time must fail.
Second apply retains every current-manifest byte and mtime.

### Subtask T027: Preserve Custom Content and Integrate Provider

**Purpose:** Safe copies/link conversion with one ownership-aware implementation.

**Steps:**
1. Implement WP02 protocol in ManagedSkillsProvider using owner preparation.
2. Keep configured agent scope, shared roots and all per-agent manifest entries.
3. Preserve copy delivery; do not introduce new links to global paths.
4. For owned link conversion, use lstat/readlink and parent confinement;
   never follow a link and overwrite its target.
5. Unknown content/links stay preserved; matching canonical adoption requires
   the existing explicit content proof, not an arbitrary current hash.
6. Drifted managed replacement/prune targets remain consent-required.
   --yes is not overwrite or independent mission-repair consent.
7. Check retirement candidates against exact owned canonical policy.
   Prefix matching alone must not authorize deleting custom skills.
8. Project missing independent files without discarding unresolved drift.
9. Preserve direct installation, verification and existing repair entrypoints.
10. Keep global execution delegated to WP03; do not call duplicate _sync_global_skill
    as an unreported second writer after the global assessment.

**Files:** installer.py, verifier.py, retired.py, paths.py as needed, provider.
Tests remain in the five owned test files; no neighboring command-skill changes.

**Validation:** Unknown canonical-looking file/link sentinels survive.
Owned safe conversion has a replace effect and leaves link target untouched.
Shared owner identities survive one-agent repair/removal behavior.
Unresolved drift remains visible while permitted independent repairs complete.
Missing required source/config refuses honestly, not success with an empty set.

### Subtask T028: Verify Clock, Backup and Plan/Apply Agreement

**Purpose:** Deliver green non-vacuous owner evidence to WP08/WP10/WP13.

**Steps:**
1. Consume WP01 independent lstat/content/link/mode/mtime observations.
2. Compare prepared effects with real owner/provider writes on equivalent fixtures.
3. Include missing, stale, shared-root, corrupted manifest, drift/custom and
   complete-current cases; require nonempty effects in missing/stale cases.
4. Exercise advancing clocks both within invocation and across independent runs.
5. Include occupied/racing backup candidates and retained legacy backups.
6. Recheck source mutation and escaping parent replacement before batch writes.
7. Inject partial I/O failure and verify actual outcomes/manifests, not mocked success.
8. Run an ordinary unwrapped public subprocess witness alongside owner tests;
   pending WP10 root integration cannot be represented as already passing.
9. Preserve existing public red until actual integrated fix is tested by WP13.
   Owner-level green is not permission to xfail the product matrix.
10. Run five owned tests, full affected skills/tool-surface subsystem, changed-file
    Ruff/mypy and calibrated repository fast checks; record actual counts.
11. Hand downstream owners exact prepared API/output examples and evidence hashes.

**Focused command after parent-approved environment prerequisites:**
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/pytest tests/specify_cli/skills/test_installer.py tests/specify_cli/skills/test_manifest.py tests/specify_cli/skills/test_manifest_repair.py tests/specify_cli/skills/test_verifier.py tests/specify_cli/tool_surface/providers/test_managed_skills.py -q
```

**Validation policy:** Disposable homes/XDG/runtime/temp roots, no live credentials
or host writes. Shared conftest can override shell sync=0; use approved isolation,
not wholesale fixture disabling. Flag=1 is not proof of live SaaS activity.
No uv resync, production dependencies or broad make test-full.
Authorized disposable test installs retain package/interpreter provenance.
Full final CORE contracts/architecture/E2E/issue-matrix gates belong to parent.
All tests above are obligations, not results executed by this prompt author.

## Definition of Done

- T023-T028 have attributable red/green evidence and canonical completion records.
- FR-002/003: complete project/global-delegated effects agree with actual writes.
- FR-004: current manifest and second application retain bytes and mtimes.
- NFR-004: custom assets, old backups and all logical owners remain preserved.
- C-001: existing inventory/writer authority retained, global work has one owner.
- Clock/path mutation controls fail, exact created_at exception remains bounded.
- Batch recheck/partial failure behavior is demonstrated with real filesystem state.
- Owned/subsystem/lint/type results and pre-existing failure dispositions recorded.
- Independent review accepts the implementation, not merely the prompt.
- No shared source/state/manifest-scope expansion or fabricated product approval.

Canonical subtask record, only when evidence actually meets criteria:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T023 --status done --mission upgrade-preview-mission-health-01M1V6E1
```
Repeat for T024-T028 with actual evidence. Do not execute these during authoring.
Parent owns runtime/finalization; no fake tasks.md/status, Op dispatch or commit
is part of this prompt-authoring task.

## Risks

- Global duplication: one runtime owner; route API corrections through WP03.
- Empty/corrupt confusion: assessment fails honestly; never overwrite malformed state.
- Timestamp masking: retain raw/per-invocation bytes and existing creation times.
- Backup collision: exclusive creation and observed absence, no destructive reuse.
- Shared roots: deduplicate physical files without collapsing per-agent entries.
- Scope: do not modify WP04 command helpers or WP10 startup integration.
- Credit-interrupted workers: local logs alone are not an approved dependency.

## Reviewer Guidance

Inspect actual backup allocator, save_manifest and provider creation path together.
Require all three to consume the same prepared values, not fresh clock samples.
Check absent-manifest /created_at exception and both prohibited-created_at controls.
Verify retained backup paths/modes after collision and after a second apply.
Challenge any unknown-content adoption or prefix-based deletion.
Look for transitive writes during assessment, including global sync and chmod.
Demand real owner filesystem effects plus public source evidence, not fake owners.
Confirm direct install/verify compatibility and truthful partial failure.
No test skip or broad timestamp normalization may manufacture plan/apply equality.
Keep owner-stage acceptance distinct from pending integrated mission gates.

