## Context: Practices and Principles

Terms describing operating principles for glossary-semantic-integrity execution.

### Mostly Invisible Process

| | |
|---|---|
| **Definition** | Glossary checks should run by default with minimal interruption during normal flow. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Highly Visible Outcomes

| | |
|---|---|
| **Definition** | Conflict results, block reasons, and clarification decisions must be visible in artifacts/logs. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Append-Only Semantic History

| | |
|---|---|
| **Definition** | Term/sense changes and conflict decisions are recorded as immutable events, not rewritten in place. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Deterministic Gate, Human Clarification

| | |
|---|---|
| **Definition** | Conflict detection/gating is deterministic; only ambiguity resolution requires human input. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### High-Severity Block Rule

| | |
|---|---|
| **Definition** | Generation is blocked only when high-severity semantic conflicts remain unresolved. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Boy Scout Rule

| | |
|---|---|
| **Definition** | Leave the code better than you found it. When passing through an area of the codebase, opportunistically improve clarity, naming, or structure — even if unrelated to the current task. Improvements are committed as their own targeted commit, separate from the WP deliverable. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **See also** | DIRECTIVE_025 (Boy Scout Rule), DIRECTIVE_033 (Targeted Staging Policy) |

---

### Human-in-Charge (Cross-Reference)

| | |
|---|---|
| **Definition** | The principle that the human remains responsible and accountable for all decisions. Agents assist and propose; the HiC owns the final call. See full definition in Identity context. |
| **Context** | Practices & Principles |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Canonical entry** | [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |
