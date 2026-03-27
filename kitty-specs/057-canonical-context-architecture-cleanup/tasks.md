# Work Packages: Canonical Context Architecture Cleanup

**Inputs**: Design documents from `kitty-specs/057-canonical-context-architecture-cleanup/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Required — 90%+ coverage on all new code, mypy --strict, integration tests for CLI commands.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: MissionContext Core (Priority: P0)

**Goal**: Build the foundational context module — dataclasses, store, resolver, and CLI middleware. This is the single dependency for all other moves.
**Independent Test**: `spec-kitty agent context resolve --wp WP01 --feature 057-canonical-context-architecture-cleanup` produces a persisted token, and `spec-kitty agent context show --context <token>` returns the bound JSON.
**Prompt**: `tasks/WP01-mission-context-core.md`
**Requirement Refs**: FR-001, FR-021, NFR-003

### Included Subtasks
- [x] T001 Create `src/specify_cli/context/__init__.py` with public API exports
- [x] T002 Create `src/specify_cli/context/models.py` — MissionContext and ContextToken dataclasses with all identity fields (project_uuid, mission_id, work_package_id, wp_code, feature_slug, target_branch, authoritative_repo, authoritative_ref, owned_files, execution_mode, dependency_mode, completion_commands)
- [x] T003 Create `src/specify_cli/context/store.py` — Read/write context token JSON files to `.kittify/runtime/contexts/<token>.json`
- [x] T004 Create `src/specify_cli/context/resolver.py` — Resolve context from raw args (wp_code, feature_slug) → build MissionContext → persist → return opaque token
- [x] T005 Create `src/specify_cli/context/middleware.py` — CLI middleware that loads context from `--context <token>` or fails fast with actionable error
- [x] T006 [P] Tests for all context module components (`tests/specify_cli/context/`)

### Implementation Notes
- ULID generation for tokens: use `ulid` library or generate from timestamp+random
- Token format: `ctx-` prefix + ULID (e.g., `ctx-01HVXYZ...`)
- Resolver reads mission identity from `meta.json`, WP identity from frontmatter
- Store creates `.kittify/runtime/contexts/` directory on first write
- Middleware is a typer callback that runs before every workflow command

### Parallel Opportunities
- T006 (tests) can proceed in parallel with T002-T005 using TDD approach

### Dependencies
- None (starting package).

### Risks & Mitigations
- ULID collision: Practically impossible but add uniqueness check in store
- Stale context tokens: Add expiry or invalidation when WP reaches terminal lane

---

## Work Package WP02: Context CLI Integration (Priority: P0)

**Goal**: Wire context tokens into CLI commands, add `resolve`/`show` commands, delete `feature_detection.py`, and update all callers.
**Independent Test**: Run `spec-kitty agent context resolve` then pass the token to any workflow command. Verify no heuristic resolution is triggered.
**Prompt**: `tasks/WP02-context-cli-integration.md`
**Requirement Refs**: FR-002, FR-003

### Included Subtasks
- [x] T007 Create `src/specify_cli/cli/commands/context.py` — `spec-kitty agent context resolve` and `spec-kitty agent context show` commands
- [x] T008 Add `--context <token>` parameter to all workflow CLI commands (implement, review, move-task, mark-status, accept, merge, status)
- [x] T009 Delete `src/specify_cli/core/feature_detection.py` (668 lines)
- [x] T010 Update all callers of `detect_feature()` across CLI commands to use context middleware
- [x] T011 [P] Tests for context CLI commands and integration (`tests/specify_cli/cli/commands/test_context.py`)

### Implementation Notes
- T009 is the most impactful deletion — search for all `from specify_cli.core.feature_detection import` and `detect_feature` calls
- T010 requires updating every CLI command that currently calls `detect_feature()` — use grep to find all call sites
- `resolve` command accepts `--wp`, `--feature`, `--agent` and returns token + JSON summary
- `show` command accepts `--context <token>` and pretty-prints the bound context

### Parallel Opportunities
- T007 (CLI commands) and T008 (parameter addition) can proceed in parallel

### Dependencies
- Depends on WP01 (needs context module).

### Risks & Mitigations
- Missing callers: grep exhaustively for `feature_detection`, `detect_feature`, `FeatureContext`
- Breaking existing tests: Many tests use `detect_feature()` — update them to use context tokens or mock the middleware

---

## Work Package WP03: WP Ownership Manifest (Priority: P0)

**Goal**: Build the ownership module — execution mode enum, ownership manifest dataclass, validation, inference, and workspace strategy routing.
**Independent Test**: At task finalization, each WP has `execution_mode`, `owned_files`, and `authoritative_surface` in frontmatter. Overlapping owned_files across WPs is rejected.
**Prompt**: `tasks/WP03-ownership-manifest.md`
**Requirement Refs**: FR-004, FR-005

### Included Subtasks
- [x] T012 Create `src/specify_cli/ownership/__init__.py` with public API exports
- [x] T013 Create `src/specify_cli/ownership/models.py` — `ExecutionMode` enum (`code_change`, `planning_artifact`), `OwnershipManifest` dataclass
- [x] T014 Create `src/specify_cli/ownership/validation.py` — Overlap detection across WPs, completeness checks, authoritative_surface prefix validation
- [x] T015 Create `src/specify_cli/ownership/inference.py` — Infer execution_mode and owned_files from WP description, file paths, and task content
- [x] T016 Update task finalization (`finalize-tasks`) to require ownership manifest fields in frontmatter
- [x] T017 [P] Tests for ownership module (`tests/specify_cli/ownership/`)

### Implementation Notes
- `planning_artifact` WPs: owned_files should be `kitty-specs/` paths or documentation paths
- `code_change` WPs: owned_files should be source code paths
- Inference heuristic: if WP mentions kitty-specs/, spec.md, plan.md, tasks.md → planning_artifact
- Validation runs at finalization time, not at WP creation time

### Parallel Opportunities
- T017 (tests) can proceed alongside implementation

### Dependencies
- Depends on WP01 (needs identity model for work_package_id, mission_id fields).

### Risks & Mitigations
- Inference accuracy: Allow manual override of inferred values in frontmatter
- Glob pattern complexity: Use `fnmatch` or `pathspec` for owned_files matching

---

## Work Package WP04: Workspace Strategy Rewrite (Priority: P1)

**Goal**: Update worktree creation to route by execution_mode. Planning-artifact WPs work in-repo without sparse checkout. Delete sparse checkout policy code.
**Independent Test**: `spec-kitty implement WP01` with `execution_mode: planning_artifact` works in-repo. `execution_mode: code_change` creates a standard worktree. No sparse checkout is applied in either case.
**Prompt**: `tasks/WP04-workspace-strategy-rewrite.md`
**Requirement Refs**: FR-006, FR-007, NFR-006

### Included Subtasks
- [x] T018 Update `src/specify_cli/core/worktree.py` — Route workspace creation by execution_mode from ownership manifest
- [x] T019 Implement planning-artifact workspace strategy: in-repo work or dedicated planning worktree with full file access (no sparse checkout)
- [x] T020 Delete sparse checkout policy code from `src/specify_cli/core/vcs/git.py` (`sparse_exclude` parameter and all callers)
- [x] T021 Delete kitty-specs/ special-case handling in worktree creation code
- [x] T022 [P] Tests for workspace strategy changes (`tests/specify_cli/core/test_worktree.py`)

### Implementation Notes
- `workspace_strategy.py` from ownership module provides the routing logic
- For `planning_artifact`: either work directly in-repo (no worktree) or create a normal worktree without sparse checkout
- For `code_change`: create standard worktree as today, but without sparse checkout
- Sparse checkout is entirely removed, not made optional

### Parallel Opportunities
- T022 (tests) can proceed alongside T018-T021

### Dependencies
- Depends on WP03 (needs ownership models for execution_mode routing).

### Risks & Mitigations
- Planning-artifact WPs editing shared files: ownership validation prevents overlaps
- Worktree creation regression: keep worktree creation for code_change WPs unchanged except for sparse checkout removal

---

## Work Package WP05: Canonical State — Event Log Authority (Priority: P1)

**Goal**: Make the event log the sole authority for mutable state. Remove dual-write, phase system, legacy bridge. Strip mutable frontmatter fields from the entire codebase.
**Independent Test**: `spec-kitty status` displays board state computed entirely from `status.events.jsonl`. No frontmatter `lane` fields are read. `status/legacy_bridge.py` and `status/phase.py` no longer exist.
**Prompt**: `tasks/WP05-canonical-state-event-log.md`
**Requirement Refs**: FR-008, FR-009, C-004, NFR-006

### Included Subtasks
- [ ] T023 Simplify `src/specify_cli/status/emit.py` — Remove dual-write path, phase checks, frontmatter update calls. Emit writes only to event log.
- [ ] T024 Create `src/specify_cli/status/views.py` — Derived view generation: produce status.json, board-summary.json from event log (replaces legacy_bridge output-only functionality)
- [ ] T025 Delete `src/specify_cli/status/legacy_bridge.py` (~300 lines)
- [ ] T026 Delete `src/specify_cli/status/phase.py` (~150 lines), `status/reconcile.py` (~200 lines), `status/migrate.py` (~150 lines)
- [ ] T027 Strip ALL frontmatter lane/review_status/reviewed_by/progress reads and writes from entire codebase (grep and remove)
- [ ] T028 [P] Tests for simplified status module, verify no dual-write paths remain

### Implementation Notes
- T027 is a codebase-wide sweep — grep for `lane`, `review_status`, `reviewed_by` in frontmatter read/write contexts
- `views.py` takes a StatusSnapshot (from reduce()) and writes to `.kittify/derived/<slug>/`
- The `emit()` function becomes simple: validate transition → append event → done
- Remove `resolve_phase()` calls everywhere — there is only one phase now
- Remove `update_frontmatter_views()` and all callers

### Parallel Opportunities
- T025-T026 (deletions) can proceed in parallel with T023-T024 (rewrites)

### Dependencies
- Depends on WP02 (context middleware replaces feature detection in status paths).

### Risks & Mitigations
- Missing frontmatter references: exhaustive grep before marking complete
- Status display regression: ensure `spec-kitty status` produces identical visual output from event log

---

## Work Package WP06: Weighted Progress and Materialization (Priority: P1)

**Goal**: Build weighted progress computation, materialization command, lazy regeneration, and define the tracked/derived boundary on disk.
**Independent Test**: `spec-kitty materialize` regenerates `.kittify/derived/<slug>/status.json` and `progress.json` from event log. CLI commands auto-regenerate when derived files are stale.
**Prompt**: `tasks/WP06-progress-and-materialization.md`
**Requirement Refs**: FR-010, FR-011, FR-022, FR-023

### Included Subtasks
- [ ] T029 Create `src/specify_cli/status/progress.py` — Weighted progress computation: configurable weights per WP, compute from snapshot lane counts, return structured JSON
- [ ] T030 Create `src/specify_cli/cli/commands/materialize.py` — `spec-kitty materialize` command for CI/debugging/external consumers
- [ ] T031 Add lazy regeneration: `materialize_if_stale(feature_dir)` checks event log mtime vs derived file mtime, regenerates if needed
- [ ] T032 Create `.kittify/derived/` directory structure; update `.gitignore` for `.kittify/derived/` and `.kittify/runtime/`
- [ ] T033 [P] Tests for progress computation, materialization, lazy regeneration

### Implementation Notes
- Lane-weighted model, NOT done-only: each lane has a fractional weight (planned=0.0, claimed=0.05, in_progress=0.3, for_review=0.6, approved=0.8, done=1.0, blocked=0.0, canceled=0.0)
- Per-WP weights configurable (default: equal, 1.0 each)
- Progress formula: `sum(wp_weight * lane_weight[wp.lane] for each WP) / sum(wp_weight for each WP) * 100`
- A mission with 3 WPs all in `in_progress` shows ~30%, not 0%
- `materialize` outputs: `status.json`, `progress.json`, `board-summary.json`
- Lazy check: `os.path.getmtime(event_log) > os.path.getmtime(derived_file)`
- Machine-readable JSON schema should be documented for future SaaS consumption

### Parallel Opportunities
- T029 (progress) and T030 (CLI command) can proceed in parallel

### Dependencies
- Depends on WP05 (needs simplified status module with event-log-only authority).

### Risks & Mitigations
- Stale derived files on CI: `spec-kitty materialize` handles this explicitly
- Performance: reduce() is O(n) on events — acceptable for typical projects (<10K events)

---

## Work Package WP07: Merge Engine v2 — Workspace and State (Priority: P2)

**Goal**: Build the dedicated merge workspace lifecycle and rewrite merge state persistence. Delete old merge executor.
**Independent Test**: `spec-kitty merge --feature <slug>` creates a workspace at `.kittify/runtime/merge/<mid>/workspace/` and persists state to `.kittify/runtime/merge/<mid>/state.json`. Main repo checkout is untouched.
**Prompt**: `tasks/WP07-merge-workspace-and-state.md`
**Requirement Refs**: FR-012, FR-013

### Included Subtasks
- [ ] T034 Create `src/specify_cli/merge/workspace.py` — Dedicated merge worktree lifecycle at `.kittify/runtime/merge/<mission_id>/workspace/`
- [ ] T035 Rewrite `src/specify_cli/merge/state.py` — MergeState with per-mission scoping, new location, lock file support
- [ ] T036 Simplify `src/specify_cli/merge/preflight.py` — Use MissionContext instead of heuristic feature detection
- [ ] T037 Delete `src/specify_cli/merge/executor.py` (~450 lines), `merge/forecast.py` (~200 lines), `merge/status_resolver.py` (~150 lines)
- [ ] T038 [P] Tests for merge workspace lifecycle and state persistence

### Implementation Notes
- Merge workspace uses `git worktree add` under `.kittify/runtime/merge/<mid>/workspace/`
- State includes: mission_id, wp_order, completed_wps, current_wp, strategy, workspace_path
- Lock file at `.kittify/runtime/merge/<mid>/lock` prevents concurrent merges
- Old `.kittify/merge-state.json` treated as legacy migration input only
- Cleanup: `git worktree remove` when merge completes or aborts

### Parallel Opportunities
- T034 (workspace) and T035 (state) can proceed in parallel

### Dependencies
- Depends on WP02 (context tokens for merge), WP05 (canonical state for event log reads).

### Risks & Mitigations
- Orphan worktrees: cleanup on abort/failure, validate on start
- Git worktree limit: not practical concern, merge creates one at a time

---

## Work Package WP08: Merge Engine v2 — Orchestration (Priority: P2)

**Goal**: Build the merge orchestrator with resume, conflict resolution, and post-merge reconciliation.
**Independent Test**: Start a merge for 3 WPs, interrupt after WP01, resume, verify WP02/WP03 merge without reprocessing WP01. Spec-kitty-owned file conflicts auto-resolve.
**Prompt**: `tasks/WP08-merge-orchestration.md`
**Requirement Refs**: FR-013, FR-014, FR-015, NFR-005

### Included Subtasks
- [ ] T039 Create `src/specify_cli/merge/engine.py` — Merge orchestrator: load context, compute merge order, iterate WPs, persist state per step, support --resume/--abort/--dry-run
- [ ] T040 Create `src/specify_cli/merge/conflict_resolver.py` — Managed resolution for spec-kitty-owned files (status.events.jsonl: append-merge, derived files: regenerate, WP frontmatter: take-theirs for static metadata)
- [ ] T041 Create `src/specify_cli/merge/reconciliation.py` — Post-merge: emit `done` events for merged WPs, verify merged ancestry, update event log
- [ ] T042 Wire merge CLI commands to new engine: `spec-kitty merge --feature`, `--resume`, `--abort`, `--dry-run`, `--context`
- [ ] T043 [P] Tests for merge orchestration, resume flow, conflict resolution, reconciliation

### Implementation Notes
- Engine flow: preflight → create workspace → checkout target → for each WP: merge branch → auto-resolve owned conflicts → update state → push → reconcile
- Conflict resolver strategies: event log (append both, dedup by event_id), frontmatter (take-theirs), derived (regenerate)
- Resume: load state → skip completed_wps → continue from current_wp
- Dry-run: predict conflicts without executing

### Parallel Opportunities
- T040 (conflict resolver) can proceed in parallel with T039 (engine)

### Dependencies
- Depends on WP07 (needs merge workspace and state).

### Risks & Mitigations
- Unresolvable conflicts on human-authored files: pause, persist state, report to user
- Rebase strategy: more complex than merge — defer rebase support to future work

---

## Work Package WP09: Thin Agent Shims (Priority: P2)

**Goal**: Build the shim module — models, generator, registry, and CLI entrypoints for `spec-kitty agent shim <command>`.
**Independent Test**: `spec-kitty agent shim implement --agent claude --raw-args "WP03"` resolves context, persists token, and dispatches to the implement workflow.
**Prompt**: `tasks/WP09-thin-agent-shims.md`
**Requirement Refs**: FR-016, FR-017, C-007

### Included Subtasks
- [x] T044 Create `src/specify_cli/shims/__init__.py` with public API exports
- [x] T045 Create `src/specify_cli/shims/models.py` — ShimTemplate and AgentShimConfig dataclasses
- [x] T046 Create `src/specify_cli/shims/generator.py` — Generate thin shim markdown files for all configured agents (3-line format: invariant + prohibition + CLI call)
- [x] T047 Create `src/specify_cli/shims/registry.py` — Skill allowlist: consumer-facing vs internal-only skills
- [x] T048 Create `src/specify_cli/shims/entrypoints.py` and `src/specify_cli/cli/commands/shim.py` — `spec-kitty agent shim <command>` handlers that resolve-if-missing → persist → execute
- [x] T049 [P] Tests for shim generation, registry, entrypoints

### Implementation Notes
- Shim template (generated markdown):
  ```
  Run this exact command and treat its output as authoritative.
  Do not rediscover context from branches, files, or prompt contents.

  `spec-kitty agent shim <command> --agent <AGENT_NAME> --raw-args "$ARGUMENTS"`
  ```
- Generator uses `get_agent_dirs_for_project()` to find configured agents
- Registry defines: specify, plan, tasks, implement, review, merge, accept, status, dashboard, checklist as consumer-facing
- Entrypoints: resolve context internally → dispatch to existing workflow handlers

### Parallel Opportunities
- T045-T047 (models, generator, registry) can all proceed in parallel

### Dependencies
- Depends on WP01 (needs context token model for shim entrypoints).

### Risks & Mitigations
- Agent-specific quirks: shim format may need minor variations per agent (e.g., Windsurf uses workflows/ not commands/)
- Skill registry completeness: start with current skill set, add missing skills in review

---

## Work Package WP10: Delete Command Templates and Agent Context (Priority: P2)

**Goal**: Delete all full command templates across all missions. Delete agent context tech-stack parsing. Delete migration code that copies markdown templates.
**Independent Test**: No `command-templates/*.md` files exist in any mission directory. `agent_context.py` is deleted. Shim generation from WP09 is the only source of agent command files.
**Prompt**: `tasks/WP10-delete-templates-and-agent-context.md`
**Requirement Refs**: NFR-006

### Included Subtasks
- [ ] T050 Delete all `src/specify_cli/missions/*/command-templates/*.md` files (~56 files across 4 missions)
- [ ] T051 Delete `src/specify_cli/core/agent_context.py` (~300 lines — tech-stack parsing from plan.md)
- [ ] T052 Delete/simplify migration code that copies or patches markdown command files into agent directories
- [ ] T053 [P] Tests verifying templates are gone, agent_context references are removed, shim-only agent surface

### Implementation Notes
- Search for all imports of `agent_context` and update callers
- Review each migration in `src/specify_cli/upgrade/migrations/` for template-copying logic
- Some migrations may need to be preserved for upgrading from pre-3.0 to 3.0 (handled by the one-shot migration instead)
- Verify `.kittify/missions/` template copies are also cleaned up

### Parallel Opportunities
- T050 and T051 can proceed in parallel (independent deletions)

### Dependencies
- Depends on WP09 (shim system must exist before deleting old templates).

### Risks & Mitigations
- Breaking existing migrations: migrations from pre-3.0 may reference command-templates — keep those as migration-input paths only in the one-shot migration
- Missing imports: grep for `agent_context`, `update_agent_context`, `command-templates`

---

## Work Package WP11: Schema Version and Upgrade Gate (Priority: P1)

**Goal**: Build schema version detection, upgrade gate, and rewrite the version detector and upgrade runner to use schema version instead of heuristics.
**Independent Test**: On an unmigrated project, any `spec-kitty` command prints "Project requires migration" and exits non-zero. On a migrated project with matching schema version, commands proceed normally.
**Prompt**: `tasks/WP11-schema-version-and-gate.md`
**Requirement Refs**: FR-019, FR-020, C-003, C-005

### Included Subtasks
- [ ] T054 Create `src/specify_cli/migration/schema_version.py` — Schema version detection from `metadata.yaml`, compatibility check (project vs CLI)
- [ ] T055 Create `src/specify_cli/migration/gate.py` — Upgrade gate: check_schema_version() called before every CLI command, refuse unmigrated, refuse newer-than-CLI
- [ ] T056 Rewrite `src/specify_cli/upgrade/detector.py` — Replace ~15 heuristic checks with single schema_version integer check
- [ ] T057 Simplify `src/specify_cli/upgrade/runner.py` — Schema-version-based migration selection instead of heuristic-based
- [ ] T058 [P] Tests for schema version gate, both directions (too old, too new)

### Implementation Notes
- Schema version: integer in `metadata.yaml` under `spec_kitty.schema_version`
- Required schema version: defined as constant in CLI package (e.g., `REQUIRED_SCHEMA_VERSION = 3`)
- Gate runs as typer callback before any command dispatch
- If `schema_version` missing → treat as legacy (schema_version = 0) → refuse
- Capabilities list is informational, not used for gating

### Parallel Opportunities
- T054 (schema_version.py) and T055 (gate.py) can proceed in parallel

### Dependencies
- Depends on WP05 (canonical state model informs what schema_version=3 means).

### Risks & Mitigations
- Gate too aggressive: include bypass flag `--skip-version-check` for emergencies (not recommended)
- Version deadlock: schema version gate is bidirectional — CLI too old also fails

---

## Work Package WP12: One-Shot Migration — Identity and Ownership Backfill (Priority: P1)

**Goal**: Build migration steps for identity backfill (project_uuid, mission_id, work_package_id), ownership inference, frontmatter stripping, and shim rewriting.
**Independent Test**: Run identity backfill on a legacy project. Every feature has mission_id in meta.json, every WP has work_package_id and wp_code in frontmatter, mutable fields are stripped, agent command files are thin shims.
**Prompt**: `tasks/WP12-migration-identity-backfill.md`
**Requirement Refs**: FR-018, FR-021, C-006

### Included Subtasks
- [ ] T059 Create `src/specify_cli/migration/__init__.py` with public API exports
- [ ] T060 Create `src/specify_cli/migration/backfill_identity.py` — Assign project_uuid to metadata.yaml, mission_id to each feature's meta.json, work_package_id + wp_code to each WP frontmatter
- [ ] T061 Create `src/specify_cli/migration/backfill_ownership.py` — Infer execution_mode and owned_files from WP content, file paths, git branch diffs
- [ ] T062 Create `src/specify_cli/migration/strip_frontmatter.py` — Remove mutable fields (lane, review_status, reviewed_by, progress) from all WP frontmatter and tasks.md
- [ ] T063 Create `src/specify_cli/migration/rewrite_shims.py` — Replace agent command files with thin shims using shim generator
- [ ] T064 [P] Tests for identity backfill, ownership inference, frontmatter stripping, shim rewriting

### Implementation Notes
- project_uuid: generate ULID, write to metadata.yaml `spec_kitty.project_uuid`
- mission_id: generate ULID per feature, write to meta.json
- work_package_id: generate ULID per WP, write to frontmatter
- wp_code: extract from existing WP ID pattern (e.g., "WP01" → wp_code: "WP01")
- Ownership inference: check WP file paths and descriptions for kitty-specs/ → planning_artifact
- Strip frontmatter: read YAML, remove keys, write back preserving non-YAML body

### Parallel Opportunities
- T060 (identity) and T061 (ownership) can proceed in parallel
- T062 (frontmatter) and T063 (shims) can proceed in parallel

### Dependencies
- Depends on WP03 (ownership models), WP09 (shim generator), WP11 (schema version model).

### Risks & Mitigations
- Frontmatter parsing: use ruamel.yaml for round-trip preservation of comments and formatting
- Mid-flight features: preserve current status in event log before stripping frontmatter

---

## Work Package WP13: One-Shot Migration — State Rebuild and Runner (Priority: P1)

**Goal**: Build event log state rebuild from legacy artifacts and the atomic migration runner with rollback.
**Independent Test**: Run full migration on a legacy project with 10+ features in mixed states. Verify event log faithfully represents pre-migration state. Verify rollback on simulated failure.
**Prompt**: `tasks/WP13-migration-state-rebuild-and-runner.md`
**Requirement Refs**: FR-018, NFR-001, NFR-002, C-006

### Included Subtasks
- [ ] T065 Create `src/specify_cli/migration/rebuild_state.py` — Rebuild canonical event log from legacy artifacts (precedence: existing event log > status.json > frontmatter)
- [ ] T066 Create `src/specify_cli/migration/runner.py` — Orchestrate migration steps atomically: backup → identity → ownership → state rebuild → strip frontmatter → rewrite shims → update schema version → gitignore → commit
- [ ] T067 Add `src/specify_cli/upgrade/migrations/m_3_0_0_canonical_context.py` — Entry point in existing migration registry
- [ ] T068 Update `.gitignore` comprehensively for new filesystem layout (`.kittify/derived/`, `.kittify/runtime/`, remove obsolete entries)
- [ ] T069 [P] Tests for state rebuild (critical: mid-flight features, conflicting sources), atomic runner, rollback

### Implementation Notes
- State rebuild precedence: if event log exists and has events, keep as-is. If no event log, read status.json. If no status.json, read frontmatter `lane` fields. Generate synthetic events for each WP's current state.
- Atomic runner: backup `.kittify/` and `kitty-specs/` before starting. On any failure, restore from backup.
- Migration runner produces summary: features migrated, WPs backfilled, events generated, warnings for conflicts
- Performance target: < 30 seconds for 20 features / 200 WPs

### Parallel Opportunities
- T065 (state rebuild) and T068 (gitignore) can proceed in parallel

### Dependencies
- Depends on WP09 (shim generator used by rewrite_shims), WP11 (schema version written by runner), WP12 (identity/ownership backfill steps).

### Risks & Mitigations
- Data loss during migration: atomic rollback is mandatory
- Conflicting legacy state: log warnings, use deterministic precedence, never silently drop state
- Performance: batch file operations, minimize git calls

---

## Work Package WP14: Integration Tests and Final Cleanup (Priority: P2)

**Goal**: End-to-end integration tests for the full new architecture. Final dead code sweep. Validate test coverage and type checking.
**Independent Test**: All integration tests pass. mypy --strict passes. pytest coverage > 90% on new code. No stale imports or dead references remain.
**Prompt**: `tasks/WP14-integration-tests-and-cleanup.md`
**Requirement Refs**: NFR-004, NFR-006, C-001

### Included Subtasks
- [ ] T070 End-to-end integration test: full WP lifecycle with context tokens (resolve → implement → review → merge) — no heuristic resolution triggered
- [ ] T071 End-to-end integration test: migration of legacy project with mid-flight features in mixed states, verify zero status information loss
- [ ] T072 End-to-end integration test: merge engine v2 with resume after interruption and spec-kitty-owned file conflict resolution
- [ ] T073 Sweep for remaining dead code: stale imports, unused test fixtures, orphan references to deleted modules
- [ ] T074 Final validation: `mypy --strict` on all new modules, `pytest` with coverage report, verify 90%+ on new code

### Implementation Notes
- Integration tests should use real git repos (not mocks) per constitution
- Create fixture: legacy project with 5+ features in various states for migration test
- Context token lifecycle test: verify token creation, usage across commands, expiry/invalidation
- Dead code sweep: grep for all deleted module names, deleted function names, deleted class names

### Parallel Opportunities
- T070, T071, T072 (integration tests) can all proceed in parallel

### Dependencies
- Depends on WP08 (merge engine), WP10 (template deletion), WP13 (migration runner) — all moves must be complete.

### Risks & Mitigations
- Test environment complexity: create helper fixtures for legacy project scaffolding
- Flaky integration tests: use deterministic timestamps and ULIDs in test fixtures

---

## Dependency & Execution Summary

```
Wave 1: WP01 (MissionContext Core)
         │
Wave 2: WP02 ──────── WP03 ──────── WP09
        (Context CLI)  (Ownership)   (Thin Shims)
         │              │              │
Wave 3: WP05 ──────── WP04 ──────── WP10
        (Canon State)  (Workspace)   (Delete Templates)
         │
Wave 4: WP06 ──────── WP07 ──────── WP11
        (Progress)     (Merge WS)    (Schema Gate)
                        │              │
Wave 5:               WP08 ──────── WP12
                      (Merge Orch)   (Migration Identity)
                                      │
Wave 6:                      WP09 + WP11 + WP12 ──▶ WP13
                                    (Migration Runner — needs shims, schema, identity)
                                      │
Wave 7:                             WP14
                                    (Integration Tests)
```

- **Sequence**: WP01 → (WP02 | WP03 | WP09) → (WP04 | WP05 | WP10) → (WP06 | WP07 | WP11) → (WP08 | WP12) → WP13 → WP14
- **Parallelization**: Up to 3 WPs can run in parallel in waves 2-5
- **MVP Scope**: WP01-WP06 deliver the core architectural changes (context tokens + ownership + canonical state). The remaining WPs (merge, shims, migration) complete the full vision.
- **Critical path**: WP01 → WP02 → WP05 → WP06 (canonical state) or WP01 → WP02 → WP05 → WP07 → WP08 (merge engine)

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP02 |
| FR-003 | WP02 |
| FR-004 | WP03 |
| FR-005 | WP03 |
| FR-006 | WP04 |
| FR-007 | WP04 |
| FR-008 | WP05 |
| FR-009 | WP05 |
| FR-010 | WP06 |
| FR-011 | WP06 |
| FR-012 | WP07 |
| FR-013 | WP07, WP08 |
| FR-014 | WP08 |
| FR-015 | WP08 |
| FR-016 | WP09 |
| FR-017 | WP09 |
| FR-018 | WP12, WP13 |
| FR-019 | WP11 |
| FR-020 | WP11 |
| FR-021 | WP01, WP12 |
| FR-022 | WP06 |
| FR-023 | WP06 |
| NFR-001 | WP13 |
| NFR-002 | WP13 |
| NFR-003 | WP01 |
| NFR-004 | WP14 |
| NFR-005 | WP08 |
| NFR-006 | WP04, WP05, WP10 |
| C-001 | WP14 |
| C-003 | WP11 |
| C-004 | WP05 |
| C-005 | WP11 |
| C-006 | WP12, WP13 |
| C-007 | WP09 |
| C-008 | All |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Parallel? |
|------------|---------|--------------|-----------|
| T001 | context/__init__.py | WP01 | No |
| T002 | context/models.py — MissionContext + ContextToken | WP01 | No |
| T003 | context/store.py — Token persistence | WP01 | No |
| T004 | context/resolver.py — Raw args → token | WP01 | No |
| T005 | context/middleware.py — CLI fail-fast | WP01 | No |
| T006 | Tests for context module | WP01 | Yes |
| T007 | cli/commands/context.py — resolve + show | WP02 | No |
| T008 | Add --context param to workflow commands | WP02 | Yes |
| T009 | Delete feature_detection.py (668 lines) | WP02 | No |
| T010 | Update all detect_feature() callers | WP02 | No |
| T011 | Tests for context CLI integration | WP02 | Yes |
| T012 | ownership/__init__.py | WP03 | No |
| T013 | ownership/models.py — ExecutionMode, OwnershipManifest | WP03 | No |
| T014 | ownership/validation.py — Overlap detection | WP03 | No |
| T015 | ownership/inference.py — Infer mode/files | WP03 | No |
| T016 | Update task finalization for ownership | WP03 | No |
| T017 | Tests for ownership module | WP03 | Yes |
| T018 | Update worktree.py for execution_mode routing | WP04 | No |
| T019 | Planning-artifact workspace strategy | WP04 | No |
| T020 | Delete sparse checkout from vcs/git.py | WP04 | No |
| T021 | Delete kitty-specs special cases in worktree | WP04 | No |
| T022 | Tests for workspace strategy | WP04 | Yes |
| T023 | Simplify status/emit.py — event-log-only | WP05 | No |
| T024 | Create status/views.py — derived views | WP05 | No |
| T025 | Delete status/legacy_bridge.py | WP05 | Yes |
| T026 | Delete phase.py, reconcile.py, migrate.py | WP05 | Yes |
| T027 | Strip mutable frontmatter from entire codebase | WP05 | No |
| T028 | Tests for simplified status | WP05 | Yes |
| T029 | Create status/progress.py — weighted progress | WP06 | No |
| T030 | Create cli/commands/materialize.py | WP06 | Yes |
| T031 | Add lazy regeneration (materialize_if_stale) | WP06 | No |
| T032 | Create .kittify/derived/ structure + .gitignore | WP06 | Yes |
| T033 | Tests for progress + materialization | WP06 | Yes |
| T034 | Create merge/workspace.py | WP07 | No |
| T035 | Rewrite merge/state.py for new location | WP07 | Yes |
| T036 | Simplify merge/preflight.py | WP07 | No |
| T037 | Delete executor.py, forecast.py, status_resolver.py | WP07 | Yes |
| T038 | Tests for merge workspace + state | WP07 | Yes |
| T039 | Create merge/engine.py — orchestrator | WP08 | No |
| T040 | Create merge/conflict_resolver.py | WP08 | Yes |
| T041 | Create merge/reconciliation.py | WP08 | Yes |
| T042 | Wire merge CLI to new engine | WP08 | No |
| T043 | Tests for merge orchestration | WP08 | Yes |
| T044 | shims/__init__.py | WP09 | No |
| T045 | shims/models.py | WP09 | Yes |
| T046 | shims/generator.py | WP09 | Yes |
| T047 | shims/registry.py | WP09 | Yes |
| T048 | shims/entrypoints.py + cli/commands/shim.py | WP09 | No |
| T049 | Tests for shims | WP09 | Yes |
| T050 | Delete all command-templates/*.md | WP10 | Yes |
| T051 | Delete core/agent_context.py | WP10 | Yes |
| T052 | Delete template-copying migration code | WP10 | No |
| T053 | Tests verifying deletions | WP10 | Yes |
| T054 | Create migration/schema_version.py | WP11 | Yes |
| T055 | Create migration/gate.py | WP11 | Yes |
| T056 | Rewrite upgrade/detector.py | WP11 | No |
| T057 | Simplify upgrade/runner.py | WP11 | No |
| T058 | Tests for schema version gate | WP11 | Yes |
| T059 | migration/__init__.py | WP12 | No |
| T060 | migration/backfill_identity.py | WP12 | Yes |
| T061 | migration/backfill_ownership.py | WP12 | Yes |
| T062 | migration/strip_frontmatter.py | WP12 | Yes |
| T063 | migration/rewrite_shims.py | WP12 | Yes |
| T064 | Tests for migration steps | WP12 | Yes |
| T065 | migration/rebuild_state.py | WP13 | No |
| T066 | migration/runner.py — atomic orchestrator | WP13 | No |
| T067 | m_3_0_0_canonical_context.py entry | WP13 | No |
| T068 | Update .gitignore comprehensively | WP13 | Yes |
| T069 | Tests for state rebuild + atomic migration | WP13 | Yes |
| T070 | E2E test: full WP lifecycle with context tokens | WP14 | Yes |
| T071 | E2E test: legacy project migration | WP14 | Yes |
| T072 | E2E test: merge engine v2 with resume | WP14 | Yes |
| T073 | Dead code sweep | WP14 | No |
| T074 | Final validation: mypy --strict + coverage | WP14 | No |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: approved
- WP02: approved
- WP03: approved
- WP04: approved
- WP09: approved
<!-- status-model:end -->
