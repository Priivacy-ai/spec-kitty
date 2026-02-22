---
step_id: "plan"
mission: "plan"
title: "Plan"
description: "Design and create planning artifacts"
estimated_duration: "25-35 minutes"
---

# Plan Phase

## Context

You are in the design and planning phase. Your role is to take the research findings and create detailed design artifacts that define how the feature will be built.

**Input**: research.md from the Research phase (step 2) and spec.md from step 1

**Output**: Complete design artifacts including architecture, data models, API contracts, and implementation sketch

**What You're Doing**: Creating:
- System architecture and component design
- Data models and schema definitions
- API contracts and interfaces
- Implementation approach and technical decisions
- Assumptions and design rationale

## Deliverables

- Design artifact documents:
  - `architecture.md` - System design and component interactions
  - `data-model.md` - Entity definitions, relationships, schemas
  - `api-contracts.md` - REST/GraphQL endpoints, request/response shapes
  - `implementation-sketch.md` - High-level implementation steps and approach
  - `design-decisions.md` - Key design choices and rationale

Alternative formats acceptable:
- Single `design.md` combining all sections
- Multiple topic-specific files in `design/` directory
- Any format that captures: architecture, data model, contracts, implementation sketch

## Instructions

1. **Design system architecture**
   - What are the main components/modules?
   - How do they interact?
   - What's the overall system structure?
   - Where does this feature fit in the larger system?
   - Draw diagrams if helpful (can be ASCII art)

2. **Define data models**
   - What entities/objects are involved?
   - What are the key attributes of each?
   - What relationships exist between entities?
   - What constraints apply (uniqueness, dependencies)?
   - Include schema definitions or examples

3. **Document API contracts**
   - What endpoints or interfaces are exposed?
   - Request/response structure for each
   - Status codes and error handling
   - Authentication and authorization
   - Rate limiting or other constraints
   - Use examples or OpenAPI/GraphQL specs

4. **Create implementation sketch**
   - What are the high-level implementation steps?
   - Which components are built first?
   - What's the critical path?
   - What can be deferred or made optional?
   - What dependencies exist between components?
   - Estimate effort for major components

5. **Document assumptions**
   - What assumptions guide this design?
   - What external constraints are we working with?
   - What future changes might break this design?
   - What would need to change if requirements evolved?

6. **Validate against specification**
   - Does the design satisfy all requirements from spec.md?
   - Does it address all success criteria?
   - Are all user scenarios supported?
   - Have all constraints been addressed?

## Success Criteria

- [ ] Design artifacts created with clear structure
- [ ] System architecture is well-documented
- [ ] Data models are specific and implementable (not vague)
- [ ] API contracts are detailed and testable
- [ ] Implementation sketch is actionable
- [ ] All design decisions are justified
- [ ] Architecture diagrams are included (text or visual)
- [ ] Design satisfies all requirements from spec.md
- [ ] Design addresses all risks identified in research.md
- [ ] Assumptions are explicitly documented
- [ ] No major gaps or inconsistencies
- [ ] Ready for review phase (step 4)
