---
work_package_id: WP03
title: Pure startup intent and global runtime assessment
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-004
- C-001
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- src/specify_cli/upgrade/intent.py
- tests/runtime/test_upgrade_preview_bootstrap.py
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/intent.py
- src/specify_cli/runtime/**
- src/specify_cli/tool_surface/providers/slash_commands.py
- tests/runtime/test_upgrade_preview_bootstrap.py
- tests/runtime/test_bootstrap_unit.py
- tests/runtime/test_agent_skills.py
- tests/specify_cli/runtime/**
role: implementer
tags: []
tracker_refs: []
---

# WP03: Pure Startup Intent and Global Runtime Assessment

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

The legacy alias maps to canonical `/spk-doctrine-profile-load`.
Run `env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro`.
Then load `charter context --action implement --json` with the same environment.
Read the binding project charter and apply its resolved/explicit governance.
Known #3908: successful context exit can still contain unresolved governance.
Disclose missing selected directives/tactics; do not claim full resolution.
Use the warm venv directly; no resync, global asset setup or model override.

## Objective

Expose one parse-only upgrade intent and read-only global-owner assessments
whose prepared effects can be applied through existing writers after recheck.
WP03 must be independently green without altering public root startup wiring;
WP10 integrates startup suppression and validated-apply ensures together.

## Context

Mission: `upgrade-preview-mission-health-01M1V6E1`.
Implementation entry, after the parent authorizes the runtime-owned workspace:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP03 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

Do not choose a base branch manually; use the returned canonical workspace.
All implementation paths below are relative to that resolved checkout.
Planning authority is the root mission's `wps.yaml`, not a coord copy.
Read `spec.md`, `plan.md`, `data-model.md`, `research.md` and all contracts.
In particular, obey `contracts/owner-operations.md` and `contracts/upgrade-cli.md`.
Use `contracts/acceptance.md` for G0-G7 and independent observer semantics.

WP01 supplies isolated fixtures and independently tested snapshot/write observers.
WP02 supplies immutable operation values and assessment/dispatch interfaces.
Consume those deliveries; do not fork either framework or edit their files.
WP05 consumes global skill preparation instead of writing global assets itself.
WP10 consumes intent and global preparation APIs; WP13 owns aggregate acceptance.
The external `task-authoring-brief.md` splits root startup files into WP10.
That authoritative slicing supersedes the broader IC-02 concern-map ownership.
Never edit `src/specify_cli/__init__.py`, `cli/helpers.py` or `cli/commands/upgrade.py`.
Do not acquire `src/runtime/next/**`; that is a different runtime domain.
No charter, shared conftest, skills installer, registry or corpus ownership here.
Route interface/harness corrections to WP02/WP01; do not make overlapping edits.

`authoritative_surface` is the longest common production prefix.
Source and test paths together have no nonempty common prefix; the canonical
validator requires a nonempty prefix of at least one owned path.
This annotation does not grant ownership beyond the exact frontmatter list.
Both absent literal owned paths are explicitly declared in `create_intent`.

### Subtask T011: Characterize Existing Global Owner Effects and Commit Owner-Level Red Regressions

**Purpose**: Establish real defect witnesses and a tidy-first baseline before
introducing new APIs or changing owner behavior.

**Steps**:
1. Inspect `runtime/bootstrap.py:ensure_runtime`, `populate_from_package`,
   `runtime/merge.py:merge_package_assets`, and the command/skill ensure methods.
2. Trace `runtime/home.py` package/home resolution and the slash provider's
   `repair` to `_regenerate` to `ensure_global_agent_commands` call path.
3. Record current effects: cache/lock creation, managed-tree replacement,
   stamps, whole-agent rendering, readonly chmod and retired cleanup.
4. Inspect touched methods for domain-local debt; perform justified
   behavior-preserving tidy-first changes with focused tests before the fix.
5. Use WP01 helpers to create realistic cold/stale/current isolated homes.
   Seed custom content, a custom prefixed symlink and ignored-file sentinels.
6. Commit failing tests through existing owner entry points for actual omissions,
   unsafe cleanup or current-marker missing-content behavior before fixing them.
7. Keep baseline public #3900 witnesses external via the WP01/parent evidence
   handoff; a future API import failure is not a reproduction of the old bug.

**Files**: Existing owned runtime modules and tests; approximately 60-120 test
lines plus proportional tidy-first changes, not a wholesale module rewrite.

**Validation**:
- Each defect has exact command, failing assertion, source SHA and RED commit.
- Confirm that failure reaches the existing behavior, not fixture/import setup.
- Preserve existing positive ensure behavior and source-resolution tests.
- Never xfail/skip unresolved public startup purity to make this WP look green.
- Root files are unchanged; public purity is not this package's completion claim.

### Subtask T012: Parse-Only UpgradeIntent from Real Click Definitions

**Purpose**: Provide immutable effective intent without executing callbacks,
side-effecting defaults, project bootstrap, prompts or persistence.

**Steps**:
1. Create `src/specify_cli/upgrade/intent.py` using the domain fields in
   `data-model.md`: mode, representation, project, target, worktrees and confirm.
2. Accept/use the actual upgrade Click command definitions supplied by the
   caller; do not maintain a second hand-written argv option scanner/catalog.
3. Extract parse-only values without invoking the command, root callback,
   eager callbacks or callable defaults that could perform writes.
4. Derive effective preview for dry-run and implicit `--project --json`;
   retain actual default JSON and project-agnostic guidance distinctions.
5. Express full-plan precedence and semantic conflicts in the pure intent
   contract; do not register `--plan-json` on the public CLI in this WP.
6. Preserve standalone hidden operations as distinct from ordinary guidance;
   reject their combinations with effective preview/guidance before dispatch.
7. Keep target text uninterpreted here: WP10's existing target validator owns
   version policy; intent is not another PEP 440 or compatibility authority.

**Files**: New `upgrade/intent.py`, approximately 80-160 lines; focused cases in
new `tests/runtime/test_upgrade_preview_bootstrap.py`.

**Validation**:
- Parse reordered existing options, equals syntax, aliases and missing values
  using the real Click definitions, asserting ordinary Click usage failures.
- Assert that callback/default invocation sentinels are never reached.
- Test pure effective-intent combinations including no-project/hidden cases.
- Distinguish semantic value tests from public invocation coverage explicitly.
- WP10 adds the actual new option and runs its real-definition/public tests.
- Do not invent a replacement Typer app and call that integration evidence.

### Subtask T013: Expose Pure Intent and Global Preparation/Apply APIs Without Changing Root Startup Wiring

**Purpose**: Deliver independently callable owner interfaces for WP10's atomic
integration while preserving ordinary startup behavior in this intermediate WP.

**Steps**:
1. Consume WP02's immutable `OwnerAssessment`, effects, dispositions, input
   observations and truthful apply-result values; do not duplicate their models.
2. Extract owner-local selection/render/compare preparation from runtime writers.
   Keep runtime format/merge decisions in runtime and slash delegation in provider.
3. Return opaque immutable prepared bytes/source observations, not executable
   callbacks, serialized apply tokens or a generic filesystem overlay.
4. Implement application through existing format-aware writers and locks;
   recheck the whole owner's sources/destinations before its first write.
5. Preserve legacy ensure signatures and ordinary callers. Where an existing
   ensure delegates internally, retain its established activation/routing behavior.
6. Expose the APIs WP10 needs for validated apply and WP05 global delegation;
   record arguments, return values, errors and batching in the handoff.
7. Do not suppress bootstrap, wire intent into root, or bypass startup gates.
   WP10 owns suppression and replacement validated-apply paths in one change.

**Files**: `runtime/bootstrap.py`, `runtime/agent_commands.py`,
`runtime/agent_skills.py` and `tool_surface/providers/slash_commands.py`;
small owner-local helpers may live inside the owned runtime tree.

**Validation**:
- Assessment is read-only, prompt-free and network-free under WP01 observers.
- Apply consumes retained preparation rather than recollecting policy silently.
- Source/config/destination changes yield a precondition conflict before writes.
- Real existing ensures still work; new API-only tests do not replace them.
- Review the diff to prove all WP10 root/CLI paths remain byte-identical.

### Subtask T014: Runtime Package Merge/Stamp/Directory Assessment Using Existing Source Selection

**Purpose**: Enumerate exactly the runtime's managed physical effects without
staging or installing package assets just to discover what would change.

**Steps**:
1. Reuse `get_package_asset_root`, `populate_from_package` source-selection
   semantics and `merge.py` managed directory/file authorities.
2. Read package assets directly on cold homes; do not run ensure/populate or
   create temporary directories as an assessment implementation technique.
3. Compare managed descendants by node kind, bytes and final mode; enumerate
   needed parent directories, version stamps and persistent lock artifacts.
4. Preserve `missions/custom/`, runtime config and all unowned cache/data.
   Do not broaden source lookup to fix unrelated missing optional package assets.
5. Required unavailable sources produce typed incomplete/blocked diagnostics,
   not an empty success or a current version stamp after partial preparation.
6. Preserve staging/locking behavior on apply as bounded execution artifacts.
   An existing orphan cleanup candidate is an observable deletion, not invisible
   housekeeping; require exact owner proof, otherwise preserve/report it.
7. Avoid same-byte rewrites and unnecessary recursive replacement; stamp only
   after successful owned work and report truthful partial failures.

**Files**: `runtime/bootstrap.py`, `runtime/merge.py` and owned runtime tests;
approximately 100-180 implementation/test lines as needed after extraction.

**Validation**:
- G0/G1/G2 owner assessments are nonempty where managed work really exists.
- Verify absent dirs, stale managed nodes, safe removals and stamps explicitly.
- Independent deltas equal assessed persistent effects; custom sentinels survive.
- Healthy second assessment/apply changes no bytes, modes or mtimes.
- Lock creation is represented if persistent; preview cannot create/open it.

### Subtask T015: Global Commands and Full-Agent Refresh Effects, Exact Retired Cleanup Ownership

**Purpose**: Replace ID-only repair visibility with complete physical command
batches while preserving configured scope and unknown custom content.

**Steps**:
1. Reuse `_get_command_templates_dir`, shim registry, output-name calculation,
   `render_command_template` and existing per-agent script/extension policy.
2. Prepare the entire affected agent bundle selected by existing repair policy,
   not only the missing/stale statuses passed to `SlashCommandsProvider.repair`.
3. Include every changed rendered member, parent directory, readonly mode,
   stamp and persistent lock; unchanged members are dispositions, not writes.
4. Keep scoped `agent_keys` calls from updating the global all-agent stamp.
   Required unreadable/missing templates cannot be swallowed into success.
5. Replace filename-prefix-only retirement decisions with exact managed-path,
   canonical-content or manifest evidence allowed by the owner contract.
6. Preserve unknown `spec-kitty.custom` links/files and edited managed content.
   Never chmod through a symlink or unlink an unproven custom cleanup target.
7. Implement slash assessment/apply delegation using provider-owned context.
   Keep reporting/removal policy for unrelated consumers; no second inventory.

**Files**: `runtime/agent_commands.py`, `providers/slash_commands.py`,
`tests/specify_cli/runtime/test_agent_commands.py` and related owned tests.

**Validation**:
- Current marker plus missing command and stale file marker cannot hide work.
- Whole-agent nonempty plan equals independent physical apply delta.
- An omitted sibling/stamp/mode effect makes the comparison fail.
- Shared physical roots retain logical owners with one operation through WP02.
- Unknown cleanup candidates survive; exact managed retired candidates are shown.
- Repeat repair is no-churn even when explicitly scoped to an agent.

### Subtask T016: Global Skills Assessment/Delegation, Current-Marker Missing-Content Controls

**Purpose**: Give global skills one owner across startup/project callers and
detect incomplete content even when the global version marker is current.

**Steps**:
1. Reuse `_discover_registry`, `_unique_global_roots`, canonical frontmatter
   normalization, skill path policy and the existing retired-name authority.
2. Prepare complete selected skill trees, final readonly permissions,
   required parents, stamps and ownership-proven cleanup effects without writes.
3. Do not treat a current `agent-skills.lock` alone as content health.
   Detect missing required skill content and stale applicable output.
4. Replace destructive prefix-only cleanup and unproven canonical-path
   replacement with preserve/conflict dispositions; enumerate owned descendants.
5. Never follow an unknown symlink to inspect ownership or make targets writable.
   Exact owned type conversion is replace; preserve the old external target.
6. Expose global preparation for WP05 delegation; retain shared root/logical
   owner identity so WP02/WP10 deduplicate global work instead of double applying.
7. Keep project copy/backup/manifest policy in WP05's installer, not runtime.
   Registry/rendering failures are diagnosed before mutation, not empty catalogs.

**Files**: `runtime/agent_skills.py`, `tests/runtime/test_agent_skills.py`;
approximately 100-160 focused implementation/test lines, guided by extraction.

**Validation**:
- G3/G7 and current-marker missing-content controls reach actual owner behavior.
- Missing/stale skill content produces real effects; custom prefixed trees survive.
- Exact retired cleanup reports every persistent path and preserves drift.
- A duplicate global/project request writes once and retains all logical owners.
- Healthy second apply retains stamps and all unchanged mtimes.
- No project manifest, installer or skill registry file is edited by this WP.

### Subtask T017: Pure Intent and Warm/Cold Owner Assessment Controls; Root Behavior Unchanged Until WP10

**Purpose**: Establish this package's honest independent green and a concrete
handoff for later public startup acceptance, without masking unfinished wiring.

**Steps**:
1. Run all written/changed owner tests and affected runtime subsystem tests.
   Keep parser/owner verification distinct from WP13's public G/B/P matrices.
2. Use WP01's independently validated lstat/content/link/mode/mtime oracle;
   consume its mutation controls rather than implementing a production-derived oracle.
3. Repeat cold/stale/warm assessment and apply on independent equivalent homes.
   Assert nonempty known-repair cases, exact operations and second-apply no churn.
4. Exercise an advancing clock between assessment/apply: prepared bytes remain
   exact; no timestamp resampling, broad manifest normalization or hidden rewrite.
5. Exercise destination/source/manifest changes and parent symlink replacement;
   refusal precedes the first owner write, even with automatic confirmation.
6. Run relevant import/layer checks and record all concrete assessment entry
   names for WP13's architecture floor; no empty owner list counts as coverage.
7. Hand WP10 the real intent API and global owner contracts, with public startup
   purity explicitly pending WP10 integration and WP13 final acceptance.

**Files**: New `tests/runtime/test_upgrade_preview_bootstrap.py`,
existing owned bootstrap/skills tests and `tests/specify_cli/runtime/**`.

**Validation commands** (future execution; not results):
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -n0 -p no:cacheprovider tests/runtime/test_upgrade_preview_bootstrap.py tests/runtime/test_bootstrap_unit.py tests/runtime/test_agent_skills.py tests/specify_cli/runtime/
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -n0 -p no:cacheprovider tests/runtime/
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 make test-fast
```
Run direct warm-venv Ruff/mypy on changed modules and relevant existing gates.
Record any affected slash-provider tests outside writable ownership as read/run
blast radius; needed test edits go through the parent for ownership resolution.
The suite autouse sync fixture can set sync=1: verify effective isolation and
use the approved WP01/parent policy, never disable shared conftest wholesale.
No whole-repo suite or duplicate full contract/architecture/E2E sweep here.

## Definition of Done

- Exact T011-T017 scope implemented; no WP10 startup or neighboring-owner edits.
- Real existing-entry RED evidence precedes functional fixes; green is recorded.
- Immutable intent uses real definitions without callbacks/default side effects.
- Runtime, global commands and global skills share owner assessment/apply logic.
- Physical effects include directories, stamps, modes and complete changed batches.
- Unknown/custom assets survive; exact ownership/preconditions govern mutation.
- Required source failures cannot become complete empty success.
- Changed-source/parent-link controls stop the batch before any write.
- Nonempty plan/apply equality and repeat no-churn hold with independent evidence.
- Root behavior stays unchanged; no claim that WP03 alone fixes public #3900.
- Focused/subsystem/lint/type/gate results have exact commands, counts and SHAs.
- Independent reviewer receives API handoff, red/green hashes and residual risks.
- Parent retains issue-matrix/final-gate/consent closure; no fabricated verdicts.

Completion evidence is event-sourced, not ticked Markdown checkboxes.
After each verified subtask, use the canonical task-status command in the
runtime-authorized context, substituting each exact ID T011 through T017:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T011 --status done --mission upgrade-preview-mission-health-01M1V6E1
```

Record returned events and verification references; do not hand-edit task state.
These commands are implementation instructions, not authorization for this author
to run them. Current document creation proves no implementation gate passed.

## Risks

- Parse-only Click handling can invoke eager callbacks/defaults: test denial.
- Full-plan option is not yet publicly registered: WP10 owns registration/tests.
- Prefix cleanup can erase custom assets: require exact proof and negative controls.
- Stamps can hide partial/current-but-missing content: verify actual health.
- Prepared data may drift: whole-batch recheck, no silent force or rerender.
- Shared root aliases can duplicate writes: retain owners and WP02 deduplication.
- Existing ensure refactoring can alter startup: positive legacy-call controls.
- Clock/chmod churn can fake idempotence: retain exact bytes and mtimes.
- Root/test metadata prefix ambiguity is documented, not codebase-wide exemption.
- Track friction externally; do not repair #3908 or global config in this WP.

## Reviewer Guidance

Inspect the real callers, not only newly introduced test parameter paths.
Verify absence of writes transitively through source lookup and owner preparation.
Try current-marker/missing-content, unknown prefixed links and partial-render cases.
Remove one supporting effect in an isolated mutation control; equality must fail.
Check whole-agent refresh is represented even when one status initiated repair.
Check prepared application never resamples clock or silently widens agent scope.
Verify warm no-op avoids stamp, chmod, lock and same-byte persistent churn.
Reject source-dependent tests that bypass package/source selection on cold homes.
Require truthful partial I/O outcomes and no global rollback claim.
Check dependency deliveries are consumed without editing their owned files.
Verify WP10's root files are unchanged and integration gaps are clearly handed off.
Approve WP03 for its owner/intent contract only, not aggregate issue acceptance.
