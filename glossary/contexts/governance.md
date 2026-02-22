## Context: Governance

Terms describing rule ownership, precedence, and policy controls in Spec Kitty.

### Constitution

| | |
|---|---|
| **Definition** | Project-level policy document that captures operating constraints and quality rules for a repository. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `.kittify/memory/constitution.md` |

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
