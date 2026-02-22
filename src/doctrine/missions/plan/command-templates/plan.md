---
step_id: "plan"
mission: "plan"
title: "Plan"
description: "Design and create planning artifacts"
estimated_duration: "25-40 minutes"
---

# Design & Planning

## Context

You are creating the technical design artifacts that will guide the implementation phase. Building on the feature specification and research findings, you now design the solution architecture, data models, APIs, and implementation approach.

**Input**: Feature specification and research findings from previous steps

**Output**: Design artifacts including architecture diagrams, data models, API contracts, and implementation sketches

**What You're Doing**:
- Designing the system architecture and component interactions
- Creating data models and entity relationships
- Defining API contracts and interfaces
- Sketching the implementation approach
- Documenting design decisions and assumptions

## Deliverables

The design planning should produce:
- **Architecture Design** (system design, component interactions, deployment model)
- **Data Model** (entities, fields, relationships, validation rules)
- **API Contracts** (REST/GraphQL endpoints, request/response formats, error handling)
- **Implementation Sketch** (high-level implementation steps, phase sequencing)
- **Design Patterns Applied** (which patterns are used and why)
- **Technical Decisions** (key design choices and their rationale)
- **Design Assumptions** (assumptions made during design)
- **Integration Design** (how this integrates with existing systems)
- **Validation Rules** (business logic and data validation requirements)

## Instructions

1. **Design system architecture**
   - How should this feature be architected?
   - What components are needed?
   - How do components interact?
   - What is the deployment model?
   - What are the boundaries of responsibility?

2. **Create data model**
   - What entities does this feature require?
   - What are the key properties of each entity?
   - What are the relationships between entities?
   - What validation rules apply?
   - What is the state model (if applicable)?

3. **Define API contracts**
   - What endpoints or interfaces are needed?
   - For each user action or requirement, what API is needed?
   - What are the request parameters?
   - What are the response formats?
   - What error cases must be handled?
   - Use standard REST or GraphQL patterns

4. **Sketch implementation approach**
   - What are the major implementation phases?
   - In what order should components be built?
   - What are the dependencies between components?
   - What are the testing requirements?
   - What are the rollout/deployment considerations?

5. **Document design patterns**
   - Which design patterns are used and why?
   - How do they apply to this feature?
   - What benefits do they provide?
   - Any anti-patterns to avoid?

6. **Record technical decisions**
   - What major technical choices were made?
   - What was the rationale for each?
   - What alternatives were considered?
   - Why were alternatives rejected?

7. **Document assumptions**
   - What assumptions are embedded in the design?
   - What if these assumptions prove false?
   - What would need to change?

## Success Criteria

- [ ] Architecture design is clear and documented
- [ ] Data model captures all required entities and relationships
- [ ] API contracts are complete with request/response examples
- [ ] Implementation sketch provides clear phasing and sequencing
- [ ] All design patterns are identified and explained
- [ ] Technical decisions are documented with rationale
- [ ] Integration points are clearly defined
- [ ] Validation rules are explicit and testable
- [ ] Design is ready to be handed off to implementation teams

## References

- Design format: Use diagrams (ASCII or markdown) for architecture clarity
- Data model: Document entity relationships and validation rules
- API contracts: Provide realistic examples of requests and responses
- Related: Implementation teams will use these artifacts to build the feature

