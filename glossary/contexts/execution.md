## Context: Execution

Terms describing tool invocation and semantic safety gates during generation.

### Tool

| | |
|---|---|
| **Definition** | Concrete runtime product used to execute commands (for example Claude Code, Codex, opencode). |
| **Context** | Execution |
| **Status** | canonical |
| **Related terms** | [Agent](./identity.md#agent), [Slash Command](#slash-command) |

---

### Slash Command

| | |
|---|---|
| **Definition** | User-facing command surface that triggers a lifecycle operation (for example specify, plan, tasks, review, merge). |
| **Context** | Execution |
| **Status** | canonical |

---

### Semantic Check

| | |
|---|---|
| **Definition** | Deterministic validation step that compares extracted terms with active glossary scope(s) before generation proceeds. |
| **Context** | Execution |
| **Status** | canonical |
| **Related terms** | [Glossary Scope](./events-telemetry.md#glossary-scope), [Strictness](#glossary-strictness) |

---

### Glossary Strictness

| | |
|---|---|
| **Definition** | Policy mode controlling warning/block behavior for semantic conflicts. |
| **Context** | Execution |
| **Status** | canonical |
| **Modes** | `off`, `medium` (default), `max` |

---

### Clarification Prompt

| | |
|---|---|
| **Definition** | Targeted question emitted when conflict severity/confidence requires human input before continuing generation. |
| **Context** | Execution |
| **Status** | canonical |
| **Burst policy** | Cap to top 3 high-priority conflicts per prompt burst |

---

### Generation Boundary

| | |
|---|---|
| **Definition** | Point where text/code generation would begin and semantic gate policy is enforced. |
| **Context** | Execution |
| **Status** | canonical |
| **Block condition** | Unresolved high-severity semantic conflict |

