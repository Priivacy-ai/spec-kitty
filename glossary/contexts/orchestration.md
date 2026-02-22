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

