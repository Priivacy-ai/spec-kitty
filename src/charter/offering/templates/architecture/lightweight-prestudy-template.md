# Prestudy: {{ initiative }}

> **Purpose:** A structured pre-design document that captures context, constraints, candidate approaches, accepted trade-offs,
> and a recommended path forward — before implementation begins.
> Use this template for decisions of moderate-to-high risk where a full architecture design document is not yet warranted
> but informal discussion is insufficient. Expand into a full design document if complexity demands it.

| Field              | Value                                            |
|--------------------|--------------------------------------------------|
| Initiative         | {{ initiative }}                                 |
| Owner              | {{ owner }}                                      |
| Date               | {{ date }}                                       |
| Status             | Draft / Under Review / Approved / Superseded     |
| Approval authority | _name or role_                                   |
| Related ADR(s)     | _link or N/A_                                    |
| Related context canvas | _link or N/A_                              |

---

## 1. Context and Problem

> Summarise the situation. Reference the System Context Canvas for full detail; do not duplicate it here.

**Problem statement:**

**Current state and friction:**

**Why now:**

---

## 2. Scope

**In scope:**

**Out of scope:**

**Assumptions that constrain this prestudy:**

---

## 3. Design Constraints

> Hard limits the solution must respect. Distinguish constraints (cannot be negotiated) from preferences (could be relaxed with justification).

| Constraint | Type (hard / soft) | Source |
|------------|--------------------|--------|
|            |                    |        |
|            |                    |        |

---

## 4. Problem Decomposition

> Break the problem into tractable sub-problems. Assign a priority (must solve / should solve / nice to have).
> This section feeds directly into solution comparison and work-package planning.

| Sub-problem | Priority | Notes |
|-------------|----------|-------|
|             |          |       |
|             |          |       |

---

## 5. Approaches Considered

> Document the realistic candidate approaches. Aim for two to four alternatives; fewer signals insufficient exploration,
> more signals unclear scope. For each, state what it is, why it was considered, and why it was accepted or rejected.

### Approach A — {{ name }}

**Description:**

**Strengths:**

**Weaknesses / risks:**

**Decision:** Accepted / Rejected — _reason_

---

### Approach B — {{ name }}

**Description:**

**Strengths:**

**Weaknesses / risks:**

**Decision:** Accepted / Rejected — _reason_

---

### Approach C — {{ name }} _(add or remove blocks as needed)_

**Description:**

**Strengths:**

**Weaknesses / risks:**

**Decision:** Accepted / Rejected — _reason_

---

## 6. Recommended Approach

> State the chosen approach and the primary rationale. Cross-reference the trade-off assessment.

**Chosen approach:**

**Rationale:**

**Key trade-offs accepted:**

| Trade-off | What is sacrificed | What is gained |
|-----------|-------------------|----------------|
|           |                   |                |

**Conditions for this recommendation to hold:**
> If any of these conditions change, the recommendation must be revisited.

---

## 7. Risk Summary

> Identify the top risks. For each, state likelihood, impact, and the mitigation strategy.
> Run a full premortem (see premortem-risk-identification tactic) for high-stakes decisions.

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
|      |            |        |            |
|      |            |        |            |

---

## 8. Feasibility Assessment

> Is the recommended approach achievable given current constraints?

**Estimated effort range:**

**Key dependencies:**

**Skill / team gaps:**

**Go / No-go recommendation:** Go / No-go / Needs further investigation — _reason_

---

## 9. Next Steps

> Concrete, time-bound actions that follow from this prestudy.

| Action | Owner | Due |
|--------|-------|-----|
|        |       |     |

---

## References

- System Context Canvas: _link_
- Quality Attribute Assessment: _link_
- Risk Identification Assessment: _link_
- Related ADRs: _link_
