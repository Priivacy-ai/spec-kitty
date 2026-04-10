## Context: Orchestration

Terms describing lifecycle and runtime orchestration semantics.

### Project

| | |
|---|---|
| **Definition** | SaaS collaboration surface that groups one or more repositories under a shared identity for collaboration, visibility, and governance. A project may span multiple repositories and exists independent of any single Git checkout. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | Prior to mission 081, "project" was used interchangeably with "repository" to mean the local Git resource. That usage is now prohibited. See [Repository](#repository). |
| **Related terms** | [Repository](#repository), [Build](#build), [Mission](#mission) |

---

### Repository

| | |
|---|---|
| **Definition** | Local Git resource (one `.git` directory) that holds mission artifacts, source code, and `.kittify/` configuration. Multiple checkouts (worktrees) of the same repository share one repository identity. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | Replaces the pre-081 usage of "project" for the local Git resource. The canonical identity field is `repository_uuid`. |
| **Related terms** | [Project](#project), [Build](#build) |

---

### Build

| | |
|---|---|
| **Definition** | One checkout or worktree of one repository. Each build has its own working tree, `.kittify/` state snapshot, and execution context. Builds are ephemeral relative to the repository they belong to. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | The canonical identity field is `build_id`. |
| **Related terms** | [Repository](#repository), [Workspace](../contexts/orchestration.md#workspace) |

---

### Mission Type

| | |
|---|---|
| **Definition** | Reusable workflow blueprint that configures mission actions, templates, and guardrails. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission

| | |
|---|---|
| **Definition** | Concrete tracked item stored under `kitty-specs/<mission-slug>/` and linked to exactly one [Mission Type](#mission-type). |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Note** | This is the generic tracked-item noun across software, research, planning, and documentation work. |

---

### Mission Run

| | |
|---|---|
| **Definition** | Runtime collaboration/execution container for one mission session. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Scoping rule** | Runtime events should be scoped by `mission_run_id` as primary identity where available |

---

### Feature

| | |
|---|---|
| **Definition** | Compatibility alias for a [Mission](#mission) whose mission type is `software-dev`. |
| **Context** | Orchestration |
| **Status** | canonical (compatibility) |
| **Applicable to** | `1.x`, `2.x` |
| **Note** | Allowed on legacy software-delivery surfaces, but not a co-equal canonical architecture noun. |

---

### Work Package

| | |
|---|---|
| **Definition** | Executable slice of work inside a mission plan, typically represented as `WPxx` tasks. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission Action

| | |
|---|---|
| **Definition** | Outer lifecycle action for a mission, such as `specify`, `plan`, `implement`, `review`, or `accept`. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Type](#mission-type), [Step Contract](#step-contract), [Procedure](./doctrine.md#procedure) |

---

### Step Contract

| | |
|---|---|
| **Definition** | Structured contract for one mission action, including step sequencing, guard evaluation, prompt binding, and delegation hooks. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Action](#mission-action), [Mission-Runtime YAML](#mission-runtime-yaml), [Procedure](./doctrine.md#procedure) |

---

### Workflow

| | |
|---|---|
| **Definition** | Umbrella prose term for the overall flow of work. |
| **Context** | Orchestration |
| **Status** | canonical (generic prose only) |
| **Applicable to** | `1.x`, `2.x` |
| **Rule** | Use [Mission Type](#mission-type), [Mission Action](#mission-action), [Step Contract](#step-contract), or [Procedure](./doctrine.md#procedure) when precision matters. |

---

### WorkPackage (Alias)

| | |
|---|---|
| **Definition** | Legacy lexical variant of [Work Package](#work-package). |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Canonical entry** | [Work Package](#work-package) |

---

### Lane

| | |
|---|---|
| **Definition** | Work package state position in the canonical lifecycle FSM. Canonical lanes: `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`. Alias: `doing` -> `in_progress`. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission-Runtime YAML

| | |
|---|---|
| **Definition** | Configuration file (`mission-runtime.yaml`) that defines a mission type's step graph, action ordering, dependencies, and prompt-template bindings. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Type](#mission-type), [Step Dependency](#step-dependency), [Step Contract](#step-contract), [Command Template](#command-template) |

---

### Step Dependency

| | |
|---|---|
| **Definition** | A declared relationship saying "this step cannot start until that step finishes." Defined in mission-runtime YAML to enforce ordering. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission-Runtime YAML](#mission-runtime-yaml), [Step Sequence](#step-sequence) |

---

### Step Sequence

| | |
|---|---|
| **Definition** | The order in which mission steps execute, determined by the step list and dependency graph in mission-runtime YAML. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Step Dependency](#step-dependency), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Command Template

| | |
|---|---|
| **Definition** | A markdown file that provides the prompt for a specific mission action. Located in the mission type's template directory and loaded at runtime based on mission type and agent configuration. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Template Resolution](#template-resolution), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Template Resolution

| | |
|---|---|
| **Definition** | The process of finding and loading the correct command template for a given mission action, considering which mission type is active and which agent is running. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Command Template](#command-template) |

---

### Mission Discovery

| | |
|---|---|
| **Definition** | How the runtime finds and loads mission-type definition files (`mission.yaml`, `mission-runtime.yaml`) from configured mission-pack roots at startup. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Type](#mission-type), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Command Envelope

| | |
|---|---|
| **Definition** | Standard JSON wrapper used to send commands to the orchestrator API. Contains identity fields, a version number, and the command payload. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Orchestrator API](#orchestrator-api), [Contract Version](#contract-version), [JSON](./technology-foundations.md#json) |

---

### Contract Version

| | |
|---|---|
| **Definition** | Version number on the orchestrator API that tells consumers whether the API has changed in a breaking way. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Orchestrator API](#orchestrator-api), [Command Envelope](#command-envelope) |

---

### Orchestrator API

| | |
|---|---|
| **Definition** | JSON-based interface that lets external orchestration tools interact with spec-kitty CLI operations programmatically, without going through the human-facing CLI. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Command Envelope](#command-envelope), [API](./technology-foundations.md#api) |

---

### Decision

| | |
|---|---|
| **Definition** | A structured choice presented to the Human-in-Charge (HiC) or their delegated agent during the next-command loop. Each decision describes what needs to happen next and offers options to advance the mission. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Decision Kind](#decision-kind), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Decision Kind

| | |
|---|---|
| **Definition** | The type of choice being presented — for example, selecting which step to run next, resolving a conflict, or assigning a work package to an agent. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Decision](#decision) |

---

### Runtime Bridge

| | |
|---|---|
| **Definition** | The adapter that connects the CLI's decision loop to the mission execution engine. It translates internal runtime decisions into the format the HiC or agent sees while keeping mission identity separate from mission-run identity. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Decision](#decision), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Mission State Derivation

| | |
|---|---|
| **Definition** | The process of figuring out where a mission currently stands by reading filesystem artifacts and event logs, so the system can determine what mission actions are available next. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Run](#mission-run), [Decision](#decision) |

---

### Target Branch

| | |
|---|---|
| **Definition** | Mission-level routing value indicating which repository line receives lifecycle/status commits for that mission. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission](#mission), [Lane](#lane), [Work Package](#work-package) |

---

### Tracker Connector

| | |
|---|---|
| **Definition** | Outbound integration boundary that projects host lifecycle state to external tracker systems without transferring lifecycle authority. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Target Branch](#target-branch), [Orchestrator API](#orchestrator-api), [WPStatusChanged](./system-events.md#wpstatuschanged) |

---

### Tracker Connector Boundary (Alias)

| | |
|---|---|
| **Definition** | Architecture-facing alias for [Tracker Connector](#tracker-connector). |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Canonical entry** | [Tracker Connector](#tracker-connector) |
