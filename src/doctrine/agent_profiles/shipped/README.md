# Shipped Agent Profiles

Reference agent profiles included in the `doctrine` package distribution. These
define the core roles with their specialization, collaboration contracts, directive
references, and initialization declarations. Language-specialist profiles (prefixed
with the language name) extend the base `implementer-ivan` role for polyglot projects.

| File | Profile ID | Primary Role |
|------|------------|------|
| `architect-alphonso.agent.yaml` | `architect-alphonso` | architect |
| `curator-carla.agent.yaml` | `curator-carla` | curator |
| `designer-dagmar.agent.yaml` | `designer-dagmar` | designer |
| `generic-agent.agent.yaml` | `generic-agent` | implementer |
| `human-in-charge.agent.yaml` | `human-in-charge` | human-in-charge |
| `implementer-ivan.agent.yaml` | `implementer-ivan` | implementer |
| `java-jenny.agent.yaml` | `java-jenny` | implementer (Java specialist) |
| `planner-priti.agent.yaml` | `planner-priti` | planner |
| `python-pedro.agent.yaml` | `python-pedro` | implementer (Python specialist) |
| `researcher-robbie.agent.yaml` | `researcher-robbie` | researcher |
| `reviewer-renata.agent.yaml` | `reviewer-renata` | reviewer |

Shipped profiles are read-only at the package level. Project-level overrides in
`.kittify/charter/agents/` can customize any profile by matching `profile-id`.
