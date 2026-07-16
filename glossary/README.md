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
| Dossier | Artifact inventory, integrity validation, and drift detection. | `docs/context/dossier.md` |
| Execution | CLI/tool invocation, generation boundaries, and collaboration modes. | `docs/context/execution.md` |
| Identity | Actors, roles, mission participation, and Human-in-Charge (HiC). | `docs/context/identity.md` |
| Lexical | Glossary internal data model — term surfaces, senses, provenance. | `docs/context/lexical.md` |
| Orchestration | Project/mission/feature/work-package lifecycle and runtime terms. Includes **Decision**, **Decision Input Request**, and **Decision Input Answer** — see disambiguation note in that file and in the SaaS `architecture/domain-glossary.md`. | `docs/context/orchestration.md` |
| Governance | Charter/ADR/policy precedence and rules. | `docs/context/governance.md` |
| Planning & Tracking | Issue-tracker organization (functional epics, meta-trackers, triage status, priority scheme) and the **Op** execution tier. Human-readable companion to `.kittify/glossaries/planning-and-tracking.yaml`. | `docs/context/planning-and-tracking.md` |
| Doctrine | Doctrine domain model and artifact taxonomy. | `docs/context/doctrine.md` |
| System Events | Event envelope, replay, glossary evolution, and system event types. | `docs/context/system-events.md` |
| Practices & Principles | Working agreements for low-friction, high-signal delivery. | `docs/context/practices-principles.md` |
| Configuration & Project Structure | Project-local structure and configuration artifacts. | `docs/context/configuration-project-structure.md` |
| Technology Foundations | General technology terms (API, CLI, YAML, etc.) for reader accessibility. | `docs/context/technology-foundations.md` |
| Testing Taxonomy | Canonical categories for tests in `tests/` — every pytest marker declared in `pytest.ini` with a usable description for choosing the right tag. | `docs/context/testing-taxonomy.md` |

## Reference Notes

| Note | File |
|---|---|
| Naming Decision: Tool vs Agent | `docs/context/naming-decision-tool-vs-agent.md` |
| Historical Terms and Mappings | `docs/context/historical-terms.md` |

## Status Lifecycle

`candidate` -> `canonical` -> `deprecated` / `superseded`

## Term Entry Schema

Each glossary term table should include:

1. `Definition`
2. `Context`
3. `Status`
4. `Applicable to` (version scope, for example `` `1.x`, `2.x` ``)

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
