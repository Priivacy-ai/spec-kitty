---
work_package_id: WP04
title: Command skill ownership and physical effects
dependencies:
- WP01
- WP02
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
- T018
- T019
- T020
- T021
- T022
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/skills/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/skills/command_installer.py
- src/specify_cli/skills/command_renderer.py
- src/specify_cli/skills/manifest_store.py
- src/specify_cli/tool_surface/providers/command_skills.py
- tests/specify_cli/skills/test_command_installer.py
- tests/specify_cli/skills/test_command_renderer.py
- tests/specify_cli/skills/test_manifest_store.py
- tests/specify_cli/tool_surface/providers/test_command_skills.py
role: implementer
tags: []
tracker_refs: []
---

# WP04: Command Skill Ownership and Physical Effects

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

The legacy alias maps to canonical `spk-doctrine-profile-load`.
Run profile and binding implement context before implementation:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty charter context --action implement --json
```

Apply initialization, specialization, directives, tactics and review handoff.
Read AGENTS.md and .kittify/charter/charter.md explicitly.
Known #3908 may return success with empty governance arrays and unavailable
directives. Disclose that limitation and use explicit binding sources; do not
claim complete resolution or repair activation/configuration here.
Use warm direct binaries; no uv resync or model override.

---

## Objective

Make command-skill assessment describe the entire physical install/repair batch,
including manifest changes and shared owners, without performing writes.
Apply the same prepared decisions with ownership rechecks, preserving custom
content and producing no second-run churn.

## Context

Mission references relative to this prompt: ../spec.md, ../plan.md,
../research.md, ../data-model.md and ../contracts/.
Read owner-operations.md, upgrade-cli.md, acceptance.md and the full-plan schema.
Corpus recovery remains separate under corpus-recovery.md; it is not an
automatic command-skill side effect.
The external parent task-authoring-brief.md assigns exactly T018-T022.

WP01 supplies the independently checked snapshot/transient-write harness.
Its green infrastructure does not certify unresolved product acceptance.
WP02 supplies immutable owner values, assessment/apply protocol and dispatch.
Consume delivered APIs; do not edit those packages' files to unblock yourself.
WP08 consumes command output for bundles; WP10 integrates CLI/finalizer behavior.
WP13 owns aggregate CLI matrices, installed wheel and final architecture witness.

This package owns four production files and four existing test files exactly.
Source abbreviations command_installer.py, command_renderer.py and
manifest_store.py refer to src/specify_cli/skills/.
Provider refers to src/specify_cli/tool_surface/providers/command_skills.py.
All paths in frontmatter already exist, so create_intent is empty.
No generated project files or host tools are authoring targets.

Existing authority is command_installer.CANONICAL_COMMANDS plus its canonical
template resolver/renderer; provider expansion is not a second catalog.
manifest_store owns command manifest schema, hashing and persistence.
Keep existing public install/remove/prune/verify entrypoints compatible.
Do not add a new command manifest, generic writer engine or dependency.
Managed skills/backup allocation belong to WP05, not this package.
Root startup files and upgrade.py belong to WP10; leave them unchanged.

Implementation entry after canonical parent dispatch:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP04 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T018: Witness Preservation Regressions and Tidy the Seam

**Purpose:** Establish genuine failing evidence before changing ownership
behavior, then refactor only the touched owner seam.

**Steps:**
1. Read install/remove/prune_stale/verify in command_installer.py.
2. Trace rendering through command_renderer.py and template source selection.
3. Read load/save, repair_stale_manifest and remove_unsafe_symlinks in
   manifest_store.py; inspect manifest entry agents/hash/timestamp semantics.
4. Trace CommandSkillsProvider.expand/probe/repair and existing tests.
5. Prepare realistic disposable project assets with canonical setup first,
   then remove one managed command and introduce unknown canonical-path content.
6. Witness the old normalization/install chain adopting arbitrary on-disk hashes.
   Record the actual existing entrypoint and assertion that turns red.
7. Add a spec-kitty.custom symlink sentinel pointing only within the sandbox.
   Witness existing prefix-based cleanup deleting an unowned link.
8. Characterize shared codex/vibe command roots and remove/refcount behavior.
9. Use WP01 public pre-fix evidence for omitted same-version command repairs;
   preserve exact source/executable/fixture provenance in the handoff.
10. Make a separate behavior-preserving tidy-first change before the functional
    correction; do not mix unrelated renderer or manifest schema cleanup.

**Files:** All four owned production files for inspection; changes should be
localized to functions actually touched. Red tests live in the four owned tests.

**Validation:**
- Existing-entrypoint red fails for ownership/effect assertions, not missing APIs.
- Public omission witness uses actual CLI, not only an in-memory fake provider.
- Unknown custom bytes, symlink target and refcounts are captured independently.
- Tests cannot prewarm a measured cold home or write outside disposable roots.
- Baseline failures are tracked under charter policy; no retry-to-green.

**Evidence:** Red commit/logs, exact assertions, snapshots and baseline SHA.
A recorded product red is not a completed fix; subsequent subtasks must turn
the owned regressions green.

### Subtask T019: Prepare Complete Rendering and Manifest Effects

**Purpose:** Extract one read-only decision/render path for the whole command
batch, not only the IDs currently reported missing.

**Steps:**
1. Add owner preparation around the existing canonical command iteration.
2. Resolve/render each required command using the existing source authority.
3. Preserve configured agent scope and all shared physical-path owners.
4. Read manifest/config/source observations without mkdir, lock creation,
   save, install or write/delete simulation.
5. Build WP02 PhysicalEffect values for command bytes, parent directories,
   applicable removals, modes and the command manifest itself.
6. Include manifest-only owner/refcount changes when file bytes are already
   correct; do not incorrectly report a file rewrite for shared reuse.
7. Keep prepared final bytes and manifest state immutable in-process.
8. Sample newly assigned installed_at values during assessment once; existing
   timestamps survive unchanged. Save/apply must not resample time.
9. Preserve real source/config failures as incomplete/blocked owner diagnostics;
   malformed manifests are not equivalent to missing manifests.
10. Retain existing logical InstallReport/RemoveReport compatibility while
    exposing the new complete owner assessment to the provider.
11. Report atomic-write/lock execution artifacts per the owner contract;
    persistent supporting files cannot disappear from the effects list.

**Files:** command_installer.py, command_renderer.py only where pure rendering
needs extraction, manifest_store.py and relevant existing tests.
Expect focused helper extraction and adapter changes, not wholesale rewrites.

**Validation:**
- Missing command fixture has nonempty command and supporting manifest effects.
- Entire canonical batch is assessed even if only one missing ID triggered repair.
- Assessment leaves bytes, directories, links, modes and mtimes unchanged.
- Unchanged prepared content produces no persistent effect.
- Shared reuse produces the right manifest update without duplicate file writes.
- Missing source or corrupt manifest cannot become successful empty assessment.

**Evidence:** Compare owner effects to independent WP01 snapshots; a production
effect helper cannot serve as the oracle. Record exact prepared manifest bytes.

### Subtask T020: Preserve Unknown Content and Require Exact Ownership

**Purpose:** Close adoption and prefix-cleanup hazards without expanding consent
or making legitimate shared reuse impossible.

**Steps:**
1. Remove arbitrary on-disk hashing as a shortcut to managed ownership during
   repair_stale_manifest normalization.
2. Missing manifest plus retained file may be adopted only through the existing
   exact canonical-rendered-byte contract; record that content proof.
3. Nonmatching unknown content is preserve/conflict, never a placeholder entry
   that becomes trusted on the next installer pass.
4. Keep proven managed-but-edited files as drift; --yes is not overwrite consent.
5. Evaluate symlinks with lstat/readlink and observed parent confinement.
6. Only exact managed-path/manifest ownership may authorize unlinking.
   A spec-kitty. prefix or unrelated current hash is insufficient.
7. Preserve unknown custom links, including dangling links and links with
   canonical-looking names; never modify their targets.
8. Preserve existing copy delivery; owned link conversion is a replace effect,
   not a write through the link.
9. Treat orphan pruning independently from expanded missing statuses.
   Retain edited owned prune candidates as consent-required drift.
10. Preserve shared remove semantics: removing one logical agent does not remove
    bytes required by another; final removal requires exact ownership proof.

**Files:** manifest_store.py, command_installer.py, provider and their tests.
Do not change shared schemas, agent registry or managed-skill implementation.

**Validation:**
- Unknown canonical-path file plus another missing command remains byte-identical.
- Matching canonical bytes can be safely reused with truthful owner entries.
- spec-kitty.custom, dangling and escaping-parent sentinels remain intact.
- Proven managed safe removal/conversion still works and is reported.
- Removing one shared owner retains file and remaining manifest references.
- A deliberately reintroduced hash-adoption/prefix-delete shortcut turns red.

**Evidence:** Preserve negative and positive controls, not only refusals.
No generic consent or blanket cleanup policy is introduced.

### Subtask T021: Apply Prepared State with Batch Rechecks

**Purpose:** Ensure the owner applies its assessed decisions exactly, or reports
a conflict/partial outcome rather than silently rerendering or overwriting.

**Steps:**
1. Route existing command write/manifest-save methods through prepared decisions.
2. Recheck source/template, configuration, manifest and destination observations
   for the entire owner batch before its first write.
3. Use existing locks and atomic file replacement where available.
   Do not add a cross-owner transaction/rollback framework.
4. Include parent confinement and symlink/type/mode/mtime observations.
5. If any precondition changes, stop the batch with precondition_changed.
   Require fresh assessment; --yes cannot bypass or automatically retry.
6. Write exactly the prepared command and manifest bytes, including chosen times.
7. Avoid unconditional manifest save, chmod or timestamp refresh for a no-op.
8. Preserve per-file application results and truthful succeeded/failed/skipped IDs.
9. On mid-batch I/O failure, persist only valid manifest state for actual work;
   never claim all requested writes completed or forget surviving shared owners.
10. Keep existing remove/prune/install public behavior and reports compatible
    except the explicitly approved safety correction.

**Files:** command_installer.py, manifest_store.py and their owned tests.
Prepared rendering helpers may be adjusted in command_renderer.py if necessary.

**Validation:**
- Change source or manifest between assess/apply: zero batch writes and conflict.
- Replace a parent with an escaping link: no target write and explicit refusal.
- Advance the clock between assess/apply: bytes match prepared hashes exactly.
- Fail after one actual write: outcome describes real partial state accurately.
- Second application retains bytes and mtimes, including the manifest.
- Recheck-bypass mutation fails the relevant focused control.

**Evidence:** Race/I/O injection at the owner boundary supplements real
filesystem integration; it cannot replace public preview/apply evidence.

### Subtask T022: Integrate Provider and Verify the Owned Subsystem

**Purpose:** Deliver a complete command owner to WP08/WP10 without confusing
owner-level correctness with the pending whole-CLI integration gate.

**Steps:**
1. Implement WP02's assessment/apply protocol in CommandSkillsProvider.
2. Preserve original statuses, instances, source identity and logical owners.
3. Delegate rendering/manifest policy to the command owner rather than copying it.
4. Ensure direct install and existing repair consumers use the same preparation.
5. Exercise missing, stale, shared, drift, custom, corrupt and unchanged fixtures.
6. Compare exact effects to real application through the owner/provider path.
7. Use narrow timestamp normalization only across independent invocations as
   allowed in owner-operations.md; never normalize paths or per-invocation bytes.
8. Run all four owned test modules and the affected skills/tool-surface subsystem.
9. Run changed-module Ruff/mypy and repository-required calibrated fast checks.
10. Hand WP08/WP10 concrete assessment examples, partial outcomes and API signatures.
    Route harness/core protocol changes to WP01/WP02 owners rather than editing
    their files. Final public integrated green and wheel witness belong to WP13.

**Focused test command after environment-policy prerequisites:**
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/pytest tests/specify_cli/skills/test_command_installer.py tests/specify_cli/skills/test_command_renderer.py tests/specify_cli/skills/test_manifest_store.py tests/specify_cli/tool_surface/providers/test_command_skills.py -q
```

**Files:** The four owned production/test pairs; no new literal file is planned.
Existing tests may gain focused cases; do not create shared conftest or a second
acceptance harness.

**Validation prerequisites:**
- Use disposable HOME/XDG/runtime/temp roots and source subprocess sync=0 last.
- Existing shared conftest can override shell sync=0; use parent-approved policy,
  not wholesale fixture disabling. Flag=1 is not proof of live SaaS traffic.
- No real home assets, live credentials, hosted endpoints or production network.
- No uv resync, production dependency changes or global installation.
- Parent-authorized isolated package installation retains exact provenance.
- No broad make test-full here; parent owns full final gates and issue closure.

## Definition of Done

- T018-T022 each has attributable red/green evidence and supported completion event.
- FR-002/003: whole-batch command/supporting effects match real owned writes.
- FR-004: second repair changes no bytes, links, modes or mtimes.
- NFR-004: unknown custom content and shared owners survive every automatic path.
- C-001: existing catalog/render/manifest authority is reused, not duplicated.
- Preparation never writes; apply rechecks the batch and consumes exact bytes.
- Corrupt required state fails honestly; incomplete is never complete no-op.
- Provider and direct install/remove paths preserve supported compatibility.
- Targeted/subsystem/lint/type commands, counts and failure dispositions recorded.
- Independent review is complete before claiming this package accepted.

After each subtask actually meets its criteria, use canonical event recording:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T018 --status done --mission upgrade-preview-mission-health-01M1V6E1
```
Repeat for T019-T022 only with evidence. No ticked checkbox substitutes for
status events; never fabricate tasks.md, status or review verdicts.

## Risks

- Placeholder hashes create ownership: prohibit normalization-by-adoption.
- Shared paths multiply writes: retain logical owners while deduplicating effects.
- Filesystem links escape sandbox: check parent confinement without following
  an untrusted target; observe absence/type changes before applying.
- Timestamp churn breaks equality: prepare once and avoid no-op manifest saves.
- Partial writes lie about ownership: report actual outcomes and valid manifests.
- Stage confusion: WP10 owns root/CLI integration, WP13 full acceptance.
- Credit-interrupted workers' test logs are not a completed upstream handoff.

## Reviewer Guidance

Verify exact manifest ownership and no neighboring provider/runtime edits.
Demand original-entrypoint red evidence, not only new helper tests.
Inspect adoption/pruning/remove paths as carefully as installation.
Require positive canonical reuse and shared-refcount controls alongside refusals.
Check the complete command batch and persistent manifest/directory effects.
Challenge any filename-prefix proof, arbitrary content adoption or global retry.
Check advancing-clock exact bytes and unchanged second-apply mtimes.
Mutation controls must expose removed ownership/recheck assertions.
Confirm no --yes consent expansion or independent mission-state mutation.
Use parent-owned final gate table for consolidation; no per-WP green substitutes
for full CORE contracts/architecture/E2E/terminal issue evidence.
All tests and gates here are obligations, not author-executed results.

