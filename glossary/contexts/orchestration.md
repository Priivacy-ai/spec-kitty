## Context: Orchestration

Terms describing lifecycle and runtime orchestration semantics.

### Project

| | |
|---|---|
| **Definition** | Entire repository initialized for Spec Kitty workflow execution. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission

| | |
|---|---|
| **Definition** | Workflow definition that configures phases, templates, and guardrails. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission Run

| | |
|---|---|
| **Definition** | Runtime collaboration/execution container for a mission instance. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Scoping rule** | Runtime events should be scoped by `mission_run_id` as primary identity where available |

---

### Feature

| | |
|---|---|
| **Definition** | Planning and delivery unit in current 2.x artifact/worktree model (`kitty-specs/<feature-slug>/`). |
| **Context** | Orchestration |
| **Status** | canonical (compatibility) |
| **Applicable to** | `1.x`, `2.x` |
| **Note** | Feature remains a practical artifact key in 2.x while mission-centric runtime identity is strengthened |
| **CLI Flag (deprecated)** | The `--feature` flag is deprecated as of version 2.2.0. The canonical flag is now `--mission`. `--feature` remains a backward-compatible alias for one deprecation cycle and emits a deprecation warning when used. See `glossary/historical-terms.md` for the deprecated alias entry. |

---

### Work Package

| | |
|---|---|
| **Definition** | Executable slice of work inside a feature plan, typically represented as `WPxx` tasks. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

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
| **Definition** | Configuration file (`mission-runtime.yaml`) that defines a mission's steps, the order they run in, which steps depend on others, and where to find the prompt templates for each step. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission](#mission), [Step Dependency](#step-dependency), [Command Template](#command-template) |

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
| **Definition** | A markdown file that provides the prompt for a specific mission step. Located in the mission's template directory and loaded at runtime based on mission type and agent configuration. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Template Resolution](#template-resolution), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Template Resolution

| | |
|---|---|
| **Definition** | The process of finding and loading the correct command template for a given mission step, considering which mission type is active and which agent is running. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Command Template](#command-template) |

---

### Mission Discovery

| | |
|---|---|
| **Definition** | How the runtime finds and loads mission definition files (mission.yaml, mission-runtime.yaml) from the missions directory at startup. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission](#mission), [Mission-Runtime YAML](#mission-runtime-yaml) |

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
| **Definition** | A structured choice presented to the Human-in-Charge (HiC) or their delegated agent during the next-command loop. Each decision describes what needs to happen next and offers options to advance the mission workflow. |
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
| **Definition** | The adapter that connects the CLI's decision loop to the mission execution engine. It translates internal runtime decisions into the format the HiC or agent sees. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Decision](#decision), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Mission State Derivation

| | |
|---|---|
| **Definition** | The process of figuring out where a mission currently stands by reading filesystem artifacts and event logs, so the system can determine what actions are available next. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Run](#mission-run), [Decision](#decision) |

---

### Target Branch

| | |
|---|---|
| **Definition** | Feature-level routing value indicating which repository line receives lifecycle/status commits for that feature. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Feature](#feature), [Lane](#lane), [Work Package](#work-package) |

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

---

### Control Plane

| | |
|---|---|
| **Definition** | The user-facing interaction surface of the Spec Kitty system. Accepts commands and routes them to Kitty-core (planning), Constitution (governance), and Orchestration (execution control). The CLI is the current implementation; could also be a TUI, web app, or IDE plugin. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Slash Command](./execution.md#slash-command), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |
| **Architecture ref** | [System Landscape](../../architecture/2.x/00_landscape/README.md#control-plane) |

---

### Kitty-core

| | |
|---|---|
| **Definition** | The planning domain of Spec Kitty. Owns the Spec-Driven Development workflow (specify→plan→tasks), constructs the execution graph (WP dependency DAG) driven by mission templates and concrete missions, and coordinates the next-action loop. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Mission](#mission), [Mission Discovery](#mission-discovery), [Work Package](#work-package) |
| **Architecture ref** | [System Landscape](../../architecture/2.x/00_landscape/README.md#kitty-core) |

---

### Event Store

| | |
|---|---|
| **Definition** | Central persistence boundary for all system state. Both Kitty-core and Orchestration write events; Dashboard reads them. Currently implemented as filesystem artifacts (JSONL event logs, WP frontmatter, meta.json). Exposed through a service layer so the backing store can change without affecting consumers. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [WPStatusChanged](./system-events.md#wpstatuschanged), [Event Envelope](./system-events.md#event-envelope), [Lane](#lane) |
| **Architecture ref** | [System Landscape](../../architecture/2.x/00_landscape/README.md#event-store) |

---

### Dashboard

| | |
|---|---|
| **Definition** | Read-only visibility surface. Reads from the Event Store to present a kanban view of mission progress, WP status, and execution history. Has no write path to any other container. Currently implemented as a local Playwright-based browser kanban. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Event Store](#event-store), [Lane](#lane), [Work Package](#work-package) |
| **Architecture ref** | [System Landscape](../../architecture/2.x/00_landscape/README.md#dashboard) |
