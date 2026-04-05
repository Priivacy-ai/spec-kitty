# Shipped Agent Profiles

Reference agent profiles included in the `doctrine` package distribution. These
define the 7 core roles with their specialization, collaboration contracts, directive
references, and initialization declarations.

| File | Profile ID | Role |
|------|------------|------|
| `architect.agent.yaml` | `architect` | architect |
| `curator.agent.yaml` | `curator` | curator |
| `designer.agent.yaml` | `designer` | designer |
| `implementer.agent.yaml` | `implementer` | implementer |
| `planner.agent.yaml` | `planner` | planner |
| `researcher.agent.yaml` | `researcher` | researcher |
| `reviewer.agent.yaml` | `reviewer` | reviewer |

Shipped profiles are read-only at the package level. Project-level overrides in
`.kittify/charter/agents/` can customize any profile by matching `profile-id`.
