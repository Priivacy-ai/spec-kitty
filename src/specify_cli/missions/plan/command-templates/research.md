---
step_id: "research"
mission: "plan"
title: "Research"
description: "Gather research inputs and technical context"
estimated_duration: "20-30 minutes"
---

# Research Phase

## Context

You are in the research phase of planning. Your role is to investigate the technical requirements, patterns, dependencies, and risks identified in the specification from step 1.

**Input**: spec.md from the Specify phase (step 1)

**Output**: A comprehensive research document (`research.md`) with technical analysis and recommendations

**What You're Doing**: Researching:
- Technical requirements and constraints
- Existing design patterns and approaches
- External dependencies and integrations
- Potential risks and mitigation strategies
- Alternative approaches and trade-offs
- Industry best practices and examples

## Deliverables

- `research.md` document with:
  - Technical Analysis (requirements breakdown)
  - Design Patterns (existing patterns that apply)
  - Dependencies (libraries, services, systems needed)
  - Risk Analysis (potential issues and mitigations)
  - Alternative Approaches (options considered)
  - Recommendations (recommended path forward)
  - References (sources and documentation)

## Instructions

1. **Conduct technical analysis**
   - What are the core technical requirements?
   - What constraints exist (performance, security, scalability)?
   - What technologies are relevant?
   - What does the current landscape offer?

2. **Research design patterns**
   - What existing patterns apply to this feature?
   - What architectural patterns are relevant?
   - Are there established best practices?
   - What do similar systems do?

3. **Identify dependencies**
   - What external libraries/frameworks are needed?
   - What services or integrations are required?
   - What internal systems does this depend on?
   - Are there licensing or compatibility concerns?

4. **Analyze risks**
   - What could go wrong technically?
   - What are the known failure modes?
   - How can we mitigate these risks?
   - What are the worst-case scenarios?

5. **Explore alternatives**
   - Are there different technical approaches?
   - What are the trade-offs between approaches?
   - Which approach has the best risk/benefit ratio?
   - When would each approach be appropriate?

6. **Make recommendations**
   - Based on research, what approach do you recommend?
   - Why is this the best choice?
   - What are the assumptions behind this recommendation?
   - What validation is needed?

## Success Criteria

- [ ] research.md file created with all required sections
- [ ] Technical analysis is thorough and specific (not generic)
- [ ] Design patterns section identifies applicable patterns
- [ ] Dependencies are clearly listed and evaluated
- [ ] Risk analysis is concrete (specific risks, not vague)
- [ ] Mitigations are practical and actionable
- [ ] Alternatives are fairly evaluated
- [ ] Recommendations are justified and supported by research
- [ ] References point to actual sources and documentation
- [ ] Document is ready for design phase (step 3)
