# Tactics

**Tactics** are reusable behavioral execution patterns that define how work is
performed. They are operational, agent-consumable, and can be selected by directives
and mission context.

## Schema

Tactic files conform to `tactic.schema.yaml` with fields for step sequences (each
with title, description, examples) and reference objects.

## Naming Convention

Files use the pattern `kebab-id.tactic.yaml` (e.g., `zombies-tdd.tactic.yaml`).

## Shipped Tactics

| Tactic | Steps | Purpose |
|--------|-------|---------|
| `acceptance-test-first` | 6 | ATDD acceptance-first workflow |
| `tdd-red-green-refactor` | 6 | Classic Red/Green/Refactor loop with guardrails |
| `zombies-tdd` | 7 | Z/O/M/B/I/E/S progressive test complexity |
| `glossary-curation-interview` | 11 | Systematic glossary expansion with HiC curation rounds |

Tactics are referenced by directives and procedures via typed edges in
`src/doctrine/graph.yaml` (relation `requires`). Inline `tactic_refs` fields
were removed in Phase 1 excision (mission
`excise-doctrine-curation-and-inline-references-01KP54J6` WP02); the graph is
now the sole authority for cross-artifact relationships.

## Glossary Reference

See [Tactic](../../../glossary/contexts/doctrine.md#tactic) in the doctrine glossary
context.
