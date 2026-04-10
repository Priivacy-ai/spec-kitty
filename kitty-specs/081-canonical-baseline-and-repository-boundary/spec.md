# Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Status**: Draft
**Created**: 2026-04-10

## Problem Statement

Spec Kitty's codebase, documentation, CLI help text, and SaaS contract surfaces currently use "project," "repository," and "build" interchangeably. This conflation creates three concrete problems:

1. **User confusion**: A contributor reading CLI help or documentation cannot tell whether "project" refers to the local Git checkout, the SaaS collaboration surface, or an external tracker workspace (Jira project, Linear team). Onboarding cost increases every time someone has to ask "which project do you mean?"

2. **Contract ambiguity**: The SaaS payload structure sends `project_identity` bundles that actually contain repository-scoped and build-scoped values. If the SaaS later supports multi-repository projects, the current naming will actively mislead both human readers and automated consumers about what boundary each identifier represents.

3. **Identity mislabeling**: The locally minted UUID stored in `.kittify/config.yaml` as `project_uuid` is not a project identity at all. It is generated per repository checkout via `uuid4()` in `project_identity.py`, never assigned by the SaaS, and never shared across repositories. It is a de-facto repository identity wearing a project label. Similarly, `repo_slug` is presented as the repository identity but is actually an optional, mutable, user-provided override derived from git remotes or directory names.

4. **Internal inconsistency**: Core path-resolution functions use `project_root` and `locate_project_root()` to find the Git repository root, while other modules correctly use `repo_root`. The same concept has two names depending on which file you happen to be reading.

This mission defines the canonical terminology contract — including a corrected identity layer model — and catalogs representative drift so that subsequent planning and implementation missions can systematically converge all surfaces onto a single, unambiguous vocabulary.

## Actors

- **Spec Kitty contributor**: Reads and writes code, documentation, and CLI commands. Needs unambiguous terminology to understand what each identifier refers to.
- **Spec Kitty end user**: Runs CLI commands, reads help text, configures `.kittify/` settings. Needs consistent language across every surface they touch.
- **SaaS consumer**: Receives and processes payloads from Spec Kitty CLI. Needs stable, well-named contract fields to build correct multi-repo project support in the future.
- **External tracker integration**: Jira, Linear, GitHub Issues. Uses "project" in its own domain-specific way; Spec Kitty must disambiguate its own "project" from the tracker's "project."

## Canonical Terminology Definitions

### Project

The **collaboration surface**. A project is the SaaS-side entity that groups one or more repositories under a shared identity for collaboration, visibility, and governance. A project may span multiple repositories. A project exists independent of any single Git checkout.

- **Identity**: `project_uuid` (optional; absent until a SaaS binding is established)
- **Scope**: SaaS-level; assigned by the SaaS when a repository is bound to a collaboration project
- **Current state**: The field name `project_uuid` exists in `.kittify/config.yaml`, but the value stored there is actually a locally minted repository identity, not a SaaS-assigned collaboration identity. No SaaS binding mechanism exists yet.

### Repository

The **local Git resource** that holds mission artifacts, source code, and `.kittify/` configuration. A repository is always a single Git repository (one `.git` directory). Multiple checkouts (worktrees) of the same repository share the same repository identity.

- **Identity**: `repository_uuid` (stable, locally minted once, persisted in `.kittify/config.yaml`, never regenerated)
- **Locator**: `repo_slug` (human-readable label derived from git remote or directory name; mutable, not a stable identity)
- **Scope**: Git-level; one per `.git` directory; shared across all worktrees of that repository
- **Current state**: The stable UUID that should be `repository_uuid` is currently stored as `project_uuid`. The `repo_slug` field is an optional user-provided override, not auto-populated, and not the primary identity for anything.

### Build

One **checkout or worktree** of one repository. Each build has its own working tree, its own `.kittify/` state snapshot, and its own execution context. Builds are ephemeral relative to the repository they belong to.

- **Identity**: `build_id` (unique per checkout/worktree instance)
- **Scope**: Worktree-level; created and destroyed as lanes are opened and closed
- **Current state**: Correctly named as `build_id` in sync payloads; not conflated with other terms

## Identity Layer Model

The canonical identity model separates four concerns that the current codebase conflates under `ProjectIdentity`:

| Field | Scope | Minted by | Persistence | Stability |
|-------|-------|-----------|-------------|-----------|
| `repository_uuid` | Repository | CLI, locally, once per repository | `.kittify/config.yaml` | Stable; never regenerated or overwritten |
| `project_uuid` | Collaboration | SaaS, during binding | `.kittify/config.yaml` | Stable once assigned; absent until binding |
| `repo_slug` | Repository | CLI, derived from git remote or directory name | `.kittify/config.yaml` | Mutable; changes if remote or directory changes |
| `build_id` | Build | CLI, locally, once per checkout/worktree | `.kittify/config.yaml` | Stable per worktree; new worktree gets new build_id |

**Key design decisions:**

1. **`repository_uuid` is the primary local identity.** It is minted once when `spec-kitty init` (or first sync) runs, persisted in `.kittify/config.yaml`, and never changes. It is the only stable repository-scoped identifier. Today this value exists but is mislabeled as `project_uuid`.

2. **`project_uuid` is optional and SaaS-assigned.** It is absent from `.kittify/config.yaml` until the user binds the repository to a SaaS collaboration project. When binding occurs, the SaaS assigns a `project_uuid` and the CLI persists it alongside (not replacing) the `repository_uuid`. Multiple repositories can share the same `project_uuid`.

3. **`repo_slug` is a locator, not an identity.** It is a human-readable convenience label. It may change when git remotes change, when the directory is renamed, or when the user provides an override. No system should use it as a primary key or stable reference.

4. **`build_id` is unchanged.** It is already correctly scoped and named.

**Migration rule:** Existing `project_uuid` values in `.kittify/config.yaml` become `repository_uuid`. The `project_uuid` field becomes empty/absent until SaaS binding is established. No locally minted identity is lost.

## Terminology Invariants

These invariants must remain true for all user-facing and contract-facing surfaces:

1. **"Project" never means "repository."** Any surface that refers to the local Git resource must use "repository" (or "repo" in informal/variable contexts). "Project" is reserved exclusively for the SaaS collaboration surface.

2. **"Repository" never means "checkout."** The repository is the `.git`-level resource. A specific checkout or worktree is a "build." Functions that resolve a working directory path are resolving the build's location within a repository, not the repository itself.

3. **`repository_uuid` is the stable local repository identity.** It is minted once, persisted locally, and never changes. It is not shared across repositories. It is the primary key for repository-scoped operations.

4. **`project_uuid` is an optional collaboration binding.** It is absent until a SaaS project claims this repository. It is assigned by the SaaS, not locally minted. Multiple repositories may share one `project_uuid`. No CLI operation requires `project_uuid` to be present.

5. **`repo_slug` is a mutable locator, not a stable identity.** It is derived from git remotes or directory names and may change. No contract or identity system should depend on its stability. It is useful for display, logging, and human-readable references only.

6. **`build_id` is a checkout/worktree identity.** It identifies which specific working tree is executing. It is unique per worktree and is always sent explicitly in SaaS payloads so the server can distinguish parallel builds from the same repository.

7. **Local-first execution is repository-native.** All CLI operations execute against a repository and build. The SaaS project layer is an optional collaboration overlay; no CLI operation requires a project to exist. Repository-native, local-first execution must remain fully functional without SaaS connectivity.

8. **Tracker "project" is a separate concept.** When integrating with Jira, Linear, or GitHub Issues, their "project" is neither Spec Kitty's project nor Spec Kitty's repository. References to tracker workspaces must be explicitly qualified (e.g., "tracker project," "Jira project key," or a domain-specific term like "tracker workspace").

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

### Category 3: Identity Mislabeling

The core identity issue: a locally minted repository UUID is stored and transmitted as `project_uuid`.

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/sync/project_identity.py` | `class ProjectIdentity` | Bundles repository-scoped (`repository_uuid` mislabeled as `project_uuid`) and build-scoped (`build_id`) fields under a "project" class name |
| `src/specify_cli/sync/project_identity.py` | `generate_project_uuid()` → `uuid4()` | Locally mints a UUID and calls it "project"; this is actually repository identity generation |
| `src/specify_cli/sync/project_identity.py` | `project_slug` via `derive_project_slug()` | Derives from git remote/directory name; presented as identity but is a mutable locator |
| `src/specify_cli/sync/project_identity.py` | `repo_slug` field: "Optional owner/repo override" | Described as optional override; spec previously overstated it as the canonical repository identity |
| `src/specify_cli/migration/backfill_identity.py` | `backfill_project_uuid()` | Writes a locally minted UUID as `project_uuid`; should be `repository_uuid` |
| `.kittify/config.yaml` | `project:` section with `uuid`, `slug`, `build_id` | Section name implies SaaS project; contents are entirely repository/build identity |

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

A contributor opens the identity module and can immediately tell which identifier is project-scoped, which is repository-scoped, and which is build-scoped. Class names, field names, and docstrings use canonical terms. The class that holds `repository_uuid` and `build_id` is not called `ProjectIdentity`.

**Acceptance**: The identity class is named to reflect its actual scope (repository + build identity). `repository_uuid` is the primary stable field. `project_uuid` is an optional field, documented as SaaS-assigned. `repo_slug` is documented as a mutable locator, not an identity.

### Scenario 3: SaaS Consumer Parses Payload

A SaaS service receives a sync payload and can distinguish the collaboration project from the repository from the build by reading field names alone. No field requires out-of-band knowledge to interpret.

**Acceptance**: SaaS payloads include `repository_uuid` for the repository identity, `build_id` for the build, `repo_slug` as an optional locator, and `project_uuid` only when a SaaS binding has been established. No field named `project_*` carries repository-scoped or build-scoped data.

### Scenario 4: Multi-Repo Project (Future Readiness)

When the SaaS later supports multi-repository projects, no local CLI behavior changes. A user can bind two repositories to one project. Each repository retains its own `repository_uuid` and generates its own `build_id` per worktree. The `project_uuid` is shared across both repositories but does not replace either repository's `repository_uuid`.

**Acceptance**: The terminology contract supports this scenario without renaming. Local-first execution in each repository is unaffected by the shared project identity. No repository-scoped identifier is lost or overwritten during binding.

### Scenario 5: Tracker Integration Clarity

A user configures a Jira integration. The Jira "project" (e.g., "INGEST") is clearly distinguished from the Spec Kitty project and the Spec Kitty repository. Config keys and CLI output never say just "project" when they mean the tracker workspace.

**Acceptance**: All tracker-facing surfaces qualify their references (e.g., "tracker project" or use the tracker's own terminology like "Jira project key").

### Scenario 6: Existing Repository Migrates to New Identity Model

An existing repository with a locally minted `project_uuid` in `.kittify/config.yaml` upgrades to the new identity model. The existing UUID value is preserved as `repository_uuid`. The `project_uuid` field becomes absent (no SaaS binding yet). No data is lost, no identity is regenerated.

**Acceptance**: After migration, `.kittify/config.yaml` contains `repository_uuid` with the exact value that was previously stored as `project_uuid`. The `project_uuid` field is absent or empty. All CLI operations continue to work identically.

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | All CLI `--help` text must use "repository" when referring to the local Git resource and "project" only when referring to the SaaS collaboration surface | Proposed |
| FR-002 | All user-facing documentation must follow the canonical terminology definitions for project, repository, and build | Proposed |
| FR-003 | The locally minted stable UUID currently labeled `project_uuid` must be renamed to `repository_uuid` in identity structures, config keys, and code | Proposed |
| FR-004 | `project_uuid` must become an optional field, absent until a SaaS collaboration binding is established, and must never be locally minted | Proposed |
| FR-005 | `repo_slug` must be documented and treated as a mutable human-readable locator, not a stable identity; no contract or identity system may depend on its stability | Proposed |
| FR-006 | SaaS contract payloads must include `repository_uuid` for the repository, `build_id` for the build, `repo_slug` as an optional locator, and `project_uuid` only when a SaaS binding exists | Proposed |
| FR-007 | Tracker integration surfaces must qualify "project" references to distinguish the tracker workspace from the Spec Kitty project (e.g., "tracker project," "Jira project key") | Proposed |
| FR-008 | The `.kittify/config.yaml` identity section must use canonical naming that reflects the actual scope of each identifier (`repository_uuid` for the stable local identity, `project_uuid` as optional binding) | Proposed |
| FR-009 | Core path-resolution functions must be named to reflect that they resolve repository roots, not project roots (e.g., `locate_repository_root` instead of `locate_project_root`) | Proposed |
| FR-010 | A canonical glossary entry for each of the four identity fields (`repository_uuid`, `project_uuid`, `repo_slug`, `build_id`) and three domain terms (project, repository, build) must be maintained and referenced from developer documentation | Proposed |
| FR-011 | Existing `project_uuid` values in `.kittify/config.yaml` must be migrated to `repository_uuid` preserving the exact UUID value; no identity regeneration is permitted | Proposed |

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
| C-004 | Existing locally minted UUID values in `.kittify/config.yaml` must be preserved as `repository_uuid` during migration; no identity is regenerated or discarded | Active |
| C-005 | `project_uuid` must not be locally minted after migration; it becomes a SaaS-assigned field only | Active |

## Success Criteria

1. A contributor can read the canonical glossary and correctly classify any identifier in the codebase as project-scoped, repository-scoped, or build-scoped without consulting the original author.
2. All user-facing terminology surfaces (CLI help, documentation, config key descriptions) converge on the canonical definitions within the scope of the implementation missions that follow this specification.
3. SaaS payload field names are unambiguous: a consumer can determine the scope of any field from its name alone, without reading external documentation.
4. Local-first, repository-native execution is unchanged: no CLI command requires a SaaS project to exist in order to function.
5. The terminology contract supports binding multiple repositories to one project without requiring any further rename and without losing any repository's stable `repository_uuid`.
6. After migration, existing repositories retain their original UUID value (now correctly labeled `repository_uuid`) with zero data loss.

## Explicit Non-Goals (v1)

- **Exhaustive drift audit**: The representative catalog in this spec establishes the pattern. A comprehensive inventory of every affected string, field, and help text is a planning activity.
- **Code migration execution**: Renaming functions, classes, config keys, and CLI flags is implementation work, not specification work.
- **Documentation rewrite**: Updating all prose in `docs/` to use canonical terms is implementation work.
- **SaaS schema migration**: Changing server-side field names or API contracts is out of scope for this mission.
- **Deprecation timeline**: Specific version numbers and deprecation schedules are planning decisions.
- **SaaS binding implementation**: The mechanism by which a SaaS project assigns `project_uuid` to a repository is out of scope; this spec only defines the contract that the binding must satisfy.

## Assumptions

1. The SaaS will eventually support multi-repository projects, and the terminology contract should be designed to accommodate that without further renaming.
2. The locally minted UUID currently stored as `project_uuid` is a correctly generated stable identity — the problem is that it is mislabeled as project-scoped when it is actually repository-scoped. The value itself is sound; only its name and documented scope are wrong.
3. `build_id` is already correctly named and scoped; no changes are needed to its definition or usage.
4. External tracker integrations will continue to use their own "project" terminology (Jira project, Linear team); Spec Kitty must disambiguate without forcing trackers to change their vocabulary.
5. `repo_slug` will remain useful as a human-readable display label and logging aid, but no system should treat it as a primary key or stable reference.

## Dependencies

- The glossary system (mission 047+) can host the canonical definitions once they are ratified.
- SaaS API versioning capabilities are needed before any payload field renames can be deployed; this is a constraint on implementation, not on this specification.

## Key Entities

| Entity | Canonical Term | Identity Field | Scope |
|--------|---------------|----------------|-------|
| Collaboration surface | Project | `project_uuid` (optional, SaaS-assigned) | SaaS-level; spans repositories |
| Git resource | Repository | `repository_uuid` (stable, locally minted once) | Git-level; one per `.git` directory |
| Repository label | Repository locator | `repo_slug` (mutable, human-readable) | Git-level; convenience label only |
| Checkout/worktree | Build | `build_id` | Worktree-level; ephemeral |
| External tracker workspace | Tracker project (qualified) | `tracker_project_slug` or domain-specific key | External system; not owned by Spec Kitty |
