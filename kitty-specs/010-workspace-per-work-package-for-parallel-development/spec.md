# Feature Specification: Workspace-per-Work-Package for Parallel Development

**Feature Branch**: `010-workspace-per-work-package-for-parallel-development`
**Created**: 2026-01-07
**Status**: Draft
**Input**: User description: "Create a new Feature based on the work(space/tree) per WP concept."

## Executive Summary

Transform Spec Kitty's workspace model from "one worktree per feature" to "one worktree per work package" to enable multiple AI agents to work on non-interdependent work packages simultaneously. This architectural change allows Agent A to implement WP01 while Agent B implements WP03 in parallel, each in isolated worktrees, without conflicts or coordination overhead.

**Core Value Proposition**: Enable parallel multi-agent development within a single feature, dramatically reducing time-to-completion for features with multiple independent work packages.

## User Scenarios & Testing

### User Story 1 - Parallel Multi-Agent Development (Priority: P1)

**User Journey**: Multiple AI agents work on different non-interdependent work packages of the same feature simultaneously, each in isolated worktrees.

**Why this priority**: This is the foundational capability - the entire reason for this architectural change. Without parallel development, the feature provides no value.

**Independent Test**: Create a feature with 3 non-interdependent WPs, assign to 3 different agents, verify all 3 can work simultaneously without conflicts or manual coordination.

**Acceptance Scenarios**:

1. **Given** a feature with WP01, WP02, WP03 (no dependencies between them), **When** Agent A runs `spec-kitty implement WP01`, Agent B runs `spec-kitty implement WP02`, and Agent C runs `spec-kitty implement WP03` simultaneously, **Then** three separate worktrees are created (`.worktrees/010-feature-WP01/`, `.worktrees/010-feature-WP02/`, `.worktrees/010-feature-WP03/`), each with isolated working directories, and agents can commit changes without conflicts.

2. **Given** Agent A is implementing WP01 in `.worktrees/010-feature-WP01/`, **When** Agent B starts implementing WP02, **Then** Agent B's workspace (`.worktrees/010-feature-WP02/`) does not contain Agent A's uncommitted changes, ensuring complete isolation.

3. **Given** three agents working on WP01, WP02, WP03 in parallel, **When** Agent A completes WP01 and commits, **Then** Agent B and Agent C continue working uninterrupted in their respective workspaces, with no merge conflicts or coordination required.

4. **Given** a feature with both dependent and independent WPs (WP01, WP02 depends on WP01, WP03 independent), **When** Agent A implements WP01 and Agent C implements WP03 simultaneously, **Then** both agents work in parallel without interference, while WP02 waits for WP01 completion.

---

### User Story 2 - Dependency-Aware Workspace Creation (Priority: P1)

**User Journey**: An agent implements a work package that depends on another work package, and the system automatically creates the workspace branching from the correct base.

**Why this priority**: Foundational for correctness - without proper dependency handling, dependent WPs would be missing prerequisite code, leading to broken implementations.

**Independent Test**: Create WP01, implement it, then implement WP02 (depends on WP01) and verify WP02's workspace contains WP01's code changes.

**Acceptance Scenarios**:

1. **Given** WP01 has no dependencies, **When** an agent runs `spec-kitty implement WP01`, **Then** workspace `.worktrees/010-feature-WP01/` is created branching from `main`, containing planning artifacts (spec.md, plan.md, tasks/*.md) but no WP-specific code changes.

2. **Given** WP02 depends on WP01, and WP01's workspace exists, **When** an agent runs `spec-kitty implement WP02 --base WP01`, **Then** workspace `.worktrees/010-feature-WP02/` is created branching from branch `010-feature-WP01`, containing both planning artifacts AND WP01's code changes.

3. **Given** WP02 depends on WP01, but WP01's workspace does not exist, **When** an agent runs `spec-kitty implement WP02 --base WP01`, **Then** the command fails with error "Base workspace WP01 does not exist. Implement WP01 first", preventing creation of WP02's workspace.

4. **Given** WP02, WP03, WP04 all depend on WP01, **When** WP01 is completed and then agents run `spec-kitty implement WP02 --base WP01`, `spec-kitty implement WP03 --base WP01`, `spec-kitty implement WP04 --base WP01` simultaneously, **Then** three workspaces are created in parallel, all branching from WP01's branch, and all three agents work simultaneously.

---

### User Story 3 - Planning Artifacts in Main Repository (Priority: P1)

**User Journey**: A user creates a feature specification, plan, and tasks without creating any worktrees, committing planning artifacts directly to the main repository.

**Why this priority**: Changes the fundamental workflow - planning must happen in main so WP workspaces can branch from a common base containing the planning artifacts.

**Independent Test**: Run `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks` and verify no worktrees created, all artifacts committed to main branch.

**Acceptance Scenarios**:

1. **Given** a user starts a new feature, **When** they run `/spec-kitty.specify`, **Then** `kitty-specs/010-feature/spec.md` is created directly in the main repository (no worktree), committed to the `main` branch, and no `.worktrees/010-feature/` directory exists.

2. **Given** spec.md exists in main, **When** user runs `/spec-kitty.plan`, **Then** `kitty-specs/010-feature/plan.md` is created in main repository, committed to `main` branch, and still no worktrees exist.

3. **Given** spec.md and plan.md exist in main, **When** user runs `/spec-kitty.tasks`, **Then** `kitty-specs/010-feature/tasks/WP01.md`, `WP02.md`, `WP03.md` are created in main repository, committed to `main` branch, each WP prompt file contains the correct `spec-kitty implement WP## [--base WP##]` command, and still no worktrees exist.

4. **Given** planning artifacts (spec, plan, tasks) are in main, **When** an agent implements any WP, **Then** the WP's workspace branches from main and contains all planning artifacts, enabling the agent to reference spec/plan/tasks during implementation.

---

### User Story 4 - WP Prompt Self-Documentation (Priority: P2)

**User Journey**: Work package prompt files automatically contain the correct implementation command with proper `--base` flag, preventing agents from accidentally branching from wrong base.

**Why this priority**: Important for correctness and developer experience, but secondary to core parallel development capability.

**Independent Test**: Generate tasks for a feature with dependencies, verify WP prompt files contain correct commands.

**Acceptance Scenarios**:

1. **Given** WP01 has no dependencies, **When** `/spec-kitty.tasks` generates `WP01.md`, **Then** the file contains implementation command `spec-kitty implement WP01` (no --base flag).

2. **Given** WP02 depends on WP01, **When** `/spec-kitty.tasks` generates `WP02.md`, **Then** the file contains implementation command `spec-kitty implement WP02 --base WP01`, making the dependency explicit.

3. **Given** an agent attempts to implement WP02 by running `spec-kitty implement WP02` (forgetting --base flag), **When** WP02 has dependencies declared in tasks.md, **Then** the command fails with error "WP02 has dependencies. Use: spec-kitty implement WP02 --base WP01", guiding the agent to the correct command.

4. **Given** WP02, WP03, WP04 all depend on WP01, **When** tasks are generated, **Then** all three WP prompt files contain `--base WP01` flag, ensuring consistent dependency specification.

---

### User Story 5 - Backward Compatibility with Legacy Worktrees (Priority: P2)

**User Journey**: Existing features created before this change (single worktree per feature) continue to function without migration, while new features use the new workspace-per-WP model.

**Why this priority**: Critical for adoption - users won't accept breaking changes to in-progress work. However, secondary to delivering new capability.

**Independent Test**: Have an existing feature (008-unified-python-cli) with legacy worktree, create a new feature (010-workspace-per-wp) with new model, verify both work correctly.

**Acceptance Scenarios**:

1. **Given** feature 008 exists with legacy worktree `.worktrees/008-unified-python-cli/` (single worktree), **When** a new feature 010 is created with workspace-per-WP model, **Then** both feature 008 (legacy) and feature 010 (new) coexist without conflicts, and tools (merge command, dashboard) handle both correctly.

2. **Given** a legacy worktree `.worktrees/008-feature/` with all WPs in `kitty-specs/008-feature/tasks/`, **When** an agent works on that feature, **Then** the system detects the legacy structure and continues to operate in legacy mode (no automatic conversion to workspace-per-WP).

3. **Given** dashboard displays feature list, **When** viewing projects with mixed legacy and new features, **Then** dashboard correctly detects and displays both structures: legacy shows single worktree, new shows multiple WP workspaces.

4. **Given** a user wants to understand the difference, **When** they inspect worktree directory, **Then** legacy features have `.worktrees/###-feature/` while new features have `.worktrees/###-feature-WP##/`, making the model difference visually clear.

---

### User Story 6 - Review Feedback Dependency Warning (Priority: P3)

**User Journey**: When a parent WP receives review feedback and changes while dependent WPs are in progress, agents are warned about the need for manual rebase.

**Why this priority**: Important for correctness in review cycles, but occurs less frequently than initial implementation. Lower priority as it's a git limitation (will be solved by jj in future).

**Independent Test**: Implement WP01 and WP02 (depends on WP01), request changes to WP01, verify agents receive warning about WP02 needing rebase.

**Acceptance Scenarios**:

1. **Given** WP02 workspace exists and depends on WP01, **When** WP01 moves to `for_review` lane, **Then** WP01's review prompt includes warning: "⚠️ WP02 depends on WP01. If changes are requested, WP02 will need manual rebase."

2. **Given** WP01 is in review and WP02 (dependent) is in `doing` lane, **When** WP01 moves back to `planned` (changes requested), **Then** the implementing agent for WP01 sees warning: "⚠️ WP02 is in progress and depends on WP01. After making changes, notify WP02's agent to rebase."

3. **Given** WP01 has been modified after WP02 started, **When** WP02's agent runs `spec-kitty implement WP02` (resuming work), **Then** a warning displays: "⚠️ WP01 (base) has changed. Consider rebasing: cd .worktrees/010-feature-WP02 && git rebase 010-feature-WP01"

4. **Given** multiple dependent WPs (WP02, WP03, WP04 all depend on WP01), **When** WP01 changes, **Then** all dependent WP agents receive rebase warnings, listing which WPs need attention.

---

### Edge Cases

#### Workspace Creation Failures

- **Worktree directory already exists**: What if `.worktrees/010-feature-WP01/` exists from a previous attempt?
  - **Resolution**: Check if it's a valid git worktree. If yes, reuse it. If no, error: "Directory exists but is not a valid worktree. Remove manually: rm -rf .worktrees/010-feature-WP01/"

- **Git worktree command fails**: What if `git worktree add` fails due to git errors (corrupt repo, permission issues)?
  - **Resolution**: Fail gracefully with original git error message and guidance: "Git worktree creation failed. Check repository health: git fsck"

#### Dependency Validation

- **Circular dependencies**: What if WP02 depends on WP03, WP03 depends on WP02?
  - **Resolution**: `/spec-kitty.tasks` detects circular dependencies during generation and errors: "Circular dependency detected: WP02 → WP03 → WP02. Fix tasks.md structure."

- **Missing dependency workspace**: What if user tries `spec-kitty implement WP03 --base WP02` but WP02 doesn't exist yet?
  - **Resolution**: Validate workspace exists before creation: "Base workspace WP02 does not exist. Implement WP02 first or use --base main if WP03 should branch from main."

- **Base workspace deleted mid-work**: What if WP01's workspace is deleted while WP02 is in progress?
  - **Resolution**: WP02's workspace still functions (it branched from WP01's branch, which still exists). Only issue is merging - handle at merge time.

#### Planning Artifact Workflow

- **No commit to main**: What if user runs `/spec-kitty.specify` but doesn't commit spec.md to main?
  - **Resolution**: Each planning command (specify, plan, tasks) automatically commits its artifacts to main with descriptive commit message: "Add spec for feature 010-workspace-per-wp"

- **Merge conflicts in main**: What if multiple features' planning artifacts conflict in main (both modify same file)?
  - **Resolution**: Standard git conflict resolution - user manually resolves conflicts in main before continuing.

#### Legacy vs New Model Detection

- **Ambiguous structure**: What if both `.worktrees/010-feature/` AND `.worktrees/010-feature-WP01/` exist?
  - **Resolution**: Prioritize new model - if any workspace-per-WP directories exist, treat as new model. Log warning: "Mixed worktree structure detected for feature 010. Recommend cleanup."

- **Dashboard WP location detection**: Where should dashboard look for WPs - main repo or worktrees?
  - **Resolution**: Dashboard always reads WP files from `kitty-specs/###-feature/tasks/` in main repo (planning artifacts), workspace structure is for implementation only.

## Requirements

### Functional Requirements

#### Planning Workflow Changes

- **FR-001**: System MUST create planning artifacts (spec.md, plan.md, tasks/*.md) directly in the main repository under `kitty-specs/###-feature/` without creating any worktrees.

- **FR-002**: System MUST automatically commit planning artifacts to the `main` branch after each planning command (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`) with descriptive commit messages.

- **FR-003**: System MUST NOT create a feature worktree during `/spec-kitty.specify`, `/spec-kitty.plan`, or `/spec-kitty.tasks` commands (breaking change from legacy behavior).

#### Workspace Creation and Management

- **FR-004**: System MUST create individual worktrees on-demand during `/spec-kitty.implement WP##` command, named `.worktrees/###-feature-WP##/` where ## is the work package number.

- **FR-005**: System MUST create git worktrees using `git worktree add .worktrees/###-feature-WP## -b ###-feature-WP##` for WPs with no dependencies (branching from main).

- **FR-006**: System MUST create git worktrees using `git worktree add .worktrees/###-feature-WP## -b ###-feature-WP## ###-feature-WPXX` for WPs with dependencies, where WPXX is the specified base WP.

- **FR-007**: System MUST accept a `--base WPXX` flag in the `spec-kitty implement` command to specify the dependency base for workspace creation.

- **FR-008**: System MUST validate that the specified base workspace exists (`.worktrees/###-feature-WPXX/`) before creating a dependent workspace, failing with clear error if missing.

#### Work Package Prompt Generation

- **FR-009**: System MUST generate WP prompt files (`WP##.md`) in `kitty-specs/###-feature/tasks/` during `/spec-kitty.tasks` command.

- **FR-010**: System MUST include the correct `spec-kitty implement WP##` command (no --base flag) in WP prompt files for WPs with no dependencies.

- **FR-011**: System MUST include the correct `spec-kitty implement WP## --base WPXX` command in WP prompt files for WPs with dependencies, where WPXX is determined from tasks.md dependency graph.

- **FR-012**: System MUST detect dependencies by parsing the dependency structure in tasks.md (tasks grouped by phase, subtask relationships, or explicit dependency markers).

#### Dependency Validation

- **FR-013**: System MUST detect circular dependencies during `/spec-kitty.tasks` generation and fail with error listing the circular dependency chain.

- **FR-014**: System MUST validate the `--base` flag matches a declared dependency in tasks.md, failing with error if attempting to base on an undeclared dependency.

- **FR-015**: System MUST provide a helpful error message when `--base` flag is missing but dependencies exist: "WP## has dependencies on WPXX. Use: spec-kitty implement WP## --base WPXX"

#### Review Feedback Warnings

- **FR-016**: System MUST display warnings in `/spec-kitty.review` prompts when reviewing a WP that has dependent WPs in progress (lanes: planned, doing), indicating manual rebase will be needed if changes are requested.

- **FR-017**: System MUST display warnings in `/spec-kitty.implement` prompts when resuming work on a WP whose base has been modified, suggesting manual rebase command.

- **FR-018**: Warnings MUST include the specific git rebase command to execute: `cd .worktrees/###-feature-WP## && git rebase ###-feature-WPXX`

#### Merge Workflow

- **FR-019**: System MUST maintain existing merge behavior: `spec-kitty merge ###-feature` merges ALL completed WPs as a single merge to main (no per-WP incremental merging in this version).

- **FR-020**: System MUST validate that ALL WP worktrees for a feature have been merged or cleaned up before allowing feature worktree removal.

- **FR-021**: System MUST document in merge command help text that workspace-per-WP features require merging entire feature (individual WP merging not yet supported).

#### Backward Compatibility

- **FR-022**: System MUST detect legacy worktrees (`.worktrees/###-feature/` without `-WP##` suffix) during upgrade to 0.11.0 and block the upgrade if any exist.

- **FR-023**: System MUST provide clear error message listing which legacy worktrees are blocking upgrade, with guidance on how to complete (merge) or delete them before upgrading.

- **FR-024**: Dashboard MUST correctly detect and display both legacy single-worktree features and new workspace-per-WP features without errors (design requirement - implementation not in this feature).

- **FR-025**: System MUST NOT automatically migrate legacy worktrees to workspace-per-WP model (non-retroactive change). Users must complete or delete legacy features before upgrading.

### Key Entities

- **Feature**: Represents a Spec Kitty feature with planning artifacts in main. Attributes: feature number, slug, spec.md path, plan.md path, tasks/*.md paths, associated WP worktrees.

- **Work Package (WP)**: Represents an independent unit of work within a feature. Attributes: WP ID (e.g., WP01), prompt file path, dependencies (list of WP IDs), worktree path (if implemented), branch name, lane status.

- **Worktree**: Represents a git worktree for a single work package. Attributes: directory path (`.worktrees/###-feature-WP##/`), branch name (`###-feature-WP##`), base branch (main or another WP branch), creation timestamp.

- **Dependency Graph**: Represents the relationships between work packages. Attributes: WP ID, depends on (list of WP IDs), dependents (list of WP IDs that depend on this WP).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Multiple agents can simultaneously implement non-interdependent WPs within a single feature, with each agent working in an isolated worktree without manual coordination.

- **SC-002**: Planning artifacts (spec.md, plan.md, tasks/*.md) are committed to main branch before any worktrees are created, verifiable by checking git history shows planning commits before implementation commits.

- **SC-003**: Dependent WPs automatically branch from correct base WP, verifiable by checking `git log --graph` shows WP02's commits branching from WP01's branch when `--base WP01` is used.

- **SC-004**: System prevents creating dependent WP workspace before base WP workspace exists, failing with clear error message 100% of the time when base is missing.

- **SC-005**: WP prompt files contain correct implementation commands with proper `--base` flags, verifiable by parsing all WP##.md files and validating commands match dependency graph.

- **SC-006**: Legacy worktrees (pre-0.11.x) and new workspace-per-WP worktrees coexist without conflicts, verifiable by having a project with features 001-008 (legacy) and 010+ (new) and confirming all tools work correctly.

- **SC-007**: Review feedback warnings appear when modifying WPs with dependent WPs in progress, verifiable by checking warning is displayed 100% of the time when condition is met.

- **SC-008**: Dashboard correctly detects and displays both legacy single-worktree and new workspace-per-WP structures without errors or misrepresentation (design requirement - implementation not in this feature).

- **SC-009**: Feature with 3 parallel WPs (WP01, WP02, WP03 with no interdependencies) can be completed by 3 agents in roughly 1/3 the time compared to sequential development (assuming equal WP complexity).

- **SC-010**: Circular dependency detection prevents invalid task structures, failing `/spec-kitty.tasks` generation 100% of the time when circular dependencies exist in tasks.md.

## Dependencies and Assumptions

### Dependencies

- **Git CLI**: Required for git worktree operations. Minimum version 2.5.0 (when git worktree was introduced).
- **Python 3.11+**: Existing Spec Kitty requirement.
- **Existing Git repository**: Feature assumes project is already a git repository initialized by Spec Kitty.

### Assumptions

- **Main branch as planning target**: Planning artifacts are committed to the `main` branch. Projects using different primary branch names (e.g., `master`, `develop`) will need configuration support (deferred to implementation).
- **Git worktree support**: The local git version supports worktree operations reliably.
- **Filesystem isolation**: Multiple worktrees in `.worktrees/` directory do not interfere with each other.
- **Linear dependency chains acceptable**: WPs can have dependencies forming a directed acyclic graph (DAG), but not arbitrary complex graphs. Most features have simple linear chains (WP02 depends on WP01) or fan-out patterns (WP02, WP03, WP04 all depend on WP01).
- **Agent coordination is external**: Agents coordinate which WP to work on through external means (conversation, task assignment). This feature only provides technical isolation, not workflow coordination.

## Open Questions

*None* - All critical decisions were resolved during discovery.

## Scope Boundaries

### In Scope

- Planning workflow changes (artifacts in main, no initial worktree)
- On-demand workspace creation during `spec-kitty implement`
- `--base` flag for dependency specification
- Validation that base workspace exists
- WP prompt self-documentation with correct commands
- Review feedback warnings for dependent WPs
- Backward compatibility with legacy worktrees
- Dashboard design considerations (not implementation)

### Out of Scope

- **Incremental WP-by-WP merging** - This version keeps existing "merge entire feature" behavior. Individual WP merging deferred to future version.
- **Dashboard implementation** - Design requirements defined, but dashboard code changes are a separate feature.
- **Automatic rebase on dependency changes** - Git limitation. Manual rebase required. Automatic rebase will come with jj integration (future feature).
- **Agent coordination/task assignment** - How agents decide which WP to work on is external to this feature.
- **Dependency graph visualization** - Tasks.md shows dependencies textually, but no graphical visualization.
- **Workspace cleanup automation** - Automatic deletion of merged worktrees deferred to future enhancement.
- **Parallel merge validation** - Validating multiple agents don't merge conflicting changes simultaneously is out of scope.

## Risk Assessment

### High Risk Items

1. **Breaking change to planning workflow** - Users accustomed to worktree creation during `/spec-kitty.specify` may be confused when no worktree appears.
   - **Mitigation**: Clear documentation, migration guide, updated slash command prompts explaining new workflow.

2. **Dependency detection accuracy** - Incorrect parsing of tasks.md dependencies could generate wrong `--base` flags in WP prompts.
   - **Mitigation**: Conservative dependency detection logic, validation during tasks generation, clear error messages for ambiguous structures.

### Medium Risk Items

1. **Review feedback rebase complexity** - Users may forget to rebase dependent WPs after parent WP changes, leading to outdated code.
   - **Mitigation**: Prominent warnings in review and implement prompts, document manual rebase commands clearly.

2. **Dashboard backward compatibility** - Dashboard must detect both legacy and new structures without breaking.
   - **Mitigation**: Explicit detection logic, feature flags for structure detection, comprehensive testing with mixed projects.

### Low Risk Items

1. **Git worktree command reliability** - Git worktree is a mature feature (since 2015) with stable behavior.
   - **Mitigation**: Existing `git_ops.py` functions already handle worktree operations, minimal new risk.

2. **Main branch commit overhead** - Committing planning artifacts to main adds 2-3 extra commits per feature.
   - **Mitigation**: Acceptable tradeoff for correct workspace-per-WP model. Commits are well-documented and meaningful.

## Assumptions and Constraints

### Technical Constraints

- **Git only**: This feature uses git worktree operations exclusively. jj workspace support is deferred to future VCS abstraction feature.
- **No concurrency control**: Multiple agents creating workspaces simultaneously could have race conditions. Acceptable risk as agents typically coordinate work assignment.
- **Filesystem-based coordination**: No distributed locking or coordination mechanism. Relies on filesystem and git's atomic operations.

### User Experience Constraints

- **Manual rebase required**: Git users must manually rebase dependent WPs when parent changes. Cannot be automated without jj.
- **No incremental merge**: Must merge entire feature at once. Per-WP merging requires more complex merge orchestration.
- **Learning curve**: Users must understand new workflow (planning in main, implement creates worktrees).

### Process Constraints

- **Backward compatibility mandatory**: Cannot break existing features (001-008) with legacy worktrees.
- **Dashboard design now, implement later**: Dashboard changes are separate feature, but requirements must be designed now to ensure feasibility.
