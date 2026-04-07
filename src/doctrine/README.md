# Doctrine

The **doctrine** package is a standalone catalog of reusable governance
knowledge. It ships typed, schema-validated YAML artifacts that define *how work
should be done* — independent of any specific project or charter configuration.

## What it contains

| Artifact kind | Directory | What it defines |
|---|---|---|
| **Paradigm** | `paradigms/` | Worldview-level framing (e.g. test-first, DDD) |
| **Directive** | `directives/` | Constraint-oriented governance rules |
| **Tactic** | `tactics/` | Reusable step-by-step behavioral recipes |
| **Procedure** | `procedures/` | Stateful multi-step workflows with entry/exit conditions |
| **Styleguide** | `styleguides/` | Cross-cutting quality and consistency conventions |
| **Toolguide** | `toolguides/` | Tool-specific operational syntax and guidance |
| **Schema** | `schemas/` | Machine-validated contracts for artifact structure |
| **Template** | `templates/` | Output scaffolds and interaction contracts |
| **Agent Profile** | `agent_profiles/` | Declarative agent identity and collaboration contracts |
| **Mission** | `missions/` | Workflow definitions (state machines, action indices, templates) |

## Design principle

Doctrine is a **pure knowledge library**. It has no dependency on the charter
package or the CLI. The charter package reads from doctrine to compile
project-specific governance bundles, but doctrine itself is unaware of any
consumer.

**Dependency direction:** nothing in this package imports from `charter` or
`specify_cli`.

## Curation pipeline

New artifacts follow a three-stage flow: raw reference material lands in
`_reference/`, gets extracted into structured YAML in `<type>/_proposed/`, and
is promoted to `<type>/shipped/` via `spec-kitty doctrine curate`. See the
curation engine in `curation/` for implementation details.

## Architecture references

- Container view: `architecture/2.x/02_containers/README.md` — "Doctrine Artifact Catalog"
- Component view: `architecture/2.x/03_components/README.md` — "Doctrine and Glossary" section
- Governance ADR: `architecture/2.x/adr/2026-02-23-1-doctrine-artifact-governance-model.md`
- Glossary: `glossary/contexts/doctrine.md`
- Naming decision (agent vs tool): `glossary/naming-decision-tool-vs-agent.md`
