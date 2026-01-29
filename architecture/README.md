# Architecture Documentation

This directory contains architectural design decisions, implementation specifications, and technical design documents for Spec Kitty.

## Purpose

The `architecture/` directory contains **Architectural Decision Records (ADRs)** - immutable records of significant architectural decisions made for Spec Kitty.

## What is an ADR?

An Architectural Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs:

- Document **why** decisions were made, not just what was decided
- Are **immutable** once accepted (new ADRs supersede old ones)
- Focus on **one decision** per document
- Include **alternatives considered** and why they were rejected
- Should be **concise** (1-2 pages maximum)
- Reference code directly for implementation details

## Directory Structure

```
architecture/
├── README.md                              # This file
├── ARCHITECTURE_DOCS_GUIDE.md            # Comprehensive ADR guide
├── NAVIGATION_GUIDE.md                   # How to navigate ADRs
├── adr-template.md                        # Template for new ADRs
└── adrs/                                  # Architectural Decision Records
    ├── 2026-01-23-1-record-architecture-decisions.md
    ├── 2026-01-23-2-explicit-base-branch-tracking.md
    ├── 2026-01-23-3-centralized-workspace-context-storage.md
    ├── 2026-01-23-4-auto-merge-multi-parent-dependencies.md
    ├── 2026-01-23-5-decorator-based-context-validation.md
    ├── 2026-01-23-6-config-driven-agent-management.md
    ├── 2026-01-25-7-research-deliverables-separation.md
    ├── 2026-01-25-8-deterministic-csv-schema-enforcement.md
    ├── 2026-01-26-9-worktree-cleanup-at-merge-not-eager.md
    ├── 2026-01-27-10-per-feature-mission-selection.md
    ├── 2026-01-27-11-dual-repository-pattern.md
    ├── 2026-01-27-12-two-branch-strategy-for-saas-transformation.md
    ├── 2026-01-29-13-target-branch-routing-for-status-commits.md
    ├── 2026-01-29-14-explicit-metadata-fields-over-implicit-defaults.md
    ├── 2026-01-29-15-merge-first-suggestion-for-completed-dependencies.md
    └── 2026-01-29-16-rich-json-outputs-for-agent-commands.md
```

**Note:** Implementation details are documented in code, tests, and docstrings. ADRs focus on decisions and link directly to code.

## Naming Conventions

### ADRs (Architectural Decision Records)

**Location:** `architecture/adrs/`

**Format:** `YYYY-MM-DD-N-descriptive-title-with-dashes.md`

**Rules:**
- **Date prefix:** Use date when decision was accepted (YYYY-MM-DD)
- **Sequential number:** N is 1, 2, 3... for decisions on that day
- **Lowercase:** All letters in lowercase
- **Hyphens:** Use hyphens to separate words, not underscores
- **Present tense verbs:** Use imperative/present tense (e.g., "use", "adopt", "implement")
- **Descriptive:** Title should clearly indicate the decision topic

**Examples:**
- `2026-01-23-1-record-architecture-decisions.md`
- `2026-01-23-2-explicit-base-branch-tracking.md`
- `2026-02-15-1-use-sqlite-for-local-storage.md`
- `2026-02-15-2-adopt-react-for-ui-framework.md`

### Where to Put Implementation Details

ADRs should be **concise decision records** (1-2 pages). Put detailed implementation information in:

- **Code comments/docstrings** - For technical implementation details
- **Test files** - For usage examples and edge cases
- **`docs/` directory** - For user-facing documentation
- **`kitty-specs/` directory** - For feature specs (using spec-kitty's own workflow)
- **ADR "More Information" section** - Brief summary with code references

## When to Create an ADR

Create an ADR for every **architecturally significant decision**, including:

### Structure Decisions
- Choosing architectural patterns (microservices, monolith, layered architecture)
- Deciding on module/package organization
- Selecting component interaction patterns

### Technology Decisions
- Choosing frameworks or libraries (React vs Vue, SQLite vs PostgreSQL)
- Selecting build tools or development environments
- Adopting new programming languages or paradigms

### Non-Functional Requirements
- Security approaches (authentication methods, encryption strategies)
- Performance optimizations (caching strategies, database indexing)
- Scalability patterns (horizontal vs vertical scaling)

### Integration Decisions
- API design choices (REST vs GraphQL, versioning strategy)
- External service integrations
- Data exchange formats

### Process Decisions
- Development workflows (git branching strategy, release process)
- Testing strategies (unit vs integration test ratios, mocking approaches)
- Deployment approaches (CI/CD pipeline design)

### When NOT to Create an ADR
- Implementation details that don't affect architecture
- Temporary workarounds or tactical decisions
- Routine bug fixes or minor refactorings
- Decisions that can be easily reversed without significant impact

## Current Documentation

### ADRs (Architectural Decision Records)

| ADR | Title | Status | Topic |
|-----|-------|--------|-------|
| [2026-01-23-1](adrs/2026-01-23-1-record-architecture-decisions.md) | Record Architecture Decisions | Accepted | Documentation Process |
| [2026-01-23-2](adrs/2026-01-23-2-explicit-base-branch-tracking.md) | Explicit Base Branch Tracking | Accepted | Git Repository Management |
| [2026-01-23-3](adrs/2026-01-23-3-centralized-workspace-context-storage.md) | Centralized Workspace Context Storage | Accepted | Git Repository Management |
| [2026-01-23-4](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md) | Auto-Merge Multi-Parent Dependencies | Accepted | Git Repository Management |
| [2026-01-23-5](adrs/2026-01-23-5-decorator-based-context-validation.md) | Decorator-Based Context Validation | Accepted | Git Repository Management |
| [2026-01-23-6](adrs/2026-01-23-6-config-driven-agent-management.md) | Config-Driven Agent Management | Accepted | Agent Management |
| [2026-01-25-7](adrs/2026-01-25-7-research-deliverables-separation.md) | Research Deliverables Separation | Accepted | Mission System |
| [2026-01-25-8](adrs/2026-01-25-8-cli-first-command-interface.md) | CLI-First Command Interface | Accepted | CLI/Automation |
| [2026-01-25-8](adrs/2026-01-25-8-deterministic-csv-schema-enforcement.md) | Deterministic CSV Schema Enforcement | Accepted | Research Mission |
| [2026-01-26-9](adrs/2026-01-26-9-worktree-cleanup-at-merge-not-eager.md) | Worktree Cleanup at Merge, Not Eager | Accepted | Git Repository Management |
| [2026-01-27-10](adrs/2026-01-27-10-per-feature-mission-selection.md) | Per-Feature Mission Selection | Accepted | Mission System |
| [2026-01-27-11](adrs/2026-01-27-11-dual-repository-pattern.md) | Dual-Repository Pattern for Private Dependency | Accepted | Dependency Management |
| [2026-01-27-12](adrs/2026-01-27-12-two-branch-strategy-for-saas-transformation.md) | Two-Branch Strategy for SaaS Transformation | Accepted | Release Strategy |
| [2026-01-29-13](adrs/2026-01-29-13-target-branch-routing-for-status-commits.md) | Target Branch Routing for Status Commits | Accepted | Git Repository Management |
| [2026-01-29-14](adrs/2026-01-29-14-explicit-metadata-fields-over-implicit-defaults.md) | Explicit Metadata Fields Over Implicit Defaults | Accepted | Metadata & Configuration |
| [2026-01-29-15](adrs/2026-01-29-15-merge-first-suggestion-for-completed-dependencies.md) | Merge-First Suggestion for Completed Dependencies | Accepted | Git Repository Management |
| [2026-01-29-16](adrs/2026-01-29-16-rich-json-outputs-for-agent-commands.md) | Rich JSON Outputs for Agent Commands | Accepted | Agent Experience |

### By Topic

**Git Repository Management** (ADRs 2, 4, 9, 13, 15)
- Base branch visibility and tracking (ADR-2)
- Multi-parent dependency handling (ADR-4, ADR-15)
- Worktree lifecycle management (ADR-9)
- Dual-branch status routing (ADR-13)
- Runtime context enforcement (ADR-5)

**Metadata & Configuration** (ADRs 3, 6, 14)
- Workspace context storage (ADR-3)
- Config-driven agent selection (ADR-6)
- Explicit metadata fields (ADR-14)

**Agent Experience** (ADRs 5, 16)
- Context validation (ADR-5)
- Rich JSON outputs (ADR-16)

**Multi-Product Strategy** (ADRs 10, 11, 12)
- Per-feature missions (ADR-10)
- Private dependencies (ADR-11)
- Two-branch development (ADR-12)

**Mission System** (ADRs 7, 8)
- Research deliverables (ADR-7)
- CSV schema enforcement (ADR-8)

**Status:** Core architecture documented ✅ (49 tests covering latest ADRs)

**Implementation:** See code references in each ADR

## How to Create a New ADR

### Step 1: Determine the Filename

Use today's date and find the next sequential number for that date.

```bash
# Check for existing ADRs today
ls architecture/adrs/ | grep "$(date +%Y-%m-%d)"
# If you see 2026-01-23-1, 2026-01-23-2, your next is 2026-01-23-3
# If no ADRs today, start with -1
```

### Step 2: Copy the Template

```bash
# Format: YYYY-MM-DD-N-your-decision-title.md
cp architecture/adr-template.md architecture/adrs/2026-01-23-3-your-decision-title.md
```

### Step 3: Fill Out the ADR

Use the template structure, ensuring you:

1. **Write a clear title** - Should be a noun phrase describing the decision
2. **Set status to "Proposed"** - Start all ADRs as "Proposed"
3. **Add context** - Explain the problem and why this decision matters
4. **List decision drivers** - What factors influenced this decision?
5. **Document all options** - Include rejected alternatives with pros/cons
6. **State the decision** - Be clear and assertive about the chosen option
7. **Document consequences** - Both positive and negative impacts
8. **Add confirmation criteria** - How will you validate this was the right choice?
9. **Keep it concise** - 1-2 pages maximum; link to code for details

### Step 4: Review Process

1. **Create a draft** - Initial version for team review
2. **Team review** - Allocate 10-15 minutes for team to read and comment
3. **Iterate** - Address feedback and questions
4. **Accept** - Once approved, change status to "Accepted" and add date
5. **Commit** - ADR becomes immutable once accepted

### Step 5: Update This README

Add an entry in the "Current Documentation" table above.

## Where to Put Implementation Details

ADRs should remain **concise** (1-2 pages). Put detailed implementation information in:

- **Code files** - Docstrings, comments, type hints
- **Test files** - Usage examples, edge cases
- **`docs/` directory** - User-facing documentation (tutorials, how-to guides)
- **`kitty-specs/` directory** - Feature specs if using spec-kitty workflow
- **Code references in ADRs** - Link directly to relevant code files

## ADR Best Practices

### Writing Good ADRs

1. **One Decision Per ADR** - If multiple decisions, create separate ADRs
2. **Keep It Concise** - Aim for 1-2 pages maximum
3. **Focus on "Why"** - Explain reasoning and tradeoffs, not implementation details
4. **Include Rejected Options** - Document why alternatives were not chosen
5. **Be Assertive** - State decisions clearly and confidently
6. **Immutable Once Accepted** - Don't edit accepted ADRs; supersede with new ones

### ADR Lifecycle

1. **Draft** - Create ADR using template, status = "Proposed"
2. **Review** - Team reviews (10-15 minutes allocated)
3. **Iterate** - Address feedback and questions
4. **Accept** - Change status to "Accepted", add date
5. **Commit** - ADR becomes immutable
6. **Supersede** (if needed) - Create new ADR, update old ADR status to "Superseded"

### When to Create an ADR

Create ADRs for **architecturally significant decisions** including:

**Structure:**
- Architectural patterns (microservices, monolith, layered)
- Module/package organization
- Component interaction patterns

**Technology:**
- Framework or library choices (React vs Vue, SQLite vs PostgreSQL)
- Build tools or development environments
- Programming language or paradigm adoption

**Non-Functional Requirements:**
- Security approaches (authentication, encryption)
- Performance optimizations (caching, indexing)
- Scalability patterns

**Integration:**
- API design (REST vs GraphQL, versioning)
- External service integrations
- Data exchange formats

**Process:**
- Development workflows (git strategy, release process)
- Testing strategies (unit vs integration ratios)
- Deployment approaches (CI/CD design)

### When NOT to Create an ADR

- Implementation details that don't affect architecture
- Temporary workarounds or tactical decisions
- Routine bug fixes or minor refactorings
- Decisions easily reversed without significant impact

## General Documentation Best Practices

1. **Keep It Current**: Update specs as implementations evolve (ADRs remain immutable)
2. **Link from Code**: Reference ADRs/specs in code comments for major components
3. **Version Control**: All architecture docs committed to git
4. **Peer Review**: Significant decisions reviewed before implementation

## Related Documentation

- [`ARCHITECTURE_DOCS_GUIDE.md`](ARCHITECTURE_DOCS_GUIDE.md) - **Start here!** Comprehensive guide to the architecture documentation system
- [`docs/`](../docs/) - User-facing documentation and guides
- [`kitty-specs/`](../kitty-specs/) - Feature specifications (using Spec Kitty's own workflow)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) - Contribution guidelines
- [`CLAUDE.md`](../CLAUDE.md) - Project instructions for AI agents

## Quick Links

### For Contributors
- **"How do I create an ADR?"** → See [How to Create a New ADR](#how-to-create-a-new-adr) above
- **"What's the difference between ADR and spec?"** → See [ARCHITECTURE_DOCS_GUIDE.md](ARCHITECTURE_DOCS_GUIDE.md)
- **"When should I create an ADR?"** → See [When to Create an ADR](#when-to-create-an-adr) above

### For Readers
- **"Why was this decision made?"** → Read the relevant ADR in `adrs/`
- **"How does this feature work?"** → Read the spec in `specs/`
- **"What's the complete picture?"** → Read spec overview + related ADRs

## Questions?

For questions about architectural decisions or to propose new designs:
1. Review existing ADRs in `architecture/adrs/`
2. Check implementation specs in `architecture/specs/`
3. Read [ARCHITECTURE_DOCS_GUIDE.md](ARCHITECTURE_DOCS_GUIDE.md) for comprehensive guidance
4. Open a discussion or issue on GitHub
