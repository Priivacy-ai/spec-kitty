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
| Execution | CLI/tool invocation and generation boundaries. | `glossary/contexts/execution.md` |
| Identity | Actors, roles, and mission participation. | `glossary/contexts/identity.md` |
| Orchestration | Project/mission/feature/work-package lifecycle terms. | `glossary/contexts/orchestration.md` |
| Governance | Constitution/ADR/policy precedence and rules. | `glossary/contexts/governance.md` |
| Events & Telemetry | Event envelope, replay, and glossary evolution history. | `glossary/contexts/events-telemetry.md` |
| Practices & Principles | Working agreements for low-friction, high-signal delivery. | `glossary/contexts/practices-principles.md` |
| Configuration & Project Structure | Project-local structure and configuration artifacts. | `glossary/contexts/configuration-project-structure.md` |

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
