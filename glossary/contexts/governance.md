## Context: Governance

Terms describing governance runtime behavior, enforcement, and decision accountability.

### Doctrine (Agentic Doctrine)

|                   |                                                                                                                                                                                                                                                                         |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Spec Kitty's governance framework that defines reusable behavioral assets and rules. Domain terms for doctrine artifacts are canonicalized in the Doctrine glossary context.                                                                                           |
| **Context**       | Governance                                                                                                                                                                                                                                                              |
| **Status**        | canonical                                                                                                                                                                                                                                                               |
| **Reference**     | Doctrine domain glossary: `glossary/contexts/doctrine.md`                                                                                                                                                                                                              |
| **Related terms** | [Constitution](#constitution), [Precedence Hierarchy](#precedence-hierarchy), [Doctrine Domain](./doctrine.md)                                                                                                                                                        |

---

### Constitution

|                         |                                                                                                                                                                                                                                                                     |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**          | A project-level governance document that narrows or extends Doctrine rules for a specific repository. It is the execution-time selector layer for active paradigms, directives, template sets, selected agent profiles, and available tools. Human-readable markdown created via `/spec-kitty.constitution` in current implementation. May narrow directive thresholds but must not contradict Guidelines. |
| **Context**             | Governance                                                                                                                                                                                                                                                          |
| **Status**              | canonical                                                                                                                                                                                                                                                           |
| **Location**            | `.kittify/memory/constitution.md`                                                                                                                                                                                                                                   |
| **In code**             | Constitution command templates; parser and enforcement are evolving under Feature 044                                                                                                                                                                               |
| **Related terms**       | [Precedence Hierarchy](#precedence-hierarchy), [Doctrine](#doctrine-agentic-doctrine), [Constitution Selection](./doctrine.md)                                                                                                                                    |
| **Precedence position** | 3 (after General and Operational Guidelines; before Directives)                                                                                                                                                                                                     |

---

### Precedence Hierarchy

|                      |                                                                                                                                                                                               |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**       | The conflict resolution order when governance rules disagree. Higher-precedence rules override lower ones. This is the governing rule for resolving conceptual conflicts in governance terms. |
| **Context**          | Governance                                                                                                                                                                                    |
| **Status**           | canonical                                                                                                                                                                                     |
| **In code**          | Defined in Feature 044 governance spec; implementation is in progress                                                                                                                         |
| **Related terms**    | [Constitution](#constitution), [Doctrine](#doctrine-agentic-doctrine), [Guideline](./doctrine.md), [Directive](./doctrine.md), [Paradigm](./doctrine.md), [Tactic](./doctrine.md)        |
| **Operational rule** | When sources disagree, apply this hierarchy first; use newer accepted ADRs over older ADRs; then align with current implementation behavior                                                   |

```
General Guidelines > Operational Guidelines > Constitution > Directives > Paradigms > Tactics/Templates
```

---

### Governance Plugin

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An ABC that validates workflow state at lifecycle boundaries. Returns a `ValidationResult` (pass/warn/block) with reasons, directive references, and suggested actions. The `NullGovernancePlugin` is the default no-op implementation. |
| **Context**       | Governance                                                                                                                                                                                                                              |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **In code**       | `GovernancePlugin` (ABC), `NullGovernancePlugin`, `DoctrineGovernancePlugin`                                                                                                                                                            |
| **Related terms** | [Validation Result](#validation-result), [Governance Context](#governance-context)                                                                                                                                                      |

---

### Validation Result

|                   |                                                                                                                                   |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Structured output of a governance check. Contains status (pass/warn/block), reasons, directive references, and suggested actions. |
| **Context**       | Governance                                                                                                                        |
| **Status**        | canonical                                                                                                                         |
| **In code**       | `ValidationResult` (Pydantic BaseModel, frozen)                                                                                   |
| **Related terms** | [Governance Plugin](#governance-plugin), [Validation Event](#validation-event)                                                    |
| **Fields**        | `status` (ValidationStatus), `reasons` (list[str]), `directive_refs` (list[int]), `suggested_actions` (list[str])                 |

---

### Governance Context

|                   |                                                                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The context object passed to governance hooks. Provides the plugin with enough information to make a validation decision without direct file access. |
| **Context**       | Governance                                                                                                                                           |
| **Status**        | canonical                                                                                                                                            |
| **In code**       | `GovernanceContext` (Pydantic BaseModel, frozen)                                                                                                     |
| **Related terms** | [Governance Plugin](#governance-plugin), [Tool](#tool), [Agent](#agent), [Role](#role)                                                               |

**Fields**:

- `phase` — Current lifecycle phase
- `feature_slug` — Feature identifier
- `work_package_id` — WP being validated
- `tool_id` — Which tool is executing
- `agent_profile_id` — Which Doctrine agent profile applies
- `agent_role` — Role: implementer, reviewer, etc.

---

### Two-Masters Problem

|                   |                                                                                                                                                                                                                                                                                                             |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The conflict that arises when both Guidelines and the Constitution claim top-level behavioral authority over agents. Resolved by the Precedence Hierarchy: Constitution sits at position 3 — it customizes within Guideline bounds, not above them.                                                     |
| **Context**       | Governance                                                                                                                                                                                                                                                                                                  |
| **Status**        | canonical                                                                                                                                                                                                                                                                                                   |
| **Synonyms**      | Dual Authority Problem                                                                                                                                                                                                                                                                                      |
| **Related terms** | [Precedence Hierarchy](#precedence-hierarchy), [Constitution](#constitution), [Guideline](./doctrine.md)                                                                                                                                                                                                  |

---

### ADR (Architectural Decision Record)

|                   |                                                                                                                                                                                                                               |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An immutable record of a single architecturally significant decision, including context, alternatives considered, decision outcome, and consequences. Accepted ADRs are not edited; changes are captured by superseding ADRs. |
| **Context**       | Governance                                                                                                                                                                                                                    |
| **Status**        | canonical                                                                                                                                                                                                                     |
| **Location**      | `architecture/adrs/`                                                                                                                                                                                                          |
| **Related terms** | [Constitution](#constitution), [Precedence Hierarchy](#precedence-hierarchy), [Living Specification](#living-specification)                                                                                                   |

---
