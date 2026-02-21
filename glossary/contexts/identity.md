## Context: Identity (Agents & Roles)

Terms describing Doctrine agent identities — *who* performs work and *what rules govern* their behavior.

### Agent

|                      |                                                                                                                                                                                             |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**       | A named identity with a role, capabilities, behavioral rules, and handoff patterns. An agent defines *who* performs a task and *what governance applies*. An agent runs on a [tool](#tool). |
| **Context**          | Identity                                                                                                                                                                                    |
| **Status**           | canonical                                                                                                                                                                                   |
| **In code**          | `AgentProfile` (dataclass), `agent_profile_id`                                                                                                                                              |
| **Related terms**    | [Agent Profile](#agent-profile), [Role](#role), [Tool](#tool), [Orchestration Assignment](#orchestration-assignment)                                                                        |
| **Examples**         | "Python Pedro" (implementer), "Review Rachel" (reviewer), "Doc Diana" (documenter)                                                                                                          |
| **Decision history** | 2026-02-15: Clarified as identity concept, distinct from tool. Existing code's "agent" refers to [Tool](#tool).                                                                             |

**Fields**:

- `id` — Unique identifier (e.g., `"python-pedro"`)
- `name` — Human-readable name (e.g., `"Python Pedro"`)
- `specialization` — Primary skill area (e.g., `"python"`, `"security"`)
- `capabilities` — What the agent can do (frozenset, e.g., `{"write-code", "write-tests"}`)
- `required_directives` — Directive numbers this agent must follow

---

### Agent Profile

|                   |                                                                                                                                                                                                                                |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The full definition document for an [agent](#agent). A markdown file with YAML front matter stored at `doctrine/agents/*.agent.md`. Contains identity, capabilities, required directives, handoff patterns, and primer matrix. |
| **Context**       | Identity                                                                                                                                                                                                                       |
| **Status**        | canonical                                                                                                                                                                                                                      |
| **In code**       | `AgentProfile` (dataclass), `AgentProfile.from_file()`                                                                                                                                                                         |
| **Related terms** | [Agent](#agent), [Directive](#directive), [Handoff Pattern](#handoff-pattern), [Primer Matrix](#primer-matrix)                                                                                                                 |

---

### Role

|                   |                                                                                                                                                                                      |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The function an agent performs in a workflow phase. Assigned per orchestration step, not permanently — the same agent profile could serve different roles across features or phases. |
| **Context**       | Identity                                                                                                                                                                             |
| **Status**        | canonical                                                                                                                                                                            |
| **In code**       | `agent_role` field on `GovernanceContext`                                                                                                                                            |
| **Related terms** | [Agent](#agent), [Phase](#phase), [Orchestration Assignment](#orchestration-assignment)                                                                                              |
| **Values**        | `implementer`, `reviewer`, `architect`, `documenter`                                                                                                                                 |

---

### Handoff Pattern

|                   |                                                                                                                                                        |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A rule in an agent profile defining who receives work next. Specifies direction (e.g., `after_implement`, `on_rejection`) and target agent profile ID. |
| **Context**       | Identity                                                                                                                                               |
| **Status**        | canonical                                                                                                                                              |
| **Related terms** | [Agent Profile](#agent-profile), [Role](#role)                                                                                                         |

---

### Primer Matrix

|                   |                                                                                                                                                            |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A mapping in an agent profile from task type to required context documents. Defines what context must be loaded before the agent starts a given task type. |
| **Context**       | Identity                                                                                                                                                   |
| **Status**        | canonical                                                                                                                                                  |
| **Related terms** | [Agent Profile](#agent-profile)                                                                                                                            |
| **Example**       | `implement: [spec, plan, architecture]`, `fix: [spec, review-comments, test-output]`                                                                       |

---
