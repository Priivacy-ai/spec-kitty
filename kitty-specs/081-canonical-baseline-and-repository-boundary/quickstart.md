# Quickstart: Canonical Terminology Reference

**Mission**: 081-canonical-baseline-and-repository-boundary
**Date**: 2026-04-10

## When to use this reference

Use this document when you are:
- Writing CLI help text, error messages, or log output
- Naming variables, functions, classes, or config keys
- Writing documentation or code comments
- Defining wire protocol fields or SaaS API contracts
- Reviewing code for terminology consistency

## The three terms

| Term | Means | Identity Field | Example |
|------|-------|----------------|---------|
| **Project** | The SaaS collaboration surface | `project_uuid` (optional, SaaS-assigned) | "Bind this repository to a project" |
| **Repository** | The local Git resource (one `.git`) | `repository_uuid` (stable, locally minted) | "Initialize a new repository" |
| **Build** | One checkout or worktree | `build_id` (per worktree) | "This build is running lane-a" |

## Quick rules

1. If you mean the local Git directory → say **repository**
2. If you mean the SaaS collaboration group → say **project**
3. If you mean one specific checkout/worktree → say **build**
4. If you mean the Jira/Linear/GitHub workspace → say **tracker project** (qualified)
5. `repo_slug` is a mutable locator, not an identity — never use it as a primary key

## Naming conventions

### Variables and parameters

| Correct | Incorrect | Why |
|---------|-----------|-----|
| `repo_root` | `project_root` | It's a repository root, not a project root |
| `repository_uuid` | `project_uuid` (for local identity) | The locally minted UUID is repository-scoped |
| `repo_slug` | `project_slug` (for the locator) | It's derived from the repo, not a project |

### Functions

| Correct | Incorrect |
|---------|-----------|
| `locate_repository_root()` | `locate_project_root()` |
| `get_repository_root_or_exit()` | `get_project_root_or_exit()` |
| `generate_repository_uuid()` | `generate_project_uuid()` |
| `derive_repo_slug()` | `derive_project_slug()` |

### Config keys

| Correct | Incorrect |
|---------|-----------|
| `repository.repository_uuid` | `project.uuid` |
| `repository.repo_slug` | `project.slug` |
| `project.project_uuid` (SaaS binding only) | `project.uuid` (for local identity) |

### CLI help text

| Correct | Incorrect |
|---------|-----------|
| "Path to repository to repair" | "Path to project to repair" |
| "Name for your new repository directory" | "Name for your new project directory" |
| "Initialize a new spec-kitty repository" | "Setup tool for spec-driven development projects" |

## Decision tree for ambiguous cases

```
Is the thing you're naming...
├── The local .git directory?
│   └── Use "repository" / repo_root / repository_uuid
├── A specific checkout or worktree?
│   └── Use "build" / build_id
├── The SaaS collaboration group?
│   └── Use "project" / project_uuid
├── A Jira/Linear/GitHub workspace?
│   └── Use "tracker project" / tracker_project_slug
└── A human-readable label for the repo?
    └── Use repo_slug (and note it's a locator, not an identity)
```

## Migration sequencing for follow-up missions

This mission (081) defines the contract. Follow-up missions implement it in this order:

1. **Config migration**: Rename `.kittify/config.yaml` `project:` → `repository:` section, `uuid` → `repository_uuid`, `slug` → `repo_slug`. Add deprecated-key reader for backwards compatibility during one release cycle.

2. **Identity class rename**: `ProjectIdentity` → `RepositoryIdentity` in `sync/project_identity.py` and all consumers. Internal change only, no user-facing impact.

3. **Path resolution rename**: `locate_project_root` → `locate_repository_root`, `get_project_root_or_exit` → `get_repository_root_or_exit`. Consolidate the two implementations first. Add deprecated aliases for one release cycle.

4. **CLI help text and variable names**: Update all `--help` strings, error messages, and `project_root` variables. User-visible change; include in release notes.

5. **Wire protocol dual-write**: CLI sends both old (`project_uuid`) and new (`repository_uuid`) field names in event envelopes and bind payloads. SaaS accepts either.

6. **SaaS cutover**: SaaS reads from new field names. Old names tolerated but ignored.

7. **Wire protocol cleanup**: CLI stops sending old field names. Document the breaking change.

Steps 1-4 are CLI-only and can be released together. Steps 5-7 require coordinated CLI + SaaS releases.
