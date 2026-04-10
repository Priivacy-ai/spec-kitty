# Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Status**: Draft
**Created**: 2026-04-10

## Problem Statement

Spec Kitty's codebase, documentation, CLI help text, and SaaS contract surfaces currently use "project," "repository," and "build" interchangeably. This conflation creates three concrete problems:

1. **User confusion**: A contributor reading CLI help or documentation cannot tell whether "project" refers to the local Git checkout, the SaaS collaboration surface, or an external tracker workspace (Jira project, Linear team). Onboarding cost increases every time someone has to ask "which project do you mean?"

2. **Contract ambiguity**: The SaaS payload structure sends `project_identity` bundles that actually contain repository-scoped and build-scoped values (`repo_slug`, `build_id`). If the SaaS later supports multi-repository projects, the current naming will actively mislead both human readers and automated consumers about what boundary each identifier represents.

3. **Internal inconsistency**: Core path-resolution functions use `project_root` and `locate_project_root()` to find the Git repository root, while other modules correctly use `repo_root`. The same concept has two names depending on which file you happen to be reading.

This mission defines the canonical terminology contract and catalogs representative drift so that subsequent planning and implementation missions can systematically converge all surfaces onto a single, unambiguous vocabulary.

## Actors

- **Spec Kitty contributor**: Reads and writes code, documentation, and CLI commands. Needs unambiguous terminology to understand what each identifier refers to.
- **Spec Kitty end user**: Runs CLI commands, reads help text, configures `.kittify/` settings. Needs consistent language across every surface they touch.
- **SaaS consumer**: Receives and processes payloads from Spec Kitty CLI. Needs stable, well-named contract fields to build correct multi-repo project support in the future.
- **External tracker integration**: Jira, Linear, GitHub Issues. Uses "project" in its own domain-specific way; Spec Kitty must disambiguate its own "project" from the tracker's "project."

## Canonical Terminology Definitions

### Project

The **collaboration surface**. A project is the SaaS-side entity that groups one or more repositories under a shared identity for collaboration, visibility, and governance. A project may span multiple repositories. A project exists independent of any single Git checkout.

- **Identity**: `project_uuid`
- **Scope**: SaaS-level; survives repository deletion, recloning, or worktree creation
- **Current state**: Not yet fully modeled in the SaaS; the term is used prematurely in CLI and config surfaces to mean "repository"

### Repository

The **local Git resource** that holds mission artifacts, source code, and `.kittify/` configuration. A repository is always a single Git repository (one `.git` directory). Multiple checkouts (worktrees) of the same repository share the same repository identity.

- **Identity**: `repo_slug` (human-readable, derived from Git remote or directory name)
- **Scope**: Git-level; one per `.git` directory; shared across all worktrees of that repository
- **Current state**: Correctly named in some modules (`repo_root`, `repo_slug`) but aliased to "project" in many others

### Build

One **checkout or worktree** of one repository. Each build has its own working tree, its own `.kittify/` state snapshot, and its own execution context. Builds are ephemeral relative to the repository they belong to.

- **Identity**: `build_id` (unique per checkout/worktree instance)
- **Scope**: Worktree-level; created and destroyed as lanes are opened and closed
- **Current state**: Correctly named as `build_id` in sync payloads; not conflated with other terms

## Terminology Invariants

These invariants must remain true for all user-facing and contract-facing surfaces:

1. **"Project" never means "repository."** Any surface that refers to the local Git resource must use "repository" (or "repo" in informal/variable contexts). "Project" is reserved exclusively for the SaaS collaboration surface.

2. **"Repository" never means "checkout."** The repository is the `.git`-level resource. A specific checkout or worktree is a "build." Functions that resolve a working directory path are resolving the build's location within a repository, not the repository itself.

3. **`project_uuid` is a collaboration identity, not a repository identity.** When sent to the SaaS, `project_uuid` identifies which collaboration surface this repository belongs to. It is not a per-repo unique key (multiple repos can share one `project_uuid` once multi-repo support exists).

4. **`repo_slug` is a repository identity.** It identifies which Git repository is active. It is derived from the Git remote or directory name and is stable across worktrees of the same repository.

5. **`build_id` is a checkout/worktree identity.** It identifies which specific working tree is executing. It is unique per worktree and is always sent explicitly in SaaS payloads so the server can distinguish parallel builds from the same repository.

6. **Local-first execution is repository-native.** All CLI operations execute against a repository and build. The SaaS project layer is an optional collaboration overlay; no CLI operation requires a project to exist. Repository-native, local-first execution must remain fully functional without SaaS connectivity.

7. **Tracker "project" is a third concept.** When integrating with Jira, Linear, or GitHub Issues, their "project" is neither Spec Kitty's project nor Spec Kitty's repository. References to tracker workspaces must be explicitly qualified (e.g., "tracker project," "Jira project," or a domain-specific term like "tracker workspace").

## Representative Drift Catalog

The following examples are representative, not exhaustive. They establish the pattern of conflation that exists today across six categories. Full inventory is deferred to the planning phase.

### Category 1: CLI Help Text

CLI help strings teach users that "project" means their local Git checkout.

| Surface | Current Text | Drift |
|---------|-------------|-------|
| `src/specify_cli/__init__.py` (app description) | "Setup tool for Spec Kitty spec-driven development **projects**" | "projects" means repositories |
| `src/specify_cli/cli/commands/init.py` (`--name` help) | "Name for your new **project** directory" | Naming a repository directory, not a SaaS project |
| `src/specify_cli/cli/commands/repair.py` (`--project-path`) | "Path to **project** to repair" | Points to a Git repository root |
| `src/specify_cli/cli/commands/init.py` (success message) | "Go to the **project** folder: cd {project_name}" | Instructing user to cd into a repository |

### Category 2: Core Path Resolution

Functions named `project_*` that locate Git repository roots.

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/core/paths.py` | `locate_project_root()` | Finds `.git` and `.kittify` markers; this is repository root resolution |
| `src/specify_cli/cli/commands/research.py` | `get_project_root_or_exit()` | Receives and returns repository root |
| Various CLI commands | `project_root = ...` variable | Holds repository root path |

### Category 3: Identity Structures

Classes and config keys that name repository-scoped identifiers as "project."

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/sync/project_identity.py` | `class ProjectIdentity` | Contains `repo_slug` and `build_id` alongside `project_uuid`; the class itself is repository-scoped identity |
| `src/specify_cli/sync/project_identity.py` | `project_uuid` docstring: "unique per project" | Actually unique per repository checkout |
| `src/specify_cli/migration/backfill_identity.py` | `backfill_project_uuid()` | Writes a repository-scoped UUID, not a SaaS project UUID |
| `.kittify/config.yaml` | `project:` section with `uuid`, `slug`, `build_id` | Section name implies SaaS project; contents are repository/build identity |

### Category 4: SaaS Payload Naming

Payloads sent to the SaaS that bundle repository and build identity under a "project" label.

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/tracker/saas_client.py` (`bind_resolve`) | `project_identity` parameter | Payload contains `repo_slug` and `build_id`, which are repository/build-scoped |
| `src/specify_cli/tracker/saas_client.py` (routing) | `project_slug` parameter | Used for external tracker routing, conflating SaaS project with tracker workspace |

### Category 5: Documentation

Docs that use "project" and "repository" interchangeably.

| Surface | Current Text | Drift |
|---------|-------------|-------|
| `docs/reference/file-structure.md` | "Project Root Overview" heading, `my-project/` example | Describes a Git repository structure |
| Command templates (specify, implement, etc.) | "project root checkout" | Means repository root checkout |

### Category 6: Tracker Integration

External tracker "project" conflated with Spec Kitty's own "project."

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/tracker/origin.py` | `project_slug = tracker_config.project_slug` | Routes to Jira/Linear workspace; three-way conflation with SaaS project and repository |

## User Scenarios and Testing

### Scenario 1: New User Reads CLI Help

A new user runs `spec-kitty --help` and `spec-kitty init --help`. Every occurrence of "project" in the output should refer to the SaaS collaboration surface. If the help text means "repository," it says "repository." The user can correctly answer: "What is a project in Spec Kitty?" without ambiguity.

**Acceptance**: All CLI `--help` output uses canonical terminology. No help string uses "project" to mean repository or build.

### Scenario 2: Contributor Reads Identity Code

A contributor opens `project_identity.py` and can immediately tell which identifier is project-scoped, which is repository-scoped, and which is build-scoped. Class names, field names, and docstrings use canonical terms.

**Acceptance**: Identity-bearing classes and fields are named according to the canonical definitions. `ProjectIdentity` is renamed or restructured so that repository-scoped fields are not grouped under a "project" label.

### Scenario 3: SaaS Consumer Parses Payload

A SaaS service receives a sync payload and can distinguish the collaboration project from the repository from the build by reading field names alone. No field requires out-of-band knowledge to interpret.

**Acceptance**: SaaS payloads use `project_uuid` for the collaboration surface, `repo_slug` for the repository, and `build_id` for the build. No field named `project_*` carries repository-scoped or build-scoped data.

### Scenario 4: Multi-Repo Project (Future Readiness)

When the SaaS later supports multi-repository projects, no local CLI behavior changes. A user can bind two repositories to one project. Each repository retains its own `repo_slug` and generates its own `build_id` per worktree. The `project_uuid` is shared across both repositories.

**Acceptance**: The terminology contract supports this scenario without renaming. Local-first execution in each repository is unaffected by the shared project identity.

### Scenario 5: Tracker Integration Clarity

A user configures a Jira integration. The Jira "project" (e.g., "INGEST") is clearly distinguished from the Spec Kitty project and the Spec Kitty repository. Config keys and CLI output never say just "project" when they mean the tracker workspace.

**Acceptance**: All tracker-facing surfaces qualify their references (e.g., "tracker project" or use the tracker's own terminology like "Jira project key").

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | All CLI `--help` text must use "repository" when referring to the local Git resource and "project" only when referring to the SaaS collaboration surface | Proposed |
| FR-002 | All user-facing documentation must follow the canonical terminology definitions for project, repository, and build | Proposed |
| FR-003 | Identity-bearing code structures (classes, fields, config keys) must name identifiers according to their actual scope: `project_*` for collaboration-scoped, `repo_*` for repository-scoped, `build_*` for build-scoped | Proposed |
| FR-004 | SaaS contract payloads must use canonical field names that unambiguously indicate scope: `project_uuid` for the collaboration surface, `repo_slug` for the repository, `build_id` for the build | Proposed |
| FR-005 | Tracker integration surfaces must qualify "project" references to distinguish the tracker workspace from the Spec Kitty project (e.g., "tracker project," "Jira project key") | Proposed |
| FR-006 | The `.kittify/config.yaml` identity section must use canonical naming that reflects the actual scope of each identifier | Proposed |
| FR-007 | Core path-resolution functions must be named to reflect that they resolve repository roots, not project roots (e.g., `locate_repository_root` instead of `locate_project_root`) | Proposed |
| FR-008 | A canonical glossary entry for each of the three terms (project, repository, build) must be maintained and referenced from developer documentation | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | Terminology convergence must not break existing SaaS API consumers | Zero breaking payload changes without a versioned migration path | Proposed |
| NFR-002 | All renamed CLI flags and config keys must include a deprecation period with clear migration guidance | Minimum one minor release cycle with deprecation warnings before removal | Proposed |
| NFR-003 | Local-first CLI operations must remain fully functional without SaaS connectivity after terminology changes | 100% of offline-capable commands continue to work identically | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | This mission defines the terminology contract only; it does not plan or execute documentation rewrites, command renames, code migrations, or SaaS schema changes | Active |
| C-002 | The canonical definitions must be forward-compatible with multi-repository project support in the SaaS, even though that feature does not exist yet | Active |
| C-003 | `build_id` naming and semantics must not change; it is already correctly scoped and named | Active |
| C-004 | Existing `project_uuid` values stored in `.kittify/` must remain valid after any rename; migration must preserve data, not regenerate identifiers | Active |

## Success Criteria

1. A contributor can read the canonical glossary and correctly classify any identifier in the codebase as project-scoped, repository-scoped, or build-scoped without consulting the original author.
2. All user-facing terminology surfaces (CLI help, documentation, config key descriptions) converge on the canonical definitions within the scope of the implementation missions that follow this specification.
3. SaaS payload field names are unambiguous: a consumer can determine the scope of any field from its name alone, without reading external documentation.
4. Local-first, repository-native execution is unchanged: no CLI command requires a SaaS project to exist in order to function.
5. The terminology contract supports binding multiple repositories to one project without requiring any further rename.

## Explicit Non-Goals (v1)

- **Exhaustive drift audit**: The representative catalog in this spec establishes the pattern. A comprehensive inventory of every affected string, field, and help text is a planning activity.
- **Code migration execution**: Renaming functions, classes, config keys, and CLI flags is implementation work, not specification work.
- **Documentation rewrite**: Updating all prose in `docs/` to use canonical terms is implementation work.
- **SaaS schema migration**: Changing server-side field names or API contracts is out of scope for this mission.
- **Deprecation timeline**: Specific version numbers and deprecation schedules are planning decisions.

## Assumptions

1. The SaaS will eventually support multi-repository projects, and the terminology contract should be designed to accommodate that without further renaming.
2. `project_uuid` as a concept (a collaboration-level identifier) is correct; the problem is that it is currently generated per-repository and described as repository-scoped, not that the identifier itself is wrong.
3. `build_id` is already correctly named and scoped; no changes are needed to its definition or usage.
4. External tracker integrations will continue to use their own "project" terminology (Jira project, Linear team); Spec Kitty must disambiguate without forcing trackers to change their vocabulary.

## Dependencies

- The glossary system (mission 047+) can host the canonical definitions once they are ratified.
- SaaS API versioning capabilities are needed before any payload field renames can be deployed; this is a constraint on implementation, not on this specification.

## Key Entities

| Entity | Canonical Term | Identity Field | Scope |
|--------|---------------|----------------|-------|
| Collaboration surface | Project | `project_uuid` | SaaS-level; spans repositories |
| Git resource | Repository | `repo_slug` | Git-level; one per `.git` directory |
| Checkout/worktree | Build | `build_id` | Worktree-level; ephemeral |
| External tracker workspace | Tracker project (qualified) | `tracker_project_slug` or domain-specific key | External system; not owned by Spec Kitty |
