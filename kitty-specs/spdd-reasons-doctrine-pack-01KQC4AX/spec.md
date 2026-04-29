# Mission Specification: Opt-in SPDD and REASONS Canvas Doctrine Pack

> Mission ID: `01KQC4AX9R4BJ40WWND37CCCJT`
> Slug: `spdd-reasons-doctrine-pack-01KQC4AX`
> Mission Type: `software-dev`
> Created: 2026-04-29
> Source: `.kittify/mission-brief.md` (extracted from epic #873)

## Purpose

Ship an opt-in doctrine pack that lets Spec Kitty projects activate Structured-Prompt-Driven Development (SPDD) and the REASONS Canvas pattern through charter selection, with no behavior change for projects that do not select it.

The pack adapts Martin Fowler's SPDD/REASONS framing to Spec Kitty's philosophy: code remains the source of truth for current behavior, while structured prompts and canvases capture change-intent and decision boundaries for missions and work packages.

## User Scenarios & Testing

### Primary Scenario: Activating SPDD/REASONS for a high-risk mission

1. A team operating Spec Kitty selects the new `structured-prompt-driven-development` paradigm during charter interview, along with the `reasons-canvas-fill` and `reasons-canvas-review` tactics and `DIRECTIVE_038`.
2. The team starts a new mission. The `specify` action injects guidance for filling Requirements and Entities. The `plan` action injects guidance for Approach and Structure. The `tasks` action injects guidance for Operations and WP boundaries.
3. The implementer agent receives WP-scoped REASONS context as part of the implement prompt.
4. The reviewer agent uses the canvas as a comparison surface; if the implementation drifts from the canvas, the reviewer either records an approved deviation, schedules a canvas update, or rejects the WP.
5. After merge, the mission's REASONS canvas remains in `kitty-specs/<mission>/reasons-canvas.md` as a record of approved intent.

### Secondary Scenario: Project that does not select the pack

1. A team has not selected the SPDD/REASONS doctrine.
2. They run `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.implement`, and `/spec-kitty.review` exactly as they did before.
3. Generated artifacts, prompt text, and review behavior are identical to current Spec Kitty output (no SPDD or REASONS sections, no new gates, no new context lines).

### Edge Cases

- **Activation mid-mission**: If a project activates SPDD/REASONS after a mission has already started, the skill must generate the canvas from existing artifacts without overwriting user-authored content.
- **Conflict between code reality and canvas**: When implementation diverges from the canvas, the reviewer must categorize the divergence as approved deviation, scope drift, or safeguard violation.
- **Trivial missions**: The skill must warn against using REASONS for tiny fixes, throwaway spikes, or emergency patches.
- **Charter never selected the pack but user invokes the skill**: The skill must escalate rather than silently enforce; ad-hoc canvas generation may proceed if explicitly requested.

### Acceptance Walkthrough

- Activate the pack via charter; run a full mission lifecycle (specify → plan → tasks → implement → review). Confirm REASONS sections appear at each phase.
- Without the pack, run the same lifecycle. Confirm output is unchanged (snapshot or golden test).
- Trigger a deliberate scope-drift in an implement WP. Confirm reviewer flags it under the new gate.
- Trigger a deliberate scope-drift on a project without the pack. Confirm reviewer behavior is unchanged.

## Functional Requirements

| ID     | Requirement                                                                                                                                                                                                                                                                                                                       | Status   |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-001 | The system MUST ship a paradigm artifact at `src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml` that defines SPDD in Spec Kitty terms (structured prompts as governed change-intent artifacts; code is current-behavior source of truth; canvas records approved intent and boundaries).            | proposed |
| FR-002 | The system MUST ship two tactic artifacts: `reasons-canvas-fill` (mission-level canvas authoring) and `reasons-canvas-review` (canvas-vs-implementation review).                                                                                                                                                                  | proposed |
| FR-003 | The system MUST ship a styleguide artifact `reasons-canvas-writing` that defines voice, structure, and section ordering for REASONS canvas content.                                                                                                                                                                              | proposed |
| FR-004 | The system MUST ship a directive `038-structured-prompt-boundary` that codifies the change-boundary rule (implementations must stay within approved canvas Requirements/Operations/Norms/Safeguards unless deviation is documented).                                                                                              | proposed |
| FR-005 | The system MUST ship a template fragment `src/doctrine/templates/fragments/reasons-canvas-template.md` containing the seven canvas sections: Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards.                                                                                                          | proposed |
| FR-006 | All shipped artifacts MUST validate against the existing doctrine schemas (`paradigm.schema.yaml`, `tactic.schema.yaml`, `styleguide.schema.yaml`, `directive.schema.yaml`) without changes to those schemas.                                                                                                                     | proposed |
| FR-007 | The charter interview/generation flow MUST allow selection of the new paradigm, tactics, and directive as optional library items (not defaults).                                                                                                                                                                                  | proposed |
| FR-008 | When the new pack is selected, the generated `governance.yaml`, `references.yaml`, and `.kittify/charter/library/*` MUST include the SPDD/REASONS entries; when not selected, those files MUST NOT include them.                                                                                                                  | proposed |
| FR-009 | The `spec-kitty charter context --action <action>` command MUST inject SPDD/REASONS guidance only when the corresponding doctrine items are present in the active selection. Action scoping MUST be: `specify` → Requirements/Entities; `plan` → Approach/Structure; `tasks` → Operations/WP boundaries; `implement` → full WP-level canvas; `review` → comparison surface for Requirements/Operations/Norms/Safeguards. | proposed |
| FR-010 | The system MUST ship a skill at `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md` whose triggers include "use SPDD", "use REASONS", "generate a REASONS canvas", "apply structured prompt driven development", "make this mission SPDD".                                                                                  | proposed |
| FR-011 | The skill MUST instruct agents to (a) detect charter activation status, (b) load mission context (`spec.md`, `plan.md`, `tasks.md`, WP prompts, charter context, glossary, research, contracts, code), (c) generate or update `kitty-specs/<mission>/reasons-canvas.md`, (d) optionally compile per-WP REASONS summaries, (e) compare implementation against the canvas in review mode. | proposed |
| FR-012 | The skill MUST warn against using REASONS as a complete system mirror, against overwriting user-authored mission artifacts, and MUST escalate (rather than silently enforce) if the charter has not selected SPDD/REASONS but the user demands enforcement.                                                                       | proposed |
| FR-013 | Mission and WP prompts MUST conditionally render REASONS-related sections only when the active doctrine context includes the new paradigm, tactics, or directive. When inactive, prompt output MUST be byte-identical (or semantically equivalent) to current output.                                                              | proposed |
| FR-014 | The implement prompt MUST, when active, include WP-specific Requirements, Entities, Approach, Structure, Operations, Norms, and Safeguards drawn from (or linked to) the mission canvas. Duplication of full spec/plan content MUST be avoided in favor of links.                                                                  | proposed |
| FR-015 | The review prompt MUST, when active, include the canvas as a comparison surface and instruct the reviewer to check trace-to-Requirements, no invented entities/architecture/files beyond the boundary, and Norms/Safeguard adherence.                                                                                              | proposed |
| FR-016 | The review gate MUST classify divergences as one of: documented approved deviation; unrecorded scope drift (block); safeguard violation (block). Charter directives still take precedence over canvas content.                                                                                                                    | proposed |
| FR-017 | When code reality proves the canvas was wrong, the reviewer MUST record one of: canvas update, deviation note, glossary update, charter follow-up, or follow-up mission.                                                                                                                                                          | proposed |
| FR-018 | The review gate MUST only activate for projects whose charter selected the SPDD/REASONS pack.                                                                                                                                                                                                                                     | proposed |
| FR-019 | The system MUST ship documentation explaining (a) what SPDD means in Spec Kitty, (b) what the REASONS Canvas is, (c) how to activate the pack, (d) how mission/WP canvases are generated and reviewed, (e) how it differs from "prompts/specs as source of truth", (f) when not to use it (tiny fixes, throwaway spikes, emergency patches), and (g) at least two examples (one lightweight, one high-risk). | proposed |
| FR-020 | Documentation MUST be linked from existing doctrine and charter docs and from the mission workflow docs.                                                                                                                                                                                                                          | proposed |

## Non-Functional Requirements

| ID      | Requirement                                                                                                                                                                                       | Threshold                                                                                                       | Status   |
|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|----------|
| NFR-001 | Inactive projects MUST see zero changes to prompt output, charter context output, or review behavior.                                                                                              | Snapshot/golden tests covering specify, plan, tasks, implement, review prompts pass byte-for-byte (or semantic-equivalence) before vs after this mission, for a project without the pack selected. | proposed |
| NFR-002 | Charter context generation MUST remain within current performance bounds when the pack is active.                                                                                                  | `spec-kitty charter context --action <action>` returns within 2 seconds for a typical project (≤100 directives). | proposed |
| NFR-003 | New shipped artifacts MUST be discoverable through the same repository/DRG paths as comparable shipped artifacts (no new artifact kind, no new loader path).                                       | Existing `find-shipped` doctrine repository tests pass for the new artifacts.                                    | proposed |
| NFR-004 | All new doctrine YAML and schema-bound files MUST pass schema validation in the existing test suite.                                                                                                | `uv run pytest tests/doctrine -q` passes including new artifacts.                                                | proposed |
| NFR-005 | Type checking MUST remain clean.                                                                                                                                                                    | `mypy --strict` passes on touched modules.                                                                       | proposed |
| NFR-006 | New code paths MUST have ≥ 90% test coverage.                                                                                                                                                       | Coverage report on new modules ≥ 90%.                                                                            | proposed |

## Constraints

| ID    | Constraint                                                                                                                                                                                                       | Status   |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| C-001 | The pack MUST NOT be hardwired into every user's workflow. Activation must be explicit through charter selection.                                                                                                | proposed |
| C-002 | The pack MUST NOT change behavior for existing projects that do not select it.                                                                                                                                   | proposed |
| C-003 | The implementation MUST prefer adding normal shipped doctrine artifacts over creating a new artifact kind.                                                                                                       | proposed |
| C-004 | Global template edits that permanently insert REASONS into all prompts are NOT allowed. Any template fragment must be rendered conditionally on active doctrine context.                                         | proposed |
| C-005 | Spec Kitty MUST NOT adopt SPDD's "prompt and code stay synchronized as co-truth" stance wholesale. "Sync" in Spec Kitty means keeping the mission's intent record and change boundary accurate, not maintaining a full prose mirror of the codebase. | proposed |
| C-006 | All work MUST land on branch `doctrine/spdd-reasons-pack` and reference issues #873–#879.                                                                                                                          | proposed |
| C-007 | Existing doctrine schemas (`paradigm`, `tactic`, `styleguide`, `directive`) MUST NOT be modified for this mission unless absolutely required; if modified, regression tests MUST cover both old and new shapes. | proposed |

## Domain Language (Optional)

| Term                | Canonical Meaning                                                                                                                                                                                  | Avoid Synonyms                              |
|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| SPDD                | Structured-Prompt-Driven Development; in Spec Kitty: structured prompts are governed delivery/change-intent artifacts.                                                                              | "spec-driven prompting", "PDD"              |
| REASONS Canvas      | The seven-section artifact (Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards) capturing approved change-intent for a mission or work package.                            | "REASONS doc", "intent canvas"              |
| Doctrine Pack       | A bundle of related shipped doctrine artifacts (paradigm + tactics + styleguide + directive + template fragment + skill + docs) selectable as a unit.                                              | "policy bundle"                             |
| Change Boundary     | The set of Requirements, Operations, Norms, and Safeguards in the canvas that bound an implementation.                                                                                              | "scope fence"                               |
| Active Doctrine     | The set of paradigms/tactics/styleguides/directives selected via charter for the current project.                                                                                                  | "selected doctrine", "doctrine selection"   |

## Key Entities

- **Paradigm artifact** (`structured-prompt-driven-development.paradigm.yaml`): defines philosophy and applicability.
- **Tactic artifacts** (`reasons-canvas-fill.tactic.yaml`, `reasons-canvas-review.tactic.yaml`): operational playbooks for canvas authoring and review.
- **Styleguide artifact** (`reasons-canvas-writing.styleguide.yaml`): voice/structure rules for canvas content.
- **Directive artifact** (`038-structured-prompt-boundary.directive.yaml`): the change-boundary rule.
- **Template fragment** (`reasons-canvas-template.md`): the seven-section canvas skeleton.
- **Mission canvas** (`kitty-specs/<mission>/reasons-canvas.md`): runtime artifact authored by the skill.
- **Skill** (`spec-kitty-spdd-reasons/SKILL.md`): agent-facing trigger and instructions.

## Success Criteria

| ID    | Criterion                                                                                                                                                                                | Measure                                                                                              |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| SC-01 | A team can activate the pack through charter selection and receive REASONS guidance at each lifecycle phase.                                                                              | Manual run-through plus automated test that asserts presence of REASONS sections when active.        |
| SC-02 | A team that does not select the pack sees no behavior change.                                                                                                                             | Snapshot/golden tests pass byte-or-semantic-identical for inactive projects.                         |
| SC-03 | The skill can generate or update a mission-level REASONS canvas from existing artifacts.                                                                                                 | Skill instructions cover all required steps; smoke test produces a canvas with all seven sections.   |
| SC-04 | The review gate flags scope drift only on active projects.                                                                                                                                | Test fixture: drift in active project blocks; same drift in inactive project does not block.         |
| SC-05 | All new artifacts pass existing doctrine schema and compliance tests.                                                                                                                     | `uv run pytest tests/doctrine -q` green.                                                              |
| SC-06 | Documentation explains the philosophy, activation, examples, and non-uses of the pack and is linked from doctrine/charter/mission docs.                                                  | Reviewer confirms presence of all required doc sections and inbound links.                            |

## Assumptions

- Existing doctrine schemas already support paradigms, tactics, styleguides, and directives with shipped/project distinction; no schema change is required.
- Charter context injection already supports per-action scoping at a code level; the work is to wire the new artifacts into existing scoping.
- Template fragments can be rendered conditionally via existing context plumbing or a small extension thereof; we will not invent a new template engine.
- The skill follows existing skill patterns under `src/doctrine/skills/`.
- Issues #873–#879 are reference scope; this mission may close them as appropriate when implementation lands.

## Deferred Decisions

(None at spec time; all open questions are answered by start-here.md or by existing repo conventions discoverable during plan phase.)

## Out of Scope

- Building a separate REASONS-canvas editor or visualization UI.
- Auto-syncing canvas content to live code (the philosophy explicitly forbids this; code remains the source of truth).
- Backfilling REASONS canvases for historical missions.
- Migrating non-SPDD/REASONS projects automatically.
- Changes to merge, lane, or worktree mechanics.

## Dependencies

- Existing doctrine schemas under `src/doctrine/schemas/`.
- Existing charter selection and `charter context` machinery.
- Existing skill loader and prompt template engine.
- GitHub issues #873 (parent), #874–#879 (children).
