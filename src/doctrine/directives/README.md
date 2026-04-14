# Directives

**Directives** are constraint-oriented governance rules that apply across flows or
phases. Each directive encodes a required or advisory expectation and can reference
lower-level tactics for execution.

## Schema

All directive files conform to `directive.schema.yaml` with fields:

- `schema_version` — Schema version string
- `id` — Unique identifier (e.g., `TEST_FIRST`)
- `title` — Human-readable name
- `intent` — What the directive enforces
- `enforcement` — `required` or `advisory`

Cross-artifact relationships (directive → tactic, directive → paradigm, etc.)
are expressed as typed edges in `src/doctrine/graph.yaml`. Inline `tactic_refs`
and `applies_to` fields were removed in Phase 1 excision (mission
`excise-doctrine-curation-and-inline-references-01KP54J6` WP02).

## Naming Convention

Numbered directives follow the pattern `NNN-kebab-title.directive.yaml` (e.g.,
`004-test-driven-implementation-standard.directive.yaml`). Non-numbered directives
use plain kebab-case (e.g., `test-first.directive.yaml`).

## Shipped Directives

Codes 001–019 are shipped reference directives, referenced by the 7 shipped agent
profiles in `agent_profiles/shipped/`. A consistency test verifies that every
directive code referenced by a shipped profile resolves to a file in this directory.

## Glossary Reference

See [Directive](../../../glossary/contexts/doctrine.md#directive) in the doctrine
glossary context.
