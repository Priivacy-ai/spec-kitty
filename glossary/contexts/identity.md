## Context: Identity

Terms describing who performs work and who owns semantic decisions.

### Agent

| | |
|---|---|
| **Definition** | Logical collaborator identity used in workflow coordination (for example implementer, reviewer). |
| **Context** | Identity |
| **Status** | canonical |
| **Related terms** | [Tool](./execution.md#tool), [Role](#role) |

---

### Role

| | |
|---|---|
| **Definition** | Responsibility assignment for a step or work package (implementer, reviewer, planner, etc.). |
| **Context** | Identity |
| **Status** | canonical |

---

### Mission Participant

| | |
|---|---|
| **Definition** | Human or tool-backed collaborator participating in a mission run. |
| **Context** | Identity |
| **Status** | canonical |

---

### Mission Owner

| | |
|---|---|
| **Definition** | Participant responsible for tie-breaking unresolved semantic conflicts when collaborators disagree. |
| **Context** | Identity |
| **Status** | canonical |
| **Rule** | Tie-break only after normal participant resolution fails |

---

### Human-in-Charge (HiC)

| | |
|---|---|
| **Definition** | The human who remains responsible and accountable for decisions made during a mission. Agents assist and propose, but the HiC owns the final call. This principle ensures that automation supports human judgement rather than replacing it. |
| **Context** | Identity |
| **Status** | candidate |
| **Related terms** | [Mission Owner](#mission-owner), [Collaboration Mode](./execution.md#collaboration-mode), [HiC cross-reference](./practices-principles.md#human-in-charge-cross-reference) |

