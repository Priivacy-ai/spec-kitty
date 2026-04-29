---
work_package_id: WP01
title: Gap Analysis and Navigation Architecture
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-016
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: researcher-robbie
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md
- docs/toc.yml
- docs/3x/toc.yml
- docs/tutorials/toc.yml
- docs/how-to/toc.yml
- docs/explanation/toc.yml
- docs/reference/toc.yml
- docs/migration/toc.yml
- docs/2x/index.md
- docs/docfx.json
tags: []
---

# WP01 — Gap Analysis and Navigation Architecture

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load researcher-robbie
```

This loads domain knowledge, tool preferences, and behavioral guidelines for research and gap analysis. Do not proceed until the profile confirms it has loaded.

## Objective

Produce the formal gap-analysis artifact and establish the full navigation infrastructure (all toc.yml files, 2x archive label). This WP is P0 — all content WPs (WP02–WP08) are blocked on its output.

Two deliverables:
1. `kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md` — structured Divio coverage matrix with all gaps called out
2. All toc.yml files updated/created to register every page planned by WP02–WP08

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP01 --agent <name>`; do not guess the worktree path

## Context

The repo uses DocFX (not MkDocs/Sphinx). Every page must appear in the `toc.yml` for its directory. The root `docs/toc.yml` lists directories; each directory has its own `toc.yml` listing individual pages.

Key files to read before starting:
- `kitty-specs/charter-end-user-docs-828-01KQCSYD/research.md` — full gap analysis already in prose form; this task formalizes it into a structured artifact
- `kitty-specs/charter-end-user-docs-828-01KQCSYD/data-model.md` — complete page map and linking strategy
- `docs/toc.yml` — current root navigation (to be updated)
- `docs/how-to/toc.yml`, `docs/tutorials/toc.yml`, `docs/reference/toc.yml`, `docs/explanation/toc.yml` — existing section navs
- `docs/2x/index.md` — to receive archive notice

## Subtask Guidance

### T001 — Produce gap-analysis.md

**File**: `kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md`

Produce a structured coverage matrix. The prose research is in `research.md` Section 2; transform it into the formal gap-analysis document.

Required sections:
1. **Coverage Matrix** — pipe table with rows = documentation areas, columns = Tutorial / How-To / Reference / Explanation. Cells: `present-current` | `present-stale` | `missing` | `intentionally-deferred`.
2. **Gap Priority Table** — list each `missing` or `present-stale` cell with: area, Divio type, priority (P0/P1/P2), planned page (from data-model.md), FR coverage.
3. **Source-of-Truth Notes** — for each gap, note the CLI command or source file that provides authoritative content.
4. **Key Invariants** — copy the invariants table from `research.md` Section 4.

No placeholder text. Every cell must be classified.

### T002 — Update docs/toc.yml

**File**: `docs/toc.yml`

Read the current file first. Apply these changes:
1. Add `3.x Docs (Current)` entry pointing to `3x/` — place it before `1.x Docs`
2. Change `2.x Docs` label to `2.x Docs (Archive)`
3. Do NOT add `retrospective-learning-loop.md` at the root level (it moves to explanation/)

Expected final state (from data-model.md Section 2):
```yaml
- name: Home
  href: index.md
- name: Tutorials
  href: tutorials/
- name: How-To Guides
  href: how-to/
- name: Reference
  href: reference/
- name: Explanation
  href: explanation/
- name: 3.x Docs (Current)
  href: 3x/
- name: 1.x Docs
  href: 1x/
- name: 2.x Docs (Archive)
  href: 2x/
```

Verify the file is valid YAML before committing.

### T003 — Create docs/3x/toc.yml

**File**: `docs/3x/toc.yml` (new file; create the `docs/3x/` directory if absent)

This toc serves WP02's three hub pages plus a nav title:

```yaml
- name: 3.x Docs (Current)
  href: index.md
- name: How Charter Works
  href: charter-overview.md
- name: Governance Files Reference
  href: governance-files.md
```

### T004 — Update/create all section toc.yml files

For each section directory, update or create the `toc.yml` to register every page that WP02–WP08 will produce. Use exact hrefs that match the planned filenames in `data-model.md`.

**docs/tutorials/toc.yml** — add:
```yaml
- name: Charter Governed Workflow (End-to-End)
  href: charter-governed-workflow.md
```

**docs/how-to/toc.yml** — add (in logical order):
```yaml
- name: Set Up Project Governance
  href: setup-governance.md
- name: Synthesize and Maintain Doctrine
  href: synthesize-doctrine.md
- name: Run a Governed Mission
  href: run-governed-mission.md
- name: Use the Retrospective Learning Loop
  href: use-retrospective-learning.md
- name: Troubleshoot Charter Failures
  href: troubleshoot-charter.md
- name: Manage the Project Glossary
  href: manage-glossary.md
```

Note: `setup-governance.md` and `manage-glossary.md` already exist — keep their hrefs; just ensure they appear.

**docs/explanation/toc.yml** — add/create:
```yaml
- name: Understanding Charter: Synthesis, DRG, and Governed Context
  href: charter-synthesis-drg.md
- name: Understanding Governed Profile Invocation
  href: governed-profile-invocation.md
- name: Understanding the Retrospective Learning Loop
  href: retrospective-learning-loop.md
```

If `explanation/toc.yml` exists, merge with existing entries. If the existing `documentation-mission.md` entry is there, keep it.

**docs/reference/toc.yml** — add:
```yaml
- name: Charter CLI Reference
  href: charter-commands.md
- name: CLI Reference
  href: cli-commands.md
- name: Profile Invocation Reference
  href: profile-invocation.md
- name: Retrospective Schema Reference
  href: retrospective-schema.md
```

Keep existing entries.

**docs/migration/toc.yml** — create if absent:
```yaml
- name: Migrating from 2.x / Early 3.x
  href: from-charter-2x.md
```

If it exists, add the entry.

After writing all files, grep for `TODO: register in docs nav` across all toc.yml files:
```bash
grep -r 'TODO: register' docs/
```
Zero results required.

### T004.1 — Update docs/docfx.json to include new directories

**File**: `docs/docfx.json`

Read the current file. The DocFX build configuration controls which Markdown files are included in the generated site — distinct from toc.yml reachability. Pages in toc.yml that are not listed in docfx.json will be absent from the generated site even if the toc is correct.

Add `docs/3x/` and `docs/migration/` to the `files` or `content` array in `docs/docfx.json`. The exact JSON key depends on the current file structure — read it first.

Expected additions (adapt to the existing JSON structure):
```json
"docs/3x/**.md",
"docs/3x/toc.yml",
"docs/migration/**.md",
"docs/migration/toc.yml"
```

Verify the file is valid JSON after editing:
```bash
python3 -c "import json; json.load(open('docs/docfx.json'))"
```

This step is **required**. Without it, the `docs/3x/` and `docs/migration/` pages will not appear in the built DocFX site even though toc.yml is correct.

### T005 — Update docs/2x/index.md with archive notice

**File**: `docs/2x/index.md`

Read the current file. Add a clearly visible archive notice at the top of the content (after any DocFX frontmatter block). Example:

```markdown
> **Archive Notice**: This section documents Spec Kitty 2.x behavior. It is preserved
> for historical reference only. For current 3.x Charter documentation, see
> [3.x Docs (Current)](../3x/index.md).
```

Do not remove or modify any existing 2.x content — this is archive material.

## Definition of Done

- [ ] `gap-analysis.md` exists in the mission dir with complete coverage matrix (no empty cells)
- [ ] `docs/toc.yml` has `3.x Docs (Current)` entry and `2.x Docs (Archive)` label
- [ ] `docs/3x/toc.yml` exists and lists all three hub pages
- [ ] All section toc.yml files updated with entries for every page WP02–WP08 will produce
- [ ] `docs/migration/toc.yml` exists
- [ ] `docs/2x/index.md` has archive notice
- [ ] `grep -r 'TODO: register' docs/` returns zero results
- [ ] All toc.yml files are valid YAML (no syntax errors)
- [ ] `docs/docfx.json` updated to include `docs/3x/` and `docs/migration/` directories; file is valid JSON
- [ ] `uv run pytest tests/docs/ -q` passes (zero failures)
