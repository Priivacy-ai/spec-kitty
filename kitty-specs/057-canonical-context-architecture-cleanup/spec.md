# Feature Specification: Canonical Context Architecture Cleanup

**Feature Branch**: `057-canonical-context-architecture-cleanup`
**Created**: 2026-03-27
**Status**: Draft
**Input**: Architectural analysis identifying four root failures in Spec Kitty's current design, with a five-move cleanup plan.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Implements a Work Package Without Context Loss (Priority: P1)

An AI agent receives a work package assignment. The agent resolves context once at the start of work, receives a bound context token, and every subsequent command (review, move-task, mark-status, accept, merge) uses that same token. The agent never re-resolves the feature slug, WP ID, branch, or owned files. If the context token is missing or invalid, the command fails immediately with an actionable error.

**Why this priority**: Context rediscovery is the single largest source of command failures, slug collisions, and cross-WP contamination. Fixing this absorbs the most bug surface area.

**Independent Test**: A full implement-through-merge cycle for one WP using only `--context <token>` on every command. No heuristic resolution triggered at any step.

**Acceptance Scenarios**:

1. **Given** an agent calls `spec-kitty agent context resolve --wp WP03 --feature 057-canonical-context-architecture-cleanup`, **When** the context is persisted, **Then** all subsequent commands accepting `--context <token>` operate on exactly WP03 with no re-resolution.
2. **Given** a persisted context token referencing WP03, **When** an agent passes that token to `spec-kitty agent tasks move-task --context <token> --to for_review`, **Then** the command moves WP03 without parsing branch names, env vars, or task file paths.
3. **Given** a command is invoked without `--context` and without sufficient arguments for unambiguous resolution, **When** the CLI attempts execution, **Then** it fails with a clear error directing the user to resolve context first.

---

### User Story 2 - Planning-Artifact WP Operates Without Worktree Confusion (Priority: P1)

A contributor works on a planning-artifact WP (e.g., writing spec.md, plan.md, or tasks.md). The WP's `execution_mode` is `planning_artifact`. The system does not create a sparse-checkout worktree. Instead, the contributor works directly on the planning surface in the main repository or in a dedicated planning worktree that includes exactly the owned files. No kitty-specs files are filtered, hidden, or confused by sparse-checkout boundaries.

**Why this priority**: Forcing planning-artifact WPs through the code-worktree pipeline is the root cause of most kitty-specs visibility failures and sparse-checkout confusion.

**Independent Test**: Create a feature, finalize tasks with at least one `planning_artifact` WP and one `code_change` WP. Implement the planning WP. Verify no sparse checkout is applied and the contributor can see and edit all owned planning files.

**Acceptance Scenarios**:

1. **Given** a WP with `execution_mode: planning_artifact` and `owned_files: ["kitty-specs/057-*/spec.md"]`, **When** the agent runs `spec-kitty implement WP01`, **Then** the system either works in-repo or creates a planning worktree with full access to the owned files, not a sparse-checkout worktree.
2. **Given** a WP with `execution_mode: code_change`, **When** the agent runs `spec-kitty implement WP02`, **Then** the system creates a standard worktree as it does today.
3. **Given** a WP with `execution_mode: planning_artifact`, **When** the agent checks the worktree contents, **Then** all files listed in `owned_files` and `authoritative_surface` are present and writable.

---

### User Story 3 - Status Is Read from One Authority (Priority: P1)

A project maintainer checks the kanban board. The board state is computed entirely from the canonical event log (`status.events.jsonl`). No frontmatter lane fields, no `status.json` projections, and no task-board caches are consulted as authoritative sources. Mutable status fields (lane, review_status, reviewed_by, progress summaries) do not exist in WP frontmatter. Derived views (status.json, board summaries) are regenerated from the event log on demand.

**Why this priority**: Multi-authority state is the root cause of drift, merge noise, and contradictory validators. Collapsing to one source eliminates an entire class of bugs.

**Independent Test**: Emit several status transitions via the event log. Verify that `spec-kitty status`, the CLI progress output, and any generated `status.json` all reflect exactly the event log state. Verify that WP frontmatter contains no mutable status fields.

**Acceptance Scenarios**:

1. **Given** a feature with 5 WPs and a sequence of status transitions in the event log, **When** a user runs `spec-kitty status`, **Then** the displayed board matches the event log exactly.
2. **Given** a WP file in `tasks/*.md`, **When** a user inspects its YAML frontmatter, **Then** only static metadata is present (title, dependencies, execution_mode, owned_files, authoritative_surface, wp_id, mission_id). No lane, review_status, reviewed_by, or progress fields exist.
3. **Given** a `status.json` file exists, **When** the event log is modified by a new transition, **Then** `status.json` is regenerated from the event log and never read as an input to status determination.

---

### User Story 4 - Merge Completes Deterministically in a Dedicated Workspace (Priority: P2)

A maintainer merges a completed feature. The merge engine creates or reuses a dedicated merge workspace independent of whatever branch is checked out in the main repository. The merge loads the canonical mission context, computes merge tips from WP branches, applies managed conflict resolution for Spec Kitty-owned files, and persists state so an interrupted merge can resume. After merge, done-state is reconciled from actual merged git ancestry.

**Why this priority**: The current merge depends on checked-out branch state, causing target-branch/worktree collisions. A dedicated workspace makes merge deterministic and resumable.

**Independent Test**: Start a merge for a feature with 3 WPs. Interrupt it after WP01 merges. Resume and verify WP02/WP03 merge without re-processing WP01. Verify the main repo's checked-out branch was never changed.

**Acceptance Scenarios**:

1. **Given** a feature with 3 completed WPs, **When** the user runs `spec-kitty merge --feature 057-canonical-context-architecture-cleanup`, **Then** a dedicated merge workspace is created, WPs are merged in dependency order, and the user's main repo checkout is untouched.
2. **Given** a merge interrupted after WP01, **When** the user runs `spec-kitty merge --resume`, **Then** the merge continues from WP02 using persisted merge state.
3. **Given** Spec Kitty-owned files (status artifacts, generated manifests) conflict during merge, **When** the merge engine encounters these, **Then** managed conflict resolvers handle them automatically without manual intervention.

---

### User Story 5 - Agent Shims Pass Through to CLI (Priority: P2)

A contributor using Claude Code (or any of the 12 supported agents) invokes `/spec-kitty.implement WP03`. The agent-specific command file is a thin shim that passes the raw arguments to `spec-kitty agent workflow implement --context <token>`. No workflow logic, recovery instructions, or argument parsing happens in the markdown command file. All behavior lives in the CLI. Internal-only skills are excluded from consumer installs via an allowlist in the packaged registry.

**Why this priority**: Copied prompt logic causes argument-semantic drift, stale prompts, and skill drift across 12 agent directories. Thin shims eliminate this entire class of maintenance burden.

**Independent Test**: Inspect a generated agent command file. Verify it contains only a CLI passthrough call with context argument forwarding. Verify no conditional logic, recovery instructions, or workflow state management is present in the file.

**Acceptance Scenarios**:

1. **Given** a project with Claude Code configured, **When** the user runs `spec-kitty upgrade`, **Then** `.claude/commands/spec-kitty.implement.md` contains only a thin passthrough to the CLI with `--context` support.
2. **Given** a project with all 12 agents configured, **When** the user inspects any agent command file, **Then** all files follow the same thin-shim pattern with no duplicated workflow logic.
3. **Given** the packaged skill registry, **When** a consumer project installs spec-kitty, **Then** internal-only skills are excluded based on the registry allowlist.

---

### User Story 6 - Legacy Project Migrates to New Architecture (Priority: P1)

A maintainer with an existing Spec Kitty project runs any CLI command. The CLI detects that the project has not been migrated and refuses to operate, directing the user to run `spec-kitty upgrade`. The upgrade performs a one-shot migration: backfills immutable IDs (project_uuid, mission_id, stable wp_id), infers execution_mode and owned_files from existing artifacts, rebuilds canonical event log state from legacy frontmatter/status files, removes mutable status fields from frontmatter, and rewrites agent command files as thin shims.

**Why this priority**: Without migration, no existing project can use the new architecture. The migration is a first-class deliverable, not incidental tooling.

**Independent Test**: Take a legacy 2.1.x project with multiple features in various states. Run `spec-kitty upgrade`. Verify all immutable IDs are assigned, mutable frontmatter fields are removed, the event log is canonical, and all commands work against the new model.

**Acceptance Scenarios**:

1. **Given** a legacy project (pre-057), **When** a user runs any spec-kitty command, **Then** the CLI prints "Project requires migration. Run `spec-kitty upgrade` to continue." and exits with a non-zero code.
2. **Given** a legacy project, **When** the user runs `spec-kitty upgrade`, **Then** every feature gets a `project_uuid`, every WP gets a stable `wp_id` and inferred `execution_mode`/`owned_files`, and the canonical event log is rebuilt from legacy state.
3. **Given** a migrated project, **When** the user inspects WP frontmatter, **Then** no mutable status fields (lane, review_status, reviewed_by, progress) remain. Only static metadata is present.
4. **Given** a legacy project with features in mid-flight (some WPs done, some in progress), **When** the migration runs, **Then** the event log faithfully represents the pre-migration state and no status information is lost.

---

### Edge Cases

- What happens when a legacy project has corrupted or conflicting status across frontmatter and status.json? The migration should use a deterministic precedence order (event log > status.json > frontmatter) and log warnings for conflicts.
- What happens when a context token references a WP that has been deleted or renumbered? The command should fail with a clear error referencing the stale token.
- What happens when a planning-artifact WP's owned_files overlap with another WP's owned_files? Task finalization should reject overlapping ownership with an explicit validation error.
- What happens when a merge workspace already exists from a previous interrupted merge of a different feature? The merge engine should detect the stale workspace, offer to clean it up, and refuse to proceed until resolved.
- What happens when the upgrade gate detects a project schema version newer than the running CLI? The CLI should refuse to operate and instruct the user to upgrade the CLI, not the project.
- What happens when a thin shim is invoked but no context token exists? The shim should instruct the agent to run context resolution first, not silently fall back to heuristic resolution.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | MissionContext object | As an agent, I want a persisted context object with immutable IDs (project_uuid, mission_id, work_package_id, wp_code, feature_slug, target_branch, authoritative_repo, authoritative_ref (optional for planning_artifact WPs), owned_files, execution_mode, dependency_mode) so that every workflow command operates on bound identity without re-resolution. | High | Open |
| FR-002 | Context token CLI interface | As an agent, I want every workflow command to accept `--context <token>` so that I never trigger heuristic slug/branch/WP resolution after initial binding. | High | Open |
| FR-003 | Fail-fast on missing context | As an agent, I want commands to fail immediately with an actionable error when invoked without sufficient context rather than falling back to heuristic resolution. | High | Open |
| FR-004 | WP execution_mode declaration | As a project maintainer, I want each WP to declare `execution_mode` (code_change or planning_artifact) at task-finalization time so that the system uses the correct workspace strategy. | High | Open |
| FR-005 | WP owned_files manifest | As a project maintainer, I want each WP to declare `owned_files` and `authoritative_surface` at task-finalization time so that file ownership is explicit and enforceable. | High | Open |
| FR-006 | Planning-artifact workspace | As a contributor, I want planning-artifact WPs to work directly on the planning surface or a dedicated planning worktree without sparse checkout so that kitty-specs files are always visible and editable. | High | Open |
| FR-007 | Remove sparse checkout from critical path | As a contributor, I want sparse checkout removed as a policy boundary so that file visibility is determined by the owned_files manifest, not checkout configuration. | High | Open |
| FR-008 | Canonical event log authority | As a maintainer, I want the status event log to be the sole authority for mutable WP state so that no other file is consulted for lane, progress, or review status. | High | Open |
| FR-009 | Remove mutable frontmatter fields | As a maintainer, I want mutable status fields (lane, review_status, reviewed_by, progress summaries) removed from WP frontmatter and tasks.md so that frontmatter contains only static metadata. | High | Open |
| FR-010 | Derived view regeneration | As a maintainer, I want status.json, board summaries, dossier snapshots, and cached manifests to be regenerated from the event log on demand and never treated as merge-critical inputs. | High | Open |
| FR-011 | Tracked vs derived boundary | As a project maintainer, I want the tracked/derived boundary to be explicit: tracked = human-authored mission/task artifacts + canonical event log; derived = status.json, board summaries, dossier snapshots, generated prompt surfaces, cached manifests. | High | Open |
| FR-012 | Dedicated merge workspace | As a maintainer, I want merge to operate in a dedicated workspace independent of the main repo's checked-out branch so that merge is deterministic and does not collide with active work. | Medium | Open |
| FR-013 | Resumable merge state machine | As a maintainer, I want merge state persisted so that an interrupted merge can resume from where it stopped without re-processing completed WPs. | Medium | Open |
| FR-014 | Managed conflict resolution | As a maintainer, I want Spec Kitty-owned files (status artifacts, generated manifests) to be auto-resolved during merge so that only human-authored conflicts require manual intervention. | Medium | Open |
| FR-015 | Merge-complete reconciliation | As a maintainer, I want done-state reconciled from actual merged git ancestry after merge completes so that the event log reflects reality. | Medium | Open |
| FR-016 | Thin agent shims | As a contributor using any of the 12 supported agents, I want agent command files to be thin CLI passthroughs that forward raw arguments to spec-kitty with `--context` so that no workflow logic is duplicated in agent directories. | Medium | Open |
| FR-017 | Internal skill allowlist | As a project maintainer, I want internal-only skills excluded from consumer installs via an explicit allowlist in the packaged registry so that end users do not see development-only capabilities. | Medium | Open |
| FR-018 | One-shot migration | As a maintainer of an existing project, I want a single `spec-kitty upgrade` command that backfills immutable IDs, infers execution_mode and owned_files, rebuilds canonical state from legacy artifacts, removes mutable frontmatter fields, and rewrites agent shims. | High | Open |
| FR-019 | Upgrade gate | As a maintainer, I want the CLI to refuse to operate on unmigrated projects and direct me to run `spec-kitty upgrade` so that there is no mixed-mode execution. | High | Open |
| FR-020 | Schema-version compatibility | As a maintainer, I want the upgrade gate based on project schema/capability version rather than exact CLI patch version so that version deadlocks are avoided. | High | Open |
| FR-021 | Immutable identity fields | As a maintainer, I want project_uuid, mission_id, and stable wp_id assigned as immutable identity so that lexical slug collisions are resolved and identity is never ambiguous. | High | Open |
| FR-022 | Weighted progress from canonical model | As a maintainer, I want weighted progress computed from the canonical lane model in one shared library usable by both CLI and future SaaS consumers so that progress calculation has a single implementation. | Medium | Open |
| FR-023 | Canonical machine-readable outputs | As a SaaS consumer (future), I want stable canonical machine-readable outputs and schemas exposed by the CLI so that SaaS can adopt the new state model without Spec Kitty changes. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Migration speed | One-shot migration completes in under 30 seconds for a project with up to 20 features and 200 WPs. | Performance | High | Open |
| NFR-002 | Migration safety | Migration is atomic: if any step fails, the project is left in its pre-migration state with no partial writes. | Reliability | High | Open |
| NFR-003 | Context resolution speed | MissionContext resolution and persistence completes in under 500ms. | Performance | Medium | Open |
| NFR-004 | Test coverage | All new code achieves 90%+ test coverage with pytest. All public interfaces pass mypy --strict. | Quality | High | Open |
| NFR-005 | Merge determinism | Given the same set of WP branches and event log, the merge engine produces identical results regardless of the main repo's checked-out branch or filesystem state. | Reliability | High | Open |
| NFR-006 | Backward deletion | The cleanup removes at least the following: branch/slug heuristic detection, sparse-checkout policy enforcement, frontmatter multi-authority logic, move-task contamination heuristics, prompt-specific recovery instructions, git-noise filtering for generated artifacts, agent-template drift from copied commands. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Big-bang release | All five architectural moves ship as one coordinated release. No intermediate compatibility shims between moves. | Process | High | Open |
| C-002 | No SaaS changes | SaaS persistence, Django views, and SaaS rollout timing are out of scope. The CLI produces canonical outputs; SaaS adopts them independently. | Scope | High | Open |
| C-003 | Fail-fast on unmigrated | The CLI must refuse to operate on unmigrated projects. No dual-authority or mixed-mode execution after release. | Technical | High | Open |
| C-004 | No dual-authority state | After migration, no runtime path may consult both the event log and frontmatter/status.json for mutable state. The event log is the sole authority. | Technical | High | Open |
| C-005 | Schema version gate | The upgrade gate must use project schema/capability version, not exact CLI patch version. | Technical | High | Open |
| C-006 | Legacy as migration input only | Old slug/branch/env heuristics and legacy state files may exist only as migration inputs, not as first-class runtime behavior. | Technical | High | Open |
| C-007 | Agent shim generation continues | Thin shim command files are still generated into agent directories. The change is removing workflow logic from them, not removing the files. | Technical | Medium | Open |
| C-008 | Python 3.11+ | All code targets Python 3.11+ using typer, rich, ruamel.yaml, pytest, mypy (strict). | Technical | High | Open |

### Key Entities

- **MissionContext**: Persisted bound-identity object containing project_uuid, mission_id, wp_id, feature_slug (display alias), target_branch, authoritative_repo, authoritative_ref, owned_files, execution_mode, dependency_mode, and completion_commands. Created by context resolution, consumed by all workflow commands via token reference.

- **WP Ownership Manifest**: Per-WP declaration of execution_mode (code_change | planning_artifact), owned_files (glob patterns), and authoritative_surface (path to the canonical location for this WP's artifacts). Set at task-finalization time. Stored as static WP frontmatter.

- **Canonical Event Log**: Append-only JSONL file (`status.events.jsonl`) per feature. Sole authority for mutable state (lane transitions, review status, progress). All other status representations are derived from this log.

- **Schema Version**: Project capability version stored in project metadata. Used by the upgrade gate to determine compatibility. Based on schema capabilities, not CLI patch version.

- **Merge State**: Persisted JSON state for resumable merge operations. Tracks feature, WP order, completed WPs, current WP, conflict status, and strategy. Lives in a dedicated merge workspace, not the main repo.

- **Agent Shim**: Thin runtime-specific wrapper file installed into agent command directories. Contains only a CLI passthrough call with context forwarding. No workflow logic, recovery instructions, or argument parsing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent can complete a full WP lifecycle (implement through merge) using only the `--context <token>` interface, with zero heuristic resolution calls triggered.
- **SC-002**: WP frontmatter across all features contains zero mutable status fields after migration. All mutable state is served exclusively from the event log.
- **SC-003**: Planning-artifact WPs complete without any sparse-checkout-related failures or file-visibility issues.
- **SC-004**: The merge engine produces identical results regardless of the main repo's checked-out branch, verified by running the same merge from different checkout states.
- **SC-005**: The one-shot migration successfully converts a legacy project with at least 10 features in mixed states (planned, in-progress, done) with zero status information loss, verified by comparing pre-migration board state to post-migration event-log-derived state.
- **SC-006**: Agent command files across all 12 agent directories contain no workflow logic — only CLI passthrough calls — verified by automated content inspection.
- **SC-007**: The following code paths are deleted or radically simplified after the release: branch/slug heuristic feature detection, sparse-checkout policy enforcement, frontmatter/status/task-board multi-authority logic, move-task contamination heuristics, prompt-specific recovery instructions, git-noise filtering for generated artifacts.
- **SC-008**: The new canonical state model exposes stable machine-readable JSON schemas documented for future SaaS consumption.
