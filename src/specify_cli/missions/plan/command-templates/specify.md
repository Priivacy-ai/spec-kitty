---
step_id: "specify"
mission: "plan"
title: "Specify"
description: "Create and document the feature specification"
estimated_duration: "15-20 minutes"
---

# Specify Feature

## Context

You are beginning the planning phase for a new feature or initiative. Your role is to create a clear, detailed specification that will guide the research and design phases.

**Input**: Feature description or user request from the specification step

**Output**: A comprehensive specification document (`spec.md`) that will be the foundation for the remaining planning steps

**What You're Doing**: Analyzing the feature request, asking clarifying questions (if needed), and documenting:
- Feature goals and objectives
- User scenarios and use cases
- Functional and non-functional requirements
- Acceptance criteria and success metrics
- Constraints and assumptions

## Deliverables

- `spec.md` document with:
  - Executive Summary (1-2 paragraphs)
  - Problem Statement (what problem does this solve?)
  - Functional Requirements (list of requirements)
  - Success Criteria (measurable outcomes)
  - User Scenarios (3-5 key user flows)
  - Assumptions and Constraints
  - Scope boundaries (in/out of scope)

## Instructions

1. **Analyze the feature request**
   - What is the core feature being requested?
   - Who are the primary users?
   - What problem does it solve?

2. **Define feature goals**
   - List 3-5 primary goals
   - Ensure each goal is measurable
   - Consider both user goals and business goals

3. **Create user scenarios**
   - Develop 3-5 key user scenarios
   - Include happy path and at least one edge case
   - Each scenario should be testable
   - Format: "As a [user type], I want to [action], so that [benefit]"

4. **Document requirements**
   - Translate goals and scenarios into testable requirements
   - Separate functional (what it does) from non-functional (performance, security, etc.)
   - Make requirements specific and measurable
   - Avoid vague terms like "fast", "easy", or "intuitive"

5. **Define success criteria**
   - What does done look like?
   - How will we validate the feature works?
   - Include both user-facing and technical criteria
   - Each criterion should be objectively verifiable

6. **Identify constraints and assumptions**
   - What technical limitations exist?
   - What are we assuming about the environment, users, etc.?
   - What's explicitly out of scope?
   - Document any dependencies on other systems

## Success Criteria

- [ ] spec.md file created with all required sections
- [ ] Feature goals are clear and measurable
- [ ] User scenarios are specific and testable (not generic)
- [ ] Requirements are testable (not vague like "fast" or "easy")
- [ ] Success criteria are technology-agnostic
- [ ] Scope boundaries are clearly stated (what's in and out of scope)
- [ ] No [NEEDS CLARIFICATION] markers remain (or justified and documented)
- [ ] Document is well-organized and readable
- [ ] Ready for research phase (step 2)
