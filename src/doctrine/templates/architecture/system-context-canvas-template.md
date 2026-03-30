# System Context Canvas: {{ initiative }}

> **Purpose:** Capture the operational and organisational context in which a solution must operate *before* design begins.
> This canvas is the mandatory input to any trade-off assessment, prestudy, or architectural decision.
> It documents not just what the system does but the forces, constraints, and uncertainties that shape what the system *can* do.

| Field           | Value                                    |
|-----------------|------------------------------------------|
| Initiative      | {{ initiative }}                         |
| Owner           | {{ owner }}                              |
| Date            | {{ date }}                               |
| Status          | Draft / Reviewed / Accepted              |
| Related prestudy | _link or N/A_                           |
| Related ADR(s)  | _link or N/A_                            |

---

## 1. Problem Statement

> In one or two sentences: what is the core problem or opportunity this initiative addresses?
> Avoid proposing solutions here — describe the *gap* between current reality and desired state.

**Current reality:**

**Desired state:**

**Why this matters now:**

---

## 2. Organisational Context

> Describe the team, product, and business environment surrounding this initiative.

**Team / ownership:**
> Who will own, build, and maintain the solution? What are the relevant team boundaries?

**Product / domain context:**
> Where does this initiative sit in the product or system landscape? What broader system does it belong to?

**Cultural forces:**
> Are there organisational norms, historical decisions, or team dynamics that will shape how solutions are received?

---

## 3. Stakeholders

> Who has a stake in this initiative? For each group, note their primary concern and what success looks like for them.
> Use the Stakeholder Persona template for detailed profiles.

| Stakeholder group | Primary concern | Success looks like |
|-------------------|-----------------|--------------------|
|                   |                 |                    |
|                   |                 |                    |
|                   |                 |                    |

**Stakeholder tensions:**
> Are any groups' interests in direct conflict? Name the tension explicitly.

---

## 4. Current System State

> Describe what exists today — what is working, what is broken, and where the friction is greatest.

**What exists:**

**Key frictions / pain points:**

**Known technical debt relevant to this initiative:**

---

## 5. System Boundaries

> Define what is in scope (will be designed or changed) and what is explicitly out of scope.
> Identify the integration points with adjacent systems.

**In scope:**

**Out of scope:**

**External integration points:**

| Adjacent system | Relationship | Interface type | Notes |
|-----------------|--------------|----------------|-------|
|                 |              |                |       |

---

## 6. External Forces

> What external pressures — market, regulatory, technology, or organisational — are shaping this initiative?

**Market / competitive forces:**

**Regulatory / compliance requirements:**

**Technology shifts:**

**Organisational mandates or strategy:**

---

## 7. Constraints

> Hard limits that the solution must respect regardless of design preference.

| Constraint type | Description | Source |
|-----------------|-------------|--------|
| Budget          |             |        |
| Timeline        |             |        |
| Team / skills   |             |        |
| Technology      |             |        |
| Regulatory      |             |        |
| Other           |             |        |

---

## 8. Key Uncertainties and Assumptions

> What do we not know yet? What are we assuming to be true that could turn out to be false?
> High-risk assumptions should trigger a safe-to-fail experiment or premortem before design is finalised.

| Assumption / Uncertainty | Risk if wrong | Owner | Validation approach |
|--------------------------|---------------|-------|---------------------|
|                          |               |       |                     |
|                          |               |       |                     |

---

## 9. Definition of Done for This Canvas

> This canvas is considered complete when:
> - [ ] All eight sections have been filled or explicitly marked N/A with a reason.
> - [ ] At least one stakeholder group has reviewed and confirmed their section.
> - [ ] Key uncertainties have been assigned owners and validation approaches.
> - [ ] The canvas has been linked from the associated prestudy or ADR.

---

## References

- Prestudy: _link_
- Stakeholder persona(s): _link_
- Related ADRs: _link_
