# Implementation Plan: Canonical Context Architecture Cleanup

**Branch**: `057-canonical-context-architecture-cleanup` | **Date**: 2026-03-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/057-canonical-context-architecture-cleanup/spec.md`

## Summary

Big-bang architectural cleanup of Spec Kitty addressing four root failures: context rediscovery, multi-authority state, single execution model for different WP types, and generated state in merge paths. Five coordinated moves ship as one breaking release with a one-shot migration. Every move includes aggressive deletion of the code it supersedes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict)
**Storage**: Filesystem only — JSONL event logs, JSON context files, YAML frontmatter
**Testing**: pytest with 90%+ coverage, mypy --strict, integration tests for CLI commands
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform)
**Project Type**: Single Python package (src/specify_cli/)
**Performance Goals**: CLI operations < 2s, context resolution < 500ms, migration < 30s for 20 features / 200 WPs
**Constraints**: Big-bang release, no SaaS changes, fail-fast on unmigrated, no dual-authority state post-release
**Scale/Scope**: 12 agent directories, ~53 existing migrations, 8-lane state machine, ~15 CLI command groups

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | Pass | All new code targets 3.11+ |
| typer/rich/ruamel.yaml | Pass | No new framework dependencies introduced |
| pytest 90%+ coverage | Pass | Required for all new code |
| mypy --strict | Pass | Required for all new interfaces |
| CLI ops < 2s | Pass | Context token lookup is O(1) file read; event log reduction is O(n) on events |
| Cross-platform | Pass | All paths use pathlib; no platform-specific APIs |
| Git required | Pass | Worktree and merge operations depend on git |
| spec-kitty-events integration | N/A | This feature does not change the events library dependency |
| Terminology: Mission not Feature | Noted | Internal code still uses `feature_*` widely; this refactoring does not rename — that is a separate effort |

## Project Structure

### Documentation (this feature)

```
kitty-specs/057-canonical-context-architecture-cleanup/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — quick reference
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks/               # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── context/                    # NEW — Move 1: MissionContext
│   ├── __init__.py
│   ├── models.py               # MissionContext, ContextToken dataclasses
│   ├── resolver.py             # Resolve context from raw args → persisted token
│   ├── store.py                # Read/write .kittify/runtime/contexts/<token>.json
│   └── middleware.py           # CLI middleware: load context or fail-fast
│
├── ownership/                  # NEW — Move 2: WP Ownership Manifest
│   ├── __init__.py
│   ├── models.py               # ExecutionMode enum, OwnershipManifest dataclass
│   ├── inference.py            # Infer execution_mode/owned_files from existing WPs
│   ├── validation.py           # Overlap detection, completeness checks
│   └── workspace_strategy.py   # Route to correct workspace type by execution_mode
│
├── status/                     # REWRITE — Move 3: Canonical State
│   ├── __init__.py             # Public API (unchanged exports, new internals)
│   ├── models.py               # Lane, StatusEvent, StatusSnapshot (keep)
│   ├── transitions.py          # ALLOWED_TRANSITIONS, guards (keep)
│   ├── reducer.py              # reduce(), materialize() (keep, simplify)
│   ├── store.py                # append_event(), read_events() (keep)
│   ├── emit.py                 # emit_status_transition() (simplify — remove dual-write)
│   ├── progress.py             # NEW — weighted progress computation (shared library)
│   ├── views.py                # NEW — derived view generation (replaces legacy_bridge)
│   └── validate.py             # Schema validation (keep, simplify)
│   # DELETED: legacy_bridge.py, phase.py, doctor.py (phase-aware), reconcile.py (drift)
│
├── merge/                      # REWRITE — Move 4: Merge Engine v2
│   ├── __init__.py
│   ├── engine.py               # NEW — dedicated merge workspace orchestrator
│   ├── state.py                # REWRITE — MergeState at .kittify/runtime/merge/<mid>/
│   ├── preflight.py            # Keep, simplify (uses MissionContext)
│   ├── ordering.py             # Keep (dependency-based ordering)
│   ├── conflict_resolver.py    # NEW — managed resolution for spec-kitty-owned files
│   ├── reconciliation.py       # NEW — post-merge done-state from git ancestry
│   └── workspace.py            # NEW — dedicated merge worktree lifecycle
│   # DELETED: executor.py (replaced by engine.py), forecast.py (absorbed), status_resolver.py
│
├── shims/                      # NEW — Move 5: Thin Agent Surface
│   ├── __init__.py
│   ├── models.py               # ShimTemplate, AgentShimConfig dataclasses
│   ├── generator.py            # Generate thin shim files for all configured agents
│   ├── registry.py             # Skill allowlist — internal vs consumer skills
│   └── entrypoints.py          # spec-kitty agent shim <command> CLI handlers
│
├── migration/                  # NEW — One-shot migration (first-class deliverable)
│   ├── __init__.py
│   ├── schema_version.py       # Schema version detection and compatibility check
│   ├── gate.py                 # Upgrade gate — refuse unmigrated, fail-fast
│   ├── backfill_identity.py    # Assign project_uuid, mission_id, work_package_id
│   ├── backfill_ownership.py   # Infer execution_mode, owned_files from legacy
│   ├── rebuild_state.py        # Rebuild event log from frontmatter/status.json
│   ├── strip_frontmatter.py    # Remove mutable fields from WP frontmatter
│   ├── rewrite_shims.py        # Replace agent command files with thin shims
│   └── runner.py               # Orchestrate migration steps atomically
│
├── core/
│   ├── worktree.py             # SIMPLIFY — remove sparse-checkout policy, use ownership
│   ├── vcs/
│   │   └── git.py              # SIMPLIFY — remove sparse_exclude from critical path
│   ├── agent_config.py         # Keep (config.yaml management)
│   └── agent_context.py        # SIMPLIFY — remove tech-stack parsing from plan.md
│   # DELETED: feature_detection.py (668 lines — replaced by context/resolver.py)
│
├── cli/commands/
│   ├── context.py              # NEW — spec-kitty agent context resolve/show
│   ├── shim.py                 # NEW — spec-kitty agent shim <command> entrypoints
│   ├── materialize.py          # NEW — spec-kitty materialize
│   └── [existing commands]     # MODIFY — add --context <token> to all workflow commands
│
└── upgrade/
    ├── detector.py             # REWRITE — schema version check, not heuristic detection
    ├── migrations/             # ADD new migration for 057
    │   └── m_3_0_0_canonical_context.py  # One-shot migration entry point
    └── runner.py               # SIMPLIFY — schema-version-based, not heuristic-based

tests/
├── specify_cli/
│   ├── context/                # NEW — MissionContext tests
│   ├── ownership/              # NEW — ownership manifest tests
│   ├── status/                 # UPDATE — remove phase/legacy_bridge tests, add progress/views
│   ├── merge/                  # REWRITE — test dedicated workspace, resume, conflict resolution
│   ├── shims/                  # NEW — shim generation, registry, entrypoint tests
│   ├── migration/              # NEW — one-shot migration tests (critical: mid-flight features)
│   └── cli/commands/
│       ├── test_context.py     # NEW
│       ├── test_shim.py        # NEW
│       └── test_materialize.py # NEW
```

**Structure Decision**: Single Python package with new top-level modules (`context/`, `ownership/`, `shims/`, `migration/`) alongside rewritten existing modules (`status/`, `merge/`). No new external dependencies.

## Filesystem Layout (Post-Migration)

```
.kittify/
├── metadata.yaml                              # TRACKED — project_uuid, schema_version, init timestamp
├── config.yaml                                # TRACKED — agent config, settings
├── skills-manifest.json                       # TRACKED — installed skills
├── constitution/                              # TRACKED (partial) — governance
├── glossaries/                                # TRACKED (partial) — canonical terms
│
├── derived/                                   # GITIGNORED — regenerable projections
│   ├── <feature_slug>/
│   │   ├── status.json                        # Materialized from event log
│   │   ├── board-summary.json                 # Kanban state cache
│   │   └── progress.json                      # Weighted progress
│   ├── dossiers/                              # Generated dossier snapshots
│   └── prompt-surfaces/                       # Generated prompt content
│
├── runtime/                                   # GITIGNORED — ephemeral state
│   ├── contexts/                              # Opaque context token files
│   │   └── ctx-01HV....json
│   ├── merge/                                 # Merge workspaces (per-mission)
│   │   └── <mission_id>/
│   │       ├── workspace/                     # Git worktree for merge
│   │       ├── state.json                     # Resume state
│   │       ├── lock                           # Merge lock
│   │       ├── context.json                   # Bound context for merge
│   │       └── log.jsonl                      # Merge operation log
│   ├── workspaces/                            # WP workspace context files
│   │   └── <feature_slug>-<wp_code>.json
│   └── locks/                                 # General operation locks
│
└── missions/                                  # GITIGNORED — mission template copies

kitty-specs/
└── <feature_slug>/
    ├── spec.md                                # TRACKED — human-authored
    ├── plan.md                                # TRACKED — human-authored
    ├── research.md                            # TRACKED — human-authored
    ├── data-model.md                          # TRACKED — human-authored
    ├── meta.json                              # TRACKED — immutable identity (mission_id, etc.)
    ├── status.events.jsonl                    # TRACKED — canonical event log (sole mutable-state authority)
    ├── tasks.md                               # TRACKED — human-authored (NO mutable status fields)
    ├── tasks/
    │   ├── WP01.md                            # TRACKED — static frontmatter only
    │   ├── WP02.md                            #   (title, dependencies, execution_mode, owned_files,
    │   └── ...                                #    authoritative_surface, work_package_id, wp_code, mission_id)
    └── checklists/                            # TRACKED — human-authored

.worktrees/                                    # GITIGNORED — WP implementation workspaces only
└── <feature_slug>-<wp_code>/                  # code_change WPs only
```

## Architectural Moves — Detailed Design

### Move 1: MissionContext Object

**What it replaces**: `src/specify_cli/core/feature_detection.py` (668 lines) and all ad-hoc slug/branch/WP resolution scattered across CLI commands.

**Identity model**:

| Field | Assigned when | Stored where | Immutable |
|-------|--------------|--------------|-----------|
| `project_uuid` | `spec-kitty init` | `.kittify/metadata.yaml` | Yes |
| `mission_id` | `create-feature` | `kitty-specs/*/meta.json` | Yes |
| `work_package_id` | task finalization | WP frontmatter | Yes |
| `wp_code` | task finalization | WP frontmatter | No (display alias) |

**Context token lifecycle**:

1. Agent invokes `spec-kitty agent shim implement --agent claude --raw-args "WP03"`
2. CLI shim entrypoint calls `context.resolver.resolve(raw_args, agent_name)`
3. Resolver parses `WP03` → looks up `work_package_id` by `wp_code` → builds `MissionContext`
4. Context persisted to `.kittify/runtime/contexts/ctx-01HV....json`
5. Token returned to caller
6. All subsequent commands use `--context ctx-01HV...` → direct file lookup, no resolution

**What gets deleted**:
- `src/specify_cli/core/feature_detection.py` — entire file (668 lines)
- All `detect_feature()` calls throughout CLI commands
- `_resolve_numeric_feature_slug()`, `_detect_from_git_branch()`, `_detect_from_cwd()`
- `SPECIFY_FEATURE` environment variable support as runtime behavior (keep only as migration input)
- Branch-name parsing for feature/WP extraction in worktree code
- `is_feature_complete()` heuristic (replaced by event log query)

### Move 2: WP Execution Modes and Ownership Manifest

**What it replaces**: Sparse checkout as policy boundary, implicit file ownership, single workspace strategy for all WP types.

**Execution modes**:

| Mode | Workspace strategy | Owned files |
|------|-------------------|-------------|
| `code_change` | Standard git worktree under `.worktrees/` | Source code globs |
| `planning_artifact` | In-repo or dedicated planning worktree (no sparse checkout) | `kitty-specs/*/` globs |

**Ownership manifest** (static WP frontmatter set at task finalization):

```yaml
---
work_package_id: "01HV..."
wp_code: "WP03"
mission_id: "01HV..."
title: "Implement MissionContext resolver"
dependencies: ["WP01"]
execution_mode: code_change
owned_files:
  - "src/specify_cli/context/**"
  - "tests/specify_cli/context/**"
authoritative_surface: "src/specify_cli/context/"
---
```

**Validation at finalization**:
- No two WPs may have overlapping `owned_files` globs
- Every source file touched by the feature should be owned by exactly one WP
- `authoritative_surface` must be a prefix of at least one `owned_files` entry

**What gets deleted**:
- Sparse checkout policy logic in `src/specify_cli/core/vcs/git.py` (`sparse_exclude` parameter and all callers)
- `create_feature_worktree()` sparse checkout setup in `src/specify_cli/core/worktree.py`
- All `kitty-specs/` special-case handling in worktree creation
- Sparse checkout recovery/repair logic in any migration or doctor command

### Move 3: Canonical State — Event Log as Sole Authority

**What it replaces**: The three-phase model (Phase 0/1/2), dual-write legacy bridge, frontmatter mutable fields, status.json as a tracked artifact.

**New model** (single phase — event log is always authoritative):

```
status.events.jsonl (TRACKED, append-only)
         │
         ▼
    reduce() → StatusSnapshot (in-memory)
         │
         ├──▶ .kittify/derived/<slug>/status.json    (GITIGNORED)
         ├──▶ .kittify/derived/<slug>/progress.json   (GITIGNORED)
         ├──▶ .kittify/derived/<slug>/board-summary.json (GITIGNORED)
         └──▶ CLI display (rich tables, progress bars)
```

**Weighted progress** (`status/progress.py`):
- Single shared implementation used by CLI and exposable to SaaS
- Weights configurable per-mission (default: equal weight per WP)
- Computed from snapshot lane counts: `done_weight / total_weight * 100`
- Returns structured JSON for machine consumption

**Lazy regeneration**: CLI commands that need derived state call `materialize_if_stale(feature_dir)` which checks event log mtime vs derived file mtime. `spec-kitty materialize` forces regeneration for CI/debugging.

**What gets deleted**:
- `src/specify_cli/status/legacy_bridge.py` — entire file (dual-write to frontmatter/tasks.md)
- `src/specify_cli/status/phase.py` — entire file (Phase 0/1/2 resolution)
- `src/specify_cli/status/doctor.py` — phase-aware health checks (rewrite as event-log-only)
- `src/specify_cli/status/reconcile.py` — cross-repo drift detection (no longer needed)
- `src/specify_cli/status/migrate.py` — bootstrap from frontmatter (moved to migration/)
- All frontmatter `lane` field reads/writes throughout the codebase
- All `status.json` reads as authoritative input (it becomes derived output only)
- `tasks.md` status block generation and parsing
- `update_frontmatter_views()` and all callers
- `resolve_phase()` and all callers
- Phase-conditional logic in `emit_status_transition()` (simplify to event-log-only path)
- `move-task` contamination heuristics that compare frontmatter vs event log

### Move 4: Merge Engine v2 — Dedicated Workspace

**What it replaces**: `src/specify_cli/merge/executor.py` which operates on the checked-out branch in the main repo.

**New merge flow**:

1. `spec-kitty merge --feature <slug>` (or `--context <token>`)
2. Load MissionContext → get mission_id, WP list, target branch
3. Create/reuse merge workspace at `.kittify/runtime/merge/<mission_id>/workspace/` (git worktree)
4. Persist `MergeState` to `.kittify/runtime/merge/<mission_id>/state.json`
5. In the merge workspace: checkout target branch, pull --ff-only
6. Compute merge order from dependency graph
7. For each WP in order:
   - Merge WP branch into workspace
   - If conflict on spec-kitty-owned file → auto-resolve via `conflict_resolver.py`
   - If conflict on human-authored file → pause, persist state, report
   - Mark WP complete in state
8. Push merged target branch (if `--push`)
9. Reconcile: emit `done` events for any WP whose branch is now merged ancestry
10. Cleanup: remove merge workspace, clear state

**Resume**: `spec-kitty merge --resume` loads state from `.kittify/runtime/merge/<mission_id>/state.json`, skips completed WPs.

**What gets deleted**:
- `src/specify_cli/merge/executor.py` — entire file (replaced by engine.py)
- `src/specify_cli/merge/forecast.py` — absorbed into engine dry-run
- `src/specify_cli/merge/status_resolver.py` — replaced by conflict_resolver.py
- `.kittify/merge-state.json` — legacy location (moved to runtime/merge/)
- All logic that checks out branches in the main repo during merge
- All logic that depends on the main repo's HEAD state during merge

### Move 5: Thin Agent Surface

**What it replaces**: ~14 full markdown command templates per mission, copied into 12 agent directories, containing workflow logic, recovery instructions, and argument parsing.

**New shim format** (identical across all agents):

```markdown
Run this exact command and treat its output as authoritative.
Do not rediscover context from branches, files, or prompt contents.

`spec-kitty agent shim implement --agent <AGENT_NAME> --raw-args "$ARGUMENTS"`
```

**CLI shim entrypoints** (`spec-kitty agent shim <command>`):
- `implement`, `review`, `status`, `specify`, `plan`, `tasks`, `merge`, `accept`
- Each entrypoint: resolve context if missing → persist token → dispatch to workflow handler
- All workflow logic stays in Python, not in markdown

**Skill registry** (`shims/registry.py`):
- Allowlist of consumer-facing skills (e.g., specify, plan, tasks, implement, review, merge, accept, status)
- Internal-only skills excluded from consumer installs (e.g., debug, doctor, materialize)
- Registry consulted during shim generation and upgrade

**What gets deleted**:
- `src/specify_cli/missions/*/command-templates/*.md` — all full prompt templates (replaced by shim templates)
- All migration code that copies/patches markdown command files into agent directories
- `src/specify_cli/core/agent_context.py` — tech-stack parsing from plan.md (no longer needed in shims)
- Prompt-specific recovery instructions scattered across templates
- Git-noise filtering instructions in agent templates
- Agent-template drift detection/repair logic in migrations

## Aggressive Deletion Inventory

This section consolidates all code scheduled for deletion. A good architecture change removes code.

### Files to Delete Entirely

| File | Lines (approx) | Replaced by |
|------|----------------|-------------|
| `src/specify_cli/core/feature_detection.py` | 668 | `context/resolver.py` |
| `src/specify_cli/status/legacy_bridge.py` | ~300 | `status/views.py` (derived only) |
| `src/specify_cli/status/phase.py` | ~150 | Nothing (single phase model) |
| `src/specify_cli/status/reconcile.py` | ~200 | Nothing (no cross-authority drift) |
| `src/specify_cli/status/migrate.py` | ~150 | `migration/rebuild_state.py` (one-shot only) |
| `src/specify_cli/merge/executor.py` | ~450 | `merge/engine.py` |
| `src/specify_cli/merge/forecast.py` | ~200 | Absorbed into `merge/engine.py` dry-run |
| `src/specify_cli/merge/status_resolver.py` | ~150 | `merge/conflict_resolver.py` |
| `src/specify_cli/core/agent_context.py` | ~300 | Not needed (shims don't carry tech context) |
| All `command-templates/*.md` (per mission) | ~14 files x ~4 missions | `shims/generator.py` |
| **Total estimated deletion** | **~2,500+ lines** | |

### Code Paths to Remove from Surviving Files

| File | What to remove |
|------|---------------|
| `src/specify_cli/core/worktree.py` | Sparse checkout setup, kitty-specs special cases |
| `src/specify_cli/core/vcs/git.py` | `sparse_exclude` parameter and callers |
| `src/specify_cli/status/emit.py` | Dual-write path, phase checks, frontmatter updates |
| `src/specify_cli/status/reducer.py` | Phase-aware materialization |
| `src/specify_cli/status/validate.py` | Multi-authority drift checks |
| `src/specify_cli/upgrade/detector.py` | Heuristic version detection (replace with schema version) |
| `src/specify_cli/upgrade/runner.py` | Heuristic-based migration selection |
| All CLI commands | `detect_feature()` calls, branch-parsing, env-var feature detection |
| All CLI commands | Frontmatter `lane` field reads/writes |
| All migrations | Code that copies full markdown templates into agent dirs |
| `src/specify_cli/workspace_context.py` | Move to `.kittify/runtime/workspaces/` (if kept) |

### Tests to Delete

| Test file/area | Reason |
|----------------|--------|
| Tests for `feature_detection.py` | Module deleted |
| Tests for `legacy_bridge.py` | Module deleted |
| Tests for `phase.py` | Module deleted |
| Tests for `reconcile.py` | Module deleted |
| Tests for `executor.py` (old merge) | Module deleted |
| Tests for `forecast.py` | Module deleted |
| Tests for sparse checkout behavior | Feature removed from critical path |
| Tests for frontmatter lane read/write | Behavior removed |
| Tests for dual-write / phase transitions | Behavior removed |

## One-Shot Migration Design

The migration is a first-class deliverable, not incidental tooling.

### Schema Version Model

```yaml
# .kittify/metadata.yaml (post-migration)
spec_kitty:
  version: "3.0.0"
  schema_version: 3        # Integer, monotonically increasing
  schema_capabilities:
    - canonical_context
    - event_log_authority
    - ownership_manifest
    - thin_shims
  initialized_at: "2026-01-01T00:00:00+00:00"
  project_uuid: "01HV..."
  last_upgraded_at: "2026-03-27T16:00:00+00:00"
```

### Upgrade Gate

Every CLI command calls `migration.gate.check_schema_version(repo_root)` before executing:
- If `schema_version` < required → refuse with "Run `spec-kitty upgrade`"
- If `schema_version` > CLI knows → refuse with "Upgrade your CLI"
- If `schema_version` matches → proceed

### Migration Steps (atomic — rollback on any failure)

1. **Backup**: Snapshot current `.kittify/` and `kitty-specs/` state
2. **Assign project_uuid**: Generate ULID, write to `metadata.yaml`
3. **For each feature in kitty-specs/**:
   a. Assign `mission_id` (ULID) to `meta.json`
   b. For each WP in `tasks/*.md`:
      - Assign `work_package_id` (ULID)
      - Set `wp_code` from existing WP label (e.g., "WP03")
      - Infer `execution_mode` from file paths (kitty-specs/ paths → `planning_artifact`, else `code_change`)
      - Infer `owned_files` from git diff of WP branch (if exists) or from task description
      - Set `authoritative_surface` from owned_files
      - Strip mutable frontmatter: remove `lane`, `review_status`, `reviewed_by`, `progress`, etc.
      - Keep static frontmatter: `title`, `dependencies`, `execution_mode`, `owned_files`, `authoritative_surface`, `work_package_id`, `wp_code`, `mission_id`
   c. Rebuild event log:
      - Read existing `status.events.jsonl` (if exists, keep as-is)
      - If no event log: infer state from frontmatter `lane` fields and `status.json`
      - Precedence: existing event log > status.json > frontmatter
      - Generate synthetic events for any state not already in event log
      - Log warnings for conflicts
   d. Move derived artifacts to `.kittify/derived/<feature_slug>/`
   e. Remove `status.json` from tracked paths (add to `.gitignore`)
4. **Rewrite agent shims**: Replace all agent command files with thin shims
5. **Update `.gitignore`**: Add `.kittify/derived/`, `.kittify/runtime/`, remove obsolete entries
6. **Update schema_version**: Set to 3, write capabilities list
7. **Migrate merge state**: Move `.kittify/merge-state.json` to `.kittify/runtime/merge/` (if active)
8. **Commit**: Single atomic commit with migration summary

### Rollback

If any step fails:
- Restore from backup
- Report which step failed and why
- Leave project in pre-migration state

## Implementation Order

These five moves are designed as a big-bang release but should be implemented in dependency order within the development program:

### Phase A: Foundation (Moves 1 + 2)

**Move 1: MissionContext** — no internal dependencies, enables all other moves.
- Build `context/` module
- Add `--context` to CLI middleware
- Add `spec-kitty agent context resolve` and `show` commands
- Delete `feature_detection.py`
- Update all CLI commands to use context token

**Move 2: Ownership Manifest** — depends on MissionContext for identity fields.
- Build `ownership/` module
- Add `execution_mode`, `owned_files`, `authoritative_surface` to WP frontmatter schema
- Add validation at task finalization
- Update worktree creation to route by execution_mode
- Delete sparse checkout policy code

### Phase B: State (Move 3)

**Move 3: Canonical State** — depends on Moves 1+2 for identity model.
- Simplify `status/emit.py` to event-log-only path
- Build `status/progress.py` and `status/views.py`
- Add `spec-kitty materialize` command
- Build lazy regeneration
- Delete `legacy_bridge.py`, `phase.py`, `reconcile.py`, `migrate.py`
- Strip all frontmatter lane reads/writes from codebase

### Phase C: Merge (Move 4)

**Move 4: Merge Engine v2** — depends on Moves 1+3 for context and canonical state.
- Build `merge/engine.py`, `workspace.py`, `conflict_resolver.py`, `reconciliation.py`
- Rewrite `merge/state.py` for new location
- Delete `executor.py`, `forecast.py`, `status_resolver.py`

### Phase D: Surface + Migration (Moves 5 + Migration)

**Move 5: Thin Agent Surface** — depends on Move 1 for shim entrypoints.
- Build `shims/` module
- Build `spec-kitty agent shim <command>` entrypoints
- Build skill registry with allowlist
- Delete all command-templates, agent-context tech parsing

**Migration** — depends on all moves being complete.
- Build `migration/` module
- Build schema version gate
- Integration test with legacy projects
- Delete heuristic version detector

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `context/` module (not extending existing) | Clean break from heuristic detection; entirely different data model | Extending `feature_detection.py` would preserve the heuristic resolution paths we're eliminating |
| New `migration/` module (not in `upgrade/migrations/`) | Migration is first-class deliverable with atomic rollback; too complex for a single migration file | A standard `m_3_0_0_*.py` migration file would be 1000+ lines and not testable in isolation |
| New `shims/` module | Agent shim generation is a new concern with its own registry, templates, and entrypoints | Putting this in `core/` or `upgrade/` conflates concerns |
