---
work_package_id: WP06
title: Explanation Pages
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
- FR-007
- FR-010
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/explanation/
execution_mode: planning_artifact
owned_files:
- docs/explanation/charter-synthesis-drg.md
- docs/explanation/governed-profile-invocation.md
- docs/explanation/retrospective-learning-loop.md
- docs/retrospective-learning-loop.md
tags: []
---

# WP06 — Explanation Pages

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Write three Divio-shaped explanation pages and convert the root-level retrospective stub to a redirect. Explanation pages answer the question "Why does this work this way?" — they are understanding-oriented, not task-oriented.

This WP can run in parallel with WP02–WP05, WP07–WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP06 --agent <name>`; do not guess the worktree path

## Context

### Explanation Page Shape (Divio)

Explanation pages explain concepts, architecture, and "why". They are not tutorials (no step-by-step) and not reference (no flag tables). The structure:

1. Opening: "This document explains X. If you want to do Y instead, see [how-to link]."
2. Background/motivation: why this concept exists
3. Core model: how it works (diagrams, prose, examples of concepts — not commands)
4. Key distinctions / design decisions
5. Known limitations (with issue links)
6. Cross-links to related how-to and reference pages

### Source Materials

Before writing, read:
- `kitty-specs/charter-end-user-docs-828-01KQCSYD/data-model.md` Section 3 — scope notes per explanation page
- `docs/retrospective-learning-loop.md` — existing root-level content (partial; has TODO marker)
- `docs/trail-model.md` if it exists — reference for profile invocation lifecycle

### Key Invariants

1. `charter.md` is the only human-edited governance file.
2. Compact-context limitation must be acknowledged in charter-synthesis-drg.md (issue #787).
3. Profile invocation lifecycle: `(profile, action, governance-context)` triple; `ask`, `advise`, `do` modes; `profile-invocation complete` closes the trail.
4. Retrospective gate: autonomous = mandatory; HiC = skippable with audit trail.

## Subtask Guidance

### T021 — Write docs/explanation/charter-synthesis-drg.md

**File**: `docs/explanation/charter-synthesis-drg.md`  
**Title**: "Understanding Charter: Synthesis, DRG, and Governed Context"  
**FR coverage**: FR-003, FR-006

**Scope** (from data-model.md): what the charter bundle is; how DRG edges are computed; bootstrap vs compact context; why the authoritative-vs-generated distinction matters; known limitations.

**Structure**:
1. Opening: "This document explains the Charter synthesis model and the DRG-backed context system. For a practical walkthrough, see [How Charter Works](../3x/charter-overview.md)."
2. **What the charter bundle is** — The bundle is the machine-readable synthesis of `charter.md`. Explain what's in it (governance.yaml, directives.yaml, etc.) and why it's needed (runtime context injection requires a structured bundle, not raw prose).
3. **How synthesis works** — The synthesizer reads `charter.md`, resolves directive relationships via the DRG (Directive Relationship Graph), and produces the bundle files. Key steps: parse → DRG edge computation → resolve directives → emit bundle.
4. **DRG edge computation** — What DRG edges are: relationships between directives (e.g., D1 implies D2, D3 overrides D4). How the runtime uses these to build action-specific context.
5. **Bootstrap vs compact context** — Bootstrap: full DRG context is injected into the governed profile invocation. Compact: when context is too large, a summarized view is injected. Name the limitation and link issue #787 or document its resolution status. Do NOT promise full-context behavior unconditionally.
6. **Why authoritative vs generated distinction matters** — Editing generated files causes drift that `charter status` will detect; next synthesis will overwrite edits. The only safe edit target is `charter.md`.
7. **Known limitations** — compact-context (with issue link), any other known synthesis limitations.

**Cross-links**:
- `docs/3x/charter-overview.md`
- `docs/3x/governance-files.md`
- `docs/how-to/synthesize-doctrine.md`
- `docs/how-to/troubleshoot-charter.md`

### T022 — Write docs/explanation/governed-profile-invocation.md

**File**: `docs/explanation/governed-profile-invocation.md`  
**Title**: "Understanding Governed Profile Invocation"  
**FR coverage**: FR-007

**Scope** (from data-model.md): the `(profile, action, governance-context)` primitive; `ask`, `advise`, `do` modes; profile invocation lifecycle; `profile-invocation complete`; evidence/artifact correlation; invocation trail model.

**Structure**:
1. Opening: "This document explains governed profile invocation. For how to run a governed mission, see [How to Run a Governed Mission](../how-to/run-governed-mission.md)."
2. **The governed invocation primitive** — Every mission action is a triple: `(profile, action, governance-context)`. The profile is an agent persona; the action is what it's doing; the governance-context is the Charter bundle context injected at invocation time.
3. **Three invocation modes** — explain each:
   - `ask`: the profile asks before acting (human approval required)
   - `advise`: the profile acts but recommends future changes
   - `do`: the profile acts autonomously
4. **Invocation lifecycle** — how an invocation opens, executes, and closes. `profile-invocation complete` is the signal that closes the trail.
5. **The invocation trail** — what gets recorded (evidence artifacts, timestamps, governance-context snapshot). Reference `docs/trail-model.md` if it exists.
6. **Evidence and artifact correlation** — how artifacts produced during an invocation are linked back to the trail record.

**Cross-links**:
- `docs/3x/charter-overview.md`
- `docs/how-to/run-governed-mission.md`
- `docs/reference/profile-invocation.md`

### T023 — Write docs/explanation/retrospective-learning-loop.md

**File**: `docs/explanation/retrospective-learning-loop.md`  
**Title**: "Understanding the Retrospective Learning Loop"  
**FR coverage**: FR-010

**Scope** (from data-model.md): why retrospectives exist; gate model (autonomous mandatory, HiC optional with audit); proposal lifecycle; synthesizer role.

**Source**: Read `docs/retrospective-learning-loop.md` (root level) — it has partial HiC/autonomous content. Transform into Divio explanation shape. Do not copy wholesale; improve structure.

**Structure**:
1. Opening: "This document explains why the retrospective learning loop exists and how it works. For how to run a retrospective, see [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md)."
2. **Why retrospectives exist** — Learning from completed missions drives doctrine improvement. Without retrospectives, governance stagnates.
3. **The gate model** — Two modes:
   - Autonomous: retrospective is mandatory; cannot be skipped; blocks next mission start.
   - HiC (Human in Charge): retrospective can be skipped with explicit operator action; an audit record is always created.
4. **Proposal lifecycle** — The retrospective produces proposals (doctrine changes, directive additions/removals). Proposals are reviewed by `retro synthesizer dry-run` then applied by `retro synthesizer apply`.
5. **The synthesizer's role** — The synthesizer validates proposals against current doctrine, resolves conflicts, and applies accepted proposals to `charter.md`. It is the only path from retrospective output to governance change.
6. **Cross-mission retrospective summary** — Aggregate view across missions (if supported — verify with `uv run spec-kitty retro summary --help`).

**Cross-links**:
- `docs/how-to/use-retrospective-learning.md`
- `docs/reference/retrospective-schema.md`
- `docs/3x/charter-overview.md`

### T024 — Convert docs/retrospective-learning-loop.md to redirect stub

**File**: `docs/retrospective-learning-loop.md` (existing root-level file)

**Action**: Replace the entire content with a one-line redirect stub to preserve existing deep links:

```markdown
This page has moved to [explanation/retrospective-learning-loop.md](explanation/retrospective-learning-loop.md).
```

Keep the DocFX frontmatter block if one exists (do not break the build). If the existing file has `TODO: register in docs nav`, that marker is removed by this replacement.

Verify after writing:
```bash
grep 'TODO' docs/retrospective-learning-loop.md
```
Zero results required.

### T025 — Update docs/explanation/toc.yml; add cross-links from explanation pages

The three explanation pages should already appear in `docs/explanation/toc.yml` (added by WP01). Verify:
```bash
grep -E 'charter-synthesis-drg|governed-profile-invocation|retrospective-learning-loop' docs/explanation/toc.yml
```
All three hrefs must appear. Do not modify the toc in this WP if they are already there.

If `documentation-mission.md` is in the existing toc, verify it is still there after WP01's update.

Verify all explanation pages have cross-links to their how-to counterparts and reference pages:
```bash
grep 'how-to/' docs/explanation/charter-synthesis-drg.md
grep 'how-to/' docs/explanation/governed-profile-invocation.md
grep 'how-to/' docs/explanation/retrospective-learning-loop.md
```
Each should return at least one result.

Also verify:
```bash
grep -r 'TODO' docs/explanation/charter-synthesis-drg.md \
  docs/explanation/governed-profile-invocation.md \
  docs/explanation/retrospective-learning-loop.md
```
Zero results required.

## Definition of Done

- [ ] `charter-synthesis-drg.md` written: bundle, DRG edges, bootstrap vs compact, authoritative/generated distinction, compact-context limitation with issue link
- [ ] `governed-profile-invocation.md` written: triple primitive, ask/advise/do, lifecycle, profile-invocation complete, trail model
- [ ] `retrospective-learning-loop.md` (explanation/) written: why, gate model (both modes), proposal lifecycle, synthesizer role
- [ ] `docs/retrospective-learning-loop.md` (root) converted to one-line redirect stub
- [ ] All three explanation pages use DocFX frontmatter
- [ ] All three pages cross-link to how-to counterparts
- [ ] All three pages appear in `docs/explanation/toc.yml`
- [ ] `grep -r 'TODO' docs/explanation/` → zero results (in new pages)
- [ ] `grep 'TODO' docs/retrospective-learning-loop.md` → zero results
- [ ] `uv run pytest tests/docs/ -q` passes
