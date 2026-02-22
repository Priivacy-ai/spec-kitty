---
step_id: "specify"
mission: "plan"
title: "Specify"
description: "Create and document the feature specification"
estimated_duration: "15-20 minutes"
---

# Specify Feature

## Context

You are beginning the planning phase for a new software feature. Your role is to create a clear, detailed specification that will guide the research and design phases.

**Input**: Feature description or user request from the specification step

**Output**: A comprehensive specification document that will be the foundation for the remaining planning steps (research → plan → review)

**What You're Doing**: Analyzing the user's feature request, asking clarifying questions if needed, and documenting:
- Feature goals and objectives
- User scenarios and use cases
- Functional and non-functional requirements
- Acceptance criteria and success metrics
- Constraints and assumptions
- Scope boundaries

## Deliverables

The planning specification should include:
- **Executive Summary** (1-2 paragraphs describing the feature at high level)
- **Problem Statement** (what problem does this feature solve?)
- **Functional Requirements** (list of what the feature must do)
- **Non-Functional Requirements** (performance, security, scalability expectations)
- **User Scenarios** (3-5 key user flows and interactions)
- **Success Criteria** (measurable outcomes that define "done")
- **Assumptions and Constraints** (what are we assuming? what are the limits?)
- **Scope Boundaries** (what's explicitly in scope and out of scope)

## Instructions

1. **Analyze the feature request**
   - What is the core feature being requested?
   - Who are the primary users?
   - What problem does it solve?
   - What value does it deliver?

2. **Define feature goals**
   - List 3-5 primary goals for this feature
   - Ensure each goal is specific and measurable
   - Prioritize goals by importance

3. **Create user scenarios**
   - Develop 3-5 key user scenarios
   - Include the happy path for each scenario
   - Include at least one edge case or error scenario
   - Each scenario should be testable and realistic

4. **Document requirements**
   - Translate goals and scenarios into specific, testable requirements
   - Separate functional requirements (what it does) from non-functional (performance, security, etc.)
   - Make requirements specific and measurable (avoid vague terms like "fast" or "user-friendly")
   - Cross-reference each requirement to a user scenario

5. **Define success criteria**
   - What does it mean for this feature to be "done"?
   - How will you validate the feature works as intended?
   - Include both user-facing criteria and technical criteria
   - Make criteria objective and testable

6. **Identify constraints and assumptions**
   - What technical limitations or dependencies exist?
   - What are we assuming about the environment, users, or systems?
   - What constraints (budget, timeline, resources) affect this feature?
   - What is explicitly out of scope?

7. **Validate for clarity**
   - Review each section for clarity and completeness
   - Remove or clarify any ambiguous language
   - Ensure there are no conflicting requirements
   - Document any assumptions or open questions

## Success Criteria

- [ ] Specification document created with all required sections
- [ ] Feature goals are clear, specific, and measurable
- [ ] User scenarios are concrete and testable (not generic)
- [ ] Requirements are testable (avoid subjective terms)
- [ ] Success criteria are objective and technology-agnostic
- [ ] Scope boundaries are clearly stated (in scope and out of scope)
- [ ] No open questions or clarifications needed (or justified as intentional)
- [ ] Specification is well-organized and readable

## References

- Specification format: Use clear section headings and structured bullet points
- Example: See documentation for specification best practices
- Related: This specification feeds into the research phase

