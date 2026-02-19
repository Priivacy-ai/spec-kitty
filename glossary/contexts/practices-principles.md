## Context: Practices & Principles

Terms describing cross-cutting development practices and principles aligned with the Agentic Doctrine.

### Human In Charge

|                   |                                                                                                                                                                                                                                                                                                                                                                                                                |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The foundational governance principle that humans retain authority over all critical decisions. Agents may operate autonomously within defined decision boundaries but must escalate architectural changes, breaking changes, security modifications, and ambiguous requirements. The `work/human-in-charge/` directory structure provides escalation channels (decision requests, blockers, problem reports). |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                                                                                                                                                         |
| **Status**        | canonical                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Related terms** | [Decision Boundary](#decision-boundary), [Escalation](#escalation), [Human Review Loop](#human-review-loop), [AFK Mode](#afk-mode)                                                                                                                                                                                                                                                                             |

---

### Human Review Loop

|                   |                                                                                                                                                                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A checkpoint in the workflow where a human reviews agent-produced work before it advances. In Spec Kitty, the `for_review` lane and `/spec-kitty.review` command embody this pattern. Ensures quality gates remain under human authority. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                    |
| **Status**        | canonical                                                                                                                                                                                                                                 |
| **Related terms** | [Human In Charge](#human-in-charge), [Lane](#lane), [Phase Checkpoint Protocol](#phase-checkpoint-protocol)                                                                                                                               |

---

### Escalation

|                   |                                                                                                                                                                                                                                                 |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The act of an agent pausing autonomous work and requesting human guidance. Triggered by blockers, critical decisions, ambiguous requirements, or unexpected results. Escalation artifacts are placed in `work/human-in-charge/` subdirectories. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                          |
| **Status**        | canonical                                                                                                                                                                                                                                       |
| **Related terms** | [Human In Charge](#human-in-charge), [Decision Boundary](#decision-boundary), [Stopping Condition](#stopping-condition)                                                                                                                         |

---

### Decision Boundary

|                   |                                                                                                                                                                                                                                                                                             |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The classification of decisions into minor (agent-autonomous) and critical (requires human approval). Minor: file naming, code style, test data, documentation phrasing. Critical: architectural changes, breaking APIs, schema modifications, dependency changes, security policy changes. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                                      |
| **Status**        | canonical                                                                                                                                                                                                                                                                                   |
| **Related terms** | [Human In Charge](#human-in-charge), [AFK Mode](#afk-mode), [Escalation](#escalation)                                                                                                                                                                                                       |

---

### Collaboration Contract

|                   |                                                                                                                                                                                                                                                                       |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The behavioral commitments defined in an agent profile — what the agent will do, how it will communicate, when it will escalate, and what quality standards it upholds. Each Doctrine agent profile (`doctrine/agents/*.agent.md`) embodies a collaboration contract. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                                                             |
| **Related terms** | [Agent Profile](#agent-profile), [Decision Boundary](#decision-boundary), [Human In Charge](#human-in-charge)                                                                                                                                                         |

---

### Phase Authority

|                   |                                                                                                                                                                                                                                                    |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The designation of who owns each phase of the Spec-Driven Development lifecycle. Different phases may have different authority levels — e.g., specification is human-owned, implementation may be agent-delegated, review requires human sign-off. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                             |
| **Status**        | canonical                                                                                                                                                                                                                                          |
| **Related terms** | [Phase](#phase), [Human In Charge](#human-in-charge), [Phase Checkpoint Protocol](#phase-checkpoint-protocol)                                                                                                                                      |

---

### Phase Checkpoint Protocol

|                   |                                                                                                                                                                                                                         |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | End-of-phase verification ensuring deliverables meet quality gates before proceeding. Each SDD phase has defined exit criteria. Checkpoints may be automated (tests pass, lint clean) or human-gated (review approval). |
| **Context**       | Practices & Principles                                                                                                                                                                                                  |
| **Status**        | canonical                                                                                                                                                                                                               |
| **Related terms** | [Phase Authority](#phase-authority), [Human Review Loop](#human-review-loop), [Validation Result](#validation-result)                                                                                                   |

---

### Pre-flight Validation

|                   |                                                                                                                                     |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Automatic validation checks run before high-impact workflow actions (especially merge) to catch blocking conditions early.          |
| **Context**       | Practices & Principles                                                                                                              |
| **Status**        | canonical                                                                                                                           |
| **Related terms** | [Phase Checkpoint Protocol](#phase-checkpoint-protocol), [Merge State](#merge-state), [Conflict Forecasting](#conflict-forecasting) |

---

### Conflict Forecasting

|                   |                                                                                                  |
|-------------------|--------------------------------------------------------------------------------------------------|
| **Definition**    | Predictive merge-time analysis that estimates likely conflicts before executing an actual merge. |
| **Context**       | Practices & Principles                                                                           |
| **Status**        | canonical                                                                                        |
| **Related terms** | [Pre-flight Validation](#pre-flight-validation), [Merge State](#merge-state)                     |

---

### Merge State

|                   |                                                                                                            |
|-------------------|------------------------------------------------------------------------------------------------------------|
| **Definition**    | Persisted merge-progress state used to support interrupted merge recovery via resume/abort workflows.      |
| **Context**       | Practices & Principles                                                                                     |
| **Status**        | canonical                                                                                                  |
| **Location**      | `.kittify/merge-state.json`                                                                                |
| **Related terms** | [Interrupted Merge Recovery](#interrupted-merge-recovery), [Pre-flight Validation](#pre-flight-validation) |

---

### Interrupted Merge Recovery

|                   |                                                                                                                                                |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The operational protocol for recovering from interrupted merges, typically using `--resume` to continue or `--abort` to reset and start clean. |
| **Context**       | Practices & Principles                                                                                                                         |
| **Status**        | canonical                                                                                                                                      |
| **Related terms** | [Merge State](#merge-state), [Pre-flight Validation](#pre-flight-validation)                                                                   |

---

### Living Glossary

|                   |                                                                                                                                                                                                                                 |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A glossary that evolves with the codebase — terms are added, refined, or deprecated as the domain understanding deepens. This very document is a living glossary. Terminology decisions are treated as architectural decisions. |
| **Context**       | Practices & Principles                                                                                                                                                                                                          |
| **Status**        | canonical                                                                                                                                                                                                                       |
| **Related terms** | [Living Specification](#living-specification)                                                                                                                                                                                   |

---

### Living Specification

|                   |                                                                                                                                                                                                                                                                                       |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A specification that evolves during discovery and planning phases, then freezes at implementation start. In Spec Kitty, `spec.md` is living during `/spec-kitty.specify` and `/spec-kitty.clarify`, then becomes the frozen contract that `plan.md` and `tasks.md` implement against. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                                                                             |
| **Related terms** | [Living Glossary](#living-glossary), [Spec-Driven Development](#spec-driven-development)                                                                                                                                                                                              |

---

### Stopping Condition

|                   |                                                                                                                                                                                                                                            |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A predefined criterion that tells an agent when to halt pursuit of a goal. Prevents unbounded iteration. Examples: test suite passes, lint clean, reviewer approves, maximum retry count reached, or an escalation condition is triggered. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                     |
| **Status**        | canonical                                                                                                                                                                                                                                  |
| **Related terms** | [Escalation](#escalation), [Decision Boundary](#decision-boundary)                                                                                                                                                                         |

---

### File-Based Orchestration

|                   |                                                                                                                                                                                                                                                                                                                                                                       |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The coordination pattern where workflow state is stored in files (YAML frontmatter, markdown, JSON) rather than a database or API. Spec Kitty uses file-based orchestration — lane status lives in WP frontmatter, config in `.kittify/config.yaml`, events in JSONL files. Enables git-native versioning and multi-agent coordination without shared infrastructure. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                                                                                                                                                             |
| **Related terms** | [Lane](#lane), [Work Package](#work-package), [EventBridge](#eventbridge)                                                                                                                                                                                                                                                                                             |

---

### AFK Mode

|                   |                                                                                                                                                                                                                                                                                                                                   |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Away From Keyboard — a session management protocol granting agents extended autonomy with defined boundaries. When activated: commit after each logical unit, push permission granted, minor decisions autonomous, critical decisions trigger escalation. Deactivated when human returns or agent encounters a critical decision. |
| **Context**       | Practices & Principles                                                                                                                                                                                                                                                                                                            |
| **Status**        | canonical                                                                                                                                                                                                                                                                                                                         |
| **Related terms** | [Human In Charge](#human-in-charge), [Decision Boundary](#decision-boundary), [Escalation](#escalation)                                                                                                                                                                                                                           |

---

