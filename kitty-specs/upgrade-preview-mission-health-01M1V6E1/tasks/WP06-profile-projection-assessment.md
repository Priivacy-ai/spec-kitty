---
work_package_id: "WP06"
title: "Profile projection and pruning assessment"
dependencies: ["WP01", "WP02"]
owned_files:
  - "src/specify_cli/tool_surface/profiles/**"
  - "src/specify_cli/tool_surface/providers/agent_profiles.py"
  - "tests/specify_cli/tool_surface/profiles/**"
  - "tests/specify_cli/tool_surface/providers/test_agent_profiles.py"
  - "tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py"
requirement_refs: ["FR-002", "FR-003", "FR-004", "NFR-004", "C-001"]
subtasks: ["T029", "T030", "T031", "T032", "T033"]
authoritative_surface: "src/specify_cli/tool_surface/profiles/"
execution_mode: "code_change"
agent_profile: "python-pedro"
role: "implementer"
agent: "codex"
create_intent: []
---

# WP06: Profile projection and pruning assessment

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Expose complete, read-only profile-owner assessments and apply their prepared
projection, manifest and prune effects after whole-batch precondition checks.
Preserve admission policy, custom content, drift, disabled surfaces and Amazon Q's
user-global exception; repaired state must produce zero repeat writes.

## Context

Audience: automation-agent implementing Python, with independent maintainer review.
This is future implementation guidance; authoring this prompt executes no work,
status transition, implementation command, commit, dispatch or acceptance gate.

Repository root checkout:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`.
Mission root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`.
External authoring brief:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/task-authoring-brief.md`.

Binding inputs, read before implementation:

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/AGENTS.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`, especially D2, D5 and IC-05.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml` (exact scope/dependencies).
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md` (excluded work).

Governance limitation: task author ran the mandated profile/context commands
first with sync disabled. Planner Priti resolved to builtin; context returned
zero references and empty directives/tactics with unresolved-governance diagnostics.
This is the documented #3908 degradation, not a successful governance resolution.
Bind explicitly to the charter above and the resolved builtin source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`.
Planner initialization limits this author to decomposition/sequencing, with no
implementation, architectural redesign or agent management. Directive 003's
decision traceability is applied through contract references and scoped rationale.
Its source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/directives/003-decision-documentation-requirement.directive.yaml`.

Python Pedro was separately resolved as builtin; source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`.
Load its resolved initialization, boundaries, directives and tactics yourself.
Apply specification fidelity, locality/tidy-first, test-first, type/lint gates,
canonical authority and independent review. Use bug-fixing-checklist and
tdd-red-green-refactor; pure-unit design tactics do not replace real owner I/O
acceptance. Retain the repository's Python >=3.11 floor despite profile prose.
Do not repair governance config or install dependencies to resolve #3908.

WP01 supplies the independent snapshot/process observer. WP02 supplies immutable
operations, assessment protocol and owner-preserving dispatch. Both must be
approved/done before implementation. Consume their delivered APIs; names in the
contract describe semantics, not permission to invent a competing interface.
WP08 consumes prepared profile projections for bundles; WP10 composes upgrade;
WP13 owns the aggregate public CLI matrix and installed-wheel witness.
Neither root startup purity nor complete mission acceptance can be claimed here.

Primary production authority is the nonempty profiles prefix in frontmatter.
It deliberately is not the empty common prefix of source and test paths (#2446).
All literal ownership entries already exist; create_intent is therefore empty.
Extend existing owned files for the planned work; no planned-new literal path.
Manifest globs remain repository-relative exactly as authored; roots above are absolute.

Scope is restricted to frontmatter ownership. Do not edit WP02 protocol/glue,
activation/invocation owners, CLI startup/finalizer, other providers, shared
preview_support, shared conftest, corpus, architecture baselines or dependencies.
Route necessary changes to the parent and owning WP; no overlap exemption.
Do not edit mission manifest, tasks.md, meta, snapshots, events or tracer files
manually. Parent owns external evidence placement, issue matrix and final gates.
No release bump, remote push, merge, Op dispatch or additional WP work.

Future implementation entry command, for the authorized implementer only:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent action implement WP06 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

Consume the returned absolute execution workspace; never guess a lane/base branch.
Use that workspace's verified absolute paths and direct warm binaries; no resync.

### Subtask T029: Characterize profile admission/pruning and witnessed omitted effects

**Purpose**: Pin the existing defect and policy before changing the owner.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py`.
Extend existing tests by roughly 80-140 lines; keep helpers local to these files.

**Steps**:

1. Inspect expand/probe/repair, _write_all, _repair_one and _prune_orphans.
   Current repair(dry_run=True) returns actionable surface IDs only.
   It does not enumerate manifest/parent writes or status-less orphan deletions.
   _write_all prunes independently of actionable statuses and saves the manifest.
2. Reuse the real-format org-pack fixture, _write_config and _run_fix from
   test_agent_profiles_prune.py. Use AgentProfilesProvider() without injecting
   a fake projector, repository result or precomputed status list.
3. Install an admitted org profile through the existing owner; retain its exact
   output bytes/hash and manifest entry. Deactivate it through fixture config.
   Verify the real expansion no longer contains the orphan's output path.
4. Witness the omission on unchanged existing entry points: dry-run gives no
   actionable orphan ID while real repair removes the owned file and updates
   its manifest. Capture both outputs and an independent physical delta.
   Logical-ID counts are not physical-effect evidence.
5. Add a failing regression for an edited, previously managed orphan: change
   its bytes after installation, deactivate, invoke existing repair, and require
   file bytes/mode and the ownership record to survive with drift disclosed.
   This must fail because current _prune_orphans deletes it, not due to imports,
   unknown options, a nonexistent assessment method or malformed setup.
6. Include a still-admitted builtin and an untracked hand-authored file as
   unchanged controls. Preserve the existing valid unchanged-orphan deletion
   test, which must continue passing after the safety correction.
7. Record exact baseline SHA, argv/cwd, executed assertion, exit and snapshot
   evidence. Commit the genuine failing regression separately through the
   parent-authorized implementation workflow before functional fixes.
8. Inspect touched complexity/debt and perform only proportionate tidy-first
   extraction within owned files after red evidence, before behavior changes.
   Keep that step behavior-preserving with focused characterization checks.

**Validation**: Reviewer can replay the red on the resolved planning base and
the same assertion on the final code. Original omission is independently
witnessed; no skipped/xfail test, fabricated failure or new-API-only red.
Do not execute any of these implementation steps while authoring this prompt.

### Subtask T030: Prepare projections/manifests with original policy and owner context

**Purpose**: Make rendering/comparison a pure preparation path consumed by writers.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/projection.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/manifest.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/profiles/test_projection.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/profiles/test_manifest.py`.
Prefer small owner-local extractions, roughly 120-200 source lines plus tests.

**Steps**:

1. Preserve default_profile_repository's explicit org_roots=[] base and project
   overlay seam. Org profiles enter solely through resolve_activated_org_profiles.
   Do not replace that path with raw org dirs or an all-known-profiles fallback.
2. Keep sentinel exclusion, layer filtering, capability/renderer selection,
   portable source provenance, source hashes and projection_version.
   Retain diagnose findings for invalid source/name, overlay conflict and
   sentinel-skipped. A required invalid source is not a complete empty batch.
3. Retain the actual provider instance, resolved repository/projections, selected
   tool policy and source/config observations from assessment to application.
   Use WP02's owner context rather than rebuilding ownership from findings.
   Scan/render once per distinct selected tool/root; retain immutable results.
4. Prepare desired UTF-8 bytes, final node kinds/modes and the exact proposed
   manifest entries. Distinguish package-source staleness from user drift:
   matching installed hash plus new canonical source can be automatically stale;
   changed disk content relative to its recorded hash remains consent-required.
5. Use ProfileManifest's existing sorted JSON/entry serialization as the sole
   format authority. Extract pure render/prepare and allow save/application to
   consume those bytes; do not add a second manifest serializer in the provider.
6. Keep manifest filename agent_profiles_manifest.json, schema_version=1,
   legacy entry readability, absolute in-memory output keys and relative disk
   output paths. Preserve portable SOURCE provenance separately from OUTPUT.
   Existing out-of-tree serialization compatibility grants no deletion authority.
7. Cover a missing manifest with retained generated files: exact canonical-byte
   equality can justify adoption only under an explicit existing content contract.
   Otherwise preserve/report ambiguity. Never hash arbitrary content into ownership.
   A truncated/corrupt manifest blocks the batch before writes; absent is distinct.
8. Compare complete physical state, not exists() alone. Include supporting
   manifest and missing parent-directory effects with exact before/after state.
   Equal bytes/type/mode produce dispositions, not repeated writes or saves.
   This manifest has no timestamp fields; do not introduce any or normalize it.
9. Return WP02 immutable effects/dispositions/diagnostics plus opaque prepared
   data and observations. Assessment must not call mkdir, write_text, save,
   unlink, lock creation, bootstrap, persistence, prompts or network.

**Validation**: Real projection and manifest tests retain provenance/roundtrip
coverage; observer records zero preparation writes, including transient ones.
Missing profile output produces nonempty create effects and the precise manifest
change. Mutating a prepared object's nested payload must not alter the plan.

### Subtask T031: Enumerate orphan pruning absent from expanded statuses, preserve drift

**Purpose**: Plan the complete prune batch without treating disappearance as consent.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/manifest.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/_paths.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py`.
Bound changes to ownership/preparation helpers and roughly 100-160 test lines.

**Steps**:

1. Enumerate ProfileManifest.all_entries() as well as admitted projections.
   Status expansion cannot discover deactivated/removed profile outputs.
   A prune-only batch must run assessment even when actionable statuses are empty.
2. Reconcile only the selected, enabled, applicable tool ownership context.
   Retain still-admitted entries and entries belonging to excluded tools.
   Tool disablement is not implicit deletion permission; do not reconstruct
   selection from every tool appearing in the manifest.
3. For each potential orphan require exact manifest identity, expected project
   confinement, supported node type and matching observed installed hash.
   A filename prefix, arbitrary absolute manifest path or Path.exists() is
   insufficient. Inspect nodes with lstat, including dangling symlinks.
4. Prepare delete effects only for proven, unchanged managed orphans.
   Remove precisely those entries in prepared manifest bytes. If an owned file
   is already absent, report only the needed manifest update, not a fake delete.
   Enumerate any intentional directory removal; never recursively prune a root.
5. Preserve edited managed orphans and their records as drift/consent_required.
   Preserve unknown files, custom symlinks and unrelated entries. Report the
   reason so callers retain unresolved-drift behavior under noninteractive --yes.
6. Protect shared physical destinations: retained logical owners keep the file;
   one eligible final deletion has one executable owner and all affected owners.
   Contradictory desired bytes become a conflict, not dictionary last-writer-wins.
   Do not introduce a profile refcount schema merely to mimic command skills.
7. Treat escaping parent links, traversal entries and out-of-tree legacy outputs
   as non-authorizing evidence. Preserve/reject the dangerous operation without
   following the link target or rewriting legacy data opportunistically.
8. Keep Amazon Q entries excluded from project manifest pruning regardless of
   tool aliases. An injected legacy Q record is a preservation control, never
   an invitation to delete a real user-global file.

**Validation**: Real org activation/deactivation gives a nonempty file delete
and manifest update despite zero orphan statuses. Edited orphan survives.
Test absent output, still-admitted output, disabled tool, unknown file,
dangling/custom link and escaping legacy entry; sentinel targets stay untouched.
Independent delta equality must fail if either delete or manifest effect is omitted.

### Subtask T032: Recheck/apply prepared effects, disabled agents and Amazon Q exception

**Purpose**: Execute exactly the assessed consent-permitted owner batch.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/manifest.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py`.
Reuse the existing writer seams; avoid a generic transaction framework.

**Steps**:

1. Implement WP02's separate assessment/apply protocol on AgentProfilesProvider.
   Keep reporting protocol and doctor/init behavior compatible through the same
   selection/render/compare authority. Do not move projection policy into CLI glue.
2. Recheck the entire batch before its first write: source/template identities,
   activation/config and manifest bytes, target kind/hash/mode/mtime, candidate
   absence, parent confinement and selected owner policy.
   Under an existing lock if available, mismatch returns precondition_changed
   with zero batch writes; no silent rerender, force, retry or alternate target.
3. Existing writers consume prepared file and manifest bytes. Retain existing
   atomic-write/lock behavior where present; report bounded transient artifacts
   separately and any persistent lock/path creation as physical effects.
   Do not claim cross-owner rollback or write-then-delete preview safety.
4. Preserve automatic policy from the WP02-owned _is_init_upgrade_auto_repairable
   seam: repairable-required only, activation mode not disabled, and no automatic
   Amazon Q agent profiles for q/amazon-q/amazon-q-agent.
   Observe this policy; do not edit that sibling-owned helper.
5. Explicit doctor repair of Amazon Q may retain its existing user-global writer,
   only in a sandbox for tests, with global effects when that mode is selected.
   It must never create project manifest entries or prune Q through project scope.
   Upgrade assessment reports the exception as a disposition, not a promised write.
6. --yes is not drift overwrite consent. Known independent missing-file repairs
   can proceed while drift remains reported; exact interactive managed-path
   approval requires fresh assessment, never adoption of unknown custom content.
7. Preserve truthful partial failure: after a later I/O error, report only actual
   successes and failures; never mark all requested IDs repaired. Retain manifest
   records for unsuccessful deletions and record only successfully installed bytes.
   Surface a manifest-save failure explicitly; do not pretend it completed.
8. Apply an unchanged prepared batch without mkdir/save/chmod churn. Reassessment
   after success yields no repair effects, even when drift dispositions remain.

**Validation**: Change a destination, manifest, profile source, activation config
and symlink parent separately between assess/apply; each aborts before any batch
write. A targeted later write/unlink failure demonstrates honest partial results.
Test explicit doctor Q repair separately from automatic upgrade exclusion.
No replacement provider/installer is allowed in successful owner-effect witnesses.

### Subtask T033: Nonempty profile plan/apply, shared ownership and repeat no-churn tests

**Purpose**: Prove FR-002/003/004 and preservation with independent observations.

**Files**:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles.py`;
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py`;
existing tests under `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/profiles/`.
Consume WP01 helpers without editing them; add roughly 120-180 focused test lines.

**Steps**:

1. Prepare independent realistic fixtures for missing profiles (P3), missing
   manifest with retained files (P4), stale source/provenance and profile
   deactivation. Use real project/org sources and provider/renderer/manifest code.
   Record executable/module provenance and actual selected policy.
2. Use WP01's independent oracle for all nodes: root/path, lstat kind, bytes hash,
   readlink target, mode, mtime, ignored files and empty directories.
   Preparation requires identical before/after snapshots and no attempted writes.
3. Compare assessed effects with actual independent net delta exactly: root,
   path, action, final kind/mode/content or link target, directories and manifest.
   Require at least one real profile creation plus manifest effect in P3 and a
   real delete plus manifest effect in the unchanged-orphan case.
4. Assert exact prepared hashes against applied bytes within one invocation.
   Profile manifests have no volatile timestamp allowance. Across equivalent
   roots normalize root identity only, not arbitrary paths, hashes or owner sets.
5. Use real multi-tool Claude/Codex outputs sharing the single profile manifest:
   one manifest write must retain both tools' entries and logical owners.
   Consume the shared-path dispatch contract from WP02; do not force Vibe to
   gain native profile support or create a synthetic renderer to manufacture it.
6. Reassess and apply twice. Remaining automatic effects are empty and every
   byte, type, link, mode and mtime is unchanged; custom/drift sentinels remain.
   Check the manifest mtime directly so unconditional save cannot pass.
7. Negative controls must make the assertions fail: omit manifest effect, omit
   orphan delete, overwrite drift, resave unchanged manifest, or drop one shared
   logical owner. Use disposable mutations or altered assertion inputs only;
   never mutate the shared production checkout for test sabotage.
8. Run owner integration through delivered WP02 dispatch as well as direct
   provider tests. Preserve public-entrypoint omission evidence from T029/WP01;
   give WP13 fixture/assertion identities for final P3/P4/P6/P8 CLI acceptance.
   Do not claim public startup purity before WP10 or require its code to pass WP06.
9. Keep error cells non-vacuous: corrupt config/manifest and unavailable required
   source must produce diagnosed blocked/incomplete assessments, not empty success.
   A crashed setup/collection or skipped symlink test is not a passed witness.

**Validation**: Run changed tests, full affected tool_surface subsystem, calibrated
make test-fast, changed-module Ruff/mypy and applicable layer/dead-code gates.
Use verified absolute warm binaries, sync=0, PYTHONDONTWRITEBYTECODE=1 and
isolated HOME/USERPROFILE/XDG/APPDATA/LOCALAPPDATA/runtime/temp roots.
Set child sync=0 last; assert effective isolation after fixtures run.
The acceptance contract records a shared autouse sync=1 override: consume the
parent-approved harness policy before any such run. Do not edit conftest,
disable it wholesale, skip required tests or silently accept the override.

Reference owner commands from the repository root, after that isolation is established:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/pytest /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/profiles/ /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles.py /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_agent_profiles_prune.py -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/pytest /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/ -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 make -C /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty test-fast
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/ruff check /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/ /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/mypy --strict /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/profiles/ /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/agent_profiles.py
```

Use equivalent absolute paths for the resolved implementation checkout.
Include changed tests in lint/type checks as applicable to repo config.
No make test-full or whole-repo pytest in this WP. Full architectural suite
is required only if authorized scope later touches shared/architectural config;
parent owns final CORE contracts/architecture/E2E/wheel gates.
Record counts and exact failures; report pre-existing failures through parent
under charter policy, never retry-to-green, skip/xfail or blanket waiver.
Report unsupported platform coverage honestly and obtain a capable-platform
witness; do not treat absence of symlink capability as universal acceptance.

## Definition of Done

- T029 has replayable existing-entrypoint RED, separate red commit and green replay.
- T030 prepares exact profile/manifest/directory effects without mutation.
- T031 includes status-less orphan effects and preserves drift/unowned/excluded data.
- T032 rechecks whole batches, preserves consent/policy and reports actual failures.
- T033 proves nonempty exact plan/apply equality, shared owners and repeat no churn.
- All manifest requirement refs map to executed tests and source changes.
- Owned/blast-radius/static checks and independent reviewer evidence are recorded.
- No implementation completion, review verdict or gate pass is inferred from prose.

Per-subtask completion evidence is a canonical
`spec-kitty agent tasks mark-status <Txxx> --status done` record (event-sourced),
not a ticked checkbox or a manually written snapshot.
After each subtask's evidence is verified, the future implementer records only
completed IDs using the exact commands below; authoring must not execute them:

```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T029 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T030 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T031 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T032 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.venv/bin/spec-kitty agent tasks mark-status T033 --status done --mission upgrade-preview-mission-health-01M1V6E1
```

These commands may commit canonical status events; consume their resolved status
surface. Never substitute task/WP frontmatter edits, event fabrication, raw
snapshot writes, --no-auto-commit bypasses or manual lane state.

## Risks

- Status-only inventory hides prune/manifests: assess the owner's complete batch.
- Manifest hash is evidence of installed content, not blanket overwrite consent.
- Legacy absolute paths can round-trip while remaining unsafe mutation targets.
- Source/template or parent-link races invalidate the whole prepared batch.
- Rebuilding projections at apply can change policy or bytes; retain preparation.
- Shared manifest writes can drop another tool's entries; test both owners.
- Amazon Q is user-global; automatic upgrade exclusion and sandboxing are mandatory.
- Dependency interface/harness gaps go to their owners; no parallel replacement.

## Reviewer Guidance

Independently replay baseline RED and final GREEN; inspect actual failing assertion.
Reject import/unknown-option errors masquerading as repaired-defect witnesses.
Trace one missing profile and one status-less prune through real preparation,
dispatch, writer and independent filesystem delta, including manifest and parents.
Verify exact provenance, preserved drift/unknown paths, disabled tools and Q policy.
Inspect whole-batch race refusal and truthful partial failure, not only happy paths.
Require omission/overwrite/no-churn negative controls to fail for the intended reason.
Check ownership/dependencies against the root manifest and all required test counts.
Confirm the author changed only this prompt; implementation evidence remains future.
Return review findings to the parent; do not self-approve, advance gates or start WP07.
