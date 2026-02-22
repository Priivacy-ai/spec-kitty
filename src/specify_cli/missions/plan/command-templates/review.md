---
step_id: "review"
mission: "plan"
title: "Review"
description: "Review and validate planning artifacts"
estimated_duration: "15-20 minutes"
---

# Review & Validation

## Context

You are conducting the final review of the planning artifacts to ensure completeness, consistency, and feasibility. This is the terminal step of the planning mission - your validation determines whether the plan is ready for implementation or needs revision.

**Input**: All planning artifacts from previous steps (specification, research, and design)

**Output**: Validation report with approval status and any required changes

**What You're Doing**:
- Validating completeness and consistency of planning artifacts
- Checking alignment between specification, research, and design
- Ensuring feasibility and implementability of the design
- Identifying any gaps or conflicts
- Approving or requesting changes

## Deliverables

The review process should produce:
- **Validation Checklist** (completeness verification)
- **Consistency Analysis** (do specification, research, and design align?)
- **Feasibility Assessment** (is the design implementable with current resources?)
- **Issues Found** (any inconsistencies, gaps, or red flags)
- **Recommendations** (changes needed, if any)
- **Approval Status** (approved, needs changes, or blocked)
- **Confidence Assessment** (confidence in the plan as documented)

## Instructions

1. **Verify specification completeness**
   - Are all required sections present?
   - Are goals and success criteria clear?
   - Is the scope well-defined?
   - Are assumptions and constraints documented?
   - Are there any ambiguities or open questions?

2. **Verify research completeness**
   - Are technical requirements addressed?
   - Are design patterns identified?
   - Are risks and mitigations documented?
   - Are recommendations clear?
   - Are dependency analysis complete?

3. **Verify design completeness**
   - Is the architecture clearly described?
   - Is the data model complete?
   - Are API contracts defined?
   - Is the implementation sketch detailed enough?
   - Are design assumptions documented?

4. **Check consistency across phases**
   - Does the design address all requirements in the specification?
   - Does the design incorporate research findings?
   - Are there any conflicts between specification and design?
   - Are dependencies from research properly handled in design?
   - Is anything in the design not grounded in specification or research?

5. **Assess feasibility**
   - Is the proposed design implementable with reasonable effort?
   - Are the required technologies available and appropriate?
   - Are the identified dependencies realistic and manageable?
   - Are timeline and resource estimates reasonable?
   - Are there any showstoppers or major red flags?

6. **Identify gaps or issues**
   - Are there missing sections or incomplete artifacts?
   - Are there conflicting requirements or design choices?
   - Are there unresolved risks?
   - Are assumptions reasonable?
   - Are there unclear or ambiguous sections?

7. **Render approval decision**
   - **Approved**: Plan is complete, consistent, feasible, and ready for implementation
   - **Needs Changes**: Specific issues must be addressed (document what and why)
   - **Blocked**: Fundamental issues prevent approval (document blockers and required changes)

## Success Criteria

- [ ] All specification sections reviewed and validated
- [ ] All research sections reviewed and validated
- [ ] All design artifacts reviewed and validated
- [ ] Consistency between phases verified
- [ ] Feasibility assessment completed
- [ ] Any issues clearly identified and documented
- [ ] Recommendations provided (if changes needed)
- [ ] Approval status clearly determined
- [ ] Plan is ready for next phase (implementation or revision)

## References

- Validation format: Use checklists and clear categories
- Cross-reference: Trace requirements through specification → research → design
- Related: After approval, this plan feeds into implementation work packages

