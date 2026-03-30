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

Tactics are referenced by directives via the `tactic_refs` field (e.g., the
`test-first` directive references `acceptance-test-first`, `tdd-red-green-refactor`,
and `zombies-tdd`).

## Glossary Reference

See [Tactic](../../../glossary/contexts/doctrine.md#tactic) in the doctrine glossary
context.
