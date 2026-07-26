# Shipped Agent Profiles

Reference agent profiles included in the `doctrine` package distribution. These
define the core roles with their specialization, collaboration contracts, directive
references, and initialization declarations. Language-specialist profiles (prefixed
with the language name) extend the base `implementer-ivan` role for polyglot projects.

| File | Profile ID | Primary Role |
|------|------------|------|
| `analyst-annie.agent.yaml` | `analyst-annie` | analyst |
| `architect-alphonso.agent.yaml` | `architect-alphonso` | architect |
| `comms-cleo.agent.yaml` | `comms-cleo` | curator / researcher |
| `curator-carla.agent.yaml` | `curator-carla` | curator |
| `debugger-debbie.agent.yaml` | `debugger-debbie` | investigator |
| `designer-dagmar.agent.yaml` | `designer-dagmar` | designer |
| `diagram-daisy.agent.yaml` | `diagram-daisy` | designer |
| `doctrine-daphne.agent.yaml` | `doctrine-daphne` | curator / onboarding-guide |
| `frontend-freddy.agent.yaml` | `frontend-freddy` | implementer |
| `generic-agent.agent.yaml` | `generic-agent` | implementer |
| `human-in-charge.agent.yaml` | `human-in-charge` | human-in-charge |
| `implementer-ivan.agent.yaml` | `implementer-ivan` | implementer |
| `java-jenny.agent.yaml` | `java-jenny` | implementer (Java specialist) |
| `lexical-larry.agent.yaml` | `lexical-larry` | semantic-analyst / terminology-reviewer / glossary-curator |
| `minutes-maker-mahad.agent.yaml` | `minutes-maker-mahad` | documentarian / meeting-facilitator |
| `node-norris.agent.yaml` | `node-norris` | implementer |
| `paula-patterns.agent.yaml` | `paula-patterns` | architecture-scout |
| `planner-priti.agent.yaml` | `planner-priti` | planner |
| `python-pedro.agent.yaml` | `python-pedro` | implementer (Python specialist) |
| `randy-reducer.agent.yaml` | `randy-reducer` | implementer (semantic compression specialist) |
| `researcher-robbie.agent.yaml` | `researcher-robbie` | researcher |
| `retrospective-facilitator.agent.yaml` | `retrospective-facilitator` | facilitator |
| `reviewer-renata.agent.yaml` | `reviewer-renata` | reviewer |
| `scribe-sally.agent.yaml` | `scribe-sally` | documentarian / transcriptionist |
| `synthesizer-sam.agent.yaml` | `synthesizer-sam` | synthesizer |

Shipped profiles are read-only at the package level. Project-level overrides in
`.kittify/charter/agents/` can customize any profile by matching `profile-id`.
