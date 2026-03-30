## Context: Execution

Terms describing tool invocation and semantic safety gates during generation.

### Tool

| | |
|---|---|
| **Definition** | Concrete runtime product used to execute commands (for example Claude Code, Codex, opencode). |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Agent](./identity.md#agent), [Slash Command](#slash-command) |

---

### Slash Command

| | |
|---|---|
| **Definition** | User-facing command surface that triggers a lifecycle operation (for example specify, plan, tasks, review, merge). |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Semantic Check

| | |
|---|---|
| **Definition** | Deterministic validation step that compares extracted terms with active glossary scope(s) before generation proceeds. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Strictness](#glossary-strictness), [Term Sense](./lexical.md#term-sense), [Semantic Check Evaluation](./system-events.md#semantic-check-evaluation) |

---

### Glossary Strictness

| | |
|---|---|
| **Definition** | Policy mode controlling warning/block behavior for semantic conflicts. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Modes** | `off`, `medium` (default), `max` |

---

### Clarification Prompt

| | |
|---|---|
| **Definition** | Targeted question emitted when conflict severity/confidence requires human input before continuing generation. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Burst policy** | Cap to top 3 high-priority conflicts per prompt burst |

---

### Generation Boundary

| | |
|---|---|
| **Definition** | Point where text/code generation would begin and semantic gate policy is enforced. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Block condition** | Unresolved high-severity semantic conflict |

---

### Middleware Pipeline

| | |
|---|---|
| **Definition** | An ordered chain of processing steps that run before a mission step produces output. Each layer in the chain can extract terms, check for semantic conflicts, gate generation, prompt the Human-in-Charge for clarification, or resume from a checkpoint. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Semantic Check](#semantic-check), [Generation Boundary](#generation-boundary), [Checkpoint/Resume](#checkpointresume) |

---

### Checkpoint/Resume

| | |
|---|---|
| **Definition** | A mechanism that lets a glossary pipeline pause at a generation boundary and pick up where it left off in a later session. The pause point and its context are saved so no work is lost. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Middleware Pipeline](#middleware-pipeline), [Generation Boundary](#generation-boundary) |

---

### Seed File

| | |
|---|---|
| **Definition** | An optional YAML file (`.kittify/glossaries/{scope}.yaml`) that pre-loads domain glossary terms before the runtime starts extracting new ones. Gives teams a head start by defining known terminology upfront. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Glossary Scope](./system-events.md#glossary-scope), [Term Sense](./lexical.md#term-sense) |

---

### Collaboration Mode

| | |
|---|---|
| **Definition** | The level of Human-in-Charge involvement during a mission step or workflow. Determines how much real-time oversight the HiC provides versus delegating to agents. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic), [Interactive Mode](#interactive-mode), [Hands-off with Review Mode](#hands-off-with-review-mode), [Fully Delegated Mode](#fully-delegated-mode) |

---

### Interactive Mode

| | |
|---|---|
| **Definition** | The HiC works alongside agents in real time — conducting interviews, pair-developing, micro-prompting, or making decisions as they arise. The HiC is present and actively steering. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Hands-off with Review Mode

| | |
|---|---|
| **Definition** | Agents operate independently during execution, but the HiC reviews results at defined checkpoints before work is accepted or advanced. The HiC is absent during execution but present for review. |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Fully Delegated Mode

| | |
|---|---|
| **Definition** | The agentic stack operates asynchronously without the HiC present. Work proceeds until a final Accept/Decline decision point, where the HiC returns to approve or reject the outcome. Also known as "AFK mode." |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `1.x`, `2.x` |
| **Alias** | AFK mode |
| **Related terms** | [Collaboration Mode](#collaboration-mode), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Agent Tool Connector

| | |
|---|---|
| **Definition** | A pluggable execution provider that receives dispatched work from Orchestration and executes it through whatever mechanism the connector implements (in-tool prompt, async shell command, SDK call, remote API). Consumes Doctrine and Constitution at execution time to operate within governance constraints. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Tool](#tool), [Agent](./identity.md#agent), [Execution Dispatch](#execution-dispatch), [Collaboration Mode](#collaboration-mode) |
| **Architecture ref** | [System Landscape](../../architecture/2.x/00_landscape/README.md#agent-tool-connectors) |

---

### Execution Dispatch

| | |
|---|---|
| **Definition** | The component that receives dispatched work from Orchestration and routes it to the correct Agent Tool Connector adapter. Ensures governance context (Doctrine, Constitution) is injected into every execution. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Agent Tool Connector](#agent-tool-connector), [Slash Command](#slash-command) |
| **Architecture ref** | [Component View](../../architecture/2.x/03_components/README.md#agent-tool-connectors) |

---

### Agent Adapter

| | |
|---|---|
| **Definition** | A per-agent implementation within the Agent Tool Connector boundary. Currently realized as markdown command templates deployed to agent-specific directories (`.claude/`, `.codex/`, etc.). The architecture envisions adapters that can also dispatch via SDK, shell, or remote API. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Agent Tool Connector](#agent-tool-connector), [Tool](#tool), [Command Template](./orchestration.md#command-template) |
