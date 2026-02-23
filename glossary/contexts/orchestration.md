## Context: Orchestration

Terms describing lifecycle and runtime orchestration semantics.

### Project

| | |
|---|---|
| **Definition** | Entire repository initialized for Spec Kitty workflow execution. |
| **Context** | Orchestration |
| **Status** | canonical |

---

### Mission

| | |
|---|---|
| **Definition** | Workflow definition that configures phases, templates, and guardrails. |
| **Context** | Orchestration |
| **Status** | canonical |

---

### Mission Run

| | |
|---|---|
| **Definition** | Runtime collaboration/execution container for a mission instance. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Scoping rule** | Runtime events should be scoped by `mission_run_id` as primary identity where available |

---

### Feature

| | |
|---|---|
| **Definition** | Planning and delivery unit in current 2.x artifact/worktree model (`kitty-specs/<feature-slug>/`). |
| **Context** | Orchestration |
| **Status** | canonical (compatibility) |
| **Note** | Feature remains a practical artifact key in 2.x while mission-centric runtime identity is strengthened |

---

### Work Package

| | |
|---|---|
| **Definition** | Executable slice of work inside a feature plan, typically represented as `WPxx` tasks. |
| **Context** | Orchestration |
| **Status** | canonical |

---

### Lane

| | |
|---|---|
| **Definition** | Work package state position (`planned`, `doing`, `for_review`, `done`, etc.). |
| **Context** | Orchestration |
| **Status** | canonical |

---

### Mission-Runtime YAML

| | |
|---|---|
| **Definition** | Configuration file (`mission-runtime.yaml`) that defines a mission's steps, the order they run in, which steps depend on others, and where to find the prompt templates for each step. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Mission](#mission), [Step Dependency](#step-dependency), [Command Template](#command-template) |

---

### Step Dependency

| | |
|---|---|
| **Definition** | A declared relationship saying "this step cannot start until that step finishes." Defined in mission-runtime YAML to enforce ordering. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Mission-Runtime YAML](#mission-runtime-yaml), [Step Sequence](#step-sequence) |

---

### Step Sequence

| | |
|---|---|
| **Definition** | The order in which mission steps execute, determined by the step list and dependency graph in mission-runtime YAML. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Step Dependency](#step-dependency), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Command Template

| | |
|---|---|
| **Definition** | A markdown file that provides the prompt for a specific mission step. Located in the mission's template directory and loaded at runtime based on mission type and agent configuration. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Template Resolution](#template-resolution), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Template Resolution

| | |
|---|---|
| **Definition** | The process of finding and loading the correct command template for a given mission step, considering which mission type is active and which agent is running. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Command Template](#command-template) |

---

### Mission Discovery

| | |
|---|---|
| **Definition** | How the runtime finds and loads mission definition files (mission.yaml, mission-runtime.yaml) from the missions directory at startup. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Mission](#mission), [Mission-Runtime YAML](#mission-runtime-yaml) |

---

### Command Envelope

| | |
|---|---|
| **Definition** | Standard JSON wrapper used to send commands to the orchestrator API. Contains identity fields, a version number, and the command payload. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Orchestrator API](#orchestrator-api), [Contract Version](#contract-version), [JSON](./technology-foundations.md#json) |

---

### Contract Version

| | |
|---|---|
| **Definition** | Version number on the orchestrator API that tells consumers whether the API has changed in a breaking way. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Orchestrator API](#orchestrator-api), [Command Envelope](#command-envelope) |

---

### Orchestrator API

| | |
|---|---|
| **Definition** | JSON-based interface that lets external orchestration tools interact with spec-kitty CLI operations programmatically, without going through the human-facing CLI. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Command Envelope](#command-envelope), [API](./technology-foundations.md#api) |

---

### Decision

| | |
|---|---|
| **Definition** | A structured choice presented to the Human-in-Charge (HiC) or their delegated agent during the next-command loop. Each decision describes what needs to happen next and offers options to advance the mission workflow. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Decision Kind](#decision-kind), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Decision Kind

| | |
|---|---|
| **Definition** | The type of choice being presented — for example, selecting which step to run next, resolving a conflict, or assigning a work package to an agent. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Decision](#decision) |

---

### Runtime Bridge

| | |
|---|---|
| **Definition** | The adapter that connects the CLI's decision loop to the mission execution engine. It translates internal runtime decisions into the format the HiC or agent sees. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Decision](#decision), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Mission State Derivation

| | |
|---|---|
| **Definition** | The process of figuring out where a mission currently stands by reading filesystem artifacts and event logs, so the system can determine what actions are available next. |
| **Context** | Orchestration |
| **Status** | candidate |
| **Related terms** | [Mission Run](#mission-run), [Decision](#decision) |

