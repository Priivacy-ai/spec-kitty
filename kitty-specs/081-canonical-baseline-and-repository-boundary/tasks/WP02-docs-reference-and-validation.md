---
work_package_id: WP02
title: Documentation Reference and Validation
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-007
- FR-008
- FR-010
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
agent: "claude:opus-4-6:implementer:implementer"
shell_pid: "6340"
history:
- timestamp: '2026-04-10T16:55:49Z'
  action: created
  actor: claude
authoritative_surface: docs/
execution_mode: code_change
owned_files:
- glossary/contexts/configuration-project-structure.md
- docs/reference/terminology.md
tags: []
---

# WP02: Documentation Reference and Validation

## Objective

Update the configuration-project-structure glossary context to align with canonical terminology, create a human-readable terminology reference document in `docs/reference/`, and validate that all glossary entries are conflict-free and well-formed.

This work package depends on WP01 (glossary canonical terms and identity fields) being complete. All references in this WP assume the glossary seed file and context documents have already been updated with canonical definitions.

## Context

**Mission 081** defines a canonical terminology contract that separates project (SaaS collaboration surface), repository (local Git resource), and build (checkout/worktree). WP01 added the canonical definitions to the glossary system. This WP propagates those definitions into:

1. The `configuration-project-structure.md` glossary context, which currently uses "project" throughout in the pre-081 sense
2. A new `docs/reference/terminology.md` human-readable reference document for contributors
3. Validation that no glossary conflicts remain

**Source of truth**: `kitty-specs/081-canonical-baseline-and-repository-boundary/spec.md` and `kitty-specs/081-canonical-baseline-and-repository-boundary/quickstart.md`

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

---

## Subtask T007: Update configuration-project-structure.md — Align with Canonical Terminology

**Purpose**: Update the `configuration-project-structure.md` glossary context so that entries using "project" to mean the local Git resource are corrected to use "repository" where appropriate, while preserving the existing document format and entries that correctly use "project."

**Steps**:
1. Open `glossary/contexts/configuration-project-structure.md`
2. Update the context heading description (line 1-2):
   - Current: "Terms describing where policy, runtime configuration, and mission artifacts live in a Spec Kitty project."
   - New: "Terms describing where policy, runtime configuration, and mission artifacts live in a Spec Kitty repository."
3. Update the `.kittify/` entry (line 5-14):
   - Current definition: "Project-local configuration and shared memory directory."
   - New definition: "Repository-local configuration and shared memory directory."
   - Keep all other fields unchanged
4. Update the `Project Charter` entry (line 66-74):
   - This entry correctly refers to a "project charter" as a governance concept — it does NOT need renaming
   - Add a `Note` row: "In this context, 'Project Charter' refers to the governance document, not the SaaS collaboration surface. See [Project](./orchestration.md#project) for the canonical definition of 'project'."
5. Review all other entries — verify that:
   - `kitty-specs/` — references "Feature" not "project"; no change needed
   - `.worktrees/` — no "project" usage; no change needed
   - `glossary/` — no "project" usage; no change needed
   - `Bootstrap (Candidate)` — references "project intent" which is ambiguous; update to "repository intent"
   - `Charter Library` — references "project-local collection" which is about governance, keep as-is but matches "Project Charter" governance usage

**Files**:
- `glossary/contexts/configuration-project-structure.md` (modify)

**Validation**:
- [ ] Context heading says "repository" not "project" (where referring to the local Git resource)
- [ ] `.kittify/` definition says "Repository-local" not "Project-local"
- [ ] `Project Charter` entry preserved (it correctly refers to governance, not the Git resource)
- [ ] `Project Charter` entry has a note distinguishing from the SaaS "project" concept
- [ ] No remaining uses of "project" that mean "repository" in this file
- [ ] Cross-references to `orchestration.md#project` still resolve correctly

---

## Subtask T008: Create docs/reference/terminology.md — Human-Readable Terminology Reference

**Purpose**: Create a contributor-facing terminology reference document that explains the canonical 3-tier model and identity fields in a format suitable for `docs/reference/`.

**Steps**:
1. Create `docs/reference/terminology.md`
2. Follow the style of existing docs in `docs/reference/` (see `file-structure.md`, `configuration.md` for format examples)
3. Include the following sections:

   **Header**:
   ```markdown
   # Terminology Reference

   This document defines the canonical terminology for Spec Kitty's three-tier domain model and identity layer. All contributors, CLI surfaces, documentation, and API contracts must use these terms consistently.

   **Canonical source**: Mission 081 — Canonical Baseline and Repository Boundary
   ```

   **Section 1: The Three Domain Terms**:
   - A table with columns: Term, Definition, Identity Field, Example Usage
   - Rows for: Project, Repository, Build
   - Definitions must match the canonical definitions from spec.md
   - Include the key distinction: "Project" = SaaS collaboration surface, "Repository" = local Git resource, "Build" = one checkout/worktree

   **Section 2: Identity Fields**:
   - A table with columns: Field, Scope, Description, Stability, Migration Note
   - Rows for all 6 fields: repository_uuid, repository_label, repo_slug, project_uuid, build_id, node_id
   - Include the migration notes (e.g., "Was mislabeled as project_uuid", "Was called project_slug")

   **Section 3: Quick Rules**:
   - Numbered list of the 7 quick rules from quickstart.md
   - These are concise guidelines for day-to-day usage

   **Section 4: Naming Conventions**:
   - Subsections for: Variables/parameters, Functions, Config keys, Wire protocol fields, CLI help text
   - Each subsection has a table with Correct vs. Incorrect columns
   - Derived from quickstart.md naming conventions

   **Section 5: Decision Tree**:
   - The decision tree from quickstart.md in a code block
   - Helps contributors resolve ambiguous cases

   **Section 6: What Changed (Migration Summary)**:
   - Brief summary of what was renamed and why
   - Table: Old Name → New Name → Reason
   - Note: "No existing identity values are lost. Only names and labels change."

4. Add a link to the new file in `docs/reference/toc.yml` if it uses a table-of-contents structure (check the file format first)

**Files**:
- `docs/reference/terminology.md` (new file)
- `docs/reference/toc.yml` (modify — add entry for terminology.md)

**Validation**:
- [ ] File exists at `docs/reference/terminology.md`
- [ ] All 3 domain terms defined with canonical definitions
- [ ] All 6 identity fields documented with correct scope and stability
- [ ] Quick rules match the 7 rules from quickstart.md
- [ ] Naming conventions cover all 5 categories (variables, functions, config, wire protocol, CLI)
- [ ] Decision tree included
- [ ] Migration summary table is accurate (old name → new name → reason)
- [ ] Format matches existing docs/reference/ style
- [ ] `docs/reference/toc.yml` updated with terminology entry

---

## Subtask T009: Validate No Glossary Conflicts and Run Existing Glossary Tests

**Purpose**: Verify that all glossary changes from WP01 and WP02 are consistent, conflict-free, and pass existing validation.

**Steps**:
1. Run glossary conflict check:
   ```bash
   spec-kitty glossary conflicts --json
   ```
   - Expected: No unresolved semantic conflicts between new canonical terms and existing terms
   - If conflicts found: document them and resolve within this WP

2. Run existing glossary tests:
   ```bash
   pytest tests/ -k glossary
   ```
   - Expected: All existing glossary tests pass
   - If failures: investigate and fix within scope of terminology changes only

3. Manual validation checklist:
   - Verify `project` in seed file has definition matching "SaaS collaboration surface"
   - Verify `repository` in seed file has definition matching "Local Git resource"
   - Verify `build` in seed file has definition matching "One checkout or worktree"
   - Verify `project root checkout` has `status: deprecated`
   - Verify `repository root checkout` has `status: active`
   - Verify all 6 identity fields present in seed file with `confidence: 1.0`
   - Verify `orchestration.md` has corrected `Project` definition
   - Verify `orchestration.md` has `Repository` and `Build` entries
   - Verify `identity-fields.md` exists with all 6 fields
   - Verify `configuration-project-structure.md` uses "repository" correctly
   - Verify `docs/reference/terminology.md` exists and is complete

4. Cross-reference validation:
   - Check that all cross-references between glossary context documents resolve correctly
   - Check that markdown links (e.g., `[Repository](#repository)`) point to entries that exist

**Files**:
- Read-only validation of all modified files from WP01 and WP02

**Validation**:
- [ ] `spec-kitty glossary conflicts --json` reports no unresolved conflicts
- [ ] `pytest tests/ -k glossary` passes
- [ ] All seed file entries have correct definitions, confidence, and status
- [ ] All context document entries have correct definitions and cross-references
- [ ] No stray "project" usage that means "repository" in any modified file
- [ ] `docs/reference/terminology.md` content matches canonical definitions

---

## Definition of Done

- [ ] `configuration-project-structure.md` aligned with canonical terminology
- [ ] `docs/reference/terminology.md` created with complete canonical reference
- [ ] `docs/reference/toc.yml` updated with terminology entry
- [ ] Glossary conflict check passes
- [ ] Existing glossary tests pass
- [ ] All cross-references between glossary documents resolve correctly
- [ ] No stray "project" usage meaning "repository" in any new or modified file

## Risks

- `configuration-project-structure.md` has "Project Charter" and "Charter Library" entries that correctly use "project" in a governance sense — must not over-correct these entries by replacing "project" with "repository" where the governance meaning is intended.
- The glossary conflict check may surface pre-existing conflicts unrelated to this mission — only resolve conflicts related to the canonical terminology changes.
- The `docs/reference/toc.yml` structure may vary — check the actual format before adding the terminology entry.

## Reviewer Guidance

- Verify each definition in `terminology.md` matches the canonical model in spec.md
- Verify `configuration-project-structure.md` changes are minimal and only correct "project" → "repository" where the Git resource is meant
- Confirm that "Project Charter" and "Charter Library" entries are NOT renamed (they correctly use "project" for governance)
- Check that `terminology.md` follows the style of existing docs in `docs/reference/`
- Run the glossary tests yourself to confirm they pass

## Activity Log

- 2026-04-10T17:13:27Z – claude:opus-4-6:implementer:implementer – shell_pid=6340 – Started implementation via action command
- 2026-04-10T17:20:20Z – claude:opus-4-6:implementer:implementer – shell_pid=6340 – All 3 subtasks complete: configuration-project-structure.md aligned, terminology.md created, validation passed
