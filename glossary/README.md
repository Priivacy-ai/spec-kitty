# Spec Kitty Living Glossary

Canonical terminology for Spec Kitty. This glossary is a living artifact and is organized by context domains.

## Architecture Framing

This glossary follows a two-layer architecture:

1. Policy layer (this glossary, journeys, doctrine): defines language, intent, and governance.
2. Runtime layer (CLI/events/SaaS projections): enforces behavior, emits contracts, and provides replayable state.

Use this glossary as policy authority for language, and runtime artifacts as operational authority for "what happened."

## Domain Index

| Domain                               | Summary                                                                                                    | File                                                   |
|--------------------------------------|------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| Execution (Tools & Invocation)       | How Spec Kitty executes work through CLI tools and records invocation outcomes.                            | `glossary/contexts/execution.md`                       |
| Identity (Agents & Roles)            | Who performs work, what profiles govern behavior, and how handoffs/roles are defined.                      | `glossary/contexts/identity.md`                        |
| Orchestration (Workflow & Lifecycle) | Feature/WP lifecycle, phases, lanes, worktrees, and mission command surface.                               | `glossary/contexts/orchestration.md`                   |
| Doctrine                             | Doctrine domain model and artifacts: paradigms, directives, tactics, templates, styleguides, and toolguides. | `glossary/contexts/doctrine.md`                        |
| Governance                           | Doctrine-aligned governance model: guidelines, directives, constitution, hooks, and validation.            | `glossary/contexts/governance.md`                      |
| Events & Telemetry                   | Event spine, status event model, envelope metadata, telemetry, and status state materialization concepts.  | `glossary/contexts/events-telemetry.md`                |
| Practices & Principles               | Human-in-charge operating model, checkpoints, escalation, merge safety concepts, and workflow principles.  | `glossary/contexts/practices-principles.md`            |
| Configuration & Project Structure    | Project-level artifacts and structure conventions (`.kittify`, `kitty-specs`, vision/bootstrap, VCS lock). | `glossary/contexts/configuration-project-structure.md` |

## Reference Notes

| Note                           | File                                        |
|--------------------------------|---------------------------------------------|
| Naming Decision: Tool vs Agent | `glossary/naming-decision-tool-vs-agent.md` |
| Historical Terms and Mappings  | `glossary/historical-terms.md`              |

## Status Lifecycle

Term maturity follows:

`candidate` -> `canonical` -> `deprecated` / `superseded`

## Status Semantics

- `canonical`: canonical terminology in the policy layer.
- `candidate`: proposed terminology pending validation or runtime integration.
- `superseded` / `deprecated`: preserved for backward compatibility and migration context.

`canonical` does not automatically mean full runtime implementation is complete. Runtime parity depends on core mission/runtime integration work.

## Published Runtime Anchors (`2.x`)

- `src/specify_cli/glossary/`
- `src/specify_cli/missions/glossary_hook.py`
- `src/specify_cli/cli/commands/glossary.py`
- `architecture/adrs/2026-02-17-3-events-contract-parity-and-vendor-deprecation.md`

## Cross-Repo Contract Notes

SaaS glossary projections consume canonical glossary event envelopes with top-level fields such as:

- `event_id`, `event_type`, `aggregate_id`, `lamport_clock`, `payload`

And payload identity/term fallbacks such as:

- mission: `mission_slug` or `mission_id` (fallback `aggregate_id`)
- term: `term_name` or `term_surface` or `term`

This keeps projections compatible during migration between legacy and canonical payload shapes.

---

*Last updated: 2026-02-15*
