# Feature Specification: Documentation Parity Sprint

**Feature**: 056-documentation-parity-sprint
**Mission**: documentation
**Created**: 2026-03-22
**Status**: draft
**Target audience**: End users of spec-kitty-cli (pip install)
**Docs site**: docs.spec-kitty.ai (built by GitHub Actions via DocFX)

---

## Purpose

Bring docs.spec-kitty.ai up to parity with v2.1.x code capabilities. The
documentation site currently publishes only versioned stubs (1.x/ and 2.x/,
~12 files total) while 56 comprehensive docs in Divio categories exist in the
repo but are excluded from the DocFX build. Additionally, 8 distributed skills
contain deep architectural knowledge that needs to be distilled into user-facing
guides.

---

## Problem Statement

1. **Build gap**: DocFX only builds `1x/` and `2x/` directories. The 56
   unversioned docs (tutorials, how-to, reference, explanation) are in the repo
   but invisible on docs.spec-kitty.ai.

2. **Skill knowledge trapped**: The 8 distributed skills (setup-doctor,
   runtime-review, glossary-context, constitution-doctrine, runtime-next,
   orchestrator-api, mission-system, git-workflow) contain the most current and
   detailed documentation of how spec-kitty works, but they're only visible to
   AI agents — not to end users browsing the docs site.

3. **Content gaps**: Several v2.x capabilities lack user-facing documentation:
   constitution/governance workflow, glossary CLI, research/Phase 0 workflow,
   diagnostics (`doctor`), operation history (`ops`), and the skill system itself.

4. **Missing file**: `how-to/use-operation-history.md` is referenced in
   `toc.yml` but does not exist.

---

## User Scenarios & Testing

### Scenario 1: New User Finds Getting Started Guide
A developer installs spec-kitty-cli and visits docs.spec-kitty.ai. They find
a clear getting-started tutorial and can follow it to create their first feature
end-to-end.

**Acceptance**: Tutorial content is accessible on the live site (not just in the
repo). Links from the homepage navigate to tutorials.

### Scenario 2: User Learns About Glossary System
A user wants to understand what the glossary does and how to use the CLI to
manage terms. They find a user-facing guide (distilled from the glossary-context
skill) in the appropriate docs section.

**Acceptance**: Guide explains glossary concepts, CLI commands, and scope
hierarchy without referencing internal middleware pipeline details.

### Scenario 3: User Sets Up Governance
A user wants to create a constitution for their project. They find a how-to
guide (distilled from constitution-doctrine skill) that walks them through
the interview, generation, and sync workflow.

**Acceptance**: Guide covers the full workflow with example commands and
expected outputs.

### Scenario 4: User Understands Git Workflow
A user is confused about what spec-kitty does with git vs what they need to do
themselves. They find a clear explanation (distilled from git-workflow skill)
of the boundary.

**Acceptance**: Guide clearly separates Python-managed vs agent-managed git
operations with concrete examples.

### Scenario 5: User Browses All 4 Divio Categories
A user navigates docs.spec-kitty.ai and can browse tutorials, how-tos,
reference docs, and explanations from the top-level navigation.

**Acceptance**: DocFX build includes all 4 Divio categories. Navigation works
from the homepage.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Update docfx.json to include tutorials/, how-to/, reference/, and explanation/ directories in the build output | draft |
| FR-002 | Create user-facing guide from glossary-context skill in appropriate Divio category | draft |
| FR-003 | Create user-facing guide from constitution-doctrine skill in appropriate Divio category | draft |
| FR-004 | Create user-facing guide from runtime-next skill in appropriate Divio category | draft |
| FR-005 | Create user-facing guide from orchestrator-api skill in appropriate Divio category | draft |
| FR-006 | Create user-facing guide from setup-doctor skill in appropriate Divio category | draft |
| FR-007 | Create user-facing guide from runtime-review skill in appropriate Divio category | draft |
| FR-008 | Create user-facing guide from mission-system skill in appropriate Divio category | draft |
| FR-009 | Create user-facing guide from git-workflow skill in appropriate Divio category | draft |
| FR-010 | Create missing how-to/use-operation-history.md referenced in toc.yml | draft |
| FR-011 | Expand 2x/ versioned docs to cover constitution, glossary, and runtime with adequate depth (currently 37-60 lines each) | draft |
| FR-012 | Update docs/index.md homepage to link to all 4 Divio categories | draft |
| FR-013 | Update toc.yml files to include new guides in navigation | draft |
| FR-014 | Verify all internal cross-references and links resolve correctly | draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | All user-facing guides must be written for end users, not contributors | No internal architecture details, no source file references | draft |
| NFR-002 | Each guide must include working CLI command examples | Every command must be copy-pasteable | draft |
| NFR-003 | Guides distilled from skills must be 40-60% the length of the source skill | Concise, not exhaustive | draft |
| NFR-004 | DocFX build must succeed without errors | Zero build warnings on new files | draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Documentation must be compatible with DocFX markdown dialect | draft |
| C-002 | File naming must follow existing kebab-case convention | draft |
| C-003 | Existing 56 docs must not be modified in ways that break current content | draft |
| C-004 | New guides must be placed in the correct Divio category (tutorial, how-to, reference, or explanation) | draft |

---

## Skill-to-Guide Mapping

| Skill | Divio Type | Proposed Guide Title | Proposed Path |
|---|---|---|---|
| glossary-context | how-to | Manage Project Terminology | `how-to/manage-glossary.md` |
| constitution-doctrine | how-to | Set Up Project Governance | `how-to/setup-governance.md` |
| runtime-next | explanation | How the Runtime Loop Works | `explanation/runtime-loop.md` |
| orchestrator-api | reference | Orchestrator API Reference | Update existing `reference/orchestrator-api.md` |
| setup-doctor | how-to | Diagnose and Repair Installation | `how-to/diagnose-installation.md` |
| runtime-review | how-to | Review a Work Package | Update existing `how-to/review-work-package.md` |
| mission-system | explanation | Understanding Missions | Update existing `explanation/mission-system.md` |
| git-workflow | explanation | How Spec Kitty Uses Git | Update existing `explanation/git-worktrees.md` or new `explanation/git-workflow.md` |

---

## Success Criteria

1. docs.spec-kitty.ai displays all 4 Divio categories (tutorials, how-to,
   reference, explanation) in the top-level navigation
2. All 8 skills have corresponding user-facing guides on the docs site
3. No broken links or missing file references in toc.yml
4. A new user can navigate from the homepage to any guide within 2 clicks
5. DocFX build succeeds with zero errors on the new content

---

## Assumptions

- The DocFX build infrastructure (GitHub Actions workflow) is functional and
  only needs `docfx.json` changes to include new directories
- The 2x/ versioned track is the canonical user-facing version; 1x/ is
  maintenance-mode and does not need updates
- Existing docs in tutorials/, how-to/, reference/, explanation/ are accurate
  for v2.1.x and do not need rewriting (only gap-filling and skill integration)

---

## Key Entities

- **Guide**: A user-facing markdown document in one of the 4 Divio categories
- **Skill**: An agent-facing SKILL.md file in `src/doctrine/skills/` with
  internal architecture documentation
- **DocFX Build**: The GitHub Actions workflow that produces docs.spec-kitty.ai
- **toc.yml**: Table-of-contents YAML files that define navigation structure
  within each Divio category

---

## Out of Scope

- Contributor/developer documentation (docs/development/)
- Architecture decision records (docs/architecture/)
- 1.x maintenance track updates
- New tutorials (the 6 existing tutorials are adequate)
- Rewriting existing complete docs (only gap-filling)
