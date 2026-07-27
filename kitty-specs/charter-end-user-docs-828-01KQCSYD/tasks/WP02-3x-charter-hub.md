---
work_package_id: WP02
title: docs/3x/ Charter Hub
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/3x/
execution_mode: planning_artifact
owned_files:
- docs/3x/index.md
- docs/3x/charter-overview.md
- docs/3x/governance-files.md
tags: []
---

# WP02 — docs/3x/ Charter Hub

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Create the three core pages of the `docs/3x/` Charter-era hub. These pages serve as the canonical current-era anchor for all other documentation. Every new how-to, explanation, and reference page cross-links to these pages for the Charter mental model.

This WP can run in parallel with WP03–WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP02 --agent <name>`; do not guess the worktree path

## Context

### Key Invariants (must hold in every page)

1. `charter.md` is the **only** human-edited governance file. `governance.yaml`, `directives.yaml`, `metadata.yaml`, and `library/*.md` are auto-generated. State this explicitly.
2. When DRG context is too large, the runtime falls back to compact-context mode (issue #787 or current). Acknowledge this limitation — do not promise full-context behavior unconditionally.
3. The `(profile, action, governance-context)` triple is the correct primitive for profile invocation.

### Source of Truth

Before writing:
- Run `uv run spec-kitty charter --help` and `uv run spec-kitty charter status --help` to verify current command surface.
- Read `kitty-specs/charter-end-user-docs-828-01KQCSYD/data-model.md` Section 3 for the page-by-page scope notes.
- Read `docs/2x/doctrine-and-charter.md` if present — understand what 2.x said so pages clearly describe Charter-era differences.

### DocFX Format

Each page needs a DocFX frontmatter block. Look at `docs/how-to/setup-governance.md` for the exact format. Typical pattern:

```markdown
---
title: <Page Title>
description: <One-line description for nav/SEO>
---
```

## Subtask Guidance

### T006 — Write docs/3x/index.md

**Purpose**: Orient readers arriving via the nav ("you are here — current product"). Briefly describe the Charter model. Link to each Divio section for their respective workflows. This is a landing/hub page — not a deep-dive.

**Structure**:
1. Brief intro: "You're looking at Spec Kitty 3.x Charter-era documentation. This is the current product."
2. One-paragraph Charter model summary: governance file (`charter.md`) -> synthesis -> charter bundle -> runtime context injection.
3. Four navigation blocks (one per Divio type): Tutorial, How-To, Reference, Explanation — each with 2–3 bullet links to the most important pages in that section.
4. "What's archived" note: link to `docs/2x/` with a clear statement that 2.x docs are preserved but not current.

**Tone**: "You are here" — direct, welcoming, minimal jargon. New users should understand what they're looking at within 30 seconds.

**Cross-links to add at the bottom ("See also")**:
- `charter-overview.md` (deeper mental model)
- `governance-files.md` (file reference)

### T007 — Write docs/3x/charter-overview.md

**Purpose**: Canonical "how Charter works" mental model page. All other new pages reference this one for the current-state Charter model. Cover: synthesis, DRG, bundle, bootstrap vs compact context.

**Structure**:
1. **What Charter Does** — governance file (`charter.md`) drives the synthesis pipeline. The synthesizer produces the charter bundle (authoritative vs generated files distinction).
2. **Synthesis Flow** — `charter interview` -> `charter generate` -> `charter lint` -> `charter synthesize` -> `charter bundle validate`. Brief description of each step's role. Include a command sequence code block (verify commands exist with `--help` before writing). Mention `charter context --action <action> --json` separately as the runtime/debug command for rendering action context, not as a synthesis step.
3. **The DRG-Backed Context Model** — how DRG edges are computed; how context is injected when `spec-kitty next` invokes an agent profile. Explain what "governed profile invocation" means at a high level.
4. **Bootstrap vs Compact Context** — when the full DRG context fits: bootstrap mode. When it's too large: compact-context mode. Link issue #787 (or note "see issue tracker" if the issue number is uncertain) for the compact-context limitation. Do not promise full-context behavior unconditionally.
5. **Key Governance Files** — one-sentence each for `charter.md` (human-edited) and the generated files. Link to `governance-files.md` for the full table.

**Invariant to state explicitly**: "`charter.md` is the only file you should ever edit in your governance layer."

**Cross-links**:
- `docs/how-to/synthesize-doctrine.md`
- `docs/how-to/setup-governance.md`
- `docs/explanation/charter-synthesis-drg.md` (deeper explanation)

### T008 — Write docs/3x/governance-files.md

**Purpose**: Authoritative reference table of every file under `.kittify/charter/`. Who writes it (human vs auto-generated), what it contains, what happens if you edit an auto-generated file.

**Structure**:
1. Intro paragraph: "The Charter governance layer lives in `.kittify/charter/`. Most files are auto-generated by the synthesizer and must not be hand-edited."
2. **File Table**:

| File path | Who writes it | Contains | Edit directly? |
|---|---|---|---|
| `.kittify/charter/charter.md` | Human | Mission vision, directives, doctrine source | ✅ Yes — this is the only human-edited file |
| `.kittify/charter/governance.yaml` | Auto-generated (synthesis) | Resolved directives in structured form | ❌ No — overwritten on next synthesis |
| `.kittify/charter/directives.yaml` | Auto-generated | Extracted directive list | ❌ No |
| `.kittify/charter/metadata.yaml` | Auto-generated | Bundle metadata, provenance | ❌ No |
| `.kittify/charter/library/*.md` | Auto-generated | Doctrine pages derived from charter.md | ❌ No |

Verify actual file paths against a real project or `uv run spec-kitty charter status` output before writing. Adjust the table to match reality.

3. **What Happens If You Edit a Generated File** — one paragraph: "The synthesizer can overwrite generated-file edits on the next `charter synthesize` run. Use `charter status`, `charter lint`, and `charter bundle validate` to detect drift before relying on the bundle."
4. **Bundle Validation** — brief note: run `charter bundle validate` to validate the canonical bundle; `charter lint` checks for graph-native decay.

**Cross-links**:
- `charter-overview.md`
- `docs/how-to/synthesize-doctrine.md`

### T009 — Verify docs/3x/ pages integrate with toc.yml

After writing all three pages, verify:

```bash
grep -r 'index.md\|charter-overview.md\|governance-files.md' docs/3x/toc.yml
```

All three hrefs must appear. The toc.yml was created by WP01; do not modify it in this WP. If a page is missing from the toc, that is a WP01 error to flag — do not edit the toc here.

Also verify no `[TODO: ...]` placeholder text remains in any of the three pages:
```bash
grep -r 'TODO' docs/3x/
```
Zero results required.

## Definition of Done

- [ ] `docs/3x/index.md` written with nav blocks, cross-links, archive pointer
- [ ] `docs/3x/charter-overview.md` written with synthesis flow, DRG model, bootstrap vs compact, file authority rule stated explicitly
- [ ] `docs/3x/governance-files.md` written with file table verified against real paths
- [ ] All three pages use DocFX frontmatter format
- [ ] All CLI command examples verified against `--help` output (no assumed commands)
- [ ] `grep -r 'TODO' docs/3x/` returns zero results
- [ ] Three pages appear in `docs/3x/toc.yml`
- [ ] `uv run pytest tests/docs/ -q` passes
