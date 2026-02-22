# Implementation Plan: Constitution Interview Compiler + First-Load Context Bootstrap

## Scope

Deliver interview-first constitution generation plus deterministic first-load constitution context injection for core lifecycle actions.

## Work Packages

### WP01 - PRD + Data Model

- Define interview answer schema and reference manifest structure.
- Define context bootstrap state model per action.

### WP02 - Interview Persistence + CLI

- Add constitution interview persistence module.
- Add `spec-kitty constitution interview` command.

### WP03 - Constitution Compiler

- Add compiler that combines interview answers and doctrine catalog.
- Generate `constitution.md`, `references.yaml`, and `library/*.md`.
- Preserve sync extraction into governance/directives/metadata.

### WP04 - Context Bootstrap Runtime

- Add context builder with first-load tracking per action.
- Add `spec-kitty constitution context --action ...` command.
- Integrate with `next` prompt builder.

### WP05 - Workflow + Template Integration

- Inject constitution context into `agent workflow implement/review` prompt output.
- Update software-dev `specify/plan/implement/review` command templates to load constitution context.

### WP06 - Tests + Validation

- Add constitution interview/compiler/context tests.
- Update CLI and prompt builder tests.
- Run focused pytest suites.
