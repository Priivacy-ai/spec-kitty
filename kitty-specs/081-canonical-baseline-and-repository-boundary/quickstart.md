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

## The three domain terms

| Term | Means | Identity Field | Example |
|------|-------|----------------|---------|
| **Project** | The SaaS collaboration surface | `project_uuid` (optional, SaaS-assigned) | "Bind this repository to a project" |
| **Repository** | The local Git resource (one `.git`) | `repository_uuid` (stable, locally minted) | "Initialize a new repository" |
| **Build** | One checkout or worktree | `build_id` (per worktree) | "This build is running lane-a" |

## The six identity fields

| Field | Scope | Description | Stability |
|-------|-------|-------------|-----------|
| `repository_uuid` | Repository | Stable local identity; required namespace key for body sync and dedup | Immutable once minted |
| `repository_label` | Repository | Human-readable display name (from git remote or dir name) | Mutable; display only |
| `repo_slug` | Repository | Optional `owner/repo` Git provider reference | Unchanged from current; optional |
| `project_uuid` | Collaboration | SaaS-assigned project binding | Absent until binding; never locally minted |
| `build_id` | Build | Per-checkout/worktree identity | Stable per worktree |
| `node_id` | Machine | Stable machine fingerprint | Stable per host |

## Quick rules

1. If you mean the local Git directory → say **repository**
2. If you mean the SaaS collaboration group → say **project**
3. If you mean one specific checkout/worktree → say **build**
4. If you mean the Jira/Linear/GitHub workspace → say **tracker project** (qualified)
5. `repository_label` is a mutable display name — never use it as a primary key
6. `repo_slug` means `owner/repo` from the Git provider — do not repurpose it for display names
7. `repository_uuid` is the required namespace key for local operations — not `project_uuid`

## Naming conventions

### Variables and parameters

| Correct | Incorrect | Why |
|---------|-----------|-----|
| `repo_root` | `project_root` | It's a repository root, not a project root |
| `repository_uuid` | `project_uuid` (for local identity) | The locally minted UUID is repository-scoped |
| `repository_label` | `project_slug` (for the display name) | It's a repository label, not a project slug |
| `repo_slug` | (no change needed) | Already correct for `owner/repo` Git provider reference |

### Functions

| Correct | Incorrect |
|---------|-----------|
| `locate_repository_root()` | `locate_project_root()` |
| `get_repository_root_or_exit()` | `get_project_root_or_exit()` |
| `generate_repository_uuid()` | `generate_project_uuid()` |
| `derive_repository_label()` | `derive_project_slug()` |

### Config keys

| Correct | Incorrect |
|---------|-----------|
| `repository.repository_uuid` | `project.uuid` |
| `repository.repository_label` | `project.slug` |
| `repository.repo_slug` | `project.repo_slug` |
| `project.project_uuid` (SaaS binding only) | `project.uuid` (for local identity) |

### Wire protocol fields

| Correct | Incorrect |
|---------|-----------|
| `repository_uuid` | `project_uuid` (for locally minted identity) |
| `repository_label` | `project_slug` (for display name) |
| `repo_slug` (unchanged) | Repurposing `repo_slug` for display names |
| `project_uuid` (only when SaaS binding exists) | `project_uuid` (for local identity) |

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
├── A human-readable label for the repo?
│   └── Use repository_label (and note it's display-only, not an identity)
├── The owner/repo Git provider reference?
│   └── Use repo_slug (and note it's optional, unchanged from current)
└── A namespace key for body sync or dedup?
    └── Use repository_uuid (never project_uuid, which is optional)
```

## Migration sequencing for follow-up missions

This mission (081) defines the contract. Follow-up missions implement it in this order:

1. **Config migration**: Rename `.kittify/config.yaml` `project:` → `repository:` section, `uuid` → `repository_uuid`, `slug` → `repository_label`. `repo_slug` stays as-is (unchanged meaning). Add deprecated-key reader for backwards compatibility during one release cycle.

2. **Identity class rename**: `ProjectIdentity` → `RepositoryIdentity` in `sync/project_identity.py` and all consumers. `project_slug` field → `repository_label`. `repo_slug` field unchanged. Internal change only, no user-facing impact.

3. **Namespace/queue key migration**: Replace `project_uuid` with `repository_uuid` in `NamespaceRef`, `body_upload_queue` SQLite schema, upstream contract, and coalescence keys. Same UUID value, new field name. Body sync continues working because `repository_uuid` is always present (locally minted).

4. **Path resolution rename**: `locate_project_root` → `locate_repository_root`, `get_project_root_or_exit` → `get_repository_root_or_exit`. Consolidate the two implementations first. Add deprecated aliases for one release cycle.

5. **CLI help text and variable names**: Update all `--help` strings, error messages, and `project_root` variables. User-visible change; include in release notes.

6. **Wire protocol dual-write**: CLI sends both old and new field names in event envelopes and bind payloads:
   - `project_uuid` AND `repository_uuid` (same value)
   - `project_slug` AND `repository_label` (same value)
   - `repo_slug` unchanged (no dual-write needed)
   - SaaS accepts either name.

7. **SaaS cutover**: SaaS reads from new field names. Old names tolerated but ignored.

8. **Wire protocol cleanup**: CLI stops sending old field names. Document the breaking change.

Steps 1-5 are CLI-only and can be released together. Steps 6-8 require coordinated CLI + SaaS releases with a deprecation window between each step.
