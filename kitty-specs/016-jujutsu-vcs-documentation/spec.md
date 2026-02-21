# Feature Specification: Jujutsu VCS Documentation

**Feature Branch**: `016-jujutsu-vcs-documentation`
**Created**: 2026-01-17
**Status**: Draft
**Mission**: documentation
**Input**: User description: "Documentation feature sprint to document jujutsu as carefully and accurately as the rest of Spec Kitty and ensure that the github pages correctly updates with the new end user documentation"

## Overview

Document the jujutsu (jj) VCS integration introduced in feature 015, following the established Divio 4-type documentation structure from feature 014. The documentation will both integrate jj mentions throughout existing docs AND create dedicated jj-specific content for users who want to leverage jj's advanced capabilities.

### Target Audience

- **Primary**: End users of spec-kitty who want to use jujutsu for better multi-agent parallel development
- **Secondary**: Existing spec-kitty users curious about jj benefits over git-only workflows

### Approach

1. **Integrate jj throughout existing docs** - Update tutorials, how-tos, and reference docs to mention jj alongside git where relevant
2. **Create dedicated jj content** - New tutorial, how-tos, reference, and explanation content for jj-specific workflows
3. **Verify GitHub Pages deployment** - Ensure DocFX builds correctly with new content

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New User Discovers jj Support (Priority: P1)

A developer installing spec-kitty for the first time sees that jj is supported and recommended. They want to understand what jj is, why spec-kitty prefers it, and how to get started with it.

**Why this priority**: First impressions matter. If jj support isn't visible during onboarding, users won't know to try it.

**Independent Test**: A new user following the Getting Started tutorial learns about jj support and can make an informed choice about which VCS to use.

**Acceptance Scenarios**:

1. **Given** a developer reading the Getting Started tutorial, **When** they reach the installation section, **Then** they see information about jj being preferred when available
2. **Given** a user who has never heard of jj, **When** they read the jj explanation, **Then** they understand the key benefits (auto-rebase, non-blocking conflicts)
3. **Given** a user installing spec-kitty, **When** they run `spec-kitty init`, **Then** the tutorial explains the jj recommendation message they'll see

---

### User Story 2 - User Learns jj-Specific Workflow (Priority: P1)

A user who has installed jj wants to learn how to use spec-kitty's jj features effectively. They need a tutorial that walks them through the jj-specific workflow including auto-rebase, syncing, and conflict handling.

**Why this priority**: Users who choose jj need clear guidance on how to use it. Without this, they'll fall back to git patterns and miss jj's benefits.

**Independent Test**: A user with jj installed can follow the jj tutorial and successfully use auto-rebase between dependent work packages.

**Acceptance Scenarios**:

1. **Given** a user with jj installed, **When** they follow the jj workflow tutorial, **Then** they successfully create and sync dependent workspaces
2. **Given** a user working on WP02 that depends on WP01, **When** WP01 changes, **Then** they know how to sync WP02 and understand the auto-rebase behavior
3. **Given** a sync that results in conflicts, **When** the user reads the tutorial, **Then** they understand that conflicts are non-blocking and how to resolve them

---

### User Story 3 - User Looks Up New Commands (Priority: P1)

A user needs to know the exact syntax and options for the new jj-related commands (`spec-kitty sync`, `spec-kitty ops log/undo/restore`). They need accurate reference documentation.

**Why this priority**: Reference documentation is essential for daily use. Users need to quickly look up command syntax.

**Independent Test**: User can find complete documentation for all new commands with accurate syntax, flags, and examples.

**Acceptance Scenarios**:

1. **Given** a user who needs to sync a workspace, **When** they look up `spec-kitty sync`, **Then** they find complete documentation with all flags and examples
2. **Given** a user who made a mistake, **When** they look up `spec-kitty ops undo`, **Then** they find clear instructions for both jj and git backends
3. **Given** a user checking ops log, **When** they read the reference, **Then** they understand the difference between jj operation log and git reflog

---

### User Story 4 - User Updates Existing Knowledge (Priority: P2)

An existing spec-kitty user who learned from the original documentation now wants to understand how jj changes things. They need updated docs that show jj alongside git without having to re-read everything.

**Why this priority**: Existing users shouldn't feel lost when jj is added. Updates should be discoverable and clearly marked.

**Independent Test**: An existing user can find jj-related updates in familiar documentation locations.

**Acceptance Scenarios**:

1. **Given** a user familiar with `spec-kitty init`, **When** they re-read the how-to, **Then** they see new information about jj detection and the `--vcs` flag
2. **Given** a user familiar with `spec-kitty implement`, **When** they re-read the reference, **Then** they understand that workspaces may be jj workspaces or git worktrees
3. **Given** a user reading the parallel development how-to, **When** they encounter jj mentions, **Then** the benefits of jj for parallel work are clear

---

### User Story 5 - User Understands Why jj (Priority: P2)

A user wants to understand the design rationale behind jj integration. Why does spec-kitty prefer jj? What problems does it solve? They need conceptual explanations.

**Why this priority**: Understanding "why" helps users make better decisions and appreciate the tool's design.

**Independent Test**: A user can read the jj explanation and articulate why jj is beneficial for multi-agent workflows.

**Acceptance Scenarios**:

1. **Given** a user curious about jj, **When** they read the jj explanation, **Then** they understand auto-rebase eliminates manual coordination
2. **Given** a user reading the explanation, **When** they encounter "non-blocking conflicts", **Then** they understand why this enables parallel development
3. **Given** a user who has read the explanation, **When** they discuss with teammates, **Then** they can explain the jj benefits

---

### User Story 6 - Documentation Deploys Correctly (Priority: P1)

The documentation team needs the GitHub Pages deployment to work correctly with all new content. DocFX must build successfully and the site must be accessible.

**Why this priority**: Documentation that doesn't deploy has zero value. This is a critical technical requirement.

**Independent Test**: GitHub Actions workflow completes successfully and new jj documentation is visible on the published site.

**Acceptance Scenarios**:

1. **Given** all new documentation is written, **When** the docs-pages workflow runs, **Then** the build completes without errors
2. **Given** the site is deployed, **When** a user navigates to jj documentation, **Then** all pages load correctly with working links
3. **Given** new content in tutorials/how-to/reference/explanation, **When** navigating via toc.yml, **Then** all new sections are discoverable

---

### Edge Cases

- What happens when a user searches for "jujutsu" vs "jj"? Both terms should be searchable and lead to relevant content
- How do docs handle the case where user has jj but runs `--vcs=git`? Document the override explicitly
- What if a user has an older spec-kitty version without jj support? Include version note where relevant
- How do we handle screenshots/examples that differ between git and jj? Show both or clarify which VCS is shown

## Requirements *(mandatory)*

### Functional Requirements

**Integration into Existing Docs**

- **FR-001**: Getting Started tutorial MUST mention jj preference and installation recommendation
- **FR-002**: `spec-kitty init` how-to MUST document jj detection and `--vcs` flag
- **FR-003**: `spec-kitty implement` reference MUST explain VCS abstraction (jj workspace vs git worktree)
- **FR-004**: Parallel development how-to MUST highlight jj benefits for multi-agent workflows
- **FR-005**: File structure reference MUST document `.jj/` alongside `.git/` in colocated mode

**New Dedicated Content**

- **FR-006**: Documentation MUST include a jj workflow tutorial (getting started with jj in spec-kitty)
- **FR-007**: Documentation MUST include how-to for syncing workspaces (`spec-kitty sync`)
- **FR-008**: Documentation MUST include how-to for handling non-blocking conflicts
- **FR-009**: Documentation MUST include how-to for using operation history (`spec-kitty ops`)
- **FR-010**: Documentation MUST include reference for `spec-kitty sync` command
- **FR-011**: Documentation MUST include reference for `spec-kitty ops` command group
- **FR-012**: Documentation MUST include explanation of why jj for multi-agent development
- **FR-013**: Documentation MUST include explanation of auto-rebase and non-blocking conflicts

**Technical Requirements**

- **FR-014**: All new pages MUST follow Divio 4-type classification
- **FR-015**: All new pages MUST have appropriate cross-references to related content
- **FR-016**: DocFX build MUST complete without errors
- **FR-017**: GitHub Pages deployment MUST succeed via existing workflow
- **FR-018**: Table of contents (toc.yml) MUST include all new pages

**Accuracy Requirements**

- **FR-019**: All command documentation MUST match actual CLI behavior (verified against `--help`)
- **FR-020**: All jj-specific behavior MUST be accurate for jj 0.20+
- **FR-021**: Examples MUST be tested and working

### Key Entities

- **VCS Backend**: Either jujutsu (jj) or git - the version control system used for a feature
- **Workspace**: An isolated working directory (jj workspace or git worktree)
- **Sync**: The operation to update a workspace with upstream changes
- **Operation**: A recorded repository mutation (jj operation log or git reflog entry)
- **Conflict**: In jj, stored data that doesn't block work; in git, blocking state requiring resolution

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can learn about jj support within the first 5 minutes of reading Getting Started
- **SC-002**: 100% of new jj commands (`sync`, `ops log`, `ops undo`, `ops restore`) are documented in Reference
- **SC-003**: Users can find jj documentation within 3 clicks from the landing page
- **SC-004**: DocFX build completes with zero errors on new content
- **SC-005**: All internal links in new documentation resolve correctly (no 404s)
- **SC-006**: jj workflow tutorial is end-to-end testable (user can follow and succeed)
- **SC-007**: Both "jujutsu" and "jj" search terms lead to relevant documentation

## Assumptions

- DocFX infrastructure from feature 014 is working correctly
- GitHub Pages workflow (`.github/workflows/docs-pages.yml`) is functional
- The Divio 4-type structure (tutorials/, how-to/, reference/, explanation/) exists
- Feature 015 jujutsu integration is complete and merged
- jj version 0.20+ is the target version for documentation
