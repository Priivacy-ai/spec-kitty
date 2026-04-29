---
work_package_id: WP06
title: SPDD/REASONS Documentation
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-019
- FR-020
- C-005
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T022
- T023
agent: "claude:opus:curator-carla:implementer"
shell_pid: "49611"
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: curator-carla
authoritative_surface: docs/doctrine/
execution_mode: planning_artifact
model: claude-opus-4-7
owned_files:
- docs/doctrine/spdd-reasons.md
- docs/doctrine/README.md
- docs/charter.md
role: implementer
tags:
- docs
---

## ⚡ Do This First: Load Agent Profile

- Run `/ad-hoc-profile-load` with profile `curator-carla` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/curator-carla.agent.yaml`.
- After load, restate identity, governance scope, and boundaries before continuing.

# WP06 — SPDD/REASONS Documentation

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP06 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Author user-facing documentation for the SPDD/REASONS doctrine pack at `docs/doctrine/spdd-reasons.md`, plus inbound links from existing doctrine and charter docs.

The doc must explain (per spec FR-019):

1. What SPDD means in Spec Kitty.
2. What the REASONS Canvas is.
3. How to activate the pack through charter selection.
4. How mission/WP canvases are generated and reviewed.
5. How it differs from "prompts/specs as source of truth" (Spec Kitty's adaptation: code is current-behavior source of truth).
6. When NOT to use it (tiny fixes, throwaway spikes, emergency patches, pure visual exploration).
7. Two examples: lightweight mission + high-risk multi-WP mission where DIRECTIVE_038 is useful.

## Context

### Spec & seed material
- FR-019, FR-020, C-005.
- [quickstart.md](../quickstart.md) — seed for activation walkthrough and examples.
- [data-model.md](../data-model.md) — full canvas section semantics.
- [research.md](../research.md) — ADRs and risk register.

### Existing doc layout
Find canonical inbound link locations BEFORE writing the new doc:
- `docs/doctrine/README.md` (or equivalent doctrine index)
- `docs/charter.md` (or equivalent charter doc)
- `docs/explanation/` (architecture/philosophy explanations)
- Any mission workflow docs (`docs/mission-*.md` etc.)

If `docs/doctrine/README.md` does not exist, choose the most natural index file under `docs/`.

## Subtasks

### T022 — Author `docs/doctrine/spdd-reasons.md`

**Path**: `docs/doctrine/spdd-reasons.md`

Suggested outline (≥6 sections, ≤700 lines):

```markdown
# SPDD and the REASONS Canvas (opt-in doctrine pack)

## Why this exists
- One paragraph framing: high-risk and multi-WP missions benefit from explicit
  change-intent and change-boundary artifacts.

## Spec Kitty's adaptation of SPDD
- Code remains the source of truth for current behavior.
- Structured prompts and the REASONS canvas are change-intent and
  decision-boundary artifacts.
- "Sync" means keeping the mission's intent record and change boundary
  accurate, NOT mirroring the codebase as prose. (C-005)

## What the REASONS Canvas is
- Seven sections: Requirements, Entities, Approach, Structure, Operations,
  Norms, Safeguards.
- Plus an append-only Deviations section.
- Per-mission canvas at `kitty-specs/<mission>/reasons-canvas.md`.

## Activation
- Run the charter interview and select any one of:
  - paradigm `structured-prompt-driven-development`
  - tactic `reasons-canvas-fill`
  - tactic `reasons-canvas-review`
  - directive `DIRECTIVE_038`
- Inactive projects see no behavior change.

## Lifecycle behavior when active
- specify → Requirements + Entities guidance.
- plan → Approach + Structure guidance.
- tasks → Operations + WP-boundary guidance.
- implement → full WP-scoped canvas.
- review → canvas as comparison surface; drift gate active.

## Generating and updating the canvas
- Trigger phrases: "use SPDD", "use REASONS", "generate a REASONS canvas",
  "apply structured prompt driven development", "make this mission SPDD".
- The skill `spec-kitty-spdd-reasons` loads mission context and authors the
  canvas, preserving any user-authored content.

## The review gate
- Drift outcomes: approved, approved_with_deviation, canvas_update_needed,
  glossary_update_needed, charter_follow_up, follow_up_mission,
  scope_drift_block, safeguard_violation_block.
- Charter directives take precedence over canvas content.

## When NOT to use it
- Tiny fixes (typos, single-line bug fixes).
- Throwaway spikes you intend to discard.
- Emergency patches.
- Pure visual exploration where the canvas is overhead.

## Example A: lightweight mission
- "Rename `foo_v2` API surface to `foo`."
- Canvas captures Requirements (user impact), Operations (rename steps),
  Safeguards (deprecation timeline). Approach/Structure/Norms can be brief.

## Example B: high-risk multi-WP mission (DIRECTIVE_038 useful)
- "Introduce new auth middleware."
- Canvas covers all seven sections in detail, with explicit Safeguards (no
  plaintext token in logs, no breaking change to OAuth callbacks). Reviewer
  uses the canvas at every WP review.

## How this differs from prompts-as-truth
- SPDD literature treats prompt and code as co-truth. Spec Kitty does NOT.
- Code is current-behavior truth; canvas is change-intent record.

## Related artifacts
- Paradigm: `src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml`
- Tactics: `reasons-canvas-fill`, `reasons-canvas-review`
- Styleguide: `reasons-canvas-writing`
- Directive: `DIRECTIVE_038`
- Template fragment: `src/doctrine/templates/fragments/reasons-canvas-template.md`
- Skill: `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md`
```

Adapt section ordering to match existing `docs/doctrine/*` voice if there is one.

### T023 — Add inbound links

Identify the canonical doctrine and charter index docs and add a one-line link:

- In `docs/doctrine/README.md` (or equivalent): list the new doc under "Optional doctrine packs" or similar.
- In `docs/charter.md` (or equivalent): mention the pack as an optional selection.
- In any mission workflow doc that enumerates lifecycle actions: mention conditional REASONS guidance.

Do NOT modify other docs' tone or structure; insert minimal link entries only.

## Definition of Done

- `docs/doctrine/spdd-reasons.md` exists with all 11 outlined sections (or equivalent coverage).
- Both required examples (lightweight + high-risk) are present.
- The "When NOT to use it" section is present.
- The C-005 distinction (canvas is change-intent, code is current-behavior truth) is explicit.
- At least two inbound links from existing doctrine/charter docs.
- No formatting regressions in other docs.

## Reviewer guidance

- Confirm the doc explains the philosophical distinction from SPDD-as-co-truth.
- Confirm the activation walkthrough is accurate (paradigm OR tactics OR directive — any one is sufficient).
- Confirm the two examples are concrete enough to be copy-pasteable.
- Confirm no inbound link site was rewritten beyond the link addition.

## Risks

- **Doc index drift**: doctrine and charter index files may have shifted; do not invent paths. Confirm before adding links.
- **C-005 wording**: this is the philosophical guardrail of the entire mission. Do NOT soften it.

## Out of scope

- Code changes (this is documentation only).
- Glossary changes (out of scope; use the glossary skill if any term needs canonicalization).

## Activity Log

- 2026-04-29T09:20:43Z – claude:opus:curator-carla:implementer – shell_pid=49611 – Started implementation via action command
