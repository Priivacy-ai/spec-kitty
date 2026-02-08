# Work Packages: Feature Status State Model Remediation

**Inputs**: Design documents from `kitty-specs/034-feature-status-state-model-remediation/`
**Prerequisites**: plan.md (architecture), spec.md (user stories), data-model.md (entities), contracts/ (schemas), research.md (decisions)

**Tests**: Explicitly required per user requirements — unit tests for transitions/reducer, integration tests for dual-write/read-cutover, cross-branch parity tests.

**Organization**: 92 subtasks (`T001`–`T092`) roll up into 17 work packages (`WP01`–`WP17`). Each WP is independently deliverable (3-7 subtasks, 250-500 line prompts).

---

## Work Package WP01: Status Models & Transition Matrix (Priority: P0)

**Goal**: Create the foundational data types (Lane enum, StatusEvent, DoneEvidence, StatusSnapshot) and the strict 7-lane transition matrix with guard conditions and alias resolution.
**Independent Test**: All model constructors validate correctly; every legal/illegal transition pair returns correct verdict.
**Prompt**: `tasks/WP01-status-models-and-transition-matrix.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T001 Create `src/specify_cli/status/__init__.py` with public API exports
- [x] T002 Create `src/specify_cli/status/models.py` — Lane enum, StatusEvent dataclass, DoneEvidence, ReviewApproval, RepoEvidence, VerificationResult, StatusSnapshot
- [x] T003 Create `src/specify_cli/status/transitions.py` — CANONICAL_LANES, LANE_ALIASES, ALLOWED_TRANSITIONS set, guard condition functions
- [x] T004 [P] Unit tests for models — schema validation, serialization, required field enforcement
- [x] T005 [P] Unit tests for transitions — all legal/illegal pairs, alias resolution, guard conditions, force override behavior

### Implementation Notes
- Lane enum should use `StrEnum` for JSON serialization compatibility
- StatusEvent uses ULID for event_id (import pattern from `sync/emitter.py`)
- Guard conditions are validator functions returning `(ok: bool, error: str | None)`
- Transition validation must accept `doing` alias and resolve to `in_progress` before checking matrix

### Parallel Opportunities
- T004 and T005 can be written in parallel (different test files)

### Dependencies
- None (starting package)

### Risks & Mitigations
- Risk: `StrEnum` requires Python 3.11+ → already enforced by constitution
- Risk: ULID import path differs between `ulid-py` and `python-ulid` → use same pattern as `sync/emitter.py`

---

## Work Package WP02: Event Store (JSONL I/O) (Priority: P0)

**Goal**: Create the append-only JSONL event store with atomic operations, corruption detection, and event reading.
**Independent Test**: Append events, read them back, verify ordering. Corrupt a line and verify detection.
**Prompt**: `tasks/WP02-event-store-jsonl-io.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T006 Create `src/specify_cli/status/store.py` — `append_event()`, `read_events()`, `read_events_raw()` functions
- [ ] T007 JSONL serialization with deterministic key ordering; deserialization with per-line validation
- [ ] T008 Corruption detection — invalid JSON lines reported with line number, fail-fast (no silent skip)
- [ ] T009 File creation on first event (idempotent); directory creation if missing
- [ ] T010 [P] Unit tests for store — append, read, corruption, atomicity, empty file handling

### Implementation Notes
- Use `open(path, "a")` for single-writer append; `json.dumps(event, sort_keys=True)` per line
- For reading: iterate lines, `json.loads()` each, collect into list
- File path: `kitty-specs/<feature>/status.events.jsonl`
- Must handle the case where the file doesn't exist yet (first event creates it)

### Parallel Opportunities
- T010 can start as soon as the store interface is defined

### Dependencies
- Depends on WP01 (uses StatusEvent model for serialization/deserialization)

### Risks & Mitigations
- Risk: Concurrent writers (multiple agents) → resolved at git merge time; ULID deduplication handles overlaps
- Risk: Large files → read_events returns generator for lazy evaluation

---

## Work Package WP03: Deterministic Reducer (Priority: P0)

**Goal**: Create the reducer that materializes `status.json` from the canonical event log — deduplication, deterministic sorting, rollback-aware state computation, byte-identical output.
**Independent Test**: Same event log always produces identical `status.json`. Rollback events override concurrent forward events.
**Prompt**: `tasks/WP03-deterministic-reducer.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T011 Create `src/specify_cli/status/reducer.py` — `reduce()` function implementing dedupe/sort/reduce algorithm
- [ ] T012 Rollback-aware precedence logic — reviewer rollback (`for_review → in_progress` with `review_ref`) beats concurrent forward progression
- [ ] T013 Byte-identical output serialization — `json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"`
- [ ] T014 `materialize()` function — read events from store, reduce, write status.json with atomic write-then-rename
- [ ] T015 [P] Unit tests for reducer determinism/idempotency — same input → same bytes
- [ ] T016 [P] Unit tests for rollback-aware conflict resolution — concurrent diverging events

### Implementation Notes
- Sorting key: `(event.at, event.event_id)` — both fields sort lexicographically
- Deduplication: first occurrence by event_id wins
- Rollback detection: event has `review_ref` set AND transition is `for_review → in_progress`
- Concurrency detection: two events from same `from_lane` for same WP
- Atomic write: write to temp file, `os.replace()` to target

### Parallel Opportunities
- T015 and T016 can be written in parallel (different test concerns)

### Dependencies
- Depends on WP01 (models), WP02 (store read)

### Risks & Mitigations
- Risk: Non-deterministic JSON serialization → enforce `sort_keys=True` and deterministic indent
- Risk: Floating-point timestamps → use ISO 8601 strings, not floats

---

## Work Package WP04: Phase Configuration (Priority: P0)

**Goal**: Create the phase resolution system — three-tier precedence (meta.json > config.yaml > default), source tracking, and 0.1x cap enforcement.
**Independent Test**: Phase resolution returns correct value and source for each precedence level.
**Prompt**: `tasks/WP04-phase-configuration.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T017 Create `src/specify_cli/status/phase.py` — `resolve_phase()` returning `(phase: int, source: str)`
- [ ] T018 [P] Add `status.phase` key to `.kittify/config.yaml` schema (config loading)
- [ ] T019 [P] Add `status_phase` field to `meta.json` loading in feature detection
- [ ] T020 0.1x branch cap enforcement — max phase 2 unless explicitly forced
- [ ] T021 [P] Unit tests for phase resolution — precedence, cap, source description

### Implementation Notes
- Load config via existing config loader pattern (see `agent_config.py`)
- Load meta.json via existing `json.loads()` pattern in `feature_detection.py`
- Built-in default: Phase 1 (dual-write)
- Phase values: 0 (hardening), 1 (dual-write), 2 (read-cutover)

### Parallel Opportunities
- T018, T019, T021 can proceed in parallel

### Dependencies
- Depends on WP01 (uses Lane enum for phase validation context)

### Risks & Mitigations
- Risk: Config file schema change → additive only, existing configs remain valid

---

## Work Package WP05: Lane Expansion in Existing Modules (Priority: P0)

**Goal**: Expand the existing 4-lane model to 7 canonical lanes throughout the codebase — `tasks_support.py`, `frontmatter.py`, and all validation touchpoints.
**Independent Test**: All 7 lanes accepted in validation; `doing` alias resolves correctly; existing tests still pass.
**Prompt**: `tasks/WP05-lane-expansion-existing-modules.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T022 Update `src/specify_cli/tasks_support.py` — expand LANES tuple to 7 canonical lanes, add LANE_ALIASES map
- [ ] T023 Update `src/specify_cli/frontmatter.py` — expand `valid_lanes` in `validate()` to 7 lanes
- [ ] T024 Update `ensure_lane()` in tasks_support.py to resolve aliases before validation
- [ ] T025 Audit all other references to old 4-lane set (grep for `"doing"`, `"planned"`, hardcoded lane lists)
- [ ] T026 [P] Unit tests for expanded lane validation, alias resolution, and backward compatibility

### Implementation Notes
- Old LANES: `("planned", "doing", "for_review", "done")`
- New LANES: `("planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled")`
- `ensure_lane("doing")` → returns `"in_progress"` (resolved alias)
- `ensure_lane("claimed")` → returns `"claimed"` (new canonical lane)
- Must update `agent_utils/status.py` lane references too

### Parallel Opportunities
- T026 can start once interface changes are clear

### Dependencies
- Depends on WP01 (uses Lane enum as reference)

### Risks & Mitigations
- Risk: Breaking existing tests that assert on 4-lane set → update test expectations
- Risk: Grep may miss hardcoded lane references → thorough codebase audit in T025

---

## Work Package WP06: Legacy Bridge (Compatibility Views) (Priority: P1)

**Goal**: Create the legacy bridge that generates frontmatter `lane` fields and `tasks.md` status sections from `status.json`. These are compatibility views, never authoritative.
**Independent Test**: Given a `status.json` snapshot, generate matching frontmatter and tasks.md content.
**Prompt**: `tasks/WP06-legacy-bridge-compatibility-views.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T027 Create `src/specify_cli/status/legacy_bridge.py` — `update_frontmatter_views()`, `update_tasks_md_views()`
- [ ] T028 Frontmatter lane field regeneration from StatusSnapshot per WP
- [ ] T029 tasks.md status section regeneration from StatusSnapshot
- [ ] T030 Phase-aware behavior — Phase 1: update views alongside dual-write; Phase 2: views are generated-only
- [ ] T031 [P] Unit tests for legacy bridge — view generation, phase behavior, round-trip consistency

### Implementation Notes
- Use existing `FrontmatterManager.update_field()` for WP frontmatter updates
- For tasks.md: parse existing content, find/replace status sections
- Phase 1: views updated after every emit (dual-write)
- Phase 2: views regenerated on materialize; manual edits detected as drift by validate

### Parallel Opportunities
- T031 can start once interface is defined

### Dependencies
- Depends on WP03 (reducer/snapshot), WP05 (expanded lane support in frontmatter)

### Risks & Mitigations
- Risk: tasks.md parsing fragility → use robust section marker detection
- Risk: Partial frontmatter updates leaving stale data → always write full normalized frontmatter

---

## Work Package WP07: Status Emit Orchestration (Priority: P1) 🎯 MVP Core

**Goal**: Create the central orchestration pipeline: validate transition → append event → materialize snapshot → update views → emit SaaS telemetry. This is the single entry point for all state changes.
**Independent Test**: Emit a transition and verify: event in JSONL, status.json updated, frontmatter updated, SaaS event sent (when configured).
**Prompt**: `tasks/WP07-status-emit-orchestration.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [ ] T032 Create emit orchestration function in `status/__init__.py` or dedicated module — the full pipeline
- [ ] T033 Integration with `sync/events.py` for SaaS fan-out (conditional on sync availability via try/except import)
- [ ] T034 Atomic operation wrapping — if any step fails, no partial state persisted
- [ ] T035 Force transition handling — validate actor + reason, bypass guards, record force flag
- [ ] T036 Done-evidence contract enforcement — reject `done` without evidence unless forced
- [ ] T037 [P] Integration tests for emit pipeline — end-to-end flow verification

### Implementation Notes
- Pipeline order: validate_transition() → append_event() → materialize() → update_views() → saas_emit()
- SaaS import: `try: from specify_cli.sync.events import emit_wp_status_changed; except ImportError: saas_emit = lambda **kw: None`
- Atomic: append to JSONL first. If materialize fails, the event is still in the log (recoverable). If frontmatter update fails, log is still canonical (views regenerable).
- The orchestration function accepts: feature_slug, wp_id, to_lane, actor, force, reason, evidence, review_ref, execution_mode

### Parallel Opportunities
- T037 can start once the pipeline interface is defined

### Dependencies
- Depends on WP02 (store), WP03 (reducer), WP04 (phase), WP06 (legacy bridge)

### Risks & Mitigations
- Risk: Circular imports between status/ and sync/ → use lazy imports for sync
- Risk: SaaS emit failure shouldn't block local persistence → emit is best-effort after canonical append

---

## Work Package WP08: CLI Status Commands (emit & materialize) (Priority: P1)

**Goal**: Create the `spec-kitty agent status` command group with `emit` and `materialize` subcommands.
**Independent Test**: Run `status emit` and `status materialize` from CLI and verify correct behavior.
**Prompt**: `tasks/WP08-cli-status-commands-emit-materialize.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T038 Create `src/specify_cli/cli/commands/agent/status.py` — typer command group `app`
- [ ] T039 `status emit` command — accepts wp_id, --to, --actor, --force, --reason, --evidence-json, --review-ref, --execution-mode; delegates to orchestration
- [ ] T040 `status materialize` command — accepts --feature; rebuilds status.json and views from log
- [ ] T041 Register `status` command group in agent CLI app (parent typer app)
- [ ] T042 [P] Integration tests for CLI commands — invoke via typer CliRunner

### Implementation Notes
- Follow existing pattern in `cli/commands/agent/tasks.py` for typer app structure
- Feature detection: reuse `detect_feature_slug()` from `core.feature_detection`
- JSON output support: `--json` flag for machine-readable output
- Evidence: accept as JSON string `--evidence-json '{"review": {...}}'`

### Parallel Opportunities
- T042 can start once command signatures are defined

### Dependencies
- Depends on WP07 (emit orchestration)

### Risks & Mitigations
- Risk: CLI registration conflicts → follow existing agent app registration pattern

---

## Work Package WP09: move-task Delegation (Priority: P1) 🎯 MVP Core

**Goal**: Refactor `move_task()` in `cli/commands/agent/tasks.py` to delegate state mutation to the `status.emit` orchestration while retaining all existing pre-validation.
**Independent Test**: `spec-kitty agent tasks move-task WP01 --to doing` works exactly as before but internally uses the canonical pipeline.
**Prompt**: `tasks/WP09-move-task-delegation.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T043 Refactor `move_task()` — replace set_scalar/write/emit sequence with call to `status.emit`
- [ ] T044 Retain existing pre-validation: subtask checks, review readiness, agent ownership, uncommitted changes
- [ ] T045 Map move-task parameters to status.emit arguments (assignee, review_status, reviewed_by as event metadata)
- [ ] T046 Backward compatibility: `--to doing` resolves to `in_progress` transparently
- [ ] T047 [P] Integration tests for move-task → status.emit delegation; verify identical behavior to pre-refactor

### Implementation Notes
- Current flow: ensure_lane → validate → set_scalar → write → commit → emit_wp_status_changed
- New flow: resolve_alias → validate → status.emit(orchestration) → commit
- The `status.emit` orchestration handles: event append, materialize, frontmatter update, SaaS emit
- Git commit step remains in `move_task()` (commits both JSONL and frontmatter changes)

### Parallel Opportunities
- T047 can start once delegation interface is clear

### Dependencies
- Depends on WP07 (emit orchestration), WP05 (lane expansion/alias in tasks_support)

### Risks & Mitigations
- Risk: Breaking existing agent workflows → extensive backward compatibility testing
- Risk: Git commit now includes additional files (status.events.jsonl, status.json) → verify git add patterns

---

## Work Package WP10: Rollback-Aware Merge Resolution (Priority: P1)

**Goal**: Replace the monotonic "most done wins" conflict resolver in `merge/status_resolver.py` with rollback-aware logic, and add event log merge support for JSONL files.
**Independent Test**: Reviewer rollback beats concurrent forward progression during merge.
**Prompt**: `tasks/WP10-rollback-aware-merge-resolution.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T048 Update `merge/status_resolver.py` — expand LANE_PRIORITY to 7 lanes
- [ ] T049 Implement rollback detection — identify reviewer rollback signals in history entries
- [ ] T050 Replace monotonic resolver with rollback-aware logic: rollback wins over forward progression
- [ ] T051 Add JSONL event log merge support — concatenate, deduplicate by event_id, sort for status.events.jsonl
- [ ] T052 [P] Unit tests for rollback resolution and event log merge

### Implementation Notes
- Current LANE_PRIORITY: `{"done": 4, "for_review": 3, "doing": 2, "planned": 1}`
- New: add `"claimed": 2, "in_progress": 3, "blocked": 0, "canceled": 5` (but precedence is secondary to rollback awareness)
- Rollback signal: history entry with "review" and "changes requested" OR frontmatter `review_status: "has_feedback"`
- For JSONL merge: read both files, concatenate, dedupe by event_id, sort by (at, event_id), write merged file

### Parallel Opportunities
- T052 can start once resolution interface is defined

### Dependencies
- Depends on WP01 (models/lanes), WP03 (reducer for event log merge)

### Risks & Mitigations
- Risk: Changing merge behavior could break existing merges → extensive test coverage of edge cases
- Risk: Event log deduplication must handle partial overlaps → test with overlapping event sets

---

## Work Package WP11: Status Validate Command (Priority: P2)

**Goal**: Create the validation engine and CLI command that checks event schema, transition legality, done-evidence, materialization drift, and derived-view drift.
**Independent Test**: Introduce violations and verify each is detected with specific error messages.
**Prompt**: `tasks/WP11-status-validate-command.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T053 Create validation engine in `status/` — event schema validation (per-event field checks)
- [ ] T054 Transition legality audit — replay events and verify each transition is legal
- [ ] T055 Done-evidence completeness check — every `done` event has evidence or force flag
- [ ] T056 Materialization drift detection — compare `status.json` on disk vs reducer output
- [ ] T057 Derived-view drift detection — compare frontmatter lanes vs status.json
- [ ] T058 [P] CLI `status validate` command + integration tests

### Implementation Notes
- Validate returns structured results: errors (blocking), warnings (informational), phase source
- Phase-aware: Phase 1 → drift is warning; Phase 2 → drift is error
- Output should include event_id and context for each violation
- CI integration: exit code 0 for pass, 1 for failures

### Parallel Opportunities
- T058 can start once validation engine interface is defined

### Dependencies
- Depends on WP03 (reducer for drift detection), WP06 (legacy bridge for view comparison)

### Risks & Mitigations
- Risk: Large event logs slow down validation → optimize with early termination on first error (optional)

---

## Work Package WP12: Status Doctor (Priority: P3)

**Goal**: Create health check framework detecting stale claims, orphan workspaces, and unresolved drift.
**Independent Test**: Create stale claims and orphan worktrees, run doctor, verify detection.
**Prompt**: `tasks/WP12-status-doctor.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T059 Create `src/specify_cli/status/doctor.py` — health check framework with pluggable checks
- [ ] T060 Stale claim detection — WPs in `claimed` or `in_progress` beyond configurable threshold
- [ ] T061 Orphan workspace/worktree detection — worktrees for completed/canceled features
- [ ] T062 Unresolved drift detection — delegate to validate engine for quick drift check
- [ ] T063 [P] CLI `status doctor` command + unit tests

### Implementation Notes
- Default staleness threshold: 7 days for `claimed`, 14 days for `in_progress`
- Orphan detection: scan `.worktrees/` for directories whose features are all `done`
- Output: structured report with recommended actions per finding

### Parallel Opportunities
- T063 can start once doctor interface is defined

### Dependencies
- Depends on WP03 (reducer for state inspection)

### Risks & Mitigations
- Risk: Worktree scanning may be slow on large repos → limit to feature-specific scans

---

## Work Package WP13: Status Reconcile (Priority: P3)

**Goal**: Create cross-repo drift detection and reconciliation event generation with `--dry-run` and `--apply` modes.
**Independent Test**: Detect planning vs implementation drift; generate reconciliation events in dry-run.
**Prompt**: `tasks/WP13-status-reconcile.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T064 Create `src/specify_cli/status/reconcile.py` — cross-repo drift scanning framework
- [ ] T065 WP-to-commit linkage detection — scan target repos for WP-linked commits (branch naming, commit messages)
- [ ] T066 Reconciliation event generation — create StatusEvents that would align planning with implementation
- [ ] T067 Dry-run mode: report suggested events without persisting
- [ ] T068 Apply mode: emit reconciliation events to canonical log (2.x only; 0.1x dry-run only)
- [ ] T069 [P] CLI `status reconcile` command (--dry-run, --apply, --feature) + unit tests

### Implementation Notes
- Detect WP-linked commits: search for branch patterns `*-WP##` and commit messages containing `WP##`
- Reconciliation events have `actor: "reconcile"` and `execution_mode: "direct_repo"`
- 0.1x cap: apply mode gated behind branch check (see phase.py)
- Evidence for reconciliation: auto-generated from commit metadata

### Parallel Opportunities
- T069 can start once reconcile interface is defined

### Dependencies
- Depends on WP03 (reducer), WP07 (emit orchestration for apply mode)

### Risks & Mitigations
- Risk: Target repo access may not be available → graceful degradation with informative error
- Risk: False positives in commit linkage → require explicit WP reference in commit or branch name

---

## Work Package WP14: Legacy Migration Command (Priority: P2)

**Goal**: Create migration command that bootstraps canonical event logs from existing frontmatter lane state.
**Independent Test**: Migrate a feature with 4 WPs at various lanes; verify event log + status.json match pre-migration state.
**Prompt**: `tasks/WP14-legacy-migration-command.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T070 Create migration function — read existing frontmatter lanes, generate bootstrap events per WP
- [ ] T071 Alias mapping in bootstrap events — `doing` → `in_progress`
- [ ] T072 Idempotency — skip features that already have `status.events.jsonl`
- [ ] T073 CLI `status migrate` command (--feature or --all for all features)
- [ ] T074 [P] Integration tests — migrate legacy feature, verify event log, materialize, compare with pre-migration state

### Implementation Notes
- Bootstrap event: `from_lane: null, to_lane: <current_lane>, actor: "migration"`, timestamp from frontmatter history or current time
- For features with history entries: optionally replay history into multiple events
- Migration report: list of features migrated, WPs per feature, any aliases resolved

### Parallel Opportunities
- T074 can start once migration interface is defined

### Dependencies
- Depends on WP02 (store for event append), WP03 (reducer for verification), WP05 (alias mapping)

### Risks & Mitigations
- Risk: Features with corrupted frontmatter → skip with warning, don't fail entire migration
- Risk: `doing` lanes must map correctly → explicit alias resolution test

---

## Work Package WP15: Comprehensive Test Suite (Priority: P2)

**Goal**: Integration tests covering dual-write, read-cutover, end-to-end CLI, and cross-branch parity fixtures.
**Independent Test**: All test scenarios pass; parity fixtures produce identical output on both branches.
**Prompt**: `tasks/WP15-comprehensive-test-suite.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [ ] T075 Dual-write integration tests — Phase 1 behavior: event appended AND frontmatter updated
- [ ] T076 Read-cutover integration tests — Phase 2 behavior: reads from status.json only
- [ ] T077 End-to-end CLI integration tests — emit → validate → materialize → doctor pipeline
- [ ] T078 Cross-branch parity test fixtures — shared JSONL files that both 2.x and 0.1x reducers must produce identical output from
- [ ] T079 Conflict resolution integration tests — reviewer rollback precedence in merge scenarios
- [ ] T080 Migration integration tests — legacy → event log → materialize → verify parity

### Implementation Notes
- Parity fixtures: create `tests/cross_branch/fixtures/` with sample event logs and expected snapshots
- These fixtures are shared between branches — copy to 0.1x during backport
- Use pytest parametrize for multi-phase testing (phase 0, 1, 2)
- Use tmp_path fixtures for isolated test environments

### Parallel Opportunities
- All test files can be written in parallel (different test concerns)

### Dependencies
- Depends on WP09 (move-task delegation), WP11 (validate command)

### Risks & Mitigations
- Risk: Test isolation — each test must create its own feature directory → use pytest tmp_path
- Risk: Parity fixtures must be deterministic → use fixed timestamps and event_ids

---

## Work Package WP16: Backport to 0.1x & Parity Matrix (Priority: P1)

**Goal**: Backport Phases 0-2 from `2.x` to the `0.1x` line (main/release branches). SaaS emission as no-op. Phase 3 dry-run only. Generate parity matrix.
**Independent Test**: Same canonical event processed by both branches produces identical status.json.
**Prompt**: `tasks/WP16-backport-to-01x-parity-matrix.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T081 Identify 0.1x branch targets — main, release/0.13.x branches
- [ ] T082 Cherry-pick/adapt status engine modules to 0.1x — adjust imports, remove SaaS dependencies
- [ ] T083 SaaS fan-out as no-op on 0.1x — conditional import, graceful skip
- [ ] T084 Phase cap enforcement — max Phase 2, reconcile --dry-run only
- [ ] T085 Run cross-branch parity tests on 0.1x
- [ ] T086 [P] Generate parity matrix document — list every feature with delta status (identical/adapted/missing)

### Implementation Notes
- Start from 2.x implementation, create backport branch from main
- Key adaptations: `sync/events.py` import → no-op wrapper; `status reconcile --apply` → disabled
- Parity matrix columns: Module | 2.x Status | 0.1x Status | Delta | Notes
- Must update pyproject.toml on 0.1x if ULID dependency is missing

### Parallel Opportunities
- T086 can proceed alongside backport work

### Dependencies
- Depends on WP01–WP15 (all implementation and tests complete on 2.x)

### Risks & Mitigations
- Risk: Cherry-pick conflicts with 0.1x changes → manual adaptation per file
- Risk: 0.1x missing dependencies → add minimal dependencies, verify compatibility

---

## Work Package WP17: Documentation & Final Report (Priority: P3)

**Goal**: Update operator/contributor documentation, generate final delivery report with branch-by-branch commit list, migration notes, parity table, and risk register.
**Independent Test**: Documentation accurately describes commands, phases, and migration steps.
**Prompt**: `tasks/WP17-documentation-and-final-report.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T087 Update operator documentation — new commands, phases, migration steps in docs/
- [ ] T088 Update contributor documentation — architecture, data model, integration points
- [ ] T089 Generate final report — branch-by-branch commit list, migration/cutover notes
- [ ] T090 [P] Parity/delta table in final report — unavoidable differences between 2.x and 0.1x
- [ ] T091 [P] Risk register and rollback plan in final report
- [ ] T092 [P] Validate quickstart.md scenario — verify all commands work as documented

### Implementation Notes
- Final report structure: Executive Summary → Commit List → Migration Notes → Parity Table → Risk Register → Rollback Plan
- Update CLAUDE.md with status model patterns
- Validate quickstart.md by running each command in sequence

### Parallel Opportunities
- T090, T091, T092 can proceed in parallel

### Dependencies
- Depends on WP16 (backport complete, parity data available)

### Risks & Mitigations
- Risk: Documentation drift → tie doc updates to specific code changes

---

## Dependency & Execution Summary

### Dependency Graph

```
WP01 ──→ WP02 ──→ WP03 ──→ WP06 ──→ WP07 ──→ WP08 ──→ WP15
  │         │         │         │         │         │
  ├──→ WP04 │    ├──→ WP10     ├──→ WP11 ├──→ WP09 │
  │         │    ├──→ WP12     │         │         │
  ├──→ WP05 │    └──→ WP13     │         │         │
  │         │                  │         │         │
  │         └──→ WP14 ←───────┘         │         │
  │                                     │         │
  └─────────────────────────────────────┘         │
                                                  ↓
                                         WP16 ──→ WP17
```

### Execution Waves (Maximum Parallelization)

| Wave | Work Packages | Parallel? |
|------|--------------|-----------|
| 1 | WP01 | Solo (foundation) |
| 2 | WP02, WP04, WP05 | 3-way parallel |
| 3 | WP03, WP10 | 2-way parallel |
| 4 | WP06, WP12, WP13 | 3-way parallel |
| 5 | WP07, WP11, WP14 | 3-way parallel |
| 6 | WP08, WP09 | 2-way parallel |
| 7 | WP15 | Solo (integration tests) |
| 8 | WP16 | Solo (backport) |
| 9 | WP17 | Solo (documentation) |

### MVP Scope

**Minimum viable delivery**: WP01 → WP02 → WP03 → WP05 → WP06 → WP07 → WP09

This gives: models, store, reducer, lane expansion, legacy bridge, emit orchestration, and move-task delegation. The canonical pipeline works end-to-end with existing commands.

### Parallelization Highlights

- **Wave 2** is the big win: WP02 (store), WP04 (phase config), WP05 (lane expansion) are fully independent
- **Wave 4**: WP06 (legacy bridge), WP12 (doctor), WP13 (reconcile) touch different modules entirely
- **Wave 5**: WP07 (orchestration), WP11 (validate), WP14 (migration) operate on different concerns

---

## Subtask Index (Reference)

| Subtask | Summary | WP | Priority | Parallel? |
|---------|---------|------|----------|-----------|
| T001 | Create status/__init__.py | WP01 | P0 | No |
| T002 | Create status/models.py | WP01 | P0 | No |
| T003 | Create status/transitions.py | WP01 | P0 | No |
| T004 | Unit tests for models | WP01 | P0 | Yes |
| T005 | Unit tests for transitions | WP01 | P0 | Yes |
| T006 | Create status/store.py | WP02 | P0 | No |
| T007 | JSONL serialization/deserialization | WP02 | P0 | No |
| T008 | Corruption detection | WP02 | P0 | No |
| T009 | File creation on first event | WP02 | P0 | No |
| T010 | Unit tests for store | WP02 | P0 | Yes |
| T011 | Create status/reducer.py | WP03 | P0 | No |
| T012 | Rollback-aware precedence | WP03 | P0 | No |
| T013 | Byte-identical serialization | WP03 | P0 | No |
| T014 | materialize() function | WP03 | P0 | No |
| T015 | Reducer determinism tests | WP03 | P0 | Yes |
| T016 | Rollback resolution tests | WP03 | P0 | Yes |
| T017 | Create status/phase.py | WP04 | P0 | No |
| T018 | Config.yaml schema update | WP04 | P0 | Yes |
| T019 | meta.json status_phase field | WP04 | P0 | Yes |
| T020 | 0.1x branch cap enforcement | WP04 | P0 | No |
| T021 | Phase resolution tests | WP04 | P0 | Yes |
| T022 | Expand LANES in tasks_support | WP05 | P0 | No |
| T023 | Expand valid_lanes in frontmatter | WP05 | P0 | No |
| T024 | Update ensure_lane() alias resolution | WP05 | P0 | No |
| T025 | Audit all lane references | WP05 | P0 | No |
| T026 | Lane expansion tests | WP05 | P0 | Yes |
| T027 | Create legacy_bridge.py | WP06 | P1 | No |
| T028 | Frontmatter lane regeneration | WP06 | P1 | No |
| T029 | tasks.md status regeneration | WP06 | P1 | No |
| T030 | Phase-aware view behavior | WP06 | P1 | No |
| T031 | Legacy bridge tests | WP06 | P1 | Yes |
| T032 | Emit orchestration pipeline | WP07 | P1 | No |
| T033 | SaaS fan-out integration | WP07 | P1 | No |
| T034 | Atomic operation wrapping | WP07 | P1 | No |
| T035 | Force transition handling | WP07 | P1 | No |
| T036 | Done-evidence enforcement | WP07 | P1 | No |
| T037 | Emit pipeline integration tests | WP07 | P1 | Yes |
| T038 | Create agent/status.py CLI group | WP08 | P1 | No |
| T039 | status emit CLI command | WP08 | P1 | No |
| T040 | status materialize CLI command | WP08 | P1 | No |
| T041 | Register status in agent CLI | WP08 | P1 | No |
| T042 | CLI command integration tests | WP08 | P1 | Yes |
| T043 | Refactor move_task() delegation | WP09 | P1 | No |
| T044 | Retain pre-validation logic | WP09 | P1 | No |
| T045 | Map move-task params to emit args | WP09 | P1 | No |
| T046 | Backward compat: --to doing alias | WP09 | P1 | No |
| T047 | Delegation integration tests | WP09 | P1 | Yes |
| T048 | Expand LANE_PRIORITY to 7 lanes | WP10 | P1 | No |
| T049 | Rollback detection in history | WP10 | P1 | No |
| T050 | Rollback-aware resolver logic | WP10 | P1 | No |
| T051 | JSONL event log merge support | WP10 | P1 | No |
| T052 | Merge resolution tests | WP10 | P1 | Yes |
| T053 | Event schema validation engine | WP11 | P2 | No |
| T054 | Transition legality audit | WP11 | P2 | No |
| T055 | Done-evidence completeness check | WP11 | P2 | No |
| T056 | Materialization drift detection | WP11 | P2 | No |
| T057 | Derived-view drift detection | WP11 | P2 | No |
| T058 | CLI status validate + tests | WP11 | P2 | Yes |
| T059 | Create status/doctor.py | WP12 | P3 | No |
| T060 | Stale claim detection | WP12 | P3 | No |
| T061 | Orphan workspace detection | WP12 | P3 | No |
| T062 | Drift detection delegation | WP12 | P3 | No |
| T063 | CLI status doctor + tests | WP12 | P3 | Yes |
| T064 | Create status/reconcile.py | WP13 | P3 | No |
| T065 | WP-to-commit linkage detection | WP13 | P3 | No |
| T066 | Reconciliation event generation | WP13 | P3 | No |
| T067 | Dry-run mode | WP13 | P3 | No |
| T068 | Apply mode (2.x only) | WP13 | P3 | No |
| T069 | CLI status reconcile + tests | WP13 | P3 | Yes |
| T070 | Migration function | WP14 | P2 | No |
| T071 | Alias mapping in bootstrap | WP14 | P2 | No |
| T072 | Migration idempotency | WP14 | P2 | No |
| T073 | CLI status migrate command | WP14 | P2 | No |
| T074 | Migration integration tests | WP14 | P2 | Yes |
| T075 | Dual-write integration tests | WP15 | P2 | Yes |
| T076 | Read-cutover integration tests | WP15 | P2 | Yes |
| T077 | E2E CLI integration tests | WP15 | P2 | Yes |
| T078 | Cross-branch parity fixtures | WP15 | P2 | Yes |
| T079 | Conflict resolution integration | WP15 | P2 | Yes |
| T080 | Migration integration tests | WP15 | P2 | Yes |
| T081 | Identify 0.1x branch targets | WP16 | P1 | No |
| T082 | Cherry-pick status engine to 0.1x | WP16 | P1 | No |
| T083 | SaaS fan-out as no-op | WP16 | P1 | No |
| T084 | Phase cap enforcement on 0.1x | WP16 | P1 | No |
| T085 | Run parity tests on 0.1x | WP16 | P1 | No |
| T086 | Generate parity matrix document | WP16 | P1 | Yes |
| T087 | Update operator documentation | WP17 | P3 | No |
| T088 | Update contributor documentation | WP17 | P3 | No |
| T089 | Generate final delivery report | WP17 | P3 | No |
| T090 | Parity/delta table in report | WP17 | P3 | Yes |
| T091 | Risk register and rollback plan | WP17 | P3 | Yes |
| T092 | Validate quickstart.md scenario | WP17 | P3 | Yes |
