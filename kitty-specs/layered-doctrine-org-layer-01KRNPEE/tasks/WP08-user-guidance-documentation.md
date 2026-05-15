---
work_package_id: WP08
title: User Guidance Documentation
dependencies:
- WP06
- WP07
requirement_refs:
- FR-006
- FR-012
- FR-013
- FR-014
- FR-015
- FR-025
- FR-026
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "715492"
history:
- date: '2026-05-15'
  event: created
agent_profile: curator-carla
authoritative_surface: docs/how-to/create-an-org-doctrine-pack.md
execution_mode: code_change
owned_files:
- docs/how-to/create-an-org-doctrine-pack.md
- docs/migration/doctrine-local-overlay-to-org-layer.md
- docs/explanation/org-doctrine-layer.md
- docs/toc.yml
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

The curator profile is appropriate here — this WP is documentation work requiring clarity,
accuracy, and audience awareness.

---

## Objective

Write three user-facing documents and update the documentation index:

1. **Pack authoring guide** — for teams that maintain existing governance artifacts
   (Markdown docs, custom formats, internal policy systems) and want to publish them as a
   spec-kitty org doctrine pack.
2. **Migration guide** — for users who have been using `.kittify/doctrine/` local overlays
   or deprecated constitution-era paths (`constitution.md`, `constitution/*.yaml`) to
   achieve shared governance, and want to migrate to the proper org layer.
3. **Explanation** — for anyone wanting to understand how the three-layer resolution model
   works, when to use each layer, and what source attribution means.

---

## Context

The three documents address distinct audiences and should be written accordingly:

- **Pack authoring guide** (`how-to/`): task-oriented. Readers are governance system
  maintainers who know their content well but are new to spec-kitty's YAML schemas. They
  want a step-by-step recipe.
- **Migration guide** (`migration/`): task-oriented. Readers are existing spec-kitty users
  who have a working but informal shared-governance setup. They want to know exactly what to
  do without breaking their current setup.
- **Explanation** (`explanation/`): understanding-oriented. Readers may be anyone — a team
  lead evaluating governance strategy, a new contributor, or a senior engineer debugging
  resolution. They want to understand the model, not just follow steps.

Verify all CLI commands, config snippets, and file paths in each document against the
actual implementations in WP05, WP06, and WP07 before finalising.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP08 --agent claude`

---

## Subtask T038 — Write `docs/how-to/create-an-org-doctrine-pack.md`

**Audience**: Governance system maintainers; existing governance in any format (Markdown
prose, YAML, proprietary systems); new to spec-kitty schemas.

**Structure**:

```markdown
# How to create an org doctrine pack

## Before you start
[Prerequisites: spec-kitty version, pack layout understanding]

## Step 1: Understand the pack layout
[Pack directory structure — reference contracts/pack-layout.md visually]
[Artifact type directory names and file extensions]
[When to include DRG extensions]

## Step 2: Author your artifacts
[For each artifact type: one example showing the YAML structure]
[ID naming convention — namespace your IDs]
[How to reference shipped artifacts in DRG extensions]

## Wrapping an existing governance system
[For teams with existing Markdown prose or internal policies]
[Conversion workflow: identify artifact type → extract → validate]
[The most common mapping: policy doc → directive.yaml]

## Step 3: Validate the pack
[spec-kitty doctrine pack validate <path>]
[Reading the output: errors vs. advisories]
[Common errors and how to fix them]

## Step 4: Publish the pack
[Option A: git repository — recommended]
[Option B: HTTPS bundle — for binary distribution]
[Option C: HTTP API endpoint — for orgs with existing governance APIs]
[Versioning strategy: tag releases, pin refs]

## Step 5: Let consumers install it
[Show the config.yaml block they add]
[Show the doctrine fetch command they run]
[Testing: create a test project and verify charter context picks up org artifacts]

## Troubleshooting
[Advisory: "org layer overrides shipped artifact" — when to worry and when not to]
[Error: "No artifact directories found" — pack validation found nothing]
[Error: "Dangling DRG edge" — how to find the URN in shipped graph]
```

**Requirements for the guide**:
- Every CLI command must match the actual command name and flags from WP05/WP06.
- Every YAML snippet must be valid against the current schema.
- At least one complete example pack directory listing (for directives + agent_profiles).
- The "Wrapping an existing governance system" section must include a concrete before/after
  example: a Markdown policy doc → a `*.directive.yaml` file.

---

## Subtask T039 — Write `docs/migration/doctrine-local-overlay-to-org-layer.md`

**Audience**: Existing spec-kitty users who have been placing shared governance artifacts
in `.kittify/doctrine/` (directly or via a bootstrap script) to share them across projects,
or who are on deprecated constitution-era paths.

**Structure**:

```markdown
# Migrating shared doctrine to the org layer

## Who this guide is for
[Users with .kittify/doctrine/ shared across projects via scripts or copy-paste]
[Users on deprecated paths: .kittify/memory/constitution.md, .kittify/constitution/*.yaml]

## What changes
[Before: shared governance in project-local .kittify/doctrine/ — must repeat per project]
[After: org layer at ~/.kittify/org/<pack>/ — inherited automatically]
[Resolution order and what this means for existing overrides]

## Option 1: Migrate from .kittify/doctrine/ local overlay

### Step 1: Convert your local overlay into a pack
[Copy your .kittify/doctrine/ contents to a new pack directory]
[Run pack validate to check schema compliance]
[Fix any issues found]

### Step 2: Publish the pack
[Push to a git repository or create a bundle]
[Tag a version]

### Step 3: Configure and fetch
[Add doctrine.org block to .kittify/config.yaml]
[Run spec-kitty doctrine fetch]
[Verify with spec-kitty doctor doctrine]

### Step 4: Clean up
[Remove the artifacts you moved from .kittify/doctrine/]
[Keep any project-specific overrides in .kittify/doctrine/ — they still work]

## Option 2: Migrate from constitution-era paths
[.kittify/memory/constitution.md → no longer a runtime path; can be deleted]
[.kittify/constitution/*.yaml → no longer loaded; migrate content to charter.md and/or doctrine pack]
[charter.md remains the governance center; external docs referenced via governance_references (Mission B)]

## Verification checklist
[spec-kitty doctor doctrine shows snapshot present]
[charter context --json shows org-layer artifacts with "source": "org"]
[Existing project tests pass]

## Rollback
[If something goes wrong, put the artifacts back in .kittify/doctrine/]
[The org layer is additive; your project layer is unchanged]
```

**Requirements for the guide**:
- Be precise about which paths are deprecated (constitution-era) vs. still valid (project
  layer `.kittify/doctrine/`). Do not deprecate the project layer.
- Verify the constitution-era path list against the actual paths from #1013 (Mission B).
  For this guide, scope to paths known at Mission A time: `.kittify/memory/constitution.md`
  and `.kittify/constitution/*.yaml` (do not guess at additional paths).
- Include a table: "Before vs. After" for the two migration scenarios.

---

## Subtask T040 — Write `docs/explanation/org-doctrine-layer.md`

**Audience**: Anyone — team leads, contributors, engineers debugging resolution.

**Structure**:

```markdown
# Understanding the org doctrine layer

## The three-layer model
[Diagram or ASCII art: shipped → org → project]
[What each layer is for]
[Precedence rules: project wins, then org, then shipped]

## When to use each layer
[Shipped: standard defaults for all spec-kitty projects]
[Org: company-wide standards, proprietary directives, org-specific agent profiles]
[Project: project-local customizations and exceptions]

## How artifacts are resolved
[Full-replace on ID collision — no field-level merging across layers]
[What "full-replace" means in practice: an example]
[Shipped-ID override advisory — when you'll see it and what it means]

## DRG and the org layer
[How graph extensions work: additive only]
[What "additive" means: no removal of shipped nodes or edges]
[Fragment files: when and why to split your graph extension]

## Source attribution
[What "source": "org" means in charter context output]
[How to read spec-kitty doctor doctrine output]
[Using lint advisories to audit the governance stack]

## The fetch model
[Why fetch writes a local snapshot rather than fetching at resolution time]
[CI/CD safety: resolution is always deterministic and offline-capable]
[Updating the snapshot: doctrine fetch is explicit, not automatic]

## Frequently asked questions
[Can I have multiple org layers? Not in this release — single org slot]
[Can a project override org artifacts? Yes — project layer always wins]
[What if the org snapshot is missing? Resolution falls back to shipped + project]
[Is it safe to gitignore the snapshot? Yes — fetch is the install step]
```

---

## Subtask T041 — Update `docs/toc.yml` and verify cross-references

**File**: `docs/toc.yml`

Add entries for the three new documents in the appropriate sections:
- `docs/how-to/create-an-org-doctrine-pack.md` → under the How-To section
- `docs/migration/doctrine-local-overlay-to-org-layer.md` → under Migration
- `docs/explanation/org-doctrine-layer.md` → under Explanation

Also check for any existing doctrine docs that should cross-reference the new documents:
- `docs/doctrine/` directory — does it have an index? Add links to the new guides.
- `docs/status-model.md` — any reference to doctrine resolution should link to the
  explanation doc.

Run a simple cross-reference check:
```bash
grep -r "org-doctrine-layer\|create-an-org-doctrine-pack\|doctrine-local-overlay" docs/
```

Verify all document links resolve (no 404s). Fix any broken references.

---

## Definition of Done

- [ ] `docs/how-to/create-an-org-doctrine-pack.md` written with complete example pack
- [ ] `docs/migration/doctrine-local-overlay-to-org-layer.md` written with before/after table
- [ ] `docs/explanation/org-doctrine-layer.md` written with three-layer model explanation
- [ ] All CLI commands in documents verified against actual WP05/WP06/WP07 implementations
- [ ] `docs/toc.yml` updated with all three new entries
- [ ] No broken cross-references

## Risks

- Commands and config syntax in the guides must match WP05/WP06/WP07 exactly. Read the
  implemented `doctrine.py` and `config.py` before writing the guides — do not invent
  flags or syntax.
- The constitution-era path list in T039 must not include paths that are still valid in
  Mission A. When in doubt, err on the side of conservatism (don't deprecate things that
  aren't deprecated yet).

## Reviewer Guidance

1. Check every code block in every guide against the actual implementation.
2. Verify the "Rollback" section in T039 is accurate — the org layer must be truly additive
   (removing the config falls back gracefully without breaking the project).
3. Confirm the explanation doc's FAQ is accurate for Mission A scope (e.g., "multiple org
   layers: not in this release").

## Activity Log

- 2026-05-15T15:04:20Z – claude:opus-4-7:python-pedro:implementer – shell_pid=715492 – Started implementation via action command
- 2026-05-15T15:12:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=715492 – Three user-facing docs (explanation/how-to/migration) + toc updates + org-charter.yaml authoring sections in how-to Step 3 and explanation 'Org charter composition'. All CLI commands verified against WP05/WP06/WP07 --help output. All cross-references validated. YAML parses cleanly.
