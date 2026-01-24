---
description: Create or update the project constitution through interactive phase-based discovery.
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

*Path: [templates/commands/constitution.md](templates/commands/constitution.md)*

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

---

## What This Command Does

This command creates or updates the **project constitution** through an interactive, phase-based discovery workflow.

**Location**: `.kittify/memory/constitution.md` (project root, not worktrees)
**Scope**: Project-wide principles that apply to ALL features

**Important**: The constitution is OPTIONAL. All spec-kitty commands work without it.

**Constitution Purpose**:
- Capture technical standards (languages, testing, deployment)
- Document code quality expectations (review process, quality gates)
- Record tribal knowledge (team conventions, lessons learned)
- Define governance (how the constitution changes, who enforces it)

---

## Discovery Workflow

This command uses a **4-phase discovery process**:

1. **Phase 1: Technical Standards** (Recommended)
   - Languages, frameworks, testing requirements
   - Performance targets, deployment constraints
   - ≈3-4 questions, creates a lean foundation

2. **Phase 2: Code Quality** (Optional)
   - PR requirements, review checklist, quality gates
   - Documentation standards
   - ≈3-4 questions

3. **Phase 3: Tribal Knowledge** (Optional)
   - Team conventions, lessons learned
   - Historical decisions (optional)
   - ≈2-4 questions

4. **Phase 4: Governance** (Optional)
   - Amendment process, compliance validation
   - Exception handling (optional)
   - ≈2-3 questions

**Paths**:
- **Minimal** (≈1 page): Phase 1 only → ≈3-5 questions
- **Comprehensive** (≈2-3 pages): All phases → ≈8-12 questions

---

## Execution Outline

### Step 1: Initial Choice

Ask the user:
```
Do you want to establish a project constitution?

A) No, skip it - I don't need a formal constitution
B) Yes, minimal - Core technical standards only (≈1 page, 3-5 questions)
C) Yes, comprehensive - Full governance and tribal knowledge (≈2-3 pages, 8-12 questions)
```

Handle responses:
- **A (Skip)**: Create a minimal placeholder at `.kittify/memory/constitution.md`:
  - Title + short note: "Constitution skipped - not required for spec-kitty usage. Run /spec-kitty.constitution anytime to create one."
  - Exit successfully.
- **B (Minimal)**: Continue with Phase 1 only.
- **C (Comprehensive)**: Continue through all phases, asking whether to skip each optional phase.

### Step 2: Phase 1 - Technical Standards

Context:
```
Phase 1: Technical Standards
These are the non-negotiable technical requirements that all features must follow.
This phase is recommended for all projects.
```

Ask one question at a time:

**Q1: Languages and Frameworks**
```
What languages and frameworks are required for this project?
Examples:
- "Python 3.11+ with FastAPI for backend"
- "TypeScript 4.9+ with React 18 for frontend"
- "Rust 1.70+ with no external dependencies"
```

**Q2: Testing Requirements**
```
What testing framework and coverage requirements?
Examples:
- "pytest with 80% line coverage, 100% for critical paths"
- "Jest with 90% coverage, unit + integration tests required"
- "cargo test, no specific coverage target but all features must have tests"
```

**Q3: Performance and Scale Targets**
```
What are the performance and scale expectations?
Examples:
- "Handle 1000 requests/second at p95 < 200ms"
- "Support 10k concurrent users, 1M daily active users"
- "CLI operations complete in < 2 seconds"
- "N/A - performance not a primary concern"
```

**Q4: Deployment and Constraints**
```
What are the deployment constraints or platform requirements?
Examples:
- "Docker-only, deployed to Kubernetes"
- "Must run on Ubuntu 20.04 LTS without external dependencies"
- "Cross-platform: Linux, macOS, Windows 10+"
- "N/A - no specific deployment constraints"
```

### Step 3: Phase 2 - Code Quality (Optional)

Ask only if comprehensive path is selected:
```
Phase 2: Code Quality
Skip this if your team uses standard practices without special requirements.

Do you want to define code quality standards?
A) Yes, ask questions
B) No, skip this phase (use standard practices)
```

If yes, ask one at a time:

**Q5: PR Requirements**
```
What are the requirements for pull requests?
Examples:
- "2 approvals required, 1 must be from core team"
- "1 approval required, PR must pass CI checks"
- "Self-merge allowed after CI passes for maintainers"
```

**Q6: Code Review Checklist**
```
What should reviewers check during code review?
Examples:
- "Tests added, docstrings updated, follows PEP 8, no security issues"
- "Type annotations present, error handling robust, performance considered"
- "Standard review - correctness, clarity, maintainability"
```

**Q7: Quality Gates**
```
What quality gates must pass before merging?
Examples:
- "All tests pass, coverage ≥80%, linter clean, security scan clean"
- "Tests pass, type checking passes, manual QA approved"
- "CI green, no merge conflicts, PR approved"
```

**Q8: Documentation Standards**
```
What documentation is required?
Examples:
- "All public APIs must have docstrings + examples"
- "README updated for new features, ADRs for architectural decisions"
- "Inline comments for complex logic, keep docs up to date"
- "Minimal - code should be self-documenting"
```

### Step 4: Phase 3 - Tribal Knowledge (Optional)

Ask only if comprehensive path is selected:
```
Phase 3: Tribal Knowledge
Skip this for new projects or if team conventions are minimal.

Do you want to capture tribal knowledge?
A) Yes, ask questions
B) No, skip this phase
```

If yes, ask:

**Q9: Team Conventions**
```
What team conventions or coding styles should everyone follow?
Examples:
- "Use Result<T, E> for fallible operations, never unwrap() in prod"
- "Prefer composition over inheritance, keep classes small (<200 lines)"
- "Use feature flags for gradual rollouts, never merge half-finished features"
```

**Q10: Lessons Learned**
```
What past mistakes or lessons learned should guide future work?
Examples:
- "Always version APIs from day 1"
- "Write integration tests first"
- "Keep dependencies minimal - every dependency is a liability"
- "N/A - no major lessons yet"
```

Optional follow-up:
```
Do you want to document historical architectural decisions?
A) Yes
B) No
```

**Q11: Historical Decisions** (only if yes)
```
Any historical architectural decisions that should guide future work?
Examples:
- "Chose microservices for independent scaling"
- "Chose monorepo for atomic changes across services"
- "Chose SQLite for simplicity over PostgreSQL"
```

### Step 5: Phase 4 - Governance (Optional)

Ask only if comprehensive path is selected:
```
Phase 4: Governance
Skip this to use simple defaults.

Do you want to define governance process?
A) Yes, ask questions
B) No, skip this phase (use simple defaults)
```

If skipped, use defaults:
- Amendment: Any team member can propose changes via PR
- Compliance: Team validates during code review
- Exceptions: Discuss with team, document in PR

If yes, ask:

**Q12: Amendment Process**
```
How should the constitution be amended?
Examples:
- "PR with 2 approvals, announce in team chat, 1 week discussion"
- "Any maintainer can update via PR"
- "Quarterly review, team votes on changes"
```

**Q13: Compliance Validation**
```
Who validates that features comply with the constitution?
Examples:
- "Code reviewers check compliance, block merge if violated"
- "Team lead reviews architecture"
- "Self-managed - developers responsible"
```

Optional follow-up:
```
Do you want to define exception handling?
A) Yes
B) No
```

**Q14: Exception Handling** (only if yes)
```
How should exceptions to the constitution be handled?
Examples:
- "Document in ADR, require 3 approvals, set sunset date"
- "Case-by-case discussion, strong justification required"
- "Exceptions discouraged - update constitution instead"
```

### Step 6: Summary and Confirmation

Present a summary and ask for confirmation:
```
Constitution Summary
====================

You've completed [X] phases and answered [Y] questions.
Here's what will be written to .kittify/memory/constitution.md:

Technical Standards:
- Languages: [Q1]
- Testing: [Q2]
- Performance: [Q3]
- Deployment: [Q4]

[If Phase 2 completed]
Code Quality:
- PR Requirements: [Q5]
- Review Checklist: [Q6]
- Quality Gates: [Q7]
- Documentation: [Q8]

[If Phase 3 completed]
Tribal Knowledge:
- Conventions: [Q9]
- Lessons Learned: [Q10]
- Historical Decisions: [Q11 if present]

Governance: [Custom if Phase 4 completed, otherwise defaults]

Estimated length: ≈[50-80 lines minimal] or ≈[150-200 lines comprehensive]

Proceed with writing constitution?
A) Yes, write it
B) No, let me start over
C) Cancel, don't create constitution
```

Handle responses:
- **A**: Write the constitution file.
- **B**: Restart from Step 1.
- **C**: Exit without writing.

### Step 7: Write Constitution File

Generate the constitution as Markdown:

```markdown
# [PROJECT_NAME] Constitution

> Auto-generated by spec-kitty constitution command
> Created: [YYYY-MM-DD]
> Version: 1.0.0

## Purpose

This constitution captures the technical standards, code quality expectations,
tribal knowledge, and governance rules for [PROJECT_NAME]. All features and
pull requests should align with these principles.

## Technical Standards

### Languages and Frameworks
[Q1]

### Testing Requirements
[Q2]

### Performance and Scale
[Q3]

### Deployment and Constraints
[Q4]

[If Phase 2 completed]
## Code Quality

### Pull Request Requirements
[Q5]

### Code Review Checklist
[Q6]

### Quality Gates
[Q7]

### Documentation Standards
[Q8]

[If Phase 3 completed]
## Tribal Knowledge

### Team Conventions
[Q9]

### Lessons Learned
[Q10]

[If Q11 present]
### Historical Decisions
[Q11]

## Governance

[If Phase 4 completed]
### Amendment Process
[Q12]

### Compliance Validation
[Q13]

[If Q14 present]
### Exception Handling
[Q14]

[If Phase 4 skipped, use defaults]
### Amendment Process
Any team member can propose amendments via pull request. Changes are discussed
and merged following standard PR review process.

### Compliance Validation
Code reviewers validate compliance during PR review. Constitution violations
should be flagged and addressed before merge.

### Exception Handling
Exceptions discussed case-by-case with team. Strong justification required.
Consider updating constitution if exceptions become common.
```

### Step 8: Success Message

After writing, provide:
- Location of the file
- Phases completed and questions answered
- Next steps (review, share with team, run /spec-kitty.specify)

---

## Required Behaviors

- Ask one question at a time.
- Offer skip options and explain when to skip.
- Keep responses concise and user-focused.
- Ensure the constitution stays lean (1-3 pages, not 10 pages).
- If user chooses to skip entirely, still create the minimal placeholder file and exit successfully.