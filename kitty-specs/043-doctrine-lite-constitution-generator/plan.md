# Implementation Plan: Doctrine-Lite Deterministic Constitution Generator

## Scope

Deliver a deterministic constitution-first doctrine slice with no agent governance entities and no scaffolding-only doctrine layers.

## Work Packages

### WP01 - Constitution Schema + Sync Simplification

- Remove agent schema classes and `selected_agent_profiles` fields.
- Stop writing/loading `agents.yaml`.
- Update CLI status output and sync file lists.

### WP02 - Deterministic Doctrine Catalog + Resolver

- Add doctrine catalog loader for paradigms/directives/template sets.
- Validate constitution governance selections against catalogs.
- Keep tool registry validation deterministic.

### WP03 - One-Step Constitution Generator

- Add `spec-kitty constitution generate` command.
- Generate deterministic constitution markdown with mission + doctrine selections.
- Auto-run sync after generation.

### WP04 - Runtime Context Injection

- Inject governance context into `spec-kitty next` prompt generation for both template and WP paths.

### WP05 - Doctrine Asset Slimming

- Remove scaffolding-only doctrine directories not used by runtime.
- Ensure concrete paradigm/directive assets exist and are referenced.

### WP06 - Test + Validation

- Update constitution schema/extractor/sync/integration/CLI tests.
- Add generator and governance-context prompt tests.
- Run targeted pytest suites.
