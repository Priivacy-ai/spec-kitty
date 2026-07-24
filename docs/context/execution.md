---
title: 'Context: Execution'
description: 'Glossary context for execution semantics: tool invocation and the semantic safety gates applied during generation within a Spec Kitty mission.'
doc_status: active
updated: '2026-07-23'
related:
- docs/context/governance.md
- docs/context/identity.md
- docs/context/lexical.md
- docs/context/system-events.md
---
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

### Tool Surface

| | |
|---|---|
| **Definition** | A tool-visible artifact or configuration entry that Spec Kitty installs, verifies, repairs, or packages for a concrete execution tool. This is `surface` **Sense 1** — the tool-facing sense, one of two unrelated domains that share the word. Realized in code by the `ToolSurfaceKind` enum in `src/specify_cli/tool_surface/enums.py` (members `COMMAND_SKILL`, `DOCTRINE_SKILL`, `CONTEXT_FILE`, `RULE`, `HOOK`, `AGENT_PROFILE`, `PLUGIN_MANIFEST`, `NATIVE_CONFIG`, `COMMAND_FILE`), renamed from the bare `SurfaceKind` per ADR [2026-07-23-1](../adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md). |
| **Context** | Execution |
| **Status** | candidate |
| **Applicable to** | `3.x` |
| **Examples** | slash command file, skill directory, custom agent profile file, hook config, MCP config, plugin manifest |
| **Use when** | Describing install/config/doctor/plugin ownership for Claude Code, Codex, Copilot, Cursor, Windsurf, Kiro, or another concrete tool. |
| **Do NOT use when** | Describing logical collaborator identity, assignment, handoff, or role; use [Agent](./identity.md#agent) or [Agent Profile](./identity.md#agent-profile) instead. The concept is the physical tree a mission artifact resolves to — use [Topology Surface](./orchestration.md#topology-surface) (`surface` **Sense 2**). Never write bare "surface" in governed prose; name the sense ("tool surface" / "topology surface"). |
| **Related terms** | [Tool](#tool), [Slash Command](#slash-command), [Agent](./identity.md#agent), [Topology Surface](./orchestration.md#topology-surface) |

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

### GovernanceContext

| | |
|---|---|
| **Definition** | The resolved set of Charter and Doctrine artifacts active for an operation. Owned by the Governance bounded module. Resolved once per operation and passed down; never re-derived mid-operation. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Owner** | Governance module |
| **Related terms** | [MissionExecutionContext](#missionexecutioncontext), [InfraContext](#infracontext), [Charter](./governance.md#charter) |

---

### MissionExecutionContext

| | |
|---|---|
| **Definition** | The resolved set of workspace root, branch name, feature directory, and WP identity for an operation. Owned by `mission_runtime/context.py` (Open Host Service facade). Resolved once per operation via `resolve_action_context`; never re-derived from CWD by individual command surfaces. Renamed from `ExecutionContext` (FR-012) to match the ubiquitous language and disambiguate from the unrelated `core/context_validation.py::ExecutionContext(StrEnum)`. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Owner** | Mission runtime (`src/mission_runtime/context.py`) |
| **OHS entry point** | `resolve_action_context` |
| **Related terms** | [GovernanceContext](#governancecontext), [InfraContext](#infracontext) |

---

### InfraContext

| | |
|---|---|
| **Definition** | The resolved set of infrastructure credentials and endpoints for an operation, including git remote URL, CI endpoint, and any external service tokens. Owned by the Execution module. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Owner** | Execution module |
| **Related terms** | [MissionExecutionContext](#missionexecutioncontext), [GovernanceContext](#governancecontext) |

---

### Effector

| | |
|---|---|
| **Definition** | The Actor realized inside the Execution domain — the execution-bound realization of an Actor that performs actions within a mission run, producing or consuming communication artefacts (commits, PRs, comments). Named concept in docs only; no code type until a concrete actor-kind-mismatch bug triggers materialization. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Materialization trigger** | First concrete actor-kind-mismatch bug, or first feature requiring cross-log (status/retrospective/run) actor identity join |
| **Placement when materialized** | `src/specify_cli/kernel/actor.py` (Shared Kernel layer) |
| **Related terms** | [communication artefact](#communication-artefact) |
| **ADR** | `docs/adr/3.x/2026-06-03-3-effector-actor-model.md` |

---

### communication artefact

| | |
|---|---|
| **Definition** | A durable artifact produced or consumed by an Effector during a mission run (for example, a commit, a pull request, a review comment). Distinct from planning artifacts (spec, plan, tasks) which are produced before execution begins. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Examples** | git commit, pull request, PR comment, CI run result |
| **Related terms** | [Effector](#effector) |

---

### repository root checkout

| | |
|---|---|
| **Definition** | The canonical repository-root working copy of a project — the single checkout from which planning commands run and against which lane worktrees are created. It is distinct from a lane worktree (an isolated per-work-package checkout under `.worktrees/`). This is `primary` **Sense C**; the charter §Branch-Intent Terminology Governance decrees "repository root checkout" as the canonical term for this sense. The retired alias phrases "primary surface" and "primary checkout" describe it. |
| **Context** | Execution |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Symbols unchanged this slice** | This entry canonicalizes the prose term only. The underlying code symbols (`primary_feature_dir_*` and the rest of the Sense-C checkout cluster) are **not** renamed in this mission; the code rename is Track 2 (#2730). |
| **Do NOT use when** | The concept is the artifact-kind partition — use [PRIMARY partition](./orchestration.md#primary-partition). The concept is the repository's default integration branch — use [primary branch](./orchestration.md#primary-branch). The concept is the ref planning artifacts commit to — use [Target Ref / Commit Target](./orchestration.md#target-ref--commit-target). Avoid the retired aliases "primary surface" and "primary checkout". |
| **Related terms** | [Build](./orchestration.md#build), [MissionExecutionContext](#missionexecutioncontext), [Lane](./orchestration.md#lane), [primary branch](./orchestration.md#primary-branch) |
