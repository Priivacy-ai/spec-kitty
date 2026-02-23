# Spec Kitty Living Glossary

Canonical terminology for Spec Kitty. This glossary is a living artifact organized by context domain.

## Source of Truth

When terms conflict, use this order:

1. Accepted product planning docs (PDR/PRD/ADR)
2. This glossary (policy language)
3. Runtime contracts and event logs (operational behavior)

## Architecture Framing

Spec Kitty uses two complementary layers:

1. Policy layer (glossary, specs, ADRs): defines language, intent, and invariants.
2. Runtime layer (CLI/events/projections): executes behavior and records what happened.

Use policy docs to answer "what should this mean?" and runtime artifacts to answer "what did the system do?"

## Domain Index

| Domain | Summary | File |
|---|---|---|
| Dossier | Artifact inventory, integrity validation, and drift detection. | `glossary/contexts/dossier.md` |
| Execution | CLI/tool invocation, generation boundaries, and collaboration modes. | `glossary/contexts/execution.md` |
| Identity | Actors, roles, mission participation, and Human-in-Charge (HiC). | `glossary/contexts/identity.md` |
| Lexical | Glossary internal data model — term surfaces, senses, provenance. | `glossary/contexts/lexical.md` |
| Orchestration | Project/mission/feature/work-package lifecycle and runtime terms. | `glossary/contexts/orchestration.md` |
| Governance | Constitution/ADR/policy precedence and rules. | `glossary/contexts/governance.md` |
| Doctrine | Doctrine domain model and artifact taxonomy. | `glossary/contexts/doctrine.md` |
| System Events | Event envelope, replay, glossary evolution, and system event types. | `glossary/contexts/system-events.md` |
| Practices & Principles | Working agreements for low-friction, high-signal delivery. | `glossary/contexts/practices-principles.md` |
| Configuration & Project Structure | Project-local structure and configuration artifacts. | `glossary/contexts/configuration-project-structure.md` |
| Technology Foundations | General technology terms (API, CLI, YAML, etc.) for reader accessibility. | `glossary/contexts/technology-foundations.md` |

## Reference Notes

| Note | File |
|---|---|
| Naming Decision: Tool vs Agent | `glossary/naming-decision-tool-vs-agent.md` |
| Historical Terms and Mappings | `glossary/historical-terms.md` |

## Status Lifecycle

`candidate` -> `canonical` -> `deprecated` / `superseded`

## Runtime Anchors (`2.x`)

- `src/specify_cli/glossary/`
- `src/specify_cli/missions/glossary_hook.py`
- `src/specify_cli/missions/primitives.py`
- `src/specify_cli/cli/commands/glossary.py`

## PDR Alignment Notes

- Scoped glossary model: `spec_kitty_core`, `team_domain`, `audience_domain`, `mission_local`
- Strictness modes: `off`, `medium` (default), `max`
- Generation block policy: block unresolved high-severity semantic conflicts only
- History model: append-only glossary evolution events, replayable from canonical logs
