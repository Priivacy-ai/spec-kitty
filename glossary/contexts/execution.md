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
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Strictness](#glossary-strictness), [Term Sense](./lexical.md#term-sense), [Semantic Check Evaluation](./system-events.md#semantic-check-evaluation) |

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

---

### Middleware Pipeline

| | |
|---|---|
| **Definition** | An ordered chain of processing steps that run before a mission step produces output. Each layer in the chain can extract terms, check for semantic conflicts, gate generation, prompt the Human-in-Charge for clarification, or resume from a checkpoint. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Semantic Check](#semantic-check), [Generation Boundary](#generation-boundary), [Checkpoint/Resume](#checkpointresume) |

---

### Checkpoint/Resume

| | |
|---|---|
| **Definition** | A mechanism that lets a glossary pipeline pause at a generation boundary and pick up where it left off in a later session. The pause point and its context are saved so no work is lost. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Middleware Pipeline](#middleware-pipeline), [Generation Boundary](#generation-boundary) |

---

### Seed File

| | |
|---|---|
| **Definition** | An optional YAML file (`.kittify/glossaries/{scope}.yaml`) that pre-loads domain glossary terms before the runtime starts extracting new ones. Gives teams a head start by defining known terminology upfront. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Term Sense](./lexical.md#term-sense) |

---

### Collaboration Mode

| | |
|---|---|
| **Definition** | The level of Human-in-Charge involvement during a mission step or workflow. Determines how much real-time oversight the HiC provides versus delegating to agents. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic), [Interactive Mode](#interactive-mode), [Hands-off with Review Mode](#hands-off-with-review-mode), [Fully Delegated Mode](#fully-delegated-mode) |

---

### Interactive Mode

| | |
|---|---|
| **Definition** | The HiC works alongside agents in real time — conducting interviews, pair-developing, micro-prompting, or making decisions as they arise. The HiC is present and actively steering. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Hands-off with Review Mode

| | |
|---|---|
| **Definition** | Agents operate independently during execution, but the HiC reviews results at defined checkpoints before work is accepted or advanced. The HiC is absent during execution but present for review. |
| **Context** | Execution |
| **Status** | candidate |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Fully Delegated Mode

| | |
|---|---|
| **Definition** | The agentic stack operates asynchronously without the HiC present. Work proceeds until a final Accept/Decline decision point, where the HiC returns to approve or reject the outcome. Also known as "AFK mode." |
| **Context** | Execution |
| **Status** | candidate |
| **Alias** | AFK mode |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

