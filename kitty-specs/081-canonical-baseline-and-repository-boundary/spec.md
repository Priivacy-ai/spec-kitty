# Canonical Baseline and Repository Boundary

**Mission**: 081-canonical-baseline-and-repository-boundary
**Status**: Draft
**Created**: 2026-04-10

## Problem Statement

Spec Kitty's codebase, documentation, CLI help text, and SaaS contract surfaces currently use "project," "repository," and "build" interchangeably. This conflation creates four concrete problems:

1. **User confusion**: A contributor reading CLI help or documentation cannot tell whether "project" refers to the local Git checkout, the SaaS collaboration surface, or an external tracker workspace (Jira project, Linear team). Onboarding cost increases every time someone has to ask "which project do you mean?"

2. **Contract ambiguity**: The SaaS payload structure sends `project_identity` bundles that actually contain repository-scoped and build-scoped values. If the SaaS later supports multi-repository projects, the current naming will actively mislead both human readers and automated consumers about what boundary each identifier represents.

3. **Identity mislabeling**: The locally minted UUID stored in `.kittify/config.yaml` as `project_uuid` is not a project identity at all. It is generated per repository checkout via `uuid4()` in `project_identity.py`, never assigned by the SaaS, and never shared across repositories. It is a de-facto repository identity wearing a project label. The same UUID is used as the required namespace scope key for body sync, queue dedup, and upstream contract validation — all local, repository-scoped operations that have nothing to do with SaaS collaboration.

4. **Internal inconsistency**: Core path-resolution functions use `project_root` and `locate_project_root()` to find the Git repository root, while other modules correctly use `repo_root`. The human-readable label derived from the git remote (`project_slug`) uses a "project" prefix for a repository-scoped value.

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
- **Label**: `repository_label` (human-readable display name derived from git remote or directory name; mutable, not a stable identity)
- **Git provider reference**: `repo_slug` (optional `owner/repo`-style identifier from the git provider; retains its current meaning unchanged)
- **Scope**: Git-level; one per `.git` directory; shared across all worktrees of that repository
- **Current state**: The stable UUID that should be `repository_uuid` is currently stored as `project_uuid`. The human-readable label that should be `repository_label` is currently stored as `project_slug`. The `repo_slug` field is an optional user-provided `owner/repo` override that retains its current semantics.

### Build

One **checkout or worktree** of one repository. Each build has its own working tree, its own `.kittify/` state snapshot, and its own execution context. Builds are ephemeral relative to the repository they belong to.

- **Identity**: `build_id` (unique per checkout/worktree instance)
- **Scope**: Worktree-level; created and destroyed as lanes are opened and closed
- **Current state**: Correctly named as `build_id` in sync payloads; not conflated with other terms

## Identity Layer Model

The canonical identity model separates concerns that the current codebase conflates under `ProjectIdentity`:

| Field | Scope | Minted by | Persistence | Stability |
|-------|-------|-----------|-------------|-----------|
| `repository_uuid` | Repository | CLI, locally, once per repository | `.kittify/config.yaml` | Stable; never regenerated or overwritten |
| `repository_label` | Repository | CLI, derived from git remote or directory name | `.kittify/config.yaml` | Mutable; changes if remote or directory changes |
| `repo_slug` | Repository | User-provided or derived from git remote | `.kittify/config.yaml` | Optional; `owner/repo` format; retains current meaning |
| `project_uuid` | Collaboration | SaaS, during binding | `.kittify/config.yaml` | Stable once assigned; absent until binding |
| `build_id` | Build | CLI, locally, once per checkout/worktree | `.kittify/config.yaml` | Stable per worktree; new worktree gets new build_id |
| `node_id` | Machine | CLI, from stable machine fingerprint | `.kittify/config.yaml` | Stable per machine |

**Key design decisions:**

1. **`repository_uuid` is the primary local identity and required namespace key.** It is minted once when `spec-kitty init` (or first sync) runs, persisted in `.kittify/config.yaml`, and never changes. It replaces `project_uuid` as the required scope key for body sync namespaces, queue dedup, and upstream contract validation. Today this value exists but is mislabeled as `project_uuid`.

2. **`project_uuid` is optional and SaaS-assigned.** It is absent from `.kittify/config.yaml` until the user binds the repository to a SaaS collaboration project. When binding occurs, the SaaS assigns a `project_uuid` and the CLI persists it alongside (not replacing) the `repository_uuid`. Multiple repositories can share the same `project_uuid`. No local operation requires it.

3. **`repository_label` is the human-readable display name (new field name).** It replaces `project_slug`. It is derived from the git remote URL or directory name. It is used for display, logging, and human-readable context only. No system should use it as a primary key or stable reference.

4. **`repo_slug` retains its current meaning.** It remains the optional `owner/repo`-style Git provider reference. Its semantics do not change. No field is renamed to `repo_slug`.

5. **`build_id` is unchanged.** It is already correctly scoped and named.

**Migration rule:** Existing `project_uuid` values in `.kittify/config.yaml` become `repository_uuid`. Existing `project_slug` values become `repository_label`. `repo_slug` is unchanged. The `project_uuid` field becomes empty/absent until SaaS binding is established. No locally minted identity is lost.

## Terminology Invariants

These invariants must remain true for all user-facing and contract-facing surfaces:

1. **"Project" never means "repository."** Any surface that refers to the local Git resource must use "repository" (or "repo" in informal/variable contexts). "Project" is reserved exclusively for the SaaS collaboration surface.

2. **"Repository" never means "checkout."** The repository is the `.git`-level resource. A specific checkout or worktree is a "build." Functions that resolve a working directory path are resolving the build's location within a repository, not the repository itself.

3. **`repository_uuid` is the stable local repository identity and required namespace key.** It is minted once, persisted locally, and never changes. It is not shared across repositories. It is the primary key for all repository-scoped operations including body sync namespaces, queue dedup, and upstream contract validation.

4. **`project_uuid` is an optional collaboration binding.** It is absent until a SaaS project claims this repository. It is assigned by the SaaS, not locally minted. Multiple repositories may share one `project_uuid`. No local CLI operation requires `project_uuid` to be present. It is never used as a local namespace key.

5. **`repository_label` is a mutable display name, not a stable identity.** It is derived from git remotes or directory names and may change. No contract or identity system should depend on its stability. It is useful for display, logging, and human-readable references only.

6. **`repo_slug` retains its current `owner/repo` meaning.** It is the optional Git provider-style reference (e.g., `Priivacy-ai/spec-kitty`). Its semantics are unchanged by this mission. It must not be repurposed to mean the human-readable display label.

7. **`build_id` is a checkout/worktree identity.** It identifies which specific working tree is executing. It is unique per worktree and is always sent explicitly in SaaS payloads so the server can distinguish parallel builds from the same repository.

8. **Local-first execution is repository-native.** All CLI operations execute against a repository and build. The SaaS project layer is an optional collaboration overlay; no CLI operation requires a project to exist. Repository-native, local-first execution must remain fully functional without SaaS connectivity.

9. **Tracker "project" is a separate concept.** When integrating with Jira, Linear, or GitHub Issues, their "project" is neither Spec Kitty's project nor Spec Kitty's repository. References to tracker workspaces must be explicitly qualified (e.g., "tracker project," "Jira project key," or a domain-specific term like "tracker workspace").

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

The core identity issue: a locally minted repository UUID is stored and transmitted as `project_uuid`, and a repository-derived display name is labeled `project_slug`.

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/sync/project_identity.py` | `class ProjectIdentity` | Bundles repository-scoped (`repository_uuid` mislabeled as `project_uuid`) and build-scoped (`build_id`) fields under a "project" class name |
| `src/specify_cli/sync/project_identity.py` | `generate_project_uuid()` → `uuid4()` | Locally mints a UUID and calls it "project"; this is actually repository identity generation |
| `src/specify_cli/sync/project_identity.py` | `project_slug` via `derive_project_slug()` | Derives a human-readable label from git remote/directory name; mislabeled as "project_slug" when it is a repository label |
| `src/specify_cli/sync/namespace.py` | `NamespaceRef.project_uuid` (required, non-empty) | Uses `project_uuid` as the required namespace scope key for body sync; this is a local repository-scoped operation that should use `repository_uuid` |
| `src/specify_cli/sync/queue.py` | `body_upload_queue.project_uuid TEXT NOT NULL` | SQLite schema requires `project_uuid` for queue dedup; this is a local repository-scoped key |
| `src/specify_cli/migration/backfill_identity.py` | `backfill_project_uuid()` | Writes a locally minted UUID as `project_uuid`; should be `repository_uuid` |
| `.kittify/config.yaml` | `project:` section with `uuid`, `slug`, `build_id` | Section name implies SaaS project; contents are entirely repository/build identity |

### Category 4: SaaS Payload Naming

Payloads sent to the SaaS that bundle repository and build identity under a "project" label.

| Surface | Current Name | Drift |
|---------|-------------|-------|
| `src/specify_cli/tracker/saas_client.py` (`bind_resolve`) | `project_identity` parameter | Payload contains `repo_slug` and `build_id`, which are repository/build-scoped |
| `src/specify_cli/tracker/saas_client.py` (routing) | `project_slug` parameter | Used for external tracker routing, conflating SaaS project with tracker workspace |
| `src/specify_cli/sync/emitter.py` (event envelope) | `project_uuid`, `project_slug` fields | Event envelope transmits locally minted UUID as `project_uuid` and display name as `project_slug` |

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

**Acceptance**: The identity class is named to reflect its actual scope (repository + build identity). `repository_uuid` is the primary stable field. `repository_label` is the display name. `repo_slug` is the optional `owner/repo` Git provider reference (unchanged meaning). `project_uuid` is an optional field, documented as SaaS-assigned.

### Scenario 3: SaaS Consumer Parses Payload

A SaaS service receives a sync payload and can distinguish the collaboration project from the repository from the build by reading field names alone. No field requires out-of-band knowledge to interpret. No existing field name has had its meaning silently changed.

**Acceptance**: SaaS payloads include `repository_uuid` for the repository identity, `repository_label` for the display name, `repo_slug` for the Git provider reference (same meaning as today), `build_id` for the build, and `project_uuid` only when a SaaS binding exists. No field named `project_*` carries repository-scoped or build-scoped data.

### Scenario 4: Multi-Repo Project (Future Readiness)

When the SaaS later supports multi-repository projects, no local CLI behavior changes. A user can bind two repositories to one project. Each repository retains its own `repository_uuid` and generates its own `build_id` per worktree. The `project_uuid` is shared across both repositories but does not replace either repository's `repository_uuid`.

**Acceptance**: The terminology contract supports this scenario without renaming. Local-first execution in each repository is unaffected by the shared project identity. No repository-scoped identifier is lost or overwritten during binding.

### Scenario 5: Tracker Integration Clarity

A user configures a Jira integration. The Jira "project" (e.g., "INGEST") is clearly distinguished from the Spec Kitty project and the Spec Kitty repository. Config keys and CLI output never say just "project" when they mean the tracker workspace.

**Acceptance**: All tracker-facing surfaces qualify their references (e.g., "tracker project" or use the tracker's own terminology like "Jira project key").

### Scenario 6: Existing Repository Migrates to New Identity Model

An existing repository with a locally minted `project_uuid` in `.kittify/config.yaml` upgrades to the new identity model. The existing UUID value is preserved as `repository_uuid`. The existing `project_slug` is preserved as `repository_label`. The `repo_slug` field is unchanged. The `project_uuid` field becomes absent (no SaaS binding yet). No data is lost, no identity is regenerated, and all local operations (body sync, queue dedup, offline mode) continue to work because `repository_uuid` replaces `project_uuid` as the required namespace key.

**Acceptance**: After migration, `.kittify/config.yaml` contains `repository_uuid` with the exact value that was previously stored as `project_uuid`, and `repository_label` with the exact value that was previously stored as `project_slug`. The `project_uuid` field is absent or empty. `repo_slug` is unchanged. All CLI operations continue to work identically.

### Scenario 7: Body Sync and Queue Dedup After Migration

After migration, body sync namespace construction uses `repository_uuid` (always present) instead of `project_uuid` (now optional/absent). Queue dedup keys and SQLite schema use `repository_uuid`. Offline queue entries created before migration remain valid because the UUID value is the same — only the field name changed.

**Acceptance**: `NamespaceRef` requires `repository_uuid` (non-empty). Body upload queue schema uses `repository_uuid TEXT NOT NULL`. Queue dedup keys use `repository_uuid`. No body sync operation fails due to absent `project_uuid`.

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | All CLI `--help` text must use "repository" when referring to the local Git resource and "project" only when referring to the SaaS collaboration surface | Proposed |
| FR-002 | All user-facing documentation must follow the canonical terminology definitions for project, repository, and build | Proposed |
| FR-003 | The locally minted stable UUID currently labeled `project_uuid` must be renamed to `repository_uuid` in identity structures, config keys, and code | Proposed |
| FR-004 | `project_uuid` must become an optional field, absent until a SaaS collaboration binding is established, and must never be locally minted | Proposed |
| FR-005 | The human-readable label currently called `project_slug` must be renamed to `repository_label`; it is a mutable display name derived from git remote or directory name | Proposed |
| FR-006 | `repo_slug` must retain its current `owner/repo` Git provider reference semantics; it must not be repurposed to mean the human-readable display label | Proposed |
| FR-007 | SaaS contract payloads must include `repository_uuid` for the repository identity, `repository_label` for the display name, `repo_slug` for the Git provider reference (unchanged meaning), `build_id` for the build, and `project_uuid` only when a SaaS binding exists | Proposed |
| FR-008 | Tracker integration surfaces must qualify "project" references to distinguish the tracker workspace from the Spec Kitty project (e.g., "tracker project," "Jira project key") | Proposed |
| FR-009 | The `.kittify/config.yaml` identity section must use a `repository:` section for local identity (`repository_uuid`, `repository_label`, `repo_slug`, `node_id`, `build_id`) and an optional `project:` section for SaaS binding | Proposed |
| FR-010 | Core path-resolution functions must be named to reflect that they resolve repository roots, not project roots (e.g., `locate_repository_root` instead of `locate_project_root`) | Proposed |
| FR-011 | A canonical glossary entry for each identity field and domain term must be maintained and referenced from developer documentation | Proposed |
| FR-012 | Existing `project_uuid` values in `.kittify/config.yaml` must be migrated to `repository_uuid` and existing `project_slug` values to `repository_label`, preserving exact values; no identity regeneration is permitted | Proposed |
| FR-013 | `repository_uuid` must replace `project_uuid` as the required namespace scope key for body sync (`NamespaceRef`), queue dedup (`body_upload_queue` schema), upstream contract validation, and event coalescence | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | Terminology convergence must not break existing SaaS API consumers | Zero breaking payload changes without a versioned migration path | Proposed |
| NFR-002 | All renamed CLI flags, config keys, and wire protocol fields must include a deprecation period with clear migration guidance | Minimum one minor release cycle with deprecation warnings before removal | Proposed |
| NFR-003 | Local-first CLI operations must remain fully functional without SaaS connectivity after terminology changes | 100% of offline-capable commands continue to work identically | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | This mission defines the terminology contract only; it does not plan or execute documentation rewrites, command renames, code migrations, or SaaS schema changes | Active |
| C-002 | The canonical definitions must be forward-compatible with multi-repository project support in the SaaS, even though that feature does not exist yet | Active |
| C-003 | `build_id` naming and semantics must not change; it is already correctly scoped and named | Active |
| C-004 | Existing locally minted UUID values in `.kittify/config.yaml` must be preserved as `repository_uuid` during migration; no identity is regenerated or discarded | Active |
| C-005 | `project_uuid` must not be locally minted after migration; it becomes a SaaS-assigned field only | Active |
| C-006 | `repo_slug` must not change meaning; it remains the optional `owner/repo` Git provider reference | Active |

## Success Criteria

1. A contributor can read the canonical glossary and correctly classify any identifier in the codebase as project-scoped, repository-scoped, or build-scoped without consulting the original author.
2. All user-facing terminology surfaces (CLI help, documentation, config key descriptions) converge on the canonical definitions within the scope of the implementation missions that follow this specification.
3. SaaS payload field names are unambiguous: a consumer can determine the scope of any field from its name alone, without reading external documentation.
4. Local-first, repository-native execution is unchanged: no CLI command requires a SaaS project to exist in order to function.
5. The terminology contract supports binding multiple repositories to one project without requiring any further rename and without losing any repository's stable `repository_uuid`.
6. After migration, existing repositories retain their original UUID value (now correctly labeled `repository_uuid`) and display name (now correctly labeled `repository_label`) with zero data loss.
7. Body sync, queue dedup, and offline operations continue to work after migration because `repository_uuid` (always present) replaces `project_uuid` (now optional) as the required namespace key.

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
5. `repository_label` (currently `project_slug`) will remain useful as a human-readable display name and logging aid, but no system should treat it as a primary key or stable reference.
6. `repo_slug` retains its existing `owner/repo` semantics and requires no rename or semantic change.

## Dependencies

- The glossary system (mission 047+) can host the canonical definitions once they are ratified.
- SaaS API versioning capabilities are needed before any payload field renames can be deployed; this is a constraint on implementation, not on this specification.

## Key Entities

| Entity | Canonical Term | Identity Field | Scope |
|--------|---------------|----------------|-------|
| Collaboration surface | Project | `project_uuid` (optional, SaaS-assigned) | SaaS-level; spans repositories |
| Git resource | Repository | `repository_uuid` (stable, locally minted once) | Git-level; one per `.git` directory |
| Repository display name | Repository label | `repository_label` (mutable, human-readable) | Git-level; display/logging only |
| Git provider reference | Repo slug | `repo_slug` (optional, `owner/repo` format, unchanged meaning) | Git-level; provider identity |
| Checkout/worktree | Build | `build_id` | Worktree-level; ephemeral |
| Machine fingerprint | Node | `node_id` | Machine-level; stable per host |
| External tracker workspace | Tracker project (qualified) | `tracker_project_slug` or domain-specific key | External system; not owned by Spec Kitty |
