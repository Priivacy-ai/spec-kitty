## Context: Governance

Terms describing rule ownership, precedence, and policy controls in Spec Kitty.

### Constitution

| | |
|---|---|
| **Definition** | Project-level policy document that captures the HiC's operating constraints, quality rules, and doctrine selections for a repository. Compiled from interview answers and doctrine catalog choices. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Project Constitution](./configuration-project-structure.md#project-constitution), [Constitution Interview](#constitution-interview), [Constitution Compiler](#constitution-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### ADR (Architectural Decision Record)

| | |
|---|---|
| **Definition** | Immutable record of a significant technical/domain decision, with context and consequences. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Location** | `architecture/1.x/adr/` and `architecture/2.x/adr/` |

---

### Glossary Strictness Policy

| | |
|---|---|
| **Definition** | Governance rule for how semantic conflicts are treated (`warn` vs `block`) under each strictness mode. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Default** | `medium` |

---

### Clarification Burst Policy

| | |
|---|---|
| **Definition** | Rule that limits clarification interruption by prioritizing highest-impact conflicts first and capping prompt count per burst. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Cap** | 3 prompts per burst |

---

### Precedence Rule

| | |
|---|---|
| **Definition** | Ordering used when policy settings conflict. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Operational order (strictness)** | CLI override > step metadata > mission config > global default |

---

### Constitution Interview

| | |
|---|---|
| **Definition** | A guided question-and-answer process that walks the HiC through their project's preferences, constraints, and doctrine selections. Answers are saved to `answers.yaml` and used to compile the constitution. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Constitution](#constitution), [Constitution Compiler](#constitution-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Constitution Compiler

| | |
|---|---|
| **Definition** | The processor that takes the HiC's interview answers and their selected doctrine artifacts, and combines them into a finalized constitution document and supporting governance files. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Constitution](#constitution), [Constitution Interview](#constitution-interview), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |

---

### Governance Resolution

| | |
|---|---|
| **Definition** | The result of checking the HiC's constitution selections against available doctrine catalogs — confirming that the referenced paradigms, directives, and tools actually exist and are compatible with each other. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Constitution Compiler](#constitution-compiler), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |

---

### Context Bootstrap

| | |
|---|---|
| **Definition** | The entry point at every execution boundary (Principle 5: Governance at the Execution Boundary) that injects action-scoped governance context into the agent prompt. Invoked via `spec-kitty constitution context --action <action>`. First invocation per action returns depth-2 full content (bootstrap); subsequent calls return depth-1 compact content. State tracked in `context-state.json`. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Location** | `src/constitution/context.py` |
| **Related terms** | [Constitution](#constitution), [Two-Stage Intersection](#two-stage-intersection), [Action Index](./doctrine.md#action-index), [Agent Tool Connector](./execution.md#agent-tool-connector) |

---

### Two-Stage Intersection

| | |
|---|---|
| **Definition** | The governance scoping mechanism that determines which doctrine content is injected for a given execution. Stage 1 selects the doctrine artifacts relevant to the action (via the Action Index). Stage 2 intersects with the project's constitution selections (via `references.yaml`). Only artifacts appearing in both stages are included. Prevents cross-action governance bleed while respecting project-level policy choices. |
| **Context** | Governance |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Context Bootstrap](#context-bootstrap), [Action Index](./doctrine.md#action-index), [Constitution Selection](./doctrine.md#constitution-selection), [Governance Resolution](#governance-resolution) |
