# Feature Specification: Documentation Mission

**Feature Branch**: `012-documentation-mission`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "I want to add a 'documentation' mission to spec kitty. I want us to research the state of the art best practices for writing software product documentation and then conceive of a set of tempaltes, commands and workflow that would let us do a documentation mission on a software project. For example, we'll dogfood this to rewrite spec kitty docs themselves. It should study <https://www.writethedocs.org/index.html> and make those people happy and it should know about the <https://docs.divio.com/documentation-system/> four types of documentation. Additionally, it should know how generated docs of common natures operate, eg generated docs from various languages and frameworks. You recommend which ones but include JS, Python, Rust for sure."

**CRITICAL INFRASTRUCTURE FIXES**: During implementation of this feature, we discovered and fixed critical issues in the workspace-per-WP workflow system (feature 010). See [INFRASTRUCTURE-FIXES.md](INFRASTRUCTURE-FIXES.md) for complete documentation of:

- Worktree state sync (git sparse-checkout + auto-commit)
- Workflow command improvements (end instructions, automated feedback)
- PID tracking restoration
- Feature slug detection fixes
- WP sizing guidance (optimize for size, not count)
- Template propagation to all 12 agents

These fixes are out of scope for the documentation mission but were necessary for continued development.

## Overview

Add a new "documentation" mission type to spec-kitty that helps teams create and maintain high-quality software documentation following industry best practices. The mission integrates Write the Docs principles, the Divio documentation system's four types (tutorials, how-to guides, reference, explanation), and automated documentation generation from code for popular languages and frameworks.

Unlike feature development missions that run once, documentation missions are designed to run iteratively throughout a project's lifetime. Each iteration can either audit existing documentation and fill gaps, or create fresh documentation for new features—the discovery phase adapts to the user's current documentation goals.

## User Scenarios & Testing

### User Story 1 - Initial Project Documentation (Priority: P1)

A developer starts a new open-source Python project and wants to create comprehensive initial documentation that follows best practices. They run the documentation mission to set up tutorials, how-to guides, API reference, and architectural explanations.

**Why this priority**: Most critical scenario—enabling teams to bootstrap documentation from scratch using proven structures. Without this, users can't adopt the documentation mission at all.

**Independent Test**: Can be fully tested by running the documentation mission on a fresh repository with minimal code, and verifying that it generates documentation structure covering all four Divio types plus auto-generated API docs.

**Acceptance Scenarios**:

1. **Given** a Python project with docstrings but no docs folder, **When** user runs `/spec-kitty.specify` with goal "create initial project documentation", **Then** the specify phase asks about target audience, documentation goals, and what Divio types to prioritize
2. **Given** specify phase completes, **When** user runs planning and implementation, **Then** system generates templates for all four Divio documentation types and integrates Sphinx for API reference generation
3. **Given** documentation mission completes, **When** user builds the docs, **Then** they have a working documentation site with tutorials, how-to guides, API reference, and explanation sections
4. **Given** code contains docstrings, **When** Sphinx generator runs, **Then** API reference is automatically populated from docstring content

---

### User Story 2 - Gap-Filling Iteration (Priority: P1)

A project has basic API documentation but users report confusion about getting started. The maintainer runs a documentation mission to audit existing docs, identify that tutorials are missing, and create hands-on getting-started tutorials following Divio principles.

**Why this priority**: Equally critical to P1—iterative improvement is the core value proposition for ongoing documentation maintenance. Teams need to identify and fill documentation gaps systematically.

**Independent Test**: Can be tested by creating a repo with only reference docs, running the mission with "improve existing documentation" goal, and verifying it detects the gap and offers to create tutorial content.

**Acceptance Scenarios**:

1. **Given** a project with existing reference documentation but no tutorials, **When** user runs `/spec-kitty.specify` with goal "improve documentation for new users", **Then** discovery phase audits existing docs and identifies missing tutorial content
2. **Given** audit identifies tutorials missing, **When** specify phase presents findings, **Then** user sees gap analysis showing which Divio types exist and which are missing
3. **Given** user confirms tutorial creation, **When** planning phase runs, **Then** plan focuses specifically on creating learning-oriented tutorials without duplicating existing reference docs
4. **Given** outdated API reference, **When** gap analysis runs, **Then** system detects version mismatches between code and docs and flags sections needing regeneration

---

### User Story 3 - New Feature Documentation (Priority: P2)

A team ships a new authentication feature and wants to document it. They run a documentation mission focused specifically on documenting this feature across appropriate Divio types (tutorial for setup, how-to for common tasks, reference for API, explanation for security model).

**Why this priority**: Common but not blocking—teams can manually write docs for new features if needed. This makes it more efficient and ensures consistency with existing documentation structure.

**Independent Test**: Can be tested by adding a new module to a documented codebase, running the mission with "document new authentication feature" goal, and verifying it creates targeted documentation only for that feature using the project's established documentation patterns.

**Acceptance Scenarios**:

1. **Given** existing documentation structure, **When** user specifies "document new authentication module", **Then** discovery phase asks which aspects need documentation (setup, common tasks, API details, architecture)
2. **Given** user selects tutorial and API reference, **When** implementation runs, **Then** system generates templates pre-filled with detected authentication classes/functions for API reference
3. **Given** JSDoc comments exist in new JavaScript auth code, **When** doc generator runs, **Then** API reference extracts type signatures, parameters, and descriptions automatically
4. **Given** generated docs created, **When** user reviews, **Then** docs follow existing project style and integrate seamlessly with current documentation structure

---

### User Story 4 - Multi-Language Project Documentation (Priority: P3)

A project uses Python for backend services and TypeScript for frontend, requiring unified documentation that handles both ecosystems. The documentation mission integrates Sphinx for Python and JSDoc for TypeScript into a cohesive documentation site.

**Why this priority**: Advanced scenario for polyglot projects—nice to have but not required for single-language projects which are more common.

**Independent Test**: Can be tested by creating a repo with Python and TypeScript code, running the mission, and verifying it detects both languages and offers to configure appropriate generators for each.

**Acceptance Scenarios**:

1. **Given** a repository with both Python and TypeScript code, **When** discovery phase analyzes project structure, **Then** system detects multiple languages and asks which should have generated reference documentation
2. **Given** user selects Python and TypeScript, **When** planning phase runs, **Then** plan includes configuration for both Sphinx and JSDoc/TypeDoc with unified output format
3. **Given** implementation completes, **When** user builds docs, **Then** Python API reference and TypeScript API reference appear in consistent style within the same documentation site
4. **Given** Rust code added later, **When** user runs new documentation iteration, **Then** system detects Rust and offers to add rustdoc integration to existing documentation

---

### Edge Cases

- What happens when existing documentation doesn't follow Divio structure (e.g., everything is mixed together)? System should analyze content and suggest restructuring during gap analysis, but allow user to keep existing structure if preferred.
- How does system handle when code lacks docstrings/comments but user wants generated reference docs? Discovery phase should detect this and warn user that generated docs will be minimal; offer to create manual reference templates instead.
- What happens when user wants only one Divio type (e.g., just API reference)? System should support partial adoption—not every project needs all four types.
- How does mission handle custom documentation generators (e.g., Doxygen, Jazzy, Godoc)? Initial implementation focuses on JSDoc, Sphinx, rustdoc; extensibility for other generators is a future enhancement marked in technical planning.
- What happens when generated docs conflict with existing manual reference docs? System should detect overlaps during planning and ask user whether to merge, replace, or keep separate; default to keeping manual docs and adding generation for new undocumented APIs.
- How does system handle internationalization/localization? Out of scope for initial implementation; documentation mission generates English documentation only; i18n support is future work.

## Requirements

### Functional Requirements

#### Mission Infrastructure

- **FR-001**: System MUST support a new mission type called "documentation" with its own phase workflow distinct from software-dev and research missions
- **FR-002**: Documentation mission MUST support iterative execution—users can run multiple documentation missions on the same project over time
- **FR-003**: System MUST persist documentation mission state between iterations to support gap analysis and avoid regenerating unchanged content

#### Discovery & Specification Phase

- **FR-004**: Specify phase MUST ask users whether this iteration is for initial documentation, gap-filling existing docs, or documenting new features
- **FR-005**: For gap-filling mode, specify phase MUST audit existing documentation and identify which Divio types are present, missing, or outdated
- **FR-006**: Specify phase MUST ask users which Divio documentation types to include (tutorials, how-to guides, reference, explanation) and allow selecting subset
- **FR-007**: System MUST detect project programming languages from file extensions and repository structure to recommend appropriate doc generators
- **FR-008**: Specify phase MUST ask about target audience (developers integrating the project, end users, contributors, operators) to guide documentation tone and depth
- **FR-009**: Generated specification MUST include gap analysis results (if gap-filling mode) showing documentation coverage matrix by Divio type

#### Divio Documentation Types

- **FR-010**: System MUST provide templates for tutorial documentation that guide users through hands-on learning experiences with step-by-step instructions
- **FR-011**: Tutorial templates MUST emphasize doing over explaining, with immediate feedback and concrete accomplishments at each step (per Divio principles)
- **FR-012**: System MUST provide templates for how-to guides that solve specific practical problems for experienced users
- **FR-013**: How-to templates MUST focus on goal-oriented recipes with actionable steps, minimal explanation, and flexibility for user adaptation
- **FR-014**: System MUST provide templates for reference documentation that describe technical details, APIs, functions, classes, and parameters
- **FR-015**: Reference templates MUST structure content around code organization, maintain consistency, and include usage examples
- **FR-016**: System MUST provide templates for explanation documentation that provide understanding-oriented discussion of concepts, architecture, and design decisions
- **FR-017**: Explanation templates MUST focus on context and insight rather than instruction, helping users understand the "why" behind design choices

#### Automated Documentation Generation

- **FR-018**: System MUST integrate with JSDoc for JavaScript/TypeScript projects to generate API reference from inline comments
- **FR-019**: System MUST integrate with Sphinx for Python projects to generate API reference from docstrings using autodoc extensions
- **FR-020**: System MUST integrate with rustdoc (via `cargo doc`) for Rust projects to generate API reference from doc comments
- **FR-021**: When language detection identifies supported languages, plan phase MUST configure appropriate documentation generator with sensible defaults
- **FR-022**: Generated reference documentation MUST be structured to integrate with manual Divio documentation types (tutorials, how-to, explanation)
- **FR-023**: System MUST support regeneration of reference docs when code changes—subsequent documentation iterations should detect code updates and offer to regenerate
- **FR-024**: For JSDoc integration, system MUST configure output format that matches project documentation style (Markdown or HTML)
- **FR-025**: For Sphinx integration, system MUST configure appropriate theme, extensions (autodoc, napoleon for Google/NumPy docstrings), and output format
- **FR-026**: For rustdoc integration, system MUST configure `cargo doc` to output in format compatible with rest of documentation site

#### Write the Docs Best Practices

- **FR-027**: Generated templates MUST follow "docs as code" methodology—documentation lives in version control alongside code
- **FR-028**: Templates MUST include guidance on writing accessible documentation (clear language, proper headings, alt text for images)
- **FR-029**: Templates MUST encourage bias-free language and inclusive examples following Write the Docs diversity principles
- **FR-030**: Reference templates MUST support embedding code examples that can be tested as part of project test suite
- **FR-031**: Planning phase MUST recommend documentation structure that treats docs as integral product component, not afterthought
- **FR-032**: Templates MUST include prompts for considering different reader skill levels and contexts

#### Planning Phase

- **FR-033**: Plan phase MUST analyze existing documentation structure (if any) and either extend it or propose new structure aligned with Divio system
- **FR-034**: For projects with detected doc generators, plan MUST include generator configuration steps with specific commands (e.g., "configure Sphinx with autodoc")
- **FR-035**: Plan MUST identify which documentation can be auto-generated and which requires manual authoring
- **FR-036**: Plan phase MUST create work breakdown showing tasks for each Divio type selected during specify phase
- **FR-037**: For gap-filling iterations, plan MUST prioritize gaps by user impact (e.g., missing tutorials block new users more than missing explanation docs)

#### Implementation & Review

- **FR-038**: Implementation phase MUST generate populated templates with placeholders for project-specific content, not empty templates
- **FR-039**: For reference documentation with detected doc generators, implementation MUST include generator setup commands and initial generation
- **FR-040**: Review phase MUST validate generated documentation against Divio principles (correct type characteristics, appropriate content for each type)
- **FR-041**: System MUST generate documentation build configuration (e.g., Sphinx conf.py, JSDoc config, mkdocs.yml) appropriate for selected generators and structure

#### Publish Phase

- **FR-046**: System MUST support optional `release.md` artifact for documenting publish and handoff details when documentation release is in scope
- **FR-047**: Specify phase SHOULD ask whether documentation release/publish is in scope for this effort to avoid unnecessary release work when publishing is handled elsewhere
- **FR-048**: When publish is in scope, `release.md` template MUST guide documenting hosting configuration (platform, URLs, domains), build output, deployment steps, access credentials, and ownership
- **FR-049**: Release template MUST include sections for monitoring, troubleshooting, and handoff checklist to ensure complete transfer of documentation ownership
- **FR-050**: Review phase MUST validate that `release.md` (if present) reflects actual publish path and handoff steps, not placeholder content

#### Mission Workflow Commands

- **FR-042**: System MUST support `/spec-kitty.specify` for documentation missions with discovery questions tailored to documentation goals
- **FR-043**: System MUST support `/spec-kitty.plan` for documentation missions generating documentation-specific implementation plans
- **FR-044**: System MUST support `/spec-kitty.implement` for documentation missions that generates templates and configures doc generators
- **FR-045**: System MUST support `/spec-kitty.review` for documentation missions validating documentation quality and completeness

### Key Entities

- **Documentation Mission**: A specification-plan-implement workflow focused on creating or improving project documentation; runs iteratively over project lifetime
- **Divio Documentation Type**: One of four types (tutorial, how-to guide, reference, explanation) with distinct purposes, characteristics, and writing guidelines
- **Documentation Template**: Pre-structured file with placeholders and guidance for authoring specific Divio documentation type
- **Documentation Generator**: Language-specific tool that automatically creates reference documentation from code comments/docstrings (JSDoc, Sphinx, rustdoc)
- **Gap Analysis**: Assessment of existing documentation identifying present/missing Divio types, outdated content, and coverage metrics
- **Documentation Coverage Matrix**: Structured view of project documentation showing which Divio types exist for which project areas/features
- **Generator Configuration**: Settings for automated doc tools including output format, theme, extensions, and integration with manual docs
- **Iteration Mode**: Approach for current documentation mission run (initial, gap-filling, feature-specific) determining discovery questions and workflow focus
- **Release Artifact**: Optional `release.md` file documenting hosting, deployment, and handoff details for documentation publish phase

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete initial project documentation setup (all four Divio types + API reference generation) in under 30 minutes for a typical small project
- **SC-002**: Gap analysis correctly identifies missing Divio documentation types with 100% accuracy for projects following standard documentation structures
- **SC-003**: Auto-generated reference documentation requires less than 10% manual correction for well-documented codebases (>70% inline documentation coverage)
- **SC-004**: Documentation mission templates reduce time to create tutorial documentation by 60% compared to writing from scratch (measured by word count produced per hour)
- **SC-005**: Multi-language projects successfully generate unified documentation integrating reference docs from at least two different language ecosystems
- **SC-006**: 90% of generated documentation passes Write the Docs accessibility guidelines (proper heading hierarchy, alt text prompts, clear language)
- **SC-007**: Users can run a second documentation iteration on the same project and system correctly detects existing documentation without duplication or conflicts
- **SC-008**: Documentation mission outputs integrate with popular documentation hosting platforms (Read the Docs, GitHub Pages, GitBook) with minimal configuration

## Assumptions

- **ASM-001**: Users running documentation missions have basic familiarity with their project's programming languages and doc generation tools for those languages
- **ASM-002**: Projects have at least minimal code comments/docstrings for reference documentation generation to be valuable; system will detect and warn about sparse documentation
- **ASM-003**: Initial implementation focuses on static site generators and Markdown-based documentation; dynamic documentation platforms (Gitbook API, Notion) are future enhancements
- **ASM-004**: Users have write access to their repository and can commit generated documentation files and configuration
- **ASM-005**: Documentation mission runs in project repository root with standard directory structures; monorepos with multiple doc locations may require manual adaptation
- **ASM-006**: For gap analysis, system can parse common documentation structures (Sphinx, Docusaurus, Jekyll, MkDocs); custom or unusual structures may require manual gap identification
- **ASM-007**: Generated templates assume English language documentation; internationalization/localization is out of scope for initial implementation
- **ASM-008**: Users are willing to refactor existing non-Divio documentation into Divio structure if gap analysis recommends it, though system supports keeping existing structure

## Out of Scope

The following are explicitly NOT included in this feature:

- **Documentation hosting/deployment**: Mission generates documentation source files but does not deploy to hosting platforms
- **Documentation analytics**: No tracking of doc page views, search queries, or user behavior within generated docs
- **AI-powered content generation**: Templates have placeholders and guidance but do not auto-write documentation prose using LLMs
- **Visual documentation**: Diagrams, screenshots, videos are out of scope; mission focuses on text-based documentation
- **API documentation from OpenAPI/GraphQL schemas**: Initial implementation is code-comment-based only; schema-based generation is future work
- **Documentation testing frameworks**: No integration with tools like doc8, vale, or write-good for automated quality checks (though templates encourage manual quality review)
- **Internationalization/localization**: Single-language (English) documentation only
- **Custom documentation generators beyond JS/Python/Rust**: Extensibility is considered in design but additional language support (Go, Java, C++, etc.) are follow-on enhancements
- **Documentation versioning/archival**: No built-in support for maintaining docs for multiple software versions simultaneously
- **Interactive documentation features**: No support for try-it-now API consoles, embedded code playgrounds, or other interactive elements

## Research Sources

This specification incorporates research from:

- **Write the Docs best practices**: Docs as code methodology, accessibility guidelines, bias reduction, documentation as product component
- **Divio documentation system**: Four-type framework (tutorials, how-to guides, reference, explanation) with distinct purposes and characteristics
- **Documentation generator landscape**: JSDoc for JavaScript, Sphinx for Python, rustdoc for Rust as standard tools in their ecosystems

These principles are embedded in template design, workflow phases, and quality validation criteria throughout the documentation mission.
