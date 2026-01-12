---
work_package_id: "WP05"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Constitution Command Redesign"
phase: "Feature - Track 2 UX Improvements"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Constitution Command Redesign

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Replace placeholder-filling approach with phase-based interactive discovery workflow for constitution creation.

**Success Criteria**:
1. Constitution command template updated at `src/specify_cli/templates/command-templates/constitution.md`
2. Four discovery phases implemented: Technical Standards, Code Quality, Tribal Knowledge, Governance
3. Each phase has skip option with clear guidance on when to skip
4. Minimal path (skip most phases, answer 3-5 questions) produces ~1 page constitution
5. Comprehensive path (complete all phases, answer 8-12 questions) produces ~2-3 page constitution
6. Summary presentation before writing (user confirmation required)
7. Plan command gracefully skips Constitution Check if no constitution exists
8. All spec-kitty commands work without constitution (tested in WP06)

**Acceptance Test**:
```bash
# Test 1: Minimal path
cd /tmp/test-project
git init
spec-kitty init

# Run constitution command, choose minimal
# Should ask ~4 questions total (just Phase 1: Technical Standards)
# Output should be ~1 page

cat .kittify/memory/constitution.md | wc -l
# Expected: ~50-80 lines

# Test 2: Comprehensive path
cd /tmp/test-project2
git init
spec-kitty init

# Run constitution command, choose comprehensive
# Should ask ~10 questions total (all 4 phases)
# Output should be ~2-3 pages

cat .kittify/memory/constitution.md | wc -l
# Expected: ~150-200 lines

# Test 3: No constitution (graceful handling)
cd /tmp/test-project3
git init
spec-kitty init
# Don't run /spec-kitty.constitution

# Run plan command
spec-kitty agent feature setup-plan --json
# Should succeed without constitution
```

---

## Context & Constraints

**Why This Matters**: Current constitution command uses placeholder-filling approach that's confusing and requires users to understand template structure. Many users skip constitutions entirely because the process is unclear. The new phase-based discovery makes constitution creation approachable and optional.

**Current Problems**:
1. **Placeholder-filling is confusing**: Users see `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`, don't know what to fill in
2. **All-or-nothing**: Either fill entire template or nothing
3. **Not optional**: Commands may error if constitution incomplete
4. **No guidance**: Users don't know which principles to include
5. **Template-centric**: Focuses on template structure, not user needs

**New Approach**:
1. **Phase-based discovery**: Ask questions one at a time, grouped by theme
2. **Skip options**: Each phase can be skipped with guidance on when/why
3. **Truly optional**: Commands work without constitution
4. **Question-driven**: Focus on gathering information, not filling templates
5. **User-centric**: Adapts to user needs (minimal vs comprehensive)

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (FR-007 through FR-016, User Story 2)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Constitution Redesign section)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (Research Area 4: Constitution Command Redesign)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Entity 3: Constitution Structure, Discovery Phases)

**Dependencies**:
- **WP01 must complete**: Template must be in `src/specify_cli/templates/command-templates/` before updating
- This WP updates the constitution.md command template
- WP06 will test that all commands work without constitution

**Design Principles**:
1. **One question at a time**: Like `/spec-kitty.specify` and `/spec-kitty.plan`
2. **Clear skip guidance**: Tell users when they should skip a phase
3. **Progressive disclosure**: Start simple (minimal), offer more depth (comprehensive)
4. **Summary before commit**: Show what will be written, get confirmation
5. **Lean by default**: Encourage concise constitutions (1 page > 10 pages)

---

## Subtasks & Detailed Guidance

### Subtask T028 – Update constitution.md template with phase-based workflow

**Purpose**: Replace entire constitution command template with new phase-based discovery workflow.

**File**: `src/specify_cli/templates/command-templates/constitution.md`

**Current Template** (lines 1-127):
```markdown
---
description: Create or update the project constitution from interactive or provided principle inputs...
---
...
## Outline

You are updating the project constitution at `/memory/constitution.md`. This file is a TEMPLATE containing placeholder tokens in square brackets (e.g. `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`). Your job is to (a) collect/derive concrete values, (b) fill the template precisely, and (c) propagate any amendments across dependent artifacts.
...
```

**Problem**: Current approach is template-centric (fill placeholders), not user-centric (gather information).

**New Template Structure**:
```markdown
---
description: Create or update the project constitution through interactive phase-based discovery.
---

# Constitution Command: Interactive Discovery Workflow

**Location**: `.kittify/memory/constitution.md` (project root, not worktree)
**Scope**: Project-wide principles applying to ALL features

**Note**: Constitution is OPTIONAL. All spec-kitty commands work without a constitution. This command helps teams capture shared principles when valuable.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

---

## What This Command Does

This command creates or updates your project's constitution through an interactive discovery process. Unlike template-filling, this workflow asks targeted questions to understand your project's needs and generates a lean, focused constitution.

**Constitution Purpose**:
- Capture technical standards (languages, testing, deployment)
- Document code quality expectations (PR process, review criteria)
- Record tribal knowledge (team conventions, lessons learned)
- Define governance (how constitution changes, who validates compliance)

**When to Use**:
- **First time**: Establishing initial project principles
- **Updates**: Adding new principles or revising existing ones
- **Never**: If your team doesn't need formal documentation of principles

---

## Discovery Workflow

This command uses a **4-phase discovery process**:

1. **Phase 1: Technical Standards** (Recommended for most projects)
   - Languages, frameworks, testing requirements
   - Performance targets, deployment constraints
   - ~3-4 questions, produces core technical foundation

2. **Phase 2: Code Quality** (Optional for established teams)
   - PR requirements, review process, quality gates
   - Documentation standards
   - ~3-4 questions, adds quality expectations

3. **Phase 3: Tribal Knowledge** (Optional for experienced teams)
   - Team conventions, lessons learned
   - Historical decisions, domain knowledge
   - ~2-4 questions, captures institutional memory

4. **Phase 4: Governance** (Optional, use simple defaults)
   - Amendment process, compliance validation
   - Exception handling
   - ~2-3 questions, defines constitution management

**Paths**:
- **Minimal** (1 page): Complete Phase 1 only, skip rest → ~3-5 questions
- **Comprehensive** (2-3 pages): Complete all 4 phases → ~8-12 questions

---

## Execution Outline

### Step 1: Initial Choice

**Ask user**:
```
Do you want to establish a project constitution?

A) No, skip it - I don't need a formal constitution
B) Yes, minimal - Just core technical standards (~1 page, 3-5 questions)
C) Yes, comprehensive - Full governance and tribal knowledge (~2-3 pages, 8-12 questions)
```

**Handle responses**:
- **A (Skip)**: Create minimal placeholder at `.kittify/memory/constitution.md` with message: "Constitution skipped - not required for spec-kitty usage. Run /spec-kitty.constitution anytime to create one." → Exit successfully
- **B (Minimal)**: Proceed to Phase 1 only, skip Phases 2-4
- **C (Comprehensive)**: Proceed through all 4 phases, asking user if they want to skip each

### Step 2: Phase 1 - Technical Standards

**Context**:
```
Phase 1: Technical Standards

These are the non-negotiable technical requirements that all features must follow.
Examples: Python 3.11+, pytest with 80% coverage, Docker deployment only.

This phase is recommended for all projects to establish basic technical foundation.
```

**Questions** (ask one at a time):

**Q1: Languages and Frameworks**
```
What languages and frameworks are required for this project?

Examples:
- "Python 3.11+ with FastAPI for backend"
- "TypeScript 4.9+ with React 18 for frontend"
- "Rust 1.70+ with no external dependencies"

Your answer:
```

**Q2: Testing Requirements**
```
What testing framework and coverage requirements?

Examples:
- "pytest with 80% line coverage, 100% for critical paths"
- "Jest with 90% coverage, unit + integration tests required"
- "cargo test, no specific coverage target but all features must have tests"

Your answer:
```

**Q3: Performance and Scale Targets**
```
What are the performance and scale expectations?

Examples:
- "Handle 1000 requests/second at p95 < 200ms"
- "Support 10k concurrent users, 1M daily active users"
- "CLI operations complete in < 2 seconds"
- "N/A - performance not a primary concern"

Your answer:
```

**Q4: Deployment and Constraints**
```
What are the deployment constraints or platform requirements?

Examples:
- "Docker-only, deployed to Kubernetes"
- "Must run on Ubuntu 20.04 LTS without external dependencies"
- "Cross-platform: Linux, macOS, Windows 10+"
- "N/A - no specific deployment constraints"

Your answer:
```

**Phase 1 Complete**: Save answers to internal data structure.

### Step 3: Phase 2 - Code Quality (Optional)

**If comprehensive path, ask**:
```
Phase 2: Code Quality

Define PR requirements, review process, and quality gates.
Skip this if your team uses standard practices without special requirements.

Do you want to define code quality standards?
A) Yes, ask questions
B) No, skip this phase (use standard practices)
```

**If skip**: Proceed to Phase 3
**If yes, ask questions**:

**Q5: PR Requirements**
```
What are the requirements for pull requests?

Examples:
- "2 approvals required, 1 must be from core team"
- "1 approval required, PR must pass CI checks"
- "Self-merge allowed after CI passes for maintainers"

Your answer:
```

**Q6: Code Review Checklist**
```
What should reviewers check during code review?

Examples:
- "Tests added, docstrings updated, follows PEP 8, no security issues"
- "Type annotations present, error handling robust, performance considered"
- "Standard review - correctness, clarity, maintainability"

Your answer:
```

**Q7: Quality Gates**
```
What quality gates must pass before merging?

Examples:
- "All tests pass, coverage ≥80%, linter clean, security scan clean"
- "Tests pass, type checking passes, manual QA approved"
- "CI green, no merge conflicts, PR approved"

Your answer:
```

**Q8: Documentation Standards**
```
What documentation is required?

Examples:
- "All public APIs must have docstrings + examples"
- "README updated for new features, ADRs for architectural decisions"
- "Inline comments for complex logic, keep docs up to date"
- "Minimal - code should be self-documenting"

Your answer:
```

**Phase 2 Complete**: Save answers to internal data structure.

### Step 4: Phase 3 - Tribal Knowledge (Optional)

**If comprehensive path, ask**:
```
Phase 3: Tribal Knowledge

Capture team conventions, lessons learned, and historical context.
Skip this for new projects or if team conventions are minimal.

Do you want to capture tribal knowledge?
A) Yes, ask questions
B) No, skip this phase
```

**If skip**: Proceed to Phase 4
**If yes, ask questions**:

**Q9: Team Conventions**
```
What team conventions or coding styles should everyone follow?

Examples:
- "Use Result<T, E> for fallible operations, never unwrap() in production code"
- "Prefer composition over inheritance, keep classes small (<200 lines)"
- "Use feature flags for gradual rollouts, never merge half-finished features"
- "Standard conventions - follow language idioms"

Your answer:
```

**Q10: Lessons Learned**
```
What past mistakes or lessons learned should guide future work?

Examples:
- "Always version APIs from day 1 (learned from painful migration)"
- "Write integration tests first - caught more bugs than unit tests"
- "Keep dependencies minimal - every dependency is a liability"
- "N/A - no major lessons to document yet"

Your answer:
```

**Q11: Historical Decisions** (optional, ask only if user wants more depth):
```
Any historical architectural decisions that should guide future work?

Examples:
- "Chose microservices for independent scaling, maintain service boundaries"
- "Chose monorepo for atomic changes across services"
- "Chose SQLite for simplicity over PostgreSQL for scale"
- "N/A - no major architectural decisions to document"

Your answer:
```

**Phase 3 Complete**: Save answers to internal data structure.

### Step 5: Phase 4 - Governance (Optional)

**If comprehensive path, ask**:
```
Phase 4: Governance

Define how the constitution is updated and how compliance is validated.
Skip this to use simple defaults (constitution can be amended anytime, no formal process).

Do you want to define governance process?
A) Yes, ask questions
B) No, skip this phase (use simple defaults)
```

**If skip**: Use defaults:
- Amendment: Any team member can propose changes via PR
- Compliance: Team validates during code review
- Exceptions: Discuss with team, document in PR

**If yes, ask questions**:

**Q12: Amendment Process**
```
How should the constitution be amended?

Examples:
- "PR with 2 approvals, announce in team chat, 1 week discussion period"
- "Any maintainer can update via PR, no special process"
- "Quarterly review, team votes on proposed changes"

Your answer:
```

**Q13: Compliance Validation**
```
Who validates that features comply with the constitution?

Examples:
- "Code reviewers check compliance, blocker for merge if violated"
- "Team lead reviews architecture, flags violations in design review"
- "Self-managed - developers responsible for compliance"

Your answer:
```

**Q14: Exception Handling** (optional):
```
How should exceptions to the constitution be handled?

Examples:
- "Document in ADR, require 3 approvals, set sunset date for exception"
- "Case-by-case discussion, must have strong justification"
- "Exceptions discouraged - update constitution instead"

Your answer:
```

**Phase 4 Complete**: Save answers to internal data structure.

### Step 6: Generate Constitution Summary

**Present summary to user for confirmation**:
```
Constitution Summary
====================

You've completed [1-4] phases. Here's what will be written to .kittify/memory/constitution.md:

Technical Standards:
- Languages: [answer from Q1]
- Testing: [answer from Q2]
- Performance: [answer from Q3]
- Deployment: [answer from Q4]

[If Phase 2 completed:]
Code Quality:
- PR Requirements: [answer from Q5]
- Review Checklist: [answer from Q6]
- Quality Gates: [answer from Q7]
- Documentation: [answer from Q8]

[If Phase 3 completed:]
Tribal Knowledge:
- Conventions: [answer from Q9]
- Lessons Learned: [answer from Q10]
[If Q11 answered:]
- Historical Decisions: [answer from Q11]

[If Phase 4 completed:]
Governance:
- Amendment: [answer from Q12]
- Compliance: [answer from Q13]
[If Q14 answered:]
- Exceptions: [answer from Q14]

Estimated length: [~50 lines for minimal, ~150 lines for comprehensive]

Proceed with writing constitution?
A) Yes, write it
B) No, let me start over
C) Cancel, don't create constitution
```

**Handle responses**:
- **A (Yes)**: Proceed to Step 7
- **B (Start over)**: Return to Step 1
- **C (Cancel)**: Exit without creating constitution, inform user they can run command again anytime

### Step 7: Write Constitution File

**Generate constitution document**:
```markdown
# [PROJECT_NAME] Constitution

> Auto-generated by spec-kitty constitution command
> Created: [YYYY-MM-DD]
> Version: 1.0.0

## Purpose

This constitution captures the technical standards, code quality expectations, tribal knowledge, and governance rules for [PROJECT_NAME]. All features and pull requests should align with these principles.

## Technical Standards

### Languages and Frameworks
[Answer from Q1, formatted as paragraph or bullet points]

### Testing Requirements
[Answer from Q2]

### Performance and Scale
[Answer from Q3]

### Deployment and Constraints
[Answer from Q4]

[If Phase 2 completed:]
## Code Quality

### Pull Request Requirements
[Answer from Q5]

### Code Review Checklist
[Answer from Q6]

### Quality Gates
[Answer from Q7]

### Documentation Standards
[Answer from Q8]

[If Phase 3 completed:]
## Tribal Knowledge

### Team Conventions
[Answer from Q9]

### Lessons Learned
[Answer from Q10]

[If Q11 answered:]
### Historical Decisions
[Answer from Q11]

[If Phase 4 completed:]
## Governance

### Amendment Process
[Answer from Q12]

### Compliance Validation
[Answer from Q13]

[If Q14 answered:]
### Exception Handling
[Answer from Q14]

[If Phase 4 skipped, use defaults:]
## Governance

### Amendment Process
Any team member can propose amendments via pull request. Changes are discussed and merged following standard PR review process.

### Compliance Validation
Code reviewers validate compliance during PR review. Constitution violations should be flagged and addressed before merge.

### Exception Handling
Exceptions discussed case-by-case with team. Strong justification required. Consider updating constitution if exceptions become common.

---

**Version**: 1.0.0 | **Created**: [YYYY-MM-DD] | **Last Updated**: [YYYY-MM-DD]
```

**Write to file**:
```python
constitution_path = project_root / ".kittify" / "memory" / "constitution.md"
constitution_path.parent.mkdir(parents=True, exist_ok=True)
constitution_path.write_text(generated_constitution, encoding="utf-8")
```

### Step 8: Completion Message

**Output to user**:
```
✓ Constitution created at .kittify/memory/constitution.md

Summary:
- [Minimal: ~50 lines, 1 page] or [Comprehensive: ~150 lines, 2-3 pages]
- [Number] phases completed
- [Number] questions answered

Your constitution captures:
[List the phases/sections included]

Next steps:
- Review and edit .kittify/memory/constitution.md if needed
- Share with team for feedback
- Use /spec-kitty.plan to see constitution checks in action
- Update constitution anytime by running this command again

Commands will validate features against your constitution during planning and review.
```

---

## Key Implementation Details

**Template Variables**:
```python
# Variables to populate
PROJECT_NAME = get_project_name()  # From git remote or repo name
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
ANSWERS = {
    "q1_languages": "...",
    "q2_testing": "...",
    # ... etc
}
```

**Path Determination**:
```python
# Constitution lives at project root, not worktree
project_root = find_project_root()  # Walk up from cwd to find .git
constitution_path = project_root / ".kittify" / "memory" / "constitution.md"
```

**Question Flow Logic**:
```python
path = ask_initial_choice()  # "skip", "minimal", "comprehensive"

if path == "skip":
    create_placeholder_constitution()
    exit_success()

# Phase 1 (always for minimal + comprehensive)
answers_phase1 = ask_phase1_questions()

if path == "comprehensive":
    # Phase 2 (optional)
    if user_wants_phase2():
        answers_phase2 = ask_phase2_questions()

    # Phase 3 (optional)
    if user_wants_phase3():
        answers_phase3 = ask_phase3_questions()

    # Phase 4 (optional)
    if user_wants_phase4():
        answers_phase4 = ask_phase4_questions()
    else:
        use_governance_defaults()

# Generate and confirm
constitution_text = generate_constitution(answers)
if confirm_constitution(constitution_text):
    write_constitution(constitution_text)
    show_success_message()
```

---

## End of Template Content

The above markdown content is what should be written to `src/specify_cli/templates/command-templates/constitution.md` in subtask T028. The subsequent subtasks (T029-T033) provide detailed implementation guidance for each phase.

---

### Subtask T029 – Implement Phase 1 (Technical Standards)

**Purpose**: Create the core technical foundation questions that most projects need.

**Questions to Implement** (from T028 template above):
1. Languages and Frameworks
2. Testing Requirements
3. Performance and Scale Targets
4. Deployment and Constraints

**Implementation Guidance**:

**Question Format**:
```markdown
**Question [N]/4: [Question Title]**

[Context and examples]

Examples:
- [Example 1]
- [Example 2]
- [Example 3]

Your answer:
```

**Answer Validation**:
- Accept any non-empty text (no strict validation)
- If user says "N/A" or "None" or similar, that's valid
- Store answer as-is for constitution generation

**Context Provision**:
- Before Phase 1, explain what technical standards are
- Give examples of good answers (concrete, specific)
- Encourage brevity (1-2 sentences better than paragraphs)

**Skip Logic**:
- Phase 1 cannot be skipped for minimal or comprehensive paths
- Only skipped if user chooses "No constitution" in Step 1

**Testing Phase 1**:
```python
# Test: Minimal path completes Phase 1 only
answers = run_minimal_path()
assert "q1_languages" in answers
assert "q2_testing" in answers
assert "q3_performance" in answers
assert "q4_deployment" in answers
assert "q5_pr_requirements" not in answers  # Phase 2 not asked

# Test: User provides "N/A" answers
answers = run_phase1_with_na_answers()
assert answers["q3_performance"] == "N/A - performance not a concern"
# Should still generate valid constitution

# Test: User provides detailed answers
answers = run_phase1_with_detailed_answers()
constitution = generate_constitution(answers)
assert "Python 3.11+" in constitution
assert "pytest" in constitution
```

---

### Subtask T030 – Implement Phase 2 (Code Quality)

**Purpose**: Capture code quality standards for teams with specific requirements.

**Questions to Implement**:
5. PR Requirements
6. Code Review Checklist
7. Quality Gates
8. Documentation Standards

**Skip Option Implementation**:
```markdown
## Phase 2: Code Quality

Define PR requirements, review process, and quality gates.
Skip this if your team uses standard practices without special requirements.

**Do you want to define code quality standards?**
A) Yes, ask questions (recommended for teams with specific quality requirements)
B) No, skip this phase (use standard industry practices)

[If comprehensive path selected in Step 1]
Your choice:
```

**Guidance on When to Skip**:
- Skip if: Standard industry practices (2 approvals, tests pass, linter clean)
- Complete if: Custom requirements (specific review checklist, non-standard gates)
- Skip if: Small team without formal process
- Complete if: Large team or open source with formal contribution guidelines

**Answer Storage**:
```python
if phase2_skipped:
    answers["phase2_completed"] = False
    # Don't include Phase 2 section in constitution
else:
    answers["phase2_completed"] = True
    answers["q5_pr_requirements"] = get_answer()
    answers["q6_review_checklist"] = get_answer()
    answers["q7_quality_gates"] = get_answer()
    answers["q8_documentation"] = get_answer()
```

**Constitution Generation (Phase 2)**:
```python
if answers.get("phase2_completed"):
    constitution += """
## Code Quality

### Pull Request Requirements
{q5_pr_requirements}

### Code Review Checklist
{q6_review_checklist}

### Quality Gates
{q7_quality_gates}

### Documentation Standards
{q8_documentation}
""".format(**answers)
```

**Testing Phase 2**:
```python
# Test: Skip Phase 2
answers = run_comprehensive_path_skip_phase2()
assert "phase2_completed" not in answers or not answers["phase2_completed"]
constitution = generate_constitution(answers)
assert "## Code Quality" not in constitution

# Test: Complete Phase 2
answers = run_comprehensive_path_complete_phase2()
assert answers["phase2_completed"] == True
constitution = generate_constitution(answers)
assert "## Code Quality" in constitution
assert "Pull Request Requirements" in constitution
```

---

### Subtask T031 – Implement Phase 3 (Tribal Knowledge)

**Purpose**: Capture institutional knowledge, team conventions, and lessons learned.

**Questions to Implement**:
9. Team Conventions
10. Lessons Learned
11. Historical Decisions (optional - only if user wants more depth)

**Skip Option Implementation**:
```markdown
## Phase 3: Tribal Knowledge

Capture team conventions, lessons learned, and historical context.
Skip this for new projects or if team conventions are minimal.

**Do you want to capture tribal knowledge?**
A) Yes, ask questions (recommended for experienced teams with accumulated wisdom)
B) No, skip this phase (minimal or no tribal knowledge to document)

[If comprehensive path selected in Step 1]
Your choice:
```

**Guidance on When to Skip**:
- Skip if: New project with no history
- Complete if: Established project with hard-won lessons
- Skip if: Team conventions are standard/obvious
- Complete if: Unique conventions that new team members should know

**Optional Question Logic (Q11)**:
```markdown
[After Q9 and Q10 answered]

You've documented conventions and lessons learned.

**Do you want to document historical architectural decisions?**
These are major decisions (technology choices, architecture patterns) that guide future work.

A) Yes, document decisions
B) No, that's enough tribal knowledge

Your choice:
```

**Answer Storage**:
```python
if phase3_skipped:
    answers["phase3_completed"] = False
else:
    answers["phase3_completed"] = True
    answers["q9_conventions"] = get_answer()
    answers["q10_lessons"] = get_answer()

    # Q11 is optional
    if user_wants_historical_decisions():
        answers["q11_historical"] = get_answer()
    else:
        answers["q11_historical"] = None
```

**Constitution Generation (Phase 3)**:
```python
if answers.get("phase3_completed"):
    constitution += """
## Tribal Knowledge

### Team Conventions
{q9_conventions}

### Lessons Learned
{q10_lessons}
""".format(**answers)

    # Q11 is optional
    if answers.get("q11_historical"):
        constitution += """
### Historical Decisions
{q11_historical}
""".format(**answers)
```

**Testing Phase 3**:
```python
# Test: Skip Phase 3
answers = run_comprehensive_path_skip_phase3()
assert not answers.get("phase3_completed")
constitution = generate_constitution(answers)
assert "## Tribal Knowledge" not in constitution

# Test: Complete Phase 3 without Q11
answers = run_phase3_without_historical()
assert answers["phase3_completed"] == True
assert "q11_historical" not in answers
constitution = generate_constitution(answers)
assert "## Tribal Knowledge" in constitution
assert "Historical Decisions" not in constitution

# Test: Complete Phase 3 with Q11
answers = run_phase3_with_historical()
assert answers["q11_historical"] is not None
constitution = generate_constitution(answers)
assert "Historical Decisions" in constitution
```

---

### Subtask T032 – Implement Phase 4 (Governance)

**Purpose**: Define how constitution is managed and enforced, or use sensible defaults.

**Questions to Implement**:
12. Amendment Process
13. Compliance Validation
14. Exception Handling (optional)

**Skip Option Implementation with Defaults**:
```markdown
## Phase 4: Governance

Define how the constitution is updated and how compliance is validated.
Skip this to use simple defaults (constitution can be amended anytime, no formal process).

**Do you want to define governance process?**
A) Yes, ask questions (recommended for large teams needing formal process)
B) No, skip this phase (use simple defaults - works for most teams)

**Default governance** (if you skip):
- Amendment: Any team member can propose changes via PR
- Compliance: Team validates during code review
- Exceptions: Discuss with team, document in PR

[If comprehensive path selected in Step 1]
Your choice:
```

**Default Governance Text**:
```python
DEFAULT_GOVERNANCE = """
## Governance

### Amendment Process
Any team member can propose amendments via pull request. Changes are discussed
and merged following standard PR review process.

### Compliance Validation
Code reviewers validate compliance during PR review. Constitution violations
should be flagged and addressed before merge.

### Exception Handling
Exceptions discussed case-by-case with team. Strong justification required.
Consider updating constitution if exceptions become common.
"""
```

**Governance Question Flow**:
```python
if phase4_skipped:
    answers["phase4_completed"] = False
    answers["governance_text"] = DEFAULT_GOVERNANCE
else:
    answers["phase4_completed"] = True
    answers["q12_amendment"] = get_answer()
    answers["q13_compliance"] = get_answer()

    # Q14 is optional
    if user_wants_exception_handling():
        answers["q14_exceptions"] = get_answer()

    # Generate custom governance text
    answers["governance_text"] = generate_governance_section(answers)
```

**Constitution Generation (Phase 4)**:
```python
# Governance section always included, either custom or default
constitution += answers["governance_text"]
```

**Testing Phase 4**:
```python
# Test: Skip Phase 4 (use defaults)
answers = run_comprehensive_path_skip_phase4()
assert not answers.get("phase4_completed")
constitution = generate_constitution(answers)
assert "## Governance" in constitution
assert "Any team member can propose amendments" in constitution  # Default text

# Test: Complete Phase 4 without Q14
answers = run_phase4_without_exceptions()
constitution = generate_constitution(answers)
assert "## Governance" in constitution
assert answers["q12_amendment"] in constitution
assert "Exception Handling" not in constitution

# Test: Complete Phase 4 with Q14
answers = run_phase4_with_exceptions()
constitution = generate_constitution(answers)
assert "Exception Handling" in constitution
assert answers["q14_exceptions"] in constitution
```

---

### Subtask T033 – Add summary presentation and user confirmation

**Purpose**: Show user what will be written before committing to file. Allow cancel or restart.

**Summary Format** (from T028 Step 6):
```
Constitution Summary
====================

You've completed [X] phases and answered [Y] questions.
Here's what will be written to .kittify/memory/constitution.md:

[Present all gathered information organized by phase]

Estimated length: [~50-80 lines for minimal, ~150-200 lines for comprehensive]

Proceed with writing constitution?
A) Yes, write it
B) No, let me start over
C) Cancel, don't create constitution
```

**Implementation**:
```python
def present_summary(answers):
    """Generate and show constitution summary to user."""

    # Count phases
    phases_completed = sum([
        True,  # Phase 1 always completed
        answers.get("phase2_completed", False),
        answers.get("phase3_completed", False),
        answers.get("phase4_completed", False) or True  # Defaults count
    ])

    # Count questions
    questions_answered = count_answered_questions(answers)

    # Generate preview constitution
    preview = generate_constitution(answers)
    estimated_lines = len(preview.split('\n'))

    # Show summary
    print(f"\nConstitution Summary")
    print(f"=" * 50)
    print(f"\nYou've completed {phases_completed} phases and answered {questions_answered} questions.")
    print(f"Here's what will be written to .kittify/memory/constitution.md:\n")

    # Show sections
    print("Technical Standards:")
    print(f"  - Languages: {answers['q1_languages'][:50]}...")
    print(f"  - Testing: {answers['q2_testing'][:50]}...")
    print(f"  - Performance: {answers['q3_performance'][:50]}...")
    print(f"  - Deployment: {answers['q4_deployment'][:50]}...")

    if answers.get("phase2_completed"):
        print("\nCode Quality:")
        print(f"  - PR Requirements: {answers['q5_pr_requirements'][:50]}...")
        print(f"  - Review Checklist: {answers['q6_review_checklist'][:50]}...")
        print(f"  - Quality Gates: {answers['q7_quality_gates'][:50]}...")
        print(f"  - Documentation: {answers['q8_documentation'][:50]}...")

    if answers.get("phase3_completed"):
        print("\nTribal Knowledge:")
        print(f"  - Conventions: {answers['q9_conventions'][:50]}...")
        print(f"  - Lessons: {answers['q10_lessons'][:50]}...")
        if answers.get("q11_historical"):
            print(f"  - Historical: {answers['q11_historical'][:50]}...")

    print(f"\nGovernance: {'Custom process' if answers.get('phase4_completed') else 'Default process'}")

    print(f"\nEstimated length: ~{estimated_lines} lines")
    print(f"                  ~{estimated_lines // 50} pages")

    # Ask for confirmation
    choice = prompt_user("""
Proceed with writing constitution?
A) Yes, write it
B) No, let me start over
C) Cancel, don't create constitution

Your choice:
""")

    return choice  # "yes", "restart", "cancel"
```

**Confirmation Handling**:
```python
def run_constitution_command():
    """Main command entry point."""

    while True:
        answers = run_discovery_phases()

        confirmation = present_summary(answers)

        if confirmation == "yes":
            write_constitution(answers)
            show_success_message(answers)
            break
        elif confirmation == "restart":
            print("\nStarting over...\n")
            continue  # Loop back to beginning
        else:  # "cancel"
            print("\nCancelled. No constitution created.")
            print("Run /spec-kitty.constitution anytime to create one.")
            break
```

**Success Message** (from T028 Step 8):
```python
def show_success_message(answers):
    """Show completion message after constitution written."""

    phases_completed = count_phases(answers)
    questions_answered = count_questions(answers)
    constitution_path = get_constitution_path()

    print(f"\n✓ Constitution created at {constitution_path}")
    print(f"\nSummary:")
    print(f"  - {'Minimal' if phases_completed == 1 else 'Comprehensive'} constitution created")
    print(f"  - {phases_completed} phases completed")
    print(f"  - {questions_answered} questions answered")

    print(f"\nYour constitution captures:")
    phases_list = []
    if True:  # Phase 1 always
        phases_list.append("  ✓ Technical Standards")
    if answers.get("phase2_completed"):
        phases_list.append("  ✓ Code Quality")
    if answers.get("phase3_completed"):
        phases_list.append("  ✓ Tribal Knowledge")
    if answers.get("phase4_completed") or True:  # Defaults or custom
        phases_list.append("  ✓ Governance")

    print("\n".join(phases_list))

    print(f"\nNext steps:")
    print(f"  - Review and edit {constitution_path} if needed")
    print(f"  - Share with team for feedback")
    print(f"  - Use /spec-kitty.plan to see constitution checks in action")
    print(f"  - Update constitution anytime by running this command again")

    print(f"\nCommands will now validate features against your constitution.")
```

**Testing Summary and Confirmation**:
```python
# Test: User confirms
answers = run_full_workflow_with_confirm()
assert constitution_file_exists()
assert constitution_contains(answers)

# Test: User restarts
answers1 = run_workflow_partial()
# User chooses "restart" at confirmation
answers2 = run_workflow_again()
# Should start from beginning, ignore answers1

# Test: User cancels
answers = run_workflow_partial()
# User chooses "cancel" at confirmation
assert not constitution_file_exists()
assert "Cancelled" in output
```

---

## Test Strategy

**Unit Tests**:
```python
# Test question flow
def test_minimal_path():
    answers = simulate_user_input(["B"])  # Minimal
    assert len(answers) == 4  # Only Phase 1 questions

def test_comprehensive_path_all_phases():
    answers = simulate_user_input([
        "C",  # Comprehensive
        "A",  # Phase 2: Yes
        "A",  # Phase 3: Yes
        "A",  # Q11: Yes
        "A",  # Phase 4: Yes
        "A",  # Q14: Yes
    ])
    assert len(answers) == 12  # All questions

def test_comprehensive_path_skip_optional():
    answers = simulate_user_input([
        "C",  # Comprehensive
        "B",  # Phase 2: Skip
        "B",  # Phase 3: Skip
        "B",  # Phase 4: Skip
    ])
    assert len(answers) == 4  # Only Phase 1 (required)

# Test constitution generation
def test_constitution_minimal():
    answers = get_minimal_answers()
    constitution = generate_constitution(answers)
    assert "## Technical Standards" in constitution
    assert "## Code Quality" not in constitution
    assert len(constitution.split('\n')) < 100  # ~50-80 lines

def test_constitution_comprehensive():
    answers = get_comprehensive_answers()
    constitution = generate_constitution(answers)
    assert "## Technical Standards" in constitution
    assert "## Code Quality" in constitution
    assert "## Tribal Knowledge" in constitution
    assert "## Governance" in constitution
    assert len(constitution.split('\n')) > 100  # ~150-200 lines
```

**Integration Tests** (defer to WP06):
- Run command in test project
- Verify constitution file created
- Verify commands work without constitution
- Verify constitution check in plan command

**Manual Testing**:
```bash
# Test 1: Minimal path
cd /tmp/test-minimal
git init
spec-kitty init
# Choose: B (Minimal)
# Answer Phase 1 questions
# Confirm: A (Yes, write it)
cat .kittify/memory/constitution.md
wc -l .kittify/memory/constitution.md  # ~50-80 lines

# Test 2: Comprehensive path
cd /tmp/test-comprehensive
git init
spec-kitty init
# Choose: C (Comprehensive)
# Complete all phases
# Confirm: A (Yes, write it)
cat .kittify/memory/constitution.md
wc -l .kittify/memory/constitution.md  # ~150-200 lines

# Test 3: Skip constitution
cd /tmp/test-skip
git init
spec-kitty init
# Choose: A (Skip)
# Should create placeholder
cat .kittify/memory/constitution.md  # Minimal placeholder

# Test 4: Restart workflow
# Choose: C (Comprehensive)
# Answer some questions
# At confirmation: B (Restart)
# Should start from beginning

# Test 5: Cancel workflow
# Choose: C (Comprehensive)
# Answer some questions
# At confirmation: C (Cancel)
# Should not create constitution
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| Users skip all phases, get empty constitution | Low | Skip option creates placeholder, commands work without constitution | All subtasks |
| Questions too vague, answers not useful | Medium | Provide concrete examples for each question | T029-T032 |
| Constitution too verbose | Medium | Encourage brevity in question prompts, 1-2 sentences preferred | All subtasks |
| User confused about when to skip | Medium | Clear skip guidance for each phase | T030-T032 |
| Constitution format breaks tooling | High | Generate valid markdown, test with plan command | T033, WP06 |

---

## Definition of Done Checklist

- [ ] All subtasks T028-T033 completed
- [ ] Constitution command template updated at `src/specify_cli/templates/command-templates/constitution.md`
- [ ] Four phases implemented with skip options
- [ ] Minimal path (Phase 1 only) produces ~1 page constitution
- [ ] Comprehensive path (all phases) produces ~2-3 page constitution
- [ ] Summary and confirmation implemented
- [ ] Default governance text provided for Phase 4 skip
- [ ] Success message shows next steps
- [ ] Manual testing completed (minimal, comprehensive, skip paths)
- [ ] Git commit created explaining redesign
- [ ] Code review requested from maintainer

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Template replaced**: Old placeholder-filling approach completely removed
2. **Four phases present**: Technical, Quality, Tribal, Governance
3. **Skip options clear**: Each optional phase has clear skip guidance
4. **Output length correct**: Minimal ~1 page, comprehensive ~2-3 pages
5. **Summary implemented**: User sees preview before writing
6. **Success message helpful**: Shows next steps, encourages usage

**Red Flags for Reviewer**:
- Placeholder-filling approach still present (old template artifacts)
- No skip guidance for optional phases
- Generated constitution too verbose (>3 pages)
- No confirmation before writing file
- Questions too vague or lack examples

**Testing Checklist for Reviewer**:
```bash
# 1. Read updated template
cat src/specify_cli/templates/command-templates/constitution.md | less

# 2. Verify four phases present
grep -c "## Phase" src/specify_cli/templates/command-templates/constitution.md
# Expected: 4

# 3. Test minimal path
cd /tmp/test-review-minimal
git init && spec-kitty init
# Run /spec-kitty.constitution, choose minimal
cat .kittify/memory/constitution.md | wc -l
# Expected: ~50-80 lines

# 4. Test comprehensive path
cd /tmp/test-review-comprehensive
git init && spec-kitty init
# Run /spec-kitty.constitution, choose comprehensive, complete all phases
cat .kittify/memory/constitution.md | wc -l
# Expected: ~150-200 lines

# 5. Verify commands work without constitution
cd /tmp/test-review-no-constitution
git init && spec-kitty init
# Don't create constitution
spec-kitty agent feature setup-plan --json
# Should succeed
```

**Context for Reviewer**:
- This makes constitution truly optional (User Story 2 goal)
- Phase-based approach matches `/spec-kitty.specify` and `/spec-kitty.plan` patterns
- Focus on user needs, not template structure
- Encourages lean constitutions (1-2 pages, not 10 pages)

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
2. **Use CLI**: `spec-kitty agent tasks move-task WP05 --to <lane> --note "message"`

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
