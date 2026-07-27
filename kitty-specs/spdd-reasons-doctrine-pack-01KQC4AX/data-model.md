# Phase 1 Data Model — SPDD/REASONS Artifact Shapes

## Paradigm: `structured-prompt-driven-development.paradigm.yaml`

**Path**: `src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml`

```yaml
schema_version: "1.0"
id: structured-prompt-driven-development
name: Structured-Prompt-Driven Development
summary: >
  Treat structured prompts and REASONS canvases as governed change-intent and
  decision-boundary artifacts. Code remains the source of truth for current
  behavior; canvases record approved intent, boundaries, and safeguards for a
  mission or work package.
applicability:
  - High-risk missions where multiple agents must align before implementation.
  - Multi-WP missions where change-boundary clarity reduces drift.
when_not_to_use:
  - Tiny fixes, throwaway spikes, emergency patches.
  - Purely visual exploration where canvas authoring is overhead.
related:
  tactics:
    - reasons-canvas-fill
    - reasons-canvas-review
  directives:
    - DIRECTIVE_038
  styleguides:
    - reasons-canvas-writing
```

## Tactic: `reasons-canvas-fill.tactic.yaml`

**Path**: `src/doctrine/tactics/shipped/reasons-canvas-fill.tactic.yaml`

Required: `id`, `schema_version`, `name`, `steps[]` (each step requires `title`).

```yaml
schema_version: "1.0"
id: reasons-canvas-fill
name: REASONS Canvas Fill
purpose: >
  Generate or update a mission-level REASONS canvas (Requirements, Entities,
  Approach, Structure, Operations, Norms, Safeguards) by reading mission
  artifacts and producing concise, traceable content.
steps:
  - title: Detect activation
    description: Confirm the project's charter selected SPDD/REASONS doctrine; if not, escalate.
  - title: Load mission context
    description: Read spec.md, plan.md, tasks.md, WP prompts, charter context, glossary, research, contracts, and code surfaces relevant to the mission.
  - title: Author or update canvas
    description: Write or revise kitty-specs/<mission>/reasons-canvas.md following the seven-section structure. Preserve user-authored content; merge rather than overwrite.
  - title: Compile WP summaries (optional)
    description: For each work package, summarize WP-scoped Requirements/Operations/Norms/Safeguards as a compact block usable inside the implement prompt.
  - title: Stop at change boundary
    description: Do not invent entities, files, or scope beyond the approved canvas. Open a deviation note when reality demands changes.
references:
  - directive: DIRECTIVE_038
  - styleguide: reasons-canvas-writing
  - paradigm: structured-prompt-driven-development
```

## Tactic: `reasons-canvas-review.tactic.yaml`

```yaml
schema_version: "1.0"
id: reasons-canvas-review
name: REASONS Canvas Review
purpose: >
  Use the canvas as a comparison surface during work-package review and classify
  any divergence as approved deviation, scope drift, or safeguard violation.
steps:
  - title: Detect activation
    description: Skip the gate entirely if the project's charter has not selected SPDD/REASONS.
  - title: Trace implementation to canvas
    description: For each Requirement and Operation in the active canvas, find concrete evidence in the diff or note its absence.
  - title: Detect uninvented entities and files
    description: Flag entities, files, or surfaces touched by the diff that do not appear in Structure or Approach.
  - title: Verify Norms and Safeguards
    description: Verify that observability, testing, and safeguard rules in the canvas remain honored.
  - title: Classify divergence
    description: Choose one of (a) approved deviation (record in canvas), (b) unrecorded scope drift (block), (c) safeguard violation (block), (d) canvas update, (e) glossary update, (f) charter follow-up, (g) follow-up mission. Charter directives take precedence over canvas content.
references:
  - directive: DIRECTIVE_038
  - tactic: reasons-canvas-fill
```

## Styleguide: `reasons-canvas-writing.styleguide.yaml`

Required: `id`, `schema_version`, `title`, `scope` (enum), `principles[]`.

```yaml
schema_version: "1.0"
id: reasons-canvas-writing
title: REASONS Canvas Writing Styleguide
scope: docs
principles:
  - Lead each section with a one-sentence summary, then bullet specifics.
  - Use canvas to capture intent, not to mirror code.
  - Link to source artifacts (spec, plan, tasks, contracts) instead of duplicating them.
  - Distinguish "must" (Safeguard), "should" (Norm), and "may" (Approach option).
  - Keep WP summaries to ≤200 words.
  - Record deviations in a "Deviations" subsection rather than rewriting prior approved content.
```

## Directive: `038-structured-prompt-boundary.directive.yaml`

Required: `id` (UPPERCASE), `schema_version`, `title`, `intent`, `enforcement`. If `lenient-adherence`, `explicit_allowances` is required.

```yaml
schema_version: "1.0"
id: DIRECTIVE_038
title: Structured Prompt Change-Boundary
intent: >
  When the SPDD/REASONS doctrine pack is active, an implementation must remain
  inside the approved canvas's Requirements, Operations, Norms, and Safeguards
  unless a deviation is explicitly recorded.
enforcement: lenient-adherence
explicit_allowances:
  - Documented approved deviation captured in kitty-specs/<mission>/reasons-canvas.md "Deviations".
  - Glossary update follow-up that resolves a terminology conflict surfaced by review.
  - Charter follow-up that revises the active doctrine selection.
  - Follow-up mission that addresses out-of-bounds work as a separate deliverable.
applies_when:
  - The project's charter selection includes paradigm structured-prompt-driven-development OR tactic reasons-canvas-fill OR tactic reasons-canvas-review OR directive DIRECTIVE_038.
applies_to_actions:
  - implement
  - review
related:
  - paradigm: structured-prompt-driven-development
  - tactic: reasons-canvas-fill
  - tactic: reasons-canvas-review
```

## Template fragment: `reasons-canvas-template.md`

**Path**: `src/doctrine/templates/fragments/reasons-canvas-template.md`

```markdown
# REASONS Canvas — <Mission Title>

> Mission: <mission-slug>
> Generated: <YYYY-MM-DD>
> Charter activation: structured-prompt-driven-development (paradigm)

## Requirements
- Problem statement: <one sentence>
- Acceptance criteria: <bulleted list>
- Definition of done: <bulleted list>

## Entities
- Domain concepts and relationships: <list>
- Glossary terms (canonical): <list with definitions>

## Approach
- Selected strategy: <summary>
- Tradeoffs considered: <list>

## Structure
- Code surfaces affected: <files / packages>
- Components and dependencies: <list>
- Ownership boundaries: <list>

## Operations
- Ordered implementation steps: <list>
- Test strategy: <list>

## Norms
- Coding/style conventions: <list>
- Observability, testing, and team rules: <list>

## Safeguards
- Hard constraints and invariants: <list>
- Security rules: <list>
- Performance limits: <list>
- Things not to break: <list>

## Deviations (append-only)
- <date> — <wp> — <description> — <rationale>
```

## Skill: `spec-kitty-spdd-reasons/SKILL.md`

**Path**: `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md`

Frontmatter mirrors `spec-kitty-charter-doctrine/SKILL.md`:

```markdown
---
name: spec-kitty-spdd-reasons
description: |
  Drive REASONS Canvas authoring and review for missions that opted in to SPDD via charter.
  Triggers: "use SPDD", "use REASONS", "generate a REASONS canvas",
  "apply structured prompt driven development", "make this mission SPDD".
  Does NOT handle: enforcing SPDD on projects whose charter has not selected the doctrine pack.
---

# spec-kitty-spdd-reasons

## What this skill does
- Detects whether the project's charter selected SPDD/REASONS doctrine.
- Loads mission context (spec.md, plan.md, tasks.md, WP prompts, charter context, glossary, research, contracts, code).
- Generates or updates `kitty-specs/<mission>/reasons-canvas.md`.
- Compiles per-WP REASONS summaries when useful.
- In review mode, compares implementation against the canvas and classifies divergences.

## What this skill does NOT do
- Mirror the entire codebase into the canvas.
- Overwrite user-authored mission artifacts. Merge; preserve intent.
- Silently enforce SPDD on projects that have not selected the doctrine. Escalate instead.

## Activation rules
- If the charter has selected the doctrine, proceed with canvas authoring or review.
- If not, and the user requests ad-hoc canvas generation, proceed but record that the project is not formally opted in.
- If not, and the user demands enforcement, escalate to the charter workflow.
```

## Active-doctrine detection contract

```python
def is_spdd_reasons_active(repo_root: Path) -> bool:
    """True iff the project's charter selection includes any one of the SPDD pack artifacts."""
```

Reads `.kittify/charter/governance.yaml` and/or `directives.yaml` via existing charter loaders. Returns True if ANY of these IDs is present in the active set:
`structured-prompt-driven-development`, `reasons-canvas-fill`, `reasons-canvas-review`, `DIRECTIVE_038`.

## Drift classification state machine

```
DivergenceDetected
   ├── No -> APPROVE
   └── Yes
        ├── Already in canvas Deviations -> APPROVE (with note)
        ├── Violates Safeguard -> BLOCK (safeguard_violation)
        ├── Out of bounds, undocumented -> BLOCK (scope_drift)
        └── In bounds but new info reveals canvas was wrong -> RECORD one of:
             * canvas_update
             * glossary_update
             * charter_follow_up
             * follow_up_mission
```

Charter directives take precedence over canvas content (FR-016 last clause).
