---
work_package_id: WP01
title: Glossary Canonical Terms and Identity Fields
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-009
- FR-011
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- timestamp: '2026-04-10T16:55:49Z'
  action: created
  actor: claude
authoritative_surface: glossary/
execution_mode: code_change
owned_files:
- .kittify/glossaries/spec_kitty_core.yaml
- glossary/contexts/orchestration.md
- glossary/contexts/identity-fields.md
tags: []
---

# WP01: Glossary Canonical Terms and Identity Fields

## Objective

Add the canonical 3-tier terminology definitions (project, repository, build) and 6 identity field definitions (repository_uuid, repository_label, project_uuid, repo_slug, build_id, node_id) to the Spec Kitty glossary system. Fix the existing `Project` definition and deprecate stale terms.

This is the foundational work package — all subsequent terminology reference documents and validation steps depend on these glossary entries being in place and correct.

## Context

**Mission 081** defines a canonical terminology contract that separates three concepts the codebase currently conflates:
- **Project** = SaaS collaboration surface (optional, absent until binding)
- **Repository** = Local Git resource (one `.git` directory)
- **Build** = One checkout/worktree of one repository

And a corrected identity layer:
- `repository_uuid` = stable local repository identity (was mislabeled `project_uuid`)
- `repository_label` = human-readable display name (was `project_slug`)
- `project_uuid` = optional SaaS-assigned collaboration binding
- `repo_slug` = optional `owner/repo` Git provider reference (unchanged meaning)
- `build_id` = per-checkout/worktree identity (unchanged)
- `node_id` = stable machine fingerprint (unchanged)

**Source of truth**: `kitty-specs/081-canonical-baseline-and-repository-boundary/spec.md`

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

---

## Subtask T001: Audit Existing Glossary Entries for Conflicts

**Purpose**: Identify any existing glossary entries whose definitions conflict with the new canonical model before making changes.

**Steps**:
1. Read `.kittify/glossaries/spec_kitty_core.yaml` — check all existing terms
2. Read all files in `glossary/contexts/` — check for terms that define "project", "repository", or "build"
3. Document conflicts found:
   - `orchestration.md` line 9: `Project` defined as "Entire repository initialized for Spec Kitty workflow execution" — **conflicts** with new definition (project = SaaS collaboration surface)
   - `spec_kitty_core.yaml` line 55: `project root checkout` — uses "project" to mean the Git repository root; needs deprecation and replacement
   - `configuration-project-structure.md` line 1: uses "project" throughout — handled in WP02
4. No other context docs define "project", "repository", or "build" as standalone terms

**Files**: Read-only audit of all files in `.kittify/glossaries/` and `glossary/contexts/`

**Validation**:
- [ ] All existing glossary files read and checked
- [ ] Conflicts documented before any changes are made

---

## Subtask T002: Update orchestration.md — Fix Project, Add Repository and Build

**Purpose**: Replace the incorrect `Project` definition in the orchestration glossary context with the canonical definition. Add `Repository` and `Build` as new terms.

**Steps**:
1. Open `glossary/contexts/orchestration.md`
2. Replace the `Project` entry (currently at line 5-13) with the canonical definition:

   ```markdown
   ### Project

   | | |
   |---|---|
   | **Definition** | SaaS collaboration surface that groups one or more repositories under a shared identity for collaboration, visibility, and governance. A project may span multiple repositories and exists independent of any single Git checkout. |
   | **Context** | Orchestration |
   | **Status** | canonical |
   | **Applicable to** | `3.x` |
   | **Note** | Prior to mission 081, "project" was used interchangeably with "repository" to mean the local Git resource. That usage is now prohibited. See [Repository](#repository). |
   | **Related terms** | [Repository](#repository), [Build](#build), [Mission](#mission) |
   ```

3. Add a `Repository` entry after `Project`:

   ```markdown
   ### Repository

   | | |
   |---|---|
   | **Definition** | Local Git resource (one `.git` directory) that holds mission artifacts, source code, and `.kittify/` configuration. Multiple checkouts (worktrees) of the same repository share one repository identity. |
   | **Context** | Orchestration |
   | **Status** | canonical |
   | **Applicable to** | `3.x` |
   | **Note** | Replaces the pre-081 usage of "project" for the local Git resource. The canonical identity field is `repository_uuid`. |
   | **Related terms** | [Project](#project), [Build](#build) |
   ```

4. Add a `Build` entry after `Repository`:

   ```markdown
   ### Build

   | | |
   |---|---|
   | **Definition** | One checkout or worktree of one repository. Each build has its own working tree, `.kittify/` state snapshot, and execution context. Builds are ephemeral relative to the repository they belong to. |
   | **Context** | Orchestration |
   | **Status** | canonical |
   | **Applicable to** | `3.x` |
   | **Note** | The canonical identity field is `build_id`. |
   | **Related terms** | [Repository](#repository), [Workspace](../contexts/orchestration.md#workspace) |
   ```

**Files**:
- `glossary/contexts/orchestration.md` (modify)

**Validation**:
- [ ] `Project` definition says "SaaS collaboration surface", not "repository"
- [ ] `Repository` entry exists with correct definition
- [ ] `Build` entry exists with correct definition
- [ ] All three entries have `Applicable to: 3.x`
- [ ] Cross-references between the three terms are correct

---

## Subtask T003: Add Domain Terms to Glossary Seed File

**Purpose**: Add machine-readable entries for the three canonical domain terms to the glossary seed file.

**Steps**:
1. Open `.kittify/glossaries/spec_kitty_core.yaml`
2. Add entries after the existing terms:

   ```yaml
     - surface: project
       definition: SaaS collaboration surface grouping one or more repositories. Not the local Git resource.
       confidence: 1.0
       status: active

     - surface: repository
       definition: Local Git resource (one .git directory) holding mission artifacts. Formerly called "project" in pre-081 code.
       confidence: 1.0
       status: active

     - surface: build
       definition: One checkout or worktree of one repository with its own execution context.
       confidence: 1.0
       status: active
   ```

**Files**:
- `.kittify/glossaries/spec_kitty_core.yaml` (modify)

**Validation**:
- [ ] Three new terms added: project, repository, build
- [ ] All have `confidence: 1.0` and `status: active`
- [ ] Definitions match the canonical definitions from spec.md

---

## Subtask T004: Update Seed File — Deprecate project root checkout

**Purpose**: Deprecate `project root checkout` and add `repository root checkout` as the canonical replacement.

**Steps**:
1. In `.kittify/glossaries/spec_kitty_core.yaml`, find the `project root checkout` entry (line 55)
2. Change its `status` from `active` to `deprecated`
3. Update its `definition` to note the deprecation:
   ```yaml
     - surface: project root checkout
       definition: "DEPRECATED (mission 081): Use 'repository root checkout' instead. The root directory of the current git repository on the target branch."
       confidence: 1.0
       status: deprecated
   ```
4. Add the replacement term:
   ```yaml
     - surface: repository root checkout
       definition: The root directory of the current git repository on the target branch — not a worktree, not an external repository. Planning commands (specify, plan, tasks) run here.
       confidence: 1.0
       status: active
   ```

**Files**:
- `.kittify/glossaries/spec_kitty_core.yaml` (modify)

**Validation**:
- [ ] `project root checkout` has `status: deprecated`
- [ ] `repository root checkout` exists with `status: active`
- [ ] The new definition preserves the clarifying note about worktrees

---

## Subtask T005: Add Identity Field Terms to Seed File

**Purpose**: Add machine-readable glossary entries for all 6 identity fields from the canonical model.

**Steps**:
1. In `.kittify/glossaries/spec_kitty_core.yaml`, add entries for each identity field:

   ```yaml
     - surface: repository_uuid
       definition: Stable local repository identity, minted once per repository. Required namespace key for body sync and dedup. Was mislabeled as project_uuid before mission 081.
       confidence: 1.0
       status: active

     - surface: repository_label
       definition: Human-readable repository display name derived from git remote or directory name. Mutable, not a stable identity. Was called project_slug before mission 081.
       confidence: 1.0
       status: active

     - surface: project_uuid
       definition: Optional SaaS-assigned collaboration identity. Absent until a repository is bound to a SaaS project. Never locally minted.
       confidence: 1.0
       status: active

     - surface: repo_slug
       definition: Optional owner/repo Git provider reference (e.g. Priivacy-ai/spec-kitty). Unchanged from pre-081 meaning.
       confidence: 1.0
       status: active

     - surface: build_id
       definition: Per-checkout/worktree identity, unique per working tree. Unchanged from pre-081.
       confidence: 1.0
       status: active

     - surface: node_id
       definition: Stable machine fingerprint (12-char hex). Unchanged from pre-081.
       confidence: 1.0
       status: active
   ```

**Files**:
- `.kittify/glossaries/spec_kitty_core.yaml` (modify)

**Validation**:
- [ ] Six identity field terms added
- [ ] All have `confidence: 1.0` and `status: active`
- [ ] `repository_uuid` definition mentions it is the required namespace key
- [ ] `project_uuid` definition says "optional" and "never locally minted"
- [ ] `repo_slug` definition says "unchanged from pre-081 meaning"

---

## Subtask T006: Create identity-fields.md Context Document

**Purpose**: Create a human-readable glossary context document for the identity layer, following the established format in `glossary/contexts/`.

**Steps**:
1. Create `glossary/contexts/identity-fields.md`
2. Follow the existing context doc format (see `identity.md` or `orchestration.md` as examples)
3. Add entries for all 6 identity fields using the markdown table format:

   Each entry should follow this structure:
   ```markdown
   ### field_name

   | | |
   |---|---|
   | **Definition** | ... |
   | **Context** | Identity Fields |
   | **Status** | canonical |
   | **Applicable to** | `3.x` |
   | **Scope** | Repository / Collaboration / Build / Machine |
   | **Note** | ... |
   | **Related terms** | ... |
   ```

4. Include a header paragraph explaining the identity layer model:
   - The 3-tier boundary (project / repository / build)
   - That `repository_uuid` is the primary local identity
   - That `project_uuid` is optional SaaS binding
   - Reference to spec.md for the full contract

**Files**:
- `glossary/contexts/identity-fields.md` (new file)

**Validation**:
- [ ] File exists at `glossary/contexts/identity-fields.md`
- [ ] All 6 identity fields have entries
- [ ] Each entry has the correct scope (Repository, Collaboration, Build, Machine)
- [ ] Format matches the existing glossary context documents
- [ ] Header paragraph explains the identity layer model

---

## Definition of Done

- [ ] All 3 domain terms (project, repository, build) in glossary seed file with canonical definitions
- [ ] All 6 identity fields in glossary seed file
- [ ] `Project` definition in `orchestration.md` corrected to mean SaaS collaboration surface
- [ ] `Repository` and `Build` entries added to `orchestration.md`
- [ ] `project root checkout` deprecated; `repository root checkout` added
- [ ] `identity-fields.md` context document created with all 6 fields
- [ ] No stray "project" usage in new/modified entries that means "repository"

## Risks

- The existing `Project` definition in `orchestration.md` is marked `canonical` — changing it is a deliberate breaking change in terminology. The note explaining the change (referencing mission 081) is critical for audit trail.
- The `planning repository` deprecated alias already exists — ensure no circular deprecation chain.

## Reviewer Guidance

- Verify each definition matches the canonical model in spec.md
- Check that `status` fields are correct (`active` for new terms, `deprecated` for replaced terms)
- Verify cross-references between terms are valid links
- Ensure the `identity-fields.md` format matches other context docs
