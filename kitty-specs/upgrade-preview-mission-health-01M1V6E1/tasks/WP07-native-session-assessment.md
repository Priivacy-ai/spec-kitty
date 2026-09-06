---
work_package_id: WP07
title: Native configuration and session presence assessment
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
- T034
- T035
- T036
- T037
- T038
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/session_presence/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/native_config.py
- src/specify_cli/tool_surface/providers/session_presence.py
- src/specify_cli/session_presence/**
- src/specify_cli/skills/vibe_config.py
- tests/specify_cli/session_presence/**
- tests/specify_cli/tool_surface/providers/test_native_config.py
- tests/specify_cli/tool_surface/providers/test_session_presence.py
role: implementer
tags: []
tracker_refs: []
---

# WP07: Native configuration and session presence assessment

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Prepare complete, read-only native/session owner assessments and apply their
retained output through existing writers after whole-batch recheck.
Report every physical change, preserve user regions, and make repeat repair
leave bytes, node types, modes and modified timestamps unchanged.

## Context

Audience: Python implementer and independent software-engineer reviewer.
This is IC-06's native/session slice of the approved plan.
WP01 supplies the independent observation harness; WP02 supplies immutable
operations and assessment dispatch. Both dependencies must be approved or done
before implementation starts. Consume their delivered APIs; do not recreate them.
WP08 consumes prepared session output for staged bundles; WP10 integrates upgrade.
WP13 owns final public CLI and installed-wheel acceptance.

### Absolute Bindings and Governance

Repository root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`

Mission root:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`

External authoring brief:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/../task-authoring-brief.md`

Binding charter:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`

Resolved planning profile source (CLI reported built-in layer):
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`

Assigned implementer built-in source:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`

Load the implementer through the resolver; apply its actual initialization,
boundaries, directives and tactics. Read the binding charter before coding.
The author's first profile/context calls used SaaS sync disabled. Context
returned empty directives/tactics with unresolved-governance diagnostics:
known #3908, not evidence that governance is absent or successfully resolved.
If repeated, disclose the degradation and bind explicitly to the charter and
resolved profile source; do not repair governance/config in this WP.
Planner Priti authors sequencing only, without implementation or architectural
decisions. Directive 003 binds rationale here to plan D2/D5 and owner contracts.
Python Pedro applies test-first, locality, type safety and canonical authority;
repository Python >=3.11 remains binding despite the profile's 3.12+ preference.

Read these absolute mission inputs:
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/AGENTS.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/missions/mission-steps/software-dev/tasks-packages/prompt.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md`

For command examples, bind the absolute root once:
```sh
WP07_REPO='/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty'
WP07_MISSION='upgrade-preview-mission-health-01M1V6E1'
```

Frontmatter paths remain exactly manifest-relative, as the ownership schema
requires. Body source/test names below resolve beneath the absolute root above;
after canonical implementation setup, use its returned absolute checkout.
Never reconstruct a lane path or choose a base branch manually.
Implementation command, for the future implementation phase only:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent action implement WP07 --agent codex
```

### Ownership and Sequencing

The explicit primary production prefix avoids the empty common-prefix defect
#2446. All literal owned paths exist at authoring time; no new literal files are
planned, hence `create_intent: []`. Extend existing tests and writer modules.
Any later proposed new literal path needs parent-coordinated ownership and
create-intent reconciliation before work; do not silently broaden the manifest.

Do not edit WP02 operations/protocol/registry/service files, WP03 global runtime,
WP04 command installers, WP05 managed skills, WP06 profiles, WP08 bundles,
WP09 charter preparation, WP10 startup/CLI/finalizer, or WP13 acceptance files.
Do not edit shared conftest, preview_support, dependency files, versions,
mission manifests/tasks/meta/state or corpus/history. Parent owns issue-matrix,
tracers and final gates; return evidence for those records.
No global asset writes, global installation, SaaS/network activity, Op dispatch,
manual status fabrication, broad skip/xfail or gate waiver. Route shared-harness
corrections to WP01; retain the failing evidence until the owner resolves them.

### Subtask T034: Characterize native/session writer ownership and mixed-file regressions

**Purpose**: Establish real RED at existing entry points and a bounded cleanup
plan before changing functional behavior.

**Steps**:
1. Inspect `src/specify_cli/tool_surface/providers/native_config.py`:
   `repair` reports surface IDs, while `_apply` calls
   `ensure_project_skill_path`; unsupported tools are research-gap dispositions.
2. Inspect `src/specify_cli/skills/vibe_config.py`: the current helper creates
   its parent and serializes the whole TOML object even when the path exists.
   Establish fixtures with comments, custom paths, tables and terminal newlines.
3. Inspect `src/specify_cli/tool_surface/providers/session_presence.py`:
   `_rewrite` invokes each writer's complete batch; `_managed_surfaces`
   exposes two hook instances at one settings path. Logical IDs are not effects.
4. Trace `src/specify_cli/session_presence/writers/markdown_rules.py`,
   `writers/claude_code.py`, `hooks/claude_code_hook.py`, and `manager.py`.
   Markdown currently calls `_atomic_write` unconditionally. Claude writes
   orientation before registering hooks. Manager content can launch a background
   upgrade check even in its existing dry-run update path.
5. Add regressions in the two owned provider tests and existing session writer
   tests. Through the existing Vibe helper, require unowned TOML text unchanged;
   through the existing Markdown writer, require repeat bytes/mode/mtime equality.
6. Through existing `SessionPresenceProvider.repair`, pair stale orientation
   with malformed settings and require the whole owner batch to refuse without
   altering orientation, settings or creating an invalid backup.
   Existing code's backup-and-rewrite behavior must be witnessed, not inferred.
7. Record baseline commit, exact node IDs, command, failing assertion and output.
   Missing new API/import/option, fixture setup failure or all-empty effects
   cannot serve as RED. Use real providers/writers, not mocks of their behavior.
8. Commit regression tests separately before functional implementation through
   the parent's canonical lane workflow. Preserve the failing commit identity.
   Then perform only necessary behavior-preserving tidy-first extraction in
   touched methods, with focused characterization tests; keep that step distinct.

**Files**: Existing provider tests plus session Markdown/Claude writer tests;
production inspection is bounded to frontmatter ownership. No new test harness.

**Validation**: At least one actual preservation failure and one real no-churn
failure at pre-existing entry points, with explicit RED provenance. Existing
substring-only and duplicate-marker tests remain useful but are insufficient.
No test/commit/status command is executed during this prompt-authoring phase.

### Subtask T035: Prepare native config and Vibe managed entries without writing

**Purpose**: Keep the Vibe helper authoritative for TOML policy while producing
immutable desired bytes and complete effects before application.

**Steps**:
1. Extract read/validate/render/compare preparation in
   `src/specify_cli/skills/vibe_config.py`; adapt
   `src/specify_cli/tool_surface/providers/native_config.py` to WP02 values.
   Do not introduce another config catalog or serializer in upgrade.
2. Resolve the configured project once; observe source config, destination
   lstat, bytes/hash/mode/mtime and parent confinement. Preparation performs no
   mkdir, write, backup, lock creation, ensure call or write/delete simulation.
3. Preserve string/list input compatibility and existing user skill paths.
   Add the exact shared skill path once, without converting an already healthy
   scalar solely for normalization or reordering unrelated entries.
4. Modify only the owned top-level TOML entry. Preserve unowned comments,
   tables, ordering, values and surrounding text. Use installed dependencies
   or bounded format-aware owner logic; no new dependency or global setup.
   Validate rendered TOML; do not use a regex that can hit nested table keys.
5. Distinguish absent config from unreadable/malformed config and invalid
   skill_paths types. Required bad input yields incomplete/blocked diagnostics
   and no application for that batch, never catch-to-empty/all-agent fallback.
6. Emit exact project-relative create/update/chmod/replace effects as applicable,
   including absent parent directories and final node modes. A healthy config
   contributes unchanged disposition, with no rewrite or redundant chmod.
7. Unknown/custom links, escaping parents and unsupported ownership remain
   preserved/refused. Do not follow a link to claim ownership or repair its target.
   Keep non-Vibe research-gap behavior and configured-agent applicability.
8. Retain desired bytes and input observations in opaque immutable owner data.
   Existing `ensure_project_skill_path` consumes the same preparation on apply;
   it must not independently rerender or discover additional writes.

**Files**: Modify the two native production modules and
`tests/specify_cli/tool_surface/providers/test_native_config.py`.
Keep preparation small and owner-local; helpers stay in existing owned modules.

**Validation**: Missing .vibe produces nonempty directory/file effects;
mixed TOML produces exactly the owned change; valid existing discovery has zero
effects and unchanged mtime. Parse errors leave raw bytes and parents unchanged.
Compare prepared after hash to actual bytes, not to another production helper.

### Subtask T036: Prepare orientation/rules/hooks/session content with unowned-region preservation

**Purpose**: Plan the complete writer batch, including shared files and sibling
hook effects, while retaining the existing writer registry and format authority.

**Steps**:
1. Extend owner preparation in `src/specify_cli/session_presence/writers/`
   and `src/specify_cli/session_presence/hooks/claude_code_hook.py`.
   Reuse `content.py`, writer metadata, registry, markers and exact hook commands;
   do not duplicate their path inventory in the provider or composer.
2. Prepare Markdown from observed bytes and retained SessionPresenceContent.
   Replace only a proven managed block; preserve prefix/suffix bytes, newline
   conventions and final modes. Append without trimming pre-existing text.
   Diagnose duplicate/unbalanced markers instead of silently appending damage.
3. A known rules filename is not proof that arbitrary custom content is owned.
   For full-file rules, preserve unknown content and edited managed regions;
   use explicit managed-path/content proof for automatic replacements.
   Keep existing version-based staleness semantics: same-version health text
   alone must not become endless upgrade churn.
4. Prepare Claude orientation and final settings together. Merge SessionStart
   and Stop into one desired JSON object and one physical settings effect.
   Preserve foreign keys, hook events, matcher metadata, entries and commands.
   Exact Spec Kitty hook commands are the managed entries, not broad prefixes.
5. A malformed/non-object/unreadable settings file or invalid required hook
   structure blocks automatic assessment/application before the first write.
   Do not reach `_load(preserve_invalid=True)` or allocate UUID backups in
   preview. Existing direct registrar recovery tests cover a distinct legacy
   recovery caller; preserve that behavior unless an approved contract changes it.
6. Shared AGENTS.md writers (Codex/OpenCode/Antigravity and preamble fallbacks)
   supply one physical update retaining all participating logical owners.
   Conflicting desired bytes are explicit conflicts, never last writer wins.
7. Respect configured/disabled tools, `can_write`, missing harness roots,
   `NullWriter` and exact context/rule/hook selection. A selected writer may
   need sibling effects, so assess its complete physical batch, not just findings.
8. Do not call `SessionPresenceManager._build_content` from assessment when it
   can start network/background/cache work. Separate pure supplied content from
   live session-start behavior; retain an explicit no-network input path.
   Missing required content sources must not become fabricated healthy success.

**Files**: Existing session writers/hooks/content/manager as needed and provider
adapter; tests in existing Markdown, AGENTS.md, Claude hook/writer and manager
files. Avoid unrelated open-ops or live upgrade-check redesign.

**Validation**: Nonempty orientation/rules/settings fixtures preserve exact
unowned Markdown bytes and decoded foreign JSON structures. Both hooks share one
effect; all necessary parents appear. Assessment has zero persistent/transient
writes and no background work. Render once; apply consumes exact prepared bytes.

### Subtask T037: Native/session provider integration and rechecked existing-writer application

**Purpose**: Connect owner preparation to WP02 dispatch without an alternate
write engine, duplicate policy, or optimistic success reporting.

**Steps**:
1. Implement WP02's delivered assessment/apply protocol in the two owned
   providers. Retain reporting compatibility and provider instance/source context.
   Existing repair entry points delegate to the same decision/render/compare seam.
2. Return effects, dispositions, completeness, diagnostics, input observations
   and prepared data. Use root-relative paths with surface_repair phase;
   include concrete reasons, ownership proof and all logical owners.
3. Before any owner-batch write, recheck every relevant source/config,
   destination and parent observation under existing locks where available.
   A changed byte/hash/type/mode/mtime or escaping/replaced parent returns
   precondition_changed for the batch; perform zero writes and require reassessment.
4. Validate Claude's full orientation/settings batch before writing orientation.
   Recheck config even if the reported repair was hook-only. Do not invoke
   separate write-time discovery that can add unreported sibling operations.
5. Apply via existing format-aware atomic writer seams using prepared content.
   Keep exclusive/constrained temp handling; never clobber an unrelated existing
   .tmp sentinel. Report bounded transient atomic artifacts separately.
   Any persistent lock/support directory must be a declared effect.
6. Skip byte/type/mode-equal output without opening it for writing. Preserve
   existing modes unless a real managed mode change was explicitly assessed.
   Same bytes with changed mtime is still a no-churn failure.
7. Preserve drift/unknown content under --yes. Independent known missing-file
   repair may proceed when its batch is valid, with unresolved drift reported.
   Malformed required state prevents the entire affected owner batch.
8. On actual I/O failure after some writes, return truthful succeeded/failed/
   skipped physical IDs and diagnostics; no all-requested success or rollback
   promise. Keep existing finalizer outcome authority in WP10.

**Files**: Owned providers and native/session writer apply seams; extend existing
provider tests for dispatch, race refusal and real filesystem partial failure.
No edits to core operations, registry dispatch, CLI or finalizer.

**Validation**: Change the last destination, source input or parent after assess;
prove earlier files remain untouched and no temporary write was attempted.
A permitted missing-hook repair has a nonempty real delta equal to its plan.
Inject an I/O fault only at the low-level boundary after a real first write;
verify observed successful IDs and failure report agree.

### Subtask T038: Mixed-file, malformed config, disabled surface and no-churn tests

**Purpose**: Make owner-effect coverage independently checkable and resistant
to empty plans, stub writers and preservation omissions.

**Steps**:
1. Use WP01's delivered independent lstat/content/link/mode/mtime oracle.
   Build equivalent disposable project/home fixtures via real owner setup,
   then introduce defects before snapshots. Never derive expected deltas using
   production effect helpers or supply production's own planned paths to scanning.
2. Cover missing Vibe config, mixed TOML, stale marked orientation, missing
   hooks, missing rule subdirectory, and shared AGENTS.md output.
   Require nonempty real effects for each applicable repair family and exact
   equality of root/path/action/final kind/mode plus exact prepared hashes.
3. Assess then apply in one invocation and compare exact prepared bytes.
   Independently assess/apply equivalent roots and normalize only root identity;
   native/session content gets no arbitrary timestamp/hash/content waiver.
4. Reassess and apply repaired fixtures twice. Require no effects and unchanged
   full snapshots, including mtime, directories, links and foreign sentinels.
   Include same-version health-line differences and selected shared writers.
5. Cover malformed TOML/JSON, non-object JSON, invalid managed-entry structure,
   unavailable required inputs, disabled agents, unsupported tools, malformed
   markers, custom whole-file rules, and unknown/escaping symlinks.
   Required failures must be explicit; not-applicable surfaces remain nonfatal.
6. Mutation controls in disposable copies: omit settings effect, omit a parent
   effect, force unowned-byte overwrite, and restore unconditional same-bytes
   rewrite. Each relevant oracle/assertion must fail while the unmutated case
   passes. No production writer mocks, permissive subset comparison or empty floor.
7. Add transient-write denial through WP01 support without replacing writers.
   Apply may use declared atomic artifacts; preview may not create/delete them.
   Record platform capability limits and obtain capable-platform evidence;
   capability skips are not acceptance and no blanket waiver is permitted.
8. Run owned tests, full affected subsystem tests, make test-fast, changed-module
   Ruff/mypy and relevant existing architecture gates. Record exact counts,
   provenance and red-to-green linkage; report baseline failures under charter
   policy through the parent rather than hiding them or retrying to green.

**Files**: Existing owned provider and session test files only.
The Vibe helper's affected skills tests are runnable but not writable by this WP.

**Validation commands** (future implementation only; use returned checkout root):
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/pytest" -c "$WP07_REPO/pytest.ini" "$WP07_REPO/tests/specify_cli/session_presence" "$WP07_REPO/tests/specify_cli/tool_surface/providers/test_native_config.py" "$WP07_REPO/tests/specify_cli/tool_surface/providers/test_session_presence.py" -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/pytest" -c "$WP07_REPO/pytest.ini" "$WP07_REPO/tests/specify_cli/tool_surface" "$WP07_REPO/tests/specify_cli/skills" -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 make -C "$WP07_REPO" test-fast
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/ruff" check "$WP07_REPO/src/specify_cli/session_presence" "$WP07_REPO/src/specify_cli/skills/vibe_config.py" "$WP07_REPO/src/specify_cli/tool_surface/providers/native_config.py" "$WP07_REPO/src/specify_cli/tool_surface/providers/session_presence.py" "$WP07_REPO/tests/specify_cli/session_presence" "$WP07_REPO/tests/specify_cli/tool_surface/providers/test_native_config.py" "$WP07_REPO/tests/specify_cli/tool_surface/providers/test_session_presence.py"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/mypy" --strict "$WP07_REPO/src/specify_cli/session_presence" "$WP07_REPO/src/specify_cli/skills/vibe_config.py" "$WP07_REPO/src/specify_cli/tool_surface/providers/native_config.py" "$WP07_REPO/src/specify_cli/tool_surface/providers/session_presence.py"
```

Use direct warm binaries, no uv resync. Run from the resolved absolute checkout
with its approved isolated fixture environment. Bind every child HOME,
USERPROFILE, XDG/APPDATA/LOCALAPPDATA, SPEC_KITTY_HOME and temporary root inside
the sandbox; clear escaping overrides and set child sync=0 last.
Use PYTHONDONTWRITEBYTECODE=1 and read-only Git observations.
Root conftest can reset sync=1: parent must establish effective sync-off fixture
policy before these runs; environment launch flags alone are not proof.
Do not disable conftest, deselect failing tests or edit shared fixtures.
No whole-repo make test-full; parent owns aggregate architecture/E2E/wheel gates.

## Definition of Done

- T034 has committed, witnessed RED through existing entry points before fixes.
- T035/T036 expose pure, complete native/session preparation with preservation.
- T037 applies retained bytes only after whole-batch recheck, with honest outcomes.
- T038 proves nonempty plan/delta equality, mixed-file preservation and no churn.
- Required tests/lint/types and relevant architecture checks have recorded results.
- Independent reviewer can reproduce RED on the planning base and GREEN on final
  code; future-API failures and mocked owner successes do not count.
- Return exact commit SHAs, commands, node IDs/counts, raw snapshot hashes, mutation
  results and unresolved failures for parent traceability and WP08/WP10 handoff.
- Subtask completion authority is the reduced event log, not a ticked checkbox,
  frontmatter lane, edited tasks.md, hand-written snapshot or summary claim.

After each subtask's evidence exists, use the canonical event-producing command
`spec-kitty agent tasks mark-status <Txxx> --status done`.
The following exact scoped invocations are instructions only: do not execute
them while authoring this prompt or claim that they have already run.
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent tasks mark-status T034 --status done --mission "$WP07_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent tasks mark-status T035 --status done --mission "$WP07_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent tasks mark-status T036 --status done --mission "$WP07_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent tasks mark-status T037 --status done --mission "$WP07_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP07_REPO/.venv/bin/spec-kitty" agent tasks mark-status T038 --status done --mission "$WP07_MISSION"
```
Let the canonical resolver select the status partition. Do not invent event rows,
manually write lifecycle state, execute Op dispatch or mark review approval.

## Risks

- Whole-file TOML serialization destroys comments: use owned-entry preparation
  and byte-preservation witnesses, not decoded-value-only assertions.
- Claude writes siblings and two hooks share a path: prepare/recheck the complete
  owner batch and compare physical effects instead of logical ID counts.
- Legacy registrar malformed-config recovery is mutating: block automatic upgrade
  assessment without weakening separately tested direct recovery behavior.
- Manager background checks contaminate preview: keep assessment content supplied
  and pure; live session behavior remains separately exercised.
- Safe-name assumptions, temp collisions and shared writers can destroy custom
  content: exact ownership, confinement observations and mutation controls apply.
- Authoring and tests do not prove public startup purity. WP10/WP13 must integrate
  and execute their gates; this WP supplies owner evidence without claiming them.

## Reviewer Guidance

Inspect the existing-entry-point RED commit before reading the fix.
Reject all-empty equality, substring-only preservation, mocked writers,
logical-ID effect counting, successful invalid-config recovery during preview,
or tests that omit directories/mtime/symlinks.
Verify new preparation has real callers in both reporting and existing repair,
with no competing inventory, generic transaction engine or serialized apply token.
Check same-version health policy, configured applicability, shared AGENTS.md,
one settings effect, and complete refusal when a late batch input changes.
Observe actual writer outcomes and exact per-invocation hashes; do not approve
from an architecture gate or test count alone.
Confirm changes stay in manifest ownership and that the parent receives evidence
for unresolved gate prerequisites. Independent review approval is a separate
runtime action, never a claim manufactured by the implementing agent.
