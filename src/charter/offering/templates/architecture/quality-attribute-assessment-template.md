# Quality Attribute Assessment: {{ initiative }}

> **Purpose:** Document the system characteristics relevant to this architectural decision, assess their impact on the proposed design, and record accepted trade-offs. This document supports ADR authoring and design reviews.

| Field           | Value                              |
|-----------------|------------------------------------|
| Initiative      | {{ initiative }}                   |
| Owner           | {{ owner }}                        |
| Date            | {{ date }}                         |
| Status          | Draft / Reviewed / Accepted        |
| Related ADR(s)  | _link or N/A_                      |
| Related Spec(s) | _link or N/A_                      |

---

## Scope

> Briefly describe the architectural decision or component change this assessment covers. What is in scope, and what is explicitly out of scope?

**In scope:**

**Out of scope:**

---

## Relevant Quality Attributes

> List the quality attributes that are materially relevant to this decision. Remove rows that do not apply; add rows for domain-specific attributes as needed. Use the key success factors to make each attribute measurable.

| Attribute        | Description                                                          | Impact on This Design      |
|------------------|----------------------------------------------------------------------|----------------------------|
| Scalability      | Handles growth in load, data volume, and concurrent users.           | promotes / degrades / neutral |
| Maintainability  | System can be understood, changed, and debugged with reasonable effort. | promotes / degrades / neutral |
| Security         | Data and resources are protected from unauthorised access.           | promotes / degrades / neutral |
| Reliability      | System performs required functions under stated conditions over time. | promotes / degrades / neutral |
| Performance      | Latency and throughput meet user and system expectations.            | promotes / degrades / neutral |
| Extensibility    | New behaviour can be added without altering the core architecture.   | promotes / degrades / neutral |
| Feasibility      | Design is achievable within the given budget, timeline, and team.    | promotes / degrades / neutral |
| Interoperability | System integrates with adjacent systems without special user effort.  | promotes / degrades / neutral |

---

## Attribute Detail

> For each relevant attribute, expand on the rationale and define measurable success factors.
> Remove sections that are not in scope.

### Scalability

**Rationale:**
> Why does scalability matter for this decision?

**Key success factors:**
- _Measurable outcome 1_
- _Measurable outcome 2_

---

### Maintainability

**Rationale:**
> Why does maintainability matter here?

**Key success factors:**
- _Measurable outcome 1_
- _Measurable outcome 2_

---

<!-- Repeat the above pattern for each relevant attribute -->

---

## Trade-Off Summary

> Every architectural decision sacrifices at least one quality attribute to gain another. Document each accepted trade-off explicitly, together with the reasoning. An assessment with no trade-offs is incomplete.

| Trade-off                              | What is sacrificed          | What is gained              | Reasoning                             |
|----------------------------------------|-----------------------------|-----------------------------|---------------------------------------|
| _e.g. Synchronous integration_         | Availability (tight coupling) | Simplicity / lower latency | Acceptable for low-volume internal API |
| _(add rows as needed)_                 |                             |                             |                                       |

---

## Constraints

> List the project constraints (budget, timeline, team size, regulatory requirements) that influenced the attribute priorities above.

- **Budget:** _describe_
- **Timeline:** _describe_
- **Team size / skills:** _describe_
- **Regulatory / compliance:** _describe or N/A_

---

## Open Questions

> Attribute assessments that cannot yet be resolved. Assign an owner and a deadline.

| Question | Owner | Deadline |
|----------|-------|----------|
|          |       |          |

---

## References

- ADR: _link_
- Related design decisions: _link_
- Applicable standards: _link or N/A_
