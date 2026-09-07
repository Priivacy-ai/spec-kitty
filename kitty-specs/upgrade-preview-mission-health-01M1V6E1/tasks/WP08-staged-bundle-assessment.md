---
work_package_id: WP08
title: Staged plugin bundle assessment
dependencies:
- WP02
- WP04
- WP05
- WP06
- WP07
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
- T039
- T040
- T041
- T042
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/bundles/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/plugin_bundle.py
- src/specify_cli/tool_surface/bundles/**
- tests/specify_cli/tool_surface/bundles/**
- tests/specify_cli/tool_surface/providers/test_plugin_bundle.py
- tests/specify_cli/tool_surface/test_plugin_build_codex.py
- tests/specify_cli/tool_surface/test_plugin_build_claude.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 - Staged plugin bundle assessment

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Expose complete, read-only assessment of policy-selected staged plugin bundles,
then apply the same prepared owner output after whole-batch precondition checks.
Every selected member, manifest and supporting path must agree with real effects;
repeat application must preserve bytes, modes, links and mtimes without churn.

## Context

Audience: Python implementer and independent core-team reviewer.
This is an implementation prompt; its author performed no implementation,
test execution, status transition, commit or dispatch.
The parent owns lifecycle advancement, issue-matrix closure and final gates.

Absolute repository root checkout:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`.
Absolute mission root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`.
The runtime resolves any later execution workspace; do not invent a worktree
or choose a base branch. Bind execution paths to that returned absolute root.
Frontmatter ownership paths and effect paths remain repository/root-relative
as their schemas require; they are not host-absolute filesystem roots.

Binding reading, after loading the profile:

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/AGENTS.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md` (scope boundary only).
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/task-authoring-brief.md` (T039-T042 and slicing safeguards).

Author initialization resolved Planner Priti from builtin, with directive 003
and no tactic references. Explicit resolved source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`.
Decision documentation source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/directives/003-decision-documentation-requirement.directive.yaml`.
Tasks charter context returned zero references, empty directives/tactics, and
unresolved-governance diagnostics. This is the known #3908 degradation, not a
successful empty-governance verdict. The charter above binds explicitly.
Resolve Pedro through the CLI, apply its initialization, boundaries, directives
and tactics, and disclose any same degradation; do not repair activation/config.

Dependencies are exactly WP02, WP04, WP05, WP06 and WP07.
WP02 delivers immutable values, provider assessment/apply protocol and dispatch.
WP04 supplies command bytes/ownership; WP05 managed-skill projections;
WP06 profile projections; WP07 applicable hooks/native configuration output.
Consume their delivered prepared values and observations, not assumed APIs.
Wait for dependency readiness and concrete outputs; route missing seams to
their owner through the parent rather than editing neighboring files.
WP10 composes upgrade phases; WP13 owns aggregate public/wheel acceptance.
WP01's independent preview harness is available transitively through dependencies;
consume it read-only and route harness corrections to WP01.

### Scope and Existing Seams

Primary production authority is the nonempty bundles prefix in frontmatter.
Do not compute a common prefix across source and tests: that yields the known
#2446 empty-authority failure. All literal owned paths already exist;
`create_intent: []` is deliberate. Extend existing tests and bundle modules.

Source and test locations to inspect before editing:

- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/providers/plugin_bundle.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/projection.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/model.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/_builder.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/claude.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/copilot.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/vscode.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/codex.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/bundles/claude_wrapper.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/providers/test_plugin_bundle.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/bundles/_support.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/bundles/test_claude.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/bundles/test_copilot.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/bundles/test_claude_wrapper.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/test_plugin_build_claude.py`.
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/tests/specify_cli/tool_surface/test_plugin_build_codex.py`.

Read-only integration authorities:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/service.py` and
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/src/specify_cli/tool_surface/repair.py`.
The former owns `build_plans_for_bundles`; the latter owns
`_is_init_upgrade_auto_repairable`. Both belong to WP02.
Root CLI, upgrade integration, other providers/installers, shared conftest,
governance, manifests describing WPs, corpus and state files are out of scope.
No version bumps, global installations, plugin enablement/registration,
marketplace publication, dependency resync, Op dispatch or remote pushes.
No new automatic plugin selection and no generic overlay/transaction framework.

### Subtask T039: Characterize selected/advisory staged-bundle policy and omitted members

**Purpose**: Establish real failing behavior at existing owner entry points,
and freeze selection/ownership boundaries before changing them.

**Steps**:

1. Record source SHA, executable/module provenance and dependency delivery SHAs
   in the parent-designated external evidence channel.
2. Inspect `plugin_manifest_definition`: OPTIONAL and DISABLED are current
   defaults. Ordinary upgrade auto-repair excludes these surfaces.
   Explicit doctor/provider staging repair is a separate selected operation;
   never force activation merely to get nonempty upgrade effects.
3. Record default projectors: ClaudeCode, Copilot and VS Code.
   CodexBundleProjector is an explicit CLI builder, not a default provider.
   ClaudeBundleProjector.build is also distinct from ClaudeCode.project.
   Preserve each target's current layout and entrypoint selection.
4. Trace `repair(dry_run=True)`, `_project_all`, `_project_one`,
   `_plans_for_projection`, `probe` and `_descriptor_from_staged`.
   Current dry-run returns logical manifest IDs, not physical member effects.
   Current staged descriptor infers component kinds from coarse directory presence.
5. Add a behavioral RED test using real projectors and real files:
   stage multiple skills plus profiles, remove one expected skill while another
   survives, retain the manifest and remaining kinds, then probe/repair through
   the existing provider. Assert the omitted member is detected and repaired.
   Do not accept category presence as proof of complete membership.
6. Add a RED repeat-build test at existing `project` or `build` entrypoints.
   Compare lstat/content/link/mode/mtime for every staging node; current
   content-only idempotence tests cannot detect same-bytes rewrites.
   Use deterministic mtime sentinels after setup rather than flaky sleeps.
7. Establish a nonempty full-bundle writer witness against the old dry-run's
   manifest-only report. Record all changed members, directories and manifest
   with an independent oracle; do not translate returned IDs into invented paths.
8. Add missing-required-source and custom-destination/symlink preservation
   regressions where the observed entrypoint violates the owner contract.
   `_read_source` currently yields empty placeholders for missing files;
   a successful empty placeholder is not complete assessment.
9. Run and retain actual assertion failures before any functional fix.
   Import failures, unknown `--plan-json`, mocked writers, forced pytest failure,
   skipped tests and startup crashes do not qualify as RED.
10. Commit the real failing tests separately through the parent-governed workflow,
    before implementation commits. Record the exact red SHA and output.
    Then perform only focused, behavior-preserving tidy-first extraction of
    touched methods; retain a distinct step and focused characterization results.

**Files**: Extend existing provider, projector and builder test files above
(approximately 80-140 test lines across the selected seams).
Tidy only owned production methods after the RED requirement is satisfied.

**Validation**: Witness a member omission and repeat-write failure through
pre-existing behavior, plus passing advisory/disabled and source-confinement
controls. Record which historical behavior is defective versus protected.
Do not claim a test ran merely because its expected failure follows from source.

### Subtask T040: Prepare whole staged bundle and manifest from delivered owner outputs

**Purpose**: Produce one immutable, complete owner assessment without staging
temporary output or invoking a writer to discover bytes.

**Steps**:

1. Extend the existing bundle projection/model seam with concrete immutable
   prepared entries: destination, exact bytes/type/mode, source observations,
   ownership proof and all contributing logical owners.
   Use WP02 PhysicalEffect/Disposition/OwnerAssessment values; no rival schema.
2. Extract selection/render/compare from `bundle_entries_for_plans`,
   per-target projectors and existing manifest rendering.
   Preserve target layouts, ordering and the installed-version source.
   Keep SurfacePlanBuilder and provider registry as inventory authorities.
3. Consume concrete WP04-WP07 prepared output for members not yet materialized
   on disk. Do not bootstrap/install prerequisites to discover their content,
   read stale pre-repair bytes, or create a generic virtual filesystem.
   Exclude CONTEXT_FILE and RULE as current bundle policy requires.
   Preserve configured-agent scope and user-global exclusion.
4. Distinguish upstream missing-on-disk-but-prepared content from genuinely
   unavailable required content. The former can be assessed exactly; the latter
   is incomplete with an owner/source diagnostic, not an empty string.
   Optional absent MCP/hooks remain inapplicable under target policy.
5. Prepare every selected member and applicable manifest before comparing.
   Enumerate parent directories and final modes. Explicit CLI build preparation
   also includes its actual supporting outputs: Claude wrappers/hooks and sibling
   marketplace catalog; Codex marketplace and applicable MCP/hooks descendants.
   Do not falsely report CLI-only artifacts for plan-level provider projection.
6. Preserve Claude manifest path lists and nontrivial-hook pointer behavior;
   Codex must keep forbidden agents/hooks keys absent and its MCP pointer
   conditional on real prepared companion output. Do not execute wrapper scripts.
7. Replace `seen[relative_path]` first-wins behavior with explicit agreement:
   identical shared output has one physical effect retaining all owners;
   differing desired bytes/type/mode is a diagnosed conflict.
   Deduplicate physical destinations across root aliases without following
   hostile links. Do not acquire upstream source-file write ownership.
8. Compare bytes/type/mode before scheduling writes. Equal outputs become
   unchanged dispositions; unknown custom content is preserved, and managed
   drift stays consent-required. A name or existing plugin.json alone is not
   blanket ownership of the staging tree.
9. Observe source bytes, selected config/catalog, manifests and destination
   kind/hash/link/mode/mtime, including parents and missing destinations.
   Enumerate exact managed removals only where current owner policy authorizes
   them; never recursively erase an unknown directory or adopt its contents.
10. Retain prepared manifest bytes and any once-sampled timestamp.
    Effect IDs and paths must be deterministic; apply cannot resample time.
    Do not persist prepared data or add install/enable instructions as effects.

**Files**: Modify projection.py/model.py, relevant per-target modules and the
owned provider (roughly 120-220 focused production lines; split helpers locally
when needed). No planned-new literal owned file is required.

**Validation**: Real missing-source, prepared-upstream-output, multi-member,
shared-output and conflicting-output tests. Read-only assessment must leave
project, staging and isolated home unchanged, including transient write attempts.
Require nonempty effects for explicitly selected missing/stale bundles and
zero effects plus explicit disposition for default advisory/disabled bundles.

### Subtask T041: Rechecked existing build/application without automatic plugin installation

**Purpose**: Consume exactly prepared owner output through existing writers,
with whole-batch refusal on changed inputs and truthful partial outcomes.

**Steps**:

1. Implement the WP02 assessment/apply protocol on PluginBundleProvider.
   Preserve reporting APIs and route changed repair/build callers through the
   same preparation seam; do not reconstruct provider context from finding IDs.
2. Preserve explicit selected staging versus ordinary upgrade policy.
   Neither `--yes` nor presence of a stale staging directory enables a plugin.
   WP10 consumes this provider; WP08 does not wire startup or upgrade CLI.
3. Before the first owner write, recheck all source/config/manifest and
   destination observations, including missing parents and parent symlinks.
   Use existing locks where available; changed input returns
   `precondition_changed` and zero batch writes. Never silently reassess/force.
4. Consume prepared bytes through existing bundle/JSON/wrapper writers.
   Avoid write_text/write_bytes/chmod/replace for unchanged nodes.
   Preserve wrapper final executable modes and safe atomic replacement.
   Do not run external CLI validation or uvx wrappers during assessment.
5. Reconcile Codex's optional hooks copy path: its current rmtree/copytree must
   not destroy unowned staged descendants or follow escaping links.
   Use exact observed owned effects and preserve unknown/custom occupants.
   Do not invent cleanup of unsupported bundle components.
6. If an explicitly approved managed replacement needs retention, use the
   contract's owner/state-derived no-clobber rules, concrete paths and collision
   observations; preserve existing backups. Never time-name hidden backups.
7. Treat source/manifest failure before writes as blocked/incomplete, not empty
   success. Once I/O starts, report actual succeeded/failed/skipped effect IDs.
   Do not append every requested manifest ID to repaired after partial failure.
   Any updated manifest must describe only valid materialized state.
8. Preserve per-file atomic behavior; no cross-owner rollback promise.
   Report persistent infrastructure effects and bounded transient apply artifacts.
   A temporary wrapper file is permitted only during apply, never preparation.
9. Keep pre-existing explicit build validation behavior independently tested.
   Do not use `skip_validate`, absent external tooling or mocked validation as
   evidence of bundle correctness; local content/effect acceptance must execute.
   Any unavailable required validator remains an explicit unmet verification.
10. Route upstream API mismatch or shared-owner conflict to the parent/WP owner.
    Do not edit WP02 dispatch, WP04-WP07 installers, or WP10 integration locally.

**Files**: Modify existing provider, write_bundle/write_json, target build paths
and wrapper writer as needed (approximately 100-180 focused production lines).

**Validation**: Race each of source, manifest, destination and parent link after
assessment. Each refuses before the first batch write with unchanged sentinels.
Inject one bounded I/O failure after a real successful write and verify truthful
partial result and manifest state. Unmutated control must execute real writes
and match every prepared after hash exactly, even when the clock advances.

### Subtask T042: Complete-member, shared-output, preservation and idempotence tests

**Purpose**: Prove FR-002/003/004, NFR-004 and C-001 with independently observed
owner effects, rather than two assertions backed by the same production logic.

**Steps**:

1. Build realistic disposable project/home fixtures through canonical setup
   before measurement; inject missing/stale members afterward.
   Use the delivered WP01 oracle without editing its support directory.
   Small layout unit fixtures may supplement, not replace, real owner evidence.
2. Capture an explicitly selected complete missing bundle and a populated stale
   bundle with at least two skills, a profile and applicable hooks/native output.
   Compare exact normalized root/path/action/kind/mode effect sets with actual
   independent filesystem delta; assert nonempty member AND manifest/directory
   coverage. Compare exact prepared bytes and raw hashes within one invocation.
3. Test every default provider target, then preserve explicit Claude/Codex
   builder coverage separately. Assert CLI-only wrapper/catalog outputs at
   their real locations when those builders run; do not broaden provider targets.
4. Use equivalent independent fixtures for assess/apply comparison, with isolated
   roots normalized only for identity. No path/content/manifests exclusion.
   Newly assigned timestamp normalization is allowed only at the exact fields
   in the owner contract; bundle paths and per-invocation bytes stay exact.
5. Cover shared codex/vibe contribution, one physical staged write/all owners,
   differing-source collision refusal, missing manifest with retained custom
   content, malformed required source, and owned versus unknown symlinks.
   Keep ignored files, extra custom bundle entries and outside-root sentinels.
6. After successful apply, reassess: no remaining repair effects.
   Repeat apply/build: no node additions/removals or bytes/type/mode/link/mtime
   change, including manifests and wrapper modes. Parent directory mtimes remain
   unchanged on the repeat; changed child creation on first apply is observed.
7. Add mutation controls in disposable copies: remove a manifest effect,
   remove one member effect, overwrite a custom sentinel, and restore an
   unconditional same-bytes write. Each must fail the corresponding oracle.
   Keep an unmutated passing control; no production helper computes actual delta.
8. Verify default optional/disabled output remains unselected and write-free;
   explicitly selected repair remains reachable. Do not manufacture required
   status to make integration look nonempty. Feed WP10/WP13 the exact fixture
   and selection evidence for their public plan/apply cells.
9. Isolate HOME/USERPROFILE/XDG/APPDATA/LOCALAPPDATA/SPEC_KITTY_HOME and temp/tool
   roots in every test subprocess; clear escaping overrides and set sync=0 last.
   Resolve direct executables before changing child HOME. No live credentials,
   production network, global test assets, or bootstrap to warm a cold witness.
10. Check effective fixture policy before running: shared conftest may set
    sync=1. Consume the parent-approved isolated sync-off harness policy;
    do not disable conftest, weaken tests or accept an outer env var as proof.
    Missing prerequisites/failing controls block acceptance until owner resolution.

**Files**: Extend all affected existing bundle/provider/build tests listed above,
including _support.py only for bundle-local fixtures (roughly 150-250 test lines).
No shared fixture, architectural test or preview_support edits.

**Validation commands** (future implementer only, from resolved absolute workspace):

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/specify_cli/tool_surface/bundles/ tests/specify_cli/tool_surface/providers/test_plugin_bundle.py tests/specify_cli/tool_surface/test_plugin_build_codex.py tests/specify_cli/tool_surface/test_plugin_build_claude.py -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/specify_cli/tool_surface/ -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 PATH="$PWD/.venv/bin:$PATH" make test-fast
.venv/bin/ruff check src/specify_cli/tool_surface/bundles/ src/specify_cli/tool_surface/providers/plugin_bundle.py tests/specify_cli/tool_surface/bundles/ tests/specify_cli/tool_surface/providers/test_plugin_bundle.py tests/specify_cli/tool_surface/test_plugin_build_codex.py tests/specify_cli/tool_surface/test_plugin_build_claude.py
.venv/bin/mypy --strict src/specify_cli/tool_surface/bundles/ src/specify_cli/tool_surface/providers/plugin_bundle.py
```

Run changed-module tests and relevant existing layer/import/dead-symbol gates
as well; record exact selections. Full architecture is required for cross-cutting
changes, which are outside this WP's ownership; route such need to the parent.
Do not run make test-full. No uv sync/resync: the warm venv is supplied.
Record all commands/cwd, SHA, effective environment, exit, collected/executed/
passed/failed/skipped counts and assertion output. Report pre-existing failures
under charter policy through the parent; no retry-to-green or skip/xfail waivers.
Report platform capability limits with missing evidence; do not silently pass them.

## Definition of Done

- All four subtasks have retained RED-before-fix and final GREEN evidence where
  behavior changed, with separate test/fix commit identities and focused tidy-first.
- Selected assessment covers all real members/supporting files, directories,
  modes and manifest outputs; advisory/disabled surfaces remain dispositions.
- Whole-batch recheck races write nothing; partial I/O failure remains truthful.
- User content and symlink targets survive; repeated application has zero churn.
- Ownership stays exactly within WP08; dependency contracts are consumed.
- All affected tests, subsystem baseline, lint/types and applicable gates have
  recorded outcomes; independent reviewer verifies the actual final diff.
- Parent receives portable requirement-to-test/effect evidence for WP10/WP13.
  Owner completion alone does not claim full public upgrade or wheel acceptance.

Canonical implementation command, for the future execution phase only:
`spec-kitty agent action implement WP08 --agent codex --mission upgrade-preview-mission-health-01M1V6E1`.
Run it with sync disabled using the resolved absolute warm CLI; the runtime
chooses workspace/lane. The prompt author must not execute it.

Per-subtask completion is a canonical event-sourced record, not a checkbox.
Only after each subtask's evidence exists, the future implementer records:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T039 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T040 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T041 --status done --mission upgrade-preview-mission-health-01M1V6E1
SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T042 --status done --mission upgrade-preview-mission-health-01M1V6E1
```

These commands are instructions only, not executed during prompt authoring.
Do not hand-edit tasks.md, frontmatter lane, metadata, manifests or event/snapshot
state to assert completion. Never fabricate gates, commits or review verdicts.
Do not self-approve; parent coordinates an independent reviewer.

## Risks

- Coarse presence checks hide missing members: compare expected concrete output.
- Optional staging can become accidental installation: retain selected-policy
  boundaries and positive explicit-staging/negative ordinary-upgrade controls.
- Projectors can silently use stale upstream files: consume prepared projections
  and retain their observations; missing deliveries block dependent work.
- First-wins dedup loses owners or content: merge identical claims, reject conflict.
- Existing rmtree/write paths erase customizations or churn mtimes: exact ownership,
  all-input recheck and independent filesystem oracle are required.
- External validators may be unavailable: report the gap without a skip waiver.

## Reviewer Guidance

Reproduce the original member/mtime RED against the recorded base, then run
the same tests on final code. Inspect real owner calls and fixture provenance;
mocks of the provider/writer or expected-delta production helpers invalidate proof.
Verify immutable prepared bytes are actually consumed after full-batch recheck.
Reject hidden manifest/member/parent writes, broad source fallback, blanket
stage-tree ownership, missing-source placeholders and forced optional activation.
Inspect both successful and partial-failure manifests and all preserved sentinels.
Confirm all five manifest dependencies and four subtask IDs remain unchanged.
Require literal create-intent validation and a nonempty production authority.
Return evidence/findings to the parent; do not advance other WPs or dispatch Ops.
