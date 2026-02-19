## Context: Orchestration (Workflow & Lifecycle)

Terms describing spec-kitty's workflow engine and lifecycle management.

### Orchestration Assignment

|                   |                                                                                                                                                                        |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The complete binding of [agent](#agent), [role](#role), and [tool](#tool) for a single workflow step. The orchestrator constructs an assignment when dispatching work. |
| **Context**       | Orchestration                                                                                                                                                          |
| **Status**        | canonical                                                                                                                                                              |
| **Related terms** | [Agent](#agent), [Role](#role), [Tool](#tool)                                                                                                                          |

> Assign agent profile **"python pedro"**, with role **implementer**, running on tool **claude**.

```
┌─────────────────────────────────────────────┐
│  Orchestration Assignment                   │
│                                             │
│  agent_profile: "python-pedro"              │
│  role: implementer                          │
│  tool: claude                               │
│                                             │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │ Agent        │    │ Tool             │   │
│  │              │    │                  │   │
│  │ name         │    │ tool_id: claude  │   │
│  │ role         │    │ command: claude  │   │
│  │ capabilities │    │ uses_stdin: true │   │
│  │ directives   │    │ is_installed()   │   │
│  │ handoffs     │    │ build_command()  │   │
│  └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────┘
```

---

### Feature

|                   |                                                                                                                                                           |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A bounded unit of product change tracked by spec-kitty. Contains a spec, plan, tasks, and one or more work packages. Goes through the full SDD lifecycle. |
| **Context**       | Orchestration                                                                                                                                             |
| **Status**        | canonical                                                                                                                                                 |
| **In code**       | Feature directory at `kitty-specs/<number>-<slug>/`                                                                                                       |
| **Related terms** | [Work Package](#work-package), [Phase](#phase), [Spec-Driven Development](#spec-driven-development)                                                       |
| **Note**          | Specs are change deltas — they describe what to change, not the final state                                                                               |

---

### Research

|                   |                                                                                                                                                                                                                          |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Phase-0 discovery and evidence artifacts associated with a feature. Captures unresolved questions, source references, trade-off analysis, and rationale that inform specification and planning decisions.               |
| **Context**       | Orchestration                                                                                                                                                                                                            |
| **Status**        | canonical                                                                                                                                                                                                                |
| **Location**      | `kitty-specs/<feature>/research.md` and/or `kitty-specs/<feature>/research/`                                                                                                                                            |
| **Related terms** | [Feature](#feature), [Spec-Driven Development (SDD)](#spec-driven-development-sdd), [Contracts](#contracts)                                                                                                            |
| **Distinction**   | Research explains *why and based on what evidence* decisions are made; [Specification](#feature) defines *what change is requested*.                                                                                   |

---

### Contracts

|                   |                                                                                                                                                                                                                          |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Formal boundary definitions for a feature, typically API/event/schema/interface contracts that implementation must satisfy. Used to make cross-component expectations explicit before and during implementation.          |
| **Context**       | Orchestration                                                                                                                                                                                                            |
| **Status**        | canonical                                                                                                                                                                                                                |
| **Location**      | `kitty-specs/<feature>/contracts/`                                                                                                                                                                                       |
| **Related terms** | [Feature](#feature), [Research](#research), [Work Package (WP)](#work-package-wp)                                                                                                                                      |
| **Distinction**   | Contracts define *shape and compatibility constraints* at boundaries; [Plan](#phase) and tasks define *execution sequencing*.                                                                                           |

---

### Work Package (WP)

|                   |                                                                                                                                                                                                   |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An independently implementable unit of work within a feature. Each WP gets its own git worktree and branch. Tracked with frontmatter YAML including status lane, dependencies, and assigned tool. |
| **Context**       | Orchestration                                                                                                                                                                                     |
| **Status**        | canonical                                                                                                                                                                                         |
| **In code**       | `work_package_id`, `WPExecution` (dataclass), WP frontmatter in `tasks/*.md`                                                                                                                      |
| **Related terms** | [Feature](#feature), [Lane](#lane), [Worktree](#worktree), [Dependency Graph](#dependency-graph)                                                                                                  |
| **Identifiers**   | `WP01`, `WP02`, etc.                                                                                                                                                                              |

---

### Phase

|                   |                                                                                                                                      |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A stage in the spec-driven development lifecycle. Phases are sequential within a feature but WPs within a phase can run in parallel. |
| **Context**       | Orchestration                                                                                                                        |
| **Status**        | canonical                                                                                                                            |
| **Related terms** | [Feature](#feature), [Lane](#lane), [Spec-Driven Development](#spec-driven-development)                                              |
| **Values**        | `specify` → `plan` → `tasks` → `implement` → `review` → `accept` → `merge`                                                           |

---

### Lane

|                     |                                                                                                                                |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Definition**      | The status state of a work package in the canonical lifecycle model. Lane transitions are recorded as immutable status events. |
| **Context**         | Orchestration                                                                                                                  |
| **Status**          | canonical                                                                                                                      |
| **In code**         | Canonical model in `src/specify_cli/status/transitions.py`; compatibility view in WP frontmatter `lane`                        |
| **Related terms**   | [Work Package](#work-package), [Lane Transition Event](#lane-transition-event)                                                 |
| **Authority**       | ADR `2026-02-09-2` (latest lifecycle ADR) supersedes older 4-lane documentation                                                |
| **Canonical lanes** | `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`                                               |
| **Legacy alias**    | `doing` maps to `in_progress` for compatibility                                                                                |

---

### Worktree

|                   |                                                                                                                                |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An isolated git working directory created per work package via `git worktree`. Provides isolation between parallel agent work. |
| **Context**       | Orchestration                                                                                                                  |
| **Status**        | canonical                                                                                                                      |
| **In code**       | Located at `.worktrees/<feature>-<WP>/`                                                                                        |
| **Related terms** | [Work Package](#work-package)                                                                                                  |
| **Synonym**       | Run Container (ADR-048)                                                                                                        |

---

### Dependency Graph

|                   |                                                                                                                              |
|-------------------|------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A directed acyclic graph (DAG) of WP dependencies within a feature. Used to enforce ordering and plan parallelization waves. |
| **Context**       | Orchestration                                                                                                                |
| **Status**        | canonical                                                                                                                    |
| **In code**       | `DependencyGraph` class in `src/specify_cli/core/dependency_graph.py`                                                        |
| **Related terms** | [Work Package](#work-package)                                                                                                |

---

### Spec-Driven Development (SDD)

|                   |                                                                                                                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Spec Kitty's core methodology. The prescribed phase sequence: spec → plan → tasks → implement → review → accept → merge. Code is the source of truth; specs are change requests (deltas). |
| **Context**       | Orchestration                                                                                                                                                                             |
| **Status**        | canonical                                                                                                                                                                                 |
| **Related terms** | [Phase](#phase), [Feature](#feature)                                                                                                                                                      |
| **Directive**     | Directive 034                                                                                                                                                                             |

---

### Mission

|                   |                                                                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A versioned orchestration recipe for a domain. A mission defines workflow states, transitions, guards, and required artifacts. |
| **Context**       | Orchestration                                                                                                                                        |
| **Status**        | canonical                                                                                                                                            |
| **In code**       | `src/doctrine/missions/*/mission.yaml` (v2); compatibility assets still exist under `src/specify_cli/missions/`                                      |
| **Related terms** | [Phase](#phase), [Slash Command](#slash-command), [Constitution](#constitution), [Tool](#tool) |
| **Distinction**   | Mission defines orchestration (*what runs and when*). Constitution selects and narrows active governance assets for the project.                      |

---

### Slash Command

|                   |                                                                                                                                                                                                               |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An agent-facing shorthand command that triggers a spec-kitty workflow step (e.g., `/spec-kitty.specify`, `/spec-kitty.plan`). Implemented as markdown prompt templates deployed to tool-specific directories. |
| **Context**       | Orchestration                                                                                                                                                                                                 |
| **Status**        | canonical                                                                                                                                                                                                     |
| **In code**       | Source templates at `src/specify_cli/missions/*/command-templates/*.md`                                                                                                                                       |
| **Related terms** | [Mission](#mission), [Phase](#phase), [Tool](#tool)                                                                                                                                                           |
| **Distinction**   | Slash commands trigger lifecycle phases; [Tactics](#tactic) provide step-by-step execution within a phase                                                                                                     |

---

### User Journey

|                   |                                                                                                                                                                                                                                                                                                                                                                                                                |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A structured, end-to-end description of how actors (human, AI, system) interact with spec-kitty across phases, system boundaries, and coordination concerns. Unlike a User Story (single slice of value in `spec.md`), a User Journey maps the full flow including actors, events, coordination rules, and acceptance scenarios. User Journeys are architectural design artifacts that drive system evolution. |
| **Context**       | Orchestration                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Status**        | canonical                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Location**      | `architecture/journeys/*.md`                                                                                                                                                                                                                                                                                                                                                                                   |
| **Related terms** | [Feature](#feature), [Phase](#phase), [Mission](#mission)                                                                                                                                                                                                                                                                                                                                                      |
| **Template**      | `src/specify_cli/missions/design/templates/user-journey-template.md`                                                                                                                                                                                                                                                                                                                                           |
| **Distinction**   | User Stories live in `spec.md` and describe *what value to deliver*. User Journeys live in `architecture/journeys/` and describe *how actors interact with the system end-to-end*.                                                                                                                                                                                                                             |

---
