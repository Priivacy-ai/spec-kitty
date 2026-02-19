# Tracking Issue 06: Stable Terminology and Role Lookup

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Terminology can drift across missions, templates, doctrine artifacts, and curation notes. Drift causes context fragmentation, misinterpretation, and slower execution for agents that need fast conceptual alignment.

## Desired Behavior

A single canonical terminology surface is maintained for the project and referenced consistently across governance artifacts, mission assets, and agent-facing instructions, with fast lookup support for `designer`, `implementer`, and `reviewer` roles.

The initiative uses Contextive glossary artifacts so the Human In Charge can keep terminology governance lightweight: YAML is machine-readable for automation, and Contextive has broad IDE/plugin ecosystem support for popular development workflows.

## Acceptance Criteria

1. Canonical terms for governance and orchestration concepts are defined once and referenced consistently across the initiative artifacts.
2. Terminology aliases and discouraged synonyms are documented where collisions are known (for example mission vs approach vs tactic semantics).
3. Agent-role workflows (`designer`, `implementer`, `reviewer`) include explicit pointers to the canonical concept source for quick lookup during task execution.
4. New doctrine/mission/template changes in this initiative include a terminology consistency check before merge.
5. Ongoing glossary artifact implementation remains tracked and reproducible from canonical markdown sources to compiled Contextive outputs.
6. Each source directory in scope includes its own Contextive glossary file that can import terminology from deployed `.kittify/memory` glossaries, and these references are discoverable through the project-level aggregate `project.glossary.yml`.

## Ongoing Implementation: Glossary Artifacts

Canonical sources (authoritative):

- `glossary/contexts/*.md`
- `glossary/README.md`
- `glossary/historical-terms.md`
- `src/specify_cli/glossary/` (runtime glossary pipeline, models, middleware, and resolution logic)

Compiled artifacts (agent-consumable outputs):

- `.kittify/memory/spec-kitty.glossary.yml`
- `.kittify/memory/contexts/*.glossary.yml`
- `project.glossary.yml` (project-level aggregate imports entrypoint)

Compilation pipeline:

- `scripts/chores/glossary-compilation.py`
- Contextive glossary format (`*.glossary.yml`) for IDE/runtime lookup

Implementation checkpoints:

1. Canonical markdown glossary remains the single source of truth.
2. Compilation to `.kittify/memory` is deterministic and repeatable.
3. Generated glossary artifacts are validated for parse integrity.
4. Role workflows (`designer`/`implementer`/`reviewer`) reference the compiled glossary entrypoints for concept lookup.

## Notes

- Rationale: prevent context drift and reduce interpretation variance between agents and contributors.
- Source anchor: `references/2026-02-17-mission-approach-fit-review.md` (semantic collision risk).
- Source anchor: ADR `architecture/adrs/2026-02-17-1-explicit-governance-layer-model.md` (glossary/model alignment as confirmation condition).
- Source anchor: `kitty-specs/053-doctrine-governance-layer-refactor/tasks.md` (WP04 glossary and Contextive sync).
- Contextive guide: `https://docs.contextive.tech/community/guides/setting-up-glossaries/` (YAML glossary setup and IDE discovery behavior).
- Implementation source anchor: `src/specify_cli/glossary/`.
