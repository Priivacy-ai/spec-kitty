## Context: Orchestration

Terms describing lifecycle and runtime orchestration semantics.

### Repository

| | |
|---|---|
| **Definition** | The local git repository that a [Project](#project) is initialized from and executes within. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | Use this term when the repository boundary itself matters, especially for repository-scoped identity and sync semantics. |
| **Related terms** | [Project](#project), [Build](#build) |

---

### Project

| | |
|---|---|
| **Definition** | Entire repository initialized for Spec Kitty workflow execution. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission Type

| | |
|---|---|
| **Definition** | Reusable workflow blueprint that configures mission actions, templates, and guardrails. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Build

| | |
|---|---|
| **Definition** | One checkout or worktree execution context inside a [Repository](#repository), identified by machine and build-scoped runtime identity. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | Use this term when distinguishing per-worktree or per-machine runtime context from the repository boundary itself. |
| **Related terms** | [Repository](#repository), [Mission Run](#mission-run) |

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
| **Definition** | A structured choice presented to the Human-in-Charge (HiC) or their delegated agent during the next-command loop. Each decision describes what needs to happen next and offers options to advance the mission. In event-backed runtimes, a pending Decision is tracked until answered, then closed. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x`, `3.x` |
| **Lifecycle** | In event-backed runtimes, opened by [Decision Input Request](#decision-input-request); closed by [Decision Input Answer](#decision-input-answer). |
| **SaaS projection** | Materialised as a `DecisionInboxItem` (pending → answered) in the TeamSpace. |
| **Not to be confused with** | SaaS `Decision` (an immutable recorded past collaboration choice); SaaS `DecisionPoint` (a first-class team-consultation entity that can be widened, deferred, or resolved independently of the loop). See the SaaS domain glossary at `architecture/domain-glossary.md`. |
| **Related terms** | [Decision Kind](#decision-kind), [Decision Input Request](#decision-input-request), [Decision Input Answer](#decision-input-answer), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Decision Kind

| | |
|---|---|
| **Definition** | The type of choice being presented — for example, selecting which step to run next, resolving a conflict, or assigning a work package to an agent. In the `spec-kitty next --json` contract this is carried as the top-level `kind` field; `DecisionInputRequested` events are emitted only for `decision_required` choices and do not repeat that field. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x`, `3.x` |
| **Related terms** | [Decision](#decision), [Decision Input Request](#decision-input-request) |

---

### Decision Input Request

| | |
|---|---|
| **Definition** | The event emitted by the runtime when it opens a [Decision](#decision) and requires a response from the HiC or a delegated agent. Carries the question text, candidate options, step context, and a unique `decision_id`. Opening a Decision Input Request is what makes a Decision "pending". |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Event type** | `DecisionInputRequested` (in `spec-kitty-events`) |
| **SaaS effect** | Creates a `DecisionInboxItem` row with `state=pending`. |
| **Related terms** | [Decision](#decision), [Decision Input Answer](#decision-input-answer), [Mission Run](#mission-run) |

---

### Decision Input Answer

| | |
|---|---|
| **Definition** | The event emitted when the HiC or a delegated agent answers a pending [Decision](#decision). Carries the chosen answer, the actor identity, and the originating `decision_id`. Answering closes the Decision; the loop continues. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Event type** | `DecisionInputAnswered` (in `spec-kitty-events`) |
| **SaaS effect** | Updates the matching `DecisionInboxItem` to `state=answered`. |
| **Related terms** | [Decision](#decision), [Decision Input Request](#decision-input-request) |

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
