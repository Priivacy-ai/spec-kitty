## Context: Governance

Terms describing rule ownership, precedence, and policy controls in Spec Kitty.

### Constitution

| | |
|---|---|
| **Definition** | Project-level policy document that captures the HiC's operating constraints, quality rules, and doctrine selections for a repository. Compiled from interview answers and doctrine catalog choices. |
| **Context** | Governance |
| **Status** | canonical |
| **Related terms** | [Project Constitution](./configuration-project-structure.md#project-constitution), [Constitution Interview](#constitution-interview), [Constitution Compiler](#constitution-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### ADR (Architectural Decision Record)

| | |
|---|---|
| **Definition** | Immutable record of a significant technical/domain decision, with context and consequences. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `architecture/adrs/` |

---

### Glossary Strictness Policy

| | |
|---|---|
| **Definition** | Governance rule for how semantic conflicts are treated (`warn` vs `block`) under each strictness mode. |
| **Context** | Governance |
| **Status** | canonical |
| **Default** | `medium` |

---

### Clarification Burst Policy

| | |
|---|---|
| **Definition** | Rule that limits clarification interruption by prioritizing highest-impact conflicts first and capping prompt count per burst. |
| **Context** | Governance |
| **Status** | canonical |
| **Cap** | 3 prompts per burst |

---

### Precedence Rule

| | |
|---|---|
| **Definition** | Ordering used when policy settings conflict. |
| **Context** | Governance |
| **Status** | canonical |
| **Operational order (strictness)** | CLI override > step metadata > mission config > global default |

---

### Constitution Interview

| | |
|---|---|
| **Definition** | A guided question-and-answer process that walks the HiC through their project's preferences, constraints, and doctrine selections. Answers are saved to `answers.yaml` and used to compile the constitution. |
| **Context** | Governance |
| **Status** | candidate |
| **Related terms** | [Constitution](#constitution), [Constitution Compiler](#constitution-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### Constitution Compiler

| | |
|---|---|
| **Definition** | The processor that takes the HiC's interview answers and their selected doctrine artifacts, and combines them into a finalized constitution document and supporting governance files. |
| **Context** | Governance |
| **Status** | candidate |
| **Related terms** | [Constitution](#constitution), [Constitution Interview](#constitution-interview), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |

---

### Governance Resolution

| | |
|---|---|
| **Definition** | The result of checking the HiC's constitution selections against available doctrine catalogs — confirming that the referenced paradigms, directives, and tools actually exist and are compatible with each other. |
| **Context** | Governance |
| **Status** | candidate |
| **Related terms** | [Constitution Compiler](#constitution-compiler), [Doctrine Catalog](./doctrine.md#doctrine-catalog) |
