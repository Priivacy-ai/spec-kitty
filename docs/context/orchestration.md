---
title: 'Context: Orchestration'
description: 'Glossary context for orchestration: lifecycle and runtime orchestration semantics, including the repository, project, and mission-run terms.'
doc_status: active
updated: '2026-07-23'
related:
- docs/context/doctrine.md
- docs/context/identity.md
- docs/context/system-events.md
- docs/context/technology-foundations.md
---
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
| **Definition** | Reusable workflow blueprint that configures the mission's steps (actions), their templates, and guardrails. |
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

### work package

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
| **Related terms** | [Mission Type](#mission-type), [step contract](#step-contract), [Procedure](./doctrine.md#procedure) |

---

### step contract

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
| **Rule** | Use [Mission Type](#mission-type), [Mission Action](#mission-action), [step contract](#step-contract), or [Procedure](./doctrine.md#procedure) when precision matters. |

---

### WorkPackage (Alias)

| | |
|---|---|
| **Definition** | Legacy lexical variant of [work package](#work-package). |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Canonical entry** | [work package](#work-package) |

---

### Lane

| | |
|---|---|
| **Definition** | work package state position in the canonical lifecycle FSM. Canonical lanes: `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`. Alias: `doing` -> `in_progress`. |
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
| **Related terms** | [Mission Type](#mission-type), [Step Dependency](#step-dependency), [step contract](#step-contract), [Command Template](#command-template) |

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

### base branch

| | |
|---|---|
| **Definition** | Overloaded key with two distinct scopes. (1) At the **mission level** (branch-context JSON output): alias for `target_branch` — the branch the mission is rooted in; `base_branch` and `target_branch` carry the same value in branch-context output. (2) At the **worktree/WP level** (WP prompt frontmatter): the specific git branch from which the individual lane worktree was created; this may be a lane branch (e.g. `kitty/mission-010-feature-lane-a`) rather than the target branch itself. JSON key: `base_branch`. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [target branch](#target-branch), [Planning base branch](#planning-base-branch), [Lane](#lane) |

---

### branch strategy gate

| | |
|---|---|
| **Definition** | The mission-create guard for PR-bound missions that requires an explicit operator or agent decision before planning artifacts are written on a primary branch. Interactive callers may confirm at the prompt; non-interactive callers record the already-made decision with `--branch-strategy already-confirmed`. When the recommended feature-branch path is chosen, pass `--start-branch` so the CLI switches before scaffold writes. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [pr-bound mission](#pr-bound-mission), [primary branch](#primary-branch), [feature branch](#feature-branch), [start branch](#start-branch) |

---

### current branch

| | |
|---|---|
| **Definition** | The git branch checked out in the main repository at the moment a workflow command is invoked. Read ephemerally from the working tree; never persisted in any mission artifact. Exposed as `current_branch` / `CURRENT_BRANCH` in branch-context JSON output. Since WP07 (FR-012), spec-kitty does **not** use `current_branch` to derive the mission target — it reads `target_branch` from `meta.json` instead, so the branch contract is stable regardless of which branch the operator is on. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [target branch](#target-branch), [base branch](#base-branch) |

---

### feature branch

| | |
|---|---|
| **Definition** | A dedicated git branch for pr-bound mission planning and implementation work, typically named `feat/<slug>` for feature work or `fix/<slug>` for bug-fix work. It is distinct from the primary branch and is the recommended start point when a mission is expected to become a pull request. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [pr-bound mission](#pr-bound-mission), [primary branch](#primary-branch), [start branch](#start-branch), [target branch](#target-branch) |

---

### gate binding

| | |
|---|---|
| **Definition** | A versioned doctrine declaration attaching a named gate handler to a status-transition edge (`{on_transition, handler, handler_kind, schema_version, fail_open, provenance}`), authored on the review `MissionStepContract`. A binding is a field/relationship, not a standalone artefact. Do NOT confuse with the five pre-existing `*gate*` senses (branch strategy gate / diff compliance gate / dependency gate / merge dependency gate / sonar quality gate) — those are unrelated one-off guards, not doctrine-resolved lane-edge checks. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [gate handler](#gate-handler), [transition gate](#transition-gate), [branch strategy gate](#branch-strategy-gate) |

---

### gate handler

| | |
|---|---|
| **Definition** | A named, dispatchable check registered in `GATE_REGISTRY`; the Spec-Kitty pre-review engine is the first handler, keyed to the `for_review` edge. Registry membership is the callable source; activation decides whether it runs. Do NOT confuse with the five pre-existing `*gate*` senses (branch strategy gate / diff compliance gate / dependency gate / merge dependency gate / sonar quality gate) — those are unrelated one-off guards, not doctrine-resolved dispatch callables. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [gate binding](#gate-binding), [transition gate](#transition-gate), [branch strategy gate](#branch-strategy-gate) |

---

### Merge target branch

| | |
|---|---|
| **Definition** | The branch where completed work-package code must ultimately land. Stored in every WP prompt's frontmatter (alongside `planning_base_branch`) to give implementing agents an explicit merge destination. In `meta.json`: legacy alias for `target_branch`, read as a fallback by `resolve_planning_branch_from_meta()` for pre-WP03 missions. In 3.x all three — `target_branch`, `planning_base_branch`, and `merge_target_branch` — carry the same value; the separation makes intent explicit in agent-facing prompts and prevents the "prep branch leak" (pre-WP07 pattern). JSON key: `merge_target_branch`. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [target branch](#target-branch), [Planning base branch](#planning-base-branch), [work package](#work-package) |

---

### Planning base branch

| | |
|---|---|
| **Definition** | The branch active in the repository root checkout when WP prompts were generated (at `finalize-tasks` time). Stored in every WP prompt's frontmatter and in `lanes.json` to root lane-worktree allocation correctly regardless of which branch the operator is on when running `finalize-tasks`. In 3.x equals `target_branch`. Introduced alongside `merge_target_branch` to close the "prep branch leak" bug (pre-WP07): when `finalize-tasks` ran from a temporary `prep/...` branch, that branch leaked into WP frontmatter and crashed lane allocation once the prep branch was deleted. JSON key: `planning_base_branch`. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [target branch](#target-branch), [Merge target branch](#merge-target-branch), [Lane](#lane), [work package](#work-package) |

---

### primary branch

| | |
|---|---|
| **Definition** | The repository's default integration branch, normally resolved from `origin/HEAD` and commonly named `main`, `master`, or `develop`. The specify branch-context output exposes this value as `primary_branch` only for branch-strategy recommendation; it is not automatically the mission's `target_branch` once `target_branch` has been persisted in `meta.json`. This is `primary` **Sense B** — the canonical term is "primary branch" (kept per operator decision D1); the wire keys `primary_branch` / `current_is_primary` are unchanged. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is the artifact-kind partition — use [PRIMARY partition](#primary-partition). The concept is the repository-root working copy versus a lane worktree — use [repository root checkout](./execution.md#repository-root-checkout). The concept is the ref planning artifacts commit to — use [Target Ref / Commit Target](#target-ref--commit-target). |
| **Related terms** | [current branch](#current-branch), [target branch](#target-branch), [feature branch](#feature-branch), [branch strategy gate](#branch-strategy-gate), [PRIMARY partition](#primary-partition), [repository root checkout](./execution.md#repository-root-checkout), [Target Ref / Commit Target](#target-ref--commit-target) |

---

### pr-bound mission

| | |
|---|---|
| **Definition** | A mission expected to land through a pull request rather than direct work on the primary branch. During mission create, `--pr-bound` activates the branch strategy gate so the branch choice is explicit before planning artifacts are written. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [branch strategy gate](#branch-strategy-gate), [feature branch](#feature-branch), [primary branch](#primary-branch) |

---

### start branch

| | |
|---|---|
| **Definition** | The branch passed to mission create with `--start-branch`. The CLI creates or switches to this branch before writing mission scaffolding, and it must match `--target-branch` when both options are supplied so mission metadata and the checked-out branch describe the same planning branch. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [feature branch](#feature-branch), [target branch](#target-branch), [branch strategy gate](#branch-strategy-gate) |

---

### target branch

| | |
|---|---|
| **Definition** | The git branch on which a mission's code, planning artifacts, and status events must ultimately land. Persisted in `meta.json` under the key `target_branch` at `mission create` time and never overwritten. Read by `resolve_planning_branch_from_meta()` as the canonical key; `merge_target_branch` is its legacy alias in older `meta.json` fixtures. Since WP07 (FR-012), all downstream commands — `finalize-tasks`, `implement`, `review`, `merge` — derive the branch contract from this stored value, not from `current_branch` at invocation time. In branch-context JSON output, `target_branch` and `base_branch` carry the same value at the mission level. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [base branch](#base-branch), [Planning base branch](#planning-base-branch), [Merge target branch](#merge-target-branch), [current branch](#current-branch), [Mission](#mission) |

---

### transition gate

| | |
|---|---|
| **Definition** | A check that must pass before a work-package status-transition edge (e.g. `in_progress->for_review`) is allowed. Resolved from the repo's active doctrine and dispatched through the inverted move-task hook (`_mt_run_transition_gates`); the flagship handler is the scoped pre-review regression check. Do NOT confuse with the five pre-existing `*gate*` senses (branch strategy gate / diff compliance gate / dependency gate / merge dependency gate / sonar quality gate) — those are unrelated one-off guards, not doctrine-resolved lane-edge checks. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [gate handler](#gate-handler), [gate binding](#gate-binding), [branch strategy gate](#branch-strategy-gate) |

---

### Tracker Connector

| | |
|---|---|
| **Definition** | Outbound integration boundary that projects host lifecycle state to external tracker systems without transferring lifecycle authority. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [target branch](#target-branch), [Orchestrator API](#orchestrator-api), [WPStatusChanged](./system-events.md#wpstatuschanged) |

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

### PRIMARY partition

| | |
|---|---|
| **Definition** | The artifact-kind partition that holds stable planning artifacts — spec, plan, work-package outlines, and `meta.json` — as distinct from the [COORD partition](#coord-partition) that holds the lifecycle artifacts (status, notes, trace, issue-matrix, `move-task`). A partition is an artifact-kind *routing* concept: it decides which [topology surface](#topology-surface) an artifact kind is written to. It is **not** a git branch. Missions with no coordination topology (`SINGLE_BRANCH` / `LANES`) route every artifact kind to PRIMARY. This is `primary` **Sense A**. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is the repository's default integration branch — use [primary branch](#primary-branch). The concept is the repository-root working copy versus a lane worktree — use [repository root checkout](./execution.md#repository-root-checkout). The concept is the ref that planning artifacts commit to — use [Target Ref / Commit Target](#target-ref--commit-target). The concept is the physical tree the routed artifact lands in — use [Topology Surface](#topology-surface). Never write bare "primary" for the partition; always say "PRIMARY partition". |
| **Related terms** | [primary branch](#primary-branch), [COORD partition](#coord-partition), [Topology Surface](#topology-surface), [repository root checkout](./execution.md#repository-root-checkout), [Target Ref / Commit Target](#target-ref--commit-target), [target branch](#target-branch) |

---

### Target Ref / Commit Target

| | |
|---|---|
| **Definition** | The git ref that a mission's planning artifacts and status events are committed against — the "commit target" the resolver writes to. In current code this resolves to the mission's `target_branch`. It is distinct from the artifact-kind partition (which decides *which surface* an artifact is written to) and from the repository's default integration branch. This is `primary` **Sense D**; the retired alias phrases "primary target" and "primary ref" describe this sense. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is the artifact-kind partition — use [PRIMARY partition](#primary-partition). The concept is the repository's default integration branch — use [primary branch](#primary-branch). The concept is the branch the mission's code must ultimately land on — use [target branch](#target-branch). Avoid the bare aliases "primary target" and "primary ref". |
| **Related terms** | [target branch](#target-branch), [Merge target branch](#merge-target-branch), [base branch](#base-branch), [current branch](#current-branch), [PRIMARY partition](#primary-partition) |

---

### Lane Consolidation

| | |
|---|---|
| **Definition** | The `spec-kitty merge` operation: LOCAL consolidation of completed lane branches into the mission branch, with **no** push to any remote. Realized by the internal helper `consolidate_lane_into_mission`. This is `merge` **Sense 1** — the first of three distinct "merge" operations. It stops at local main; it never publishes. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is the `git merge` that integrates the mission branch into its target branch — use [Branch Integration / Git Merge](#branch-integration--git-merge). The concept is publishing merged work to `origin/main` — use [Publish to origin/main](#publish-to-originmain). Never write bare "merge"; name the operation. |
| **Related terms** | [Branch Integration / Git Merge](#branch-integration--git-merge), [Publish to origin/main](#publish-to-originmain), [Merge target branch](#merge-target-branch), [Lane](#lane), [Topology Surface](#topology-surface) |

---

### Branch Integration / Git Merge

| | |
|---|---|
| **Definition** | The `git merge` operation that integrates the mission branch into its target branch. Realized by the internal helper `integrate_mission_into_target`. This is `merge` **Sense 2** — branch-to-branch integration, distinct from local lane consolidation and from publishing to origin. The `MergeStrategy` literals (`merge` / `squash` / `rebase`) select *how* this integration is performed and are unchanged serialized contracts. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is `spec-kitty merge`'s local lane consolidation — use [Lane Consolidation](#lane-consolidation). The concept is publishing merged work to `origin/main` — use [Publish to origin/main](#publish-to-originmain). |
| **Related terms** | [Lane Consolidation](#lane-consolidation), [Publish to origin/main](#publish-to-originmain), [target branch](#target-branch), [Merge target branch](#merge-target-branch) |

---

### Publish to origin/main

| | |
|---|---|
| **Definition** | The operator-only act of publishing merged mission work to `origin/main`, always through a pull request — never a direct push. Represented in the merge flow by `push_requested`. `spec-kitty merge` deliberately does **not** perform this step; it stops at LOCAL consolidation. This is `merge` **Sense 3** — the publish operation, sometimes called "operator merge". |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is `spec-kitty merge`'s local lane consolidation — use [Lane Consolidation](#lane-consolidation). The concept is the `git merge` branch-integration step — use [Branch Integration / Git Merge](#branch-integration--git-merge). |
| **Related terms** | [Lane Consolidation](#lane-consolidation), [Branch Integration / Git Merge](#branch-integration--git-merge), [primary branch](#primary-branch) |

---

### COORD partition

| | |
|---|---|
| **Definition** | The artifact-kind partition that holds a mission's lifecycle/coordination artifacts — status events, notes, trace, issue-matrix, acceptance-matrix, review cycles, `move-task` — as distinct from the [PRIMARY partition](#primary-partition) that holds stable planning artifacts. Like PRIMARY it is an artifact-kind *routing* concept, **not** a git branch and **not** a directory: it decides which surface a kind is written to. Only missions whose stored topology routes through coordination (`COORD` / `LANES_WITH_COORD`) have a materialised COORD surface; `SINGLE_BRANCH` / `LANES` missions route every kind to PRIMARY. Realized in code as the `_PLACEMENT_ARTIFACT_KINDS` frozenset in `mission_runtime/artifacts.py`, whose partition-invariant P-1 (disjoint and jointly exhaustive with `_PRIMARY_ARTIFACT_KINDS`) is asserted at the placement seam. |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Do NOT use when** | The concept is the physical tree an artifact resolves to — use [Topology Surface](#topology-surface). The concept is a coordination *branch* or *worktree* — say "coord branch" / "coord worktree" explicitly. Never write bare "coord" for the partition; always say "COORD partition". |
| **Related terms** | [PRIMARY partition](#primary-partition), [Topology Surface](#topology-surface), [Lane](#lane), [Mission](#mission) |

---

### Topology Surface

| | |
|---|---|
| **Definition** | The physical tree (working copy / checkout location) that a mission artifact resolves to for reading and writing. This is `surface` **Sense 2** — the mission-topology sense. Modelled by the `TopologySurface` enum in `src/mission_runtime/artifacts.py`, carried on `MissionArtifactHome` as `read_surface` / `write_surface`, and returned by `artifact_home_for`. Live members today: `PRIMARY` — the repository-root planning tree; `COORD` — the mission's coordination tree. Planned members, landing together with the surface→filesystem translation seam that makes each resolvable: `LANE` — a per-work-package lane worktree under `.worktrees/`; `CONSOLIDATED` — the tree after lane branches have been consolidated into the mission branch; `TEMP` — an ephemeral scratch tree with no durable home. The three planned members are deliberately **not** declared ahead of that seam: a member no caller can translate to a location is a phantom, and the seam's totality test exists precisely to catch that. Renamed from `Surface` (whose members were `PRIMARY` \| `PLACEMENT`, with a `str` mixin and an `ArtifactSurface` back-compat alias, both retired) per ADR [2026-07-23-1](../adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md). |
| **Context** | Orchestration |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Note** | A topology surface is a *location*; a partition is a *routing rule over artifact kinds*. The two vocabularies coincide only on the `PRIMARY` and `COORD` values — the [PRIMARY partition](#primary-partition) routes its kinds to the `PRIMARY` topology surface and the [COORD partition](#coord-partition) to the `COORD` topology surface. `LANE`, `CONSOLIDATED`, and `TEMP` are locations with no partition of their own. Prose also uses "surface" as an ungoverned generic modifier ("command surface", "API surface", "doc surface") meaning "the outward face of X"; that usage is not governed here, but it must always carry its modifier — bare "surface" always means one of the two governed senses. |
| **Note (naming vs conditioning)** | Naming a surface `COORD` does **not** violate the rule against conditioning behaviour on topology. Naming a real surface is correct; *branching* on it — `if surface is COORD: ...` in place of a resolved read/write path — is what is forbidden. The prior member name `PLACEMENT` avoided the *word* while keeping the *concept*; explicitness is preferred. |
| **Note (`CONSOLIDATED`, not `MERGED`)** | The post-consolidation surface is named `CONSOLIDATED` because `merge` is itself a three-sense overloaded term in this codebase — [Lane Consolidation](#lane-consolidation), [Branch Integration / Git Merge](#branch-integration--git-merge), and [Publish to origin/main](#publish-to-originmain). A member named `MERGED` would not say which of the three had happened. `CONSOLIDATED` names exactly one: the surface that exists after [Lane Consolidation](#lane-consolidation). This is the same disambiguation discipline already applied to `primary` / `main` / `base`. |
| **Do NOT use when** | The concept is a tool-visible artifact or configuration entry Spec Kitty installs for a concrete execution tool — use [Tool Surface](./execution.md#tool-surface) (`surface` **Sense 1**). The concept is the artifact-kind routing rule rather than the location — use [PRIMARY partition](#primary-partition) or [COORD partition](#coord-partition). The concept is the repository-root working copy versus a lane worktree as an operator-facing checkout — use [repository root checkout](./execution.md#repository-root-checkout). Never write bare "surface" in governed prose; name the sense ("topology surface" / "tool surface"). |
| **Related terms** | [Tool Surface](./execution.md#tool-surface), [PRIMARY partition](#primary-partition), [COORD partition](#coord-partition), [Lane](#lane), [Lane Consolidation](#lane-consolidation), [repository root checkout](./execution.md#repository-root-checkout) |
