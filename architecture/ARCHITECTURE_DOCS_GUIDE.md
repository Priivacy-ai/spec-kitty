# Guide to Spec Kitty Architecture Documentation

## Overview

Spec Kitty uses **Architectural Decision Records (ADRs)** to document significant architectural decisions.

ADRs:

- Capture **why** decisions were made, not just what was decided
- Are **immutable** once accepted (preserve decision context over time)
- Are **concise** (1-2 pages maximum)
- **Reference code directly** for implementation details

---

## What Goes in an ADR

### Purpose

ADRs document **architectural decisions** - the significant choices that shape the system.

### Characteristics

- **Concise** - 1-2 pages maximum
- **Focused** - One decision per ADR
- **Immutable** - Once accepted, never edited (supersede with new ADRs)
- **Include alternatives** - Document what was NOT chosen and why
- **Link to code** - Reference implementation directly

### Key Sections

1. **Context** - What problem are we solving? Why does it matter?
2. **Decision Drivers** - What factors influenced the decision?
3. **Considered Options** - What alternatives did we evaluate?
4. **Decision Outcome** - What did we choose and why?
5. **Consequences** - What are the positive and negative impacts?
6. **Pros and Cons** - Detailed analysis of each option
7. **More Information** - Code references, related ADRs

### When to Create an ADR

Create ADRs for **architecturally significant decisions**:

**Technology Choices:**

- Frameworks, libraries, tools
- Build systems, development environments
- Programming language or paradigm adoption

**Architectural Patterns:**

- System structure (monolith vs microservices)
- Component organization (layered, modular, etc.)
- Integration patterns (REST vs GraphQL, event-driven, etc.)

**Non-Functional Requirements:**

- Security approaches (auth methods, encryption)
- Performance optimizations (caching, indexing)
- Scalability patterns (horizontal vs vertical)

**Development Processes:**

- Git workflows, branching strategies
- Testing strategies, CI/CD design
- Release processes

### When NOT to Create an ADR

- Implementation details that don't affect architecture
- Temporary workarounds or tactical decisions
- Routine bug fixes or minor refactorings
- Decisions easily reversed without significant impact

---

## Should I Create an ADR?

**Ask yourself:** "Is this an architecturally significant DECISION?"

### Create an ADR if

- ✅ You're choosing between alternatives (Option A vs Option B)
- ✅ The decision has significant impact on the codebase
- ✅ You want to preserve WHY you chose this approach
- ✅ Future developers might question this choice
- ✅ The decision is unlikely to change frequently
- ✅ The decision affects multiple components or has broad impact

**Example:** "Should we use explicit base branch tracking in frontmatter or derive it at runtime?"
→ **Yes, create ADR** (significant architectural choice)

### Don't Create an ADR if

- ❌ It's just implementation details (put in code comments/docstrings)
- ❌ It's a temporary workaround (document in code or issue tracker)
- ❌ It's easily reversible (no ADR needed)
- ❌ It only affects one small area (code comment sufficient)

**Example:** "Should this function return a tuple or a dataclass?"
→ **No ADR needed** (implementation detail, use best practices)

### Where to Put Detailed Information

ADRs should be **concise** (1-2 pages). For detailed information:

- **Code** - Docstrings, type hints, comments
- **Tests** - Usage examples, edge cases
- **docs/** - User guides, tutorials, how-to
- **kitty-specs/** - Feature specs (if using spec-kitty workflow)
- **ADR "More Information"** - Brief summary + code references

---

## Directory Structure

```
architecture/
│
├── README.md                    # Quick reference and index
├── ARCHITECTURE_DOCS_GUIDE.md  # This guide (comprehensive)
├── NAVIGATION_GUIDE.md         # How to navigate ADRs
│
└── adrs/                        # Architectural Decision Records
    ├── 2026-01-23-1-record-architecture-decisions.md
    ├── 2026-01-23-2-explicit-base-branch-tracking.md
    ├── 2026-01-23-3-centralized-workspace-context-storage.md
    ├── 2026-01-23-4-auto-merge-multi-parent-dependencies.md
    └── 2026-01-23-5-decorator-based-context-validation.md
```

**That's it!** Architecture documentation is just ADRs. Implementation details live in:

- Code (docstrings, comments)
- Tests (usage examples)
- docs/ (user guides)
- kitty-specs/ (feature specs)

ADR template (canonical): `src/doctrine/templates/architecture/adr-template.md`

---

## How to Use ADRs

### For Understanding Decisions

**Read the relevant ADR** in `architecture/adrs/`

ADRs answer:

- What problem were we solving?
- What options did we consider?
- Why did we choose this option?
- What tradeoffs did we accept?

**Example:** "Why do we auto-merge multi-parent dependencies instead of requiring manual merges?"
→ Read [ADR-2026-01-23-4](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md)

### For Understanding Implementation

**Follow code references** in ADR "More Information" section

Each ADR links to:

- Relevant source files
- Test suites
- Related ADRs

**Example:** "How does auto-merge work in detail?"
→ Read ADR-2026-01-23-4, then check `src/specify_cli/core/multi_parent_merge.py`

### For Implementing New Features

1. **Check existing ADRs** - Ensure approach aligns with architectural decisions
2. **Create ADR for key decisions** - Document significant architectural choices
3. **Implement with good documentation** - Docstrings, comments, tests
4. **Reference ADRs** - Link to relevant ADRs in code comments
5. **Update architecture/README.md** - Add new ADR to table

### For Code Reviews

1. **Reference ADRs** - Validate changes align with architectural decisions
2. **Suggest new ADRs** - If review reveals undocumented significant decisions
3. **Check ADR references** - Ensure code matches decisions in ADRs

---

## Example: Git Repository Management ADRs

The git repository management enhancement demonstrates good ADR practice:

### Four Focused ADRs

Each ADR documents **one significant decision**:

1. [**ADR-2026-01-23-2**](adrs/2026-01-23-2-explicit-base-branch-tracking.md)
   - **Decision:** Store base branch in WP frontmatter
   - **Why:** Single source of truth, visible to agents
   - **Alternative rejected:** Runtime derivation (too complex)

2. [**ADR-2026-01-23-3**](adrs/2026-01-23-3-centralized-workspace-context-storage.md)
   - **Decision:** Store context in `.kittify/workspaces/`
   - **Why:** Survives deletion, no merge conflicts
   - **Alternative rejected:** Per-worktree files (lost on deletion)

3. [**ADR-2026-01-23-4**](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md)
   - **Decision:** Auto-merge all dependencies
   - **Why:** Fully deterministic, no manual steps
   - **Alternative rejected:** Manual merge (error-prone)

4. [**ADR-2026-01-23-5**](adrs/2026-01-23-5-decorator-based-context-validation.md)
   - **Decision:** Use decorators for location validation
   - **Why:** Declarative, reusable, can't be removed
   - **Alternative rejected:** Manual guards (verbose, forgettable)

### How to Read Them

**For understanding decisions:**

1. Read relevant ADR (1-2 pages)
2. Understand context, options, and tradeoffs

**For implementation details:**

1. Check "More Information" section in ADR
2. Follow code references
3. Read tests for usage examples
4. Check docstrings for API details

**Reading path:**

```
ADR-2026-01-23-2 (Why explicit tracking?)
    ↓ Code References section
src/specify_cli/workspace_context.py (Implementation)
    ↓ Usage examples
tests/unit/test_base_branch_tracking.py (Tests)
```

---

## Maintaining ADRs

### When Code Changes

**ADRs are immutable** - Never edit an accepted ADR

**If implementation changes:**

- Update code, docstrings, tests
- If decision changes → Create new ADR that supersedes the old one
- Update old ADR status to "Superseded" with link to new ADR

**Example:**

- Auto-merge algorithm optimization → Update code and tests (no ADR change)
- Decide NOT to auto-merge → Create ADR-0006 superseding ADR-2026-01-23-4

### When Adding Features

**If feature requires architectural decision:**

1. Create ADR documenting the decision
2. Keep it concise (1-2 pages)
3. Reference code directly in "More Information"
4. Update architecture/README.md

**If no significant architectural choice:**

- Document in code comments/docstrings
- Add to docs/ if user-facing
- No ADR needed

---

## References

This ADR system follows guidance from:

- [ADR GitHub Organization](https://adr.github.io/) - Templates and examples
- [AWS ADR Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/) - Process guidance
- [Microsoft Azure ADR Guidance](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) - Writing guidelines
- [Joel Parker Henderson's ADR Repository](https://github.com/joelparkerhenderson/architecture-decision-record) - Comprehensive examples

---

## Quick Start

### Creating Your First ADR

```bash
# 1. Find next number
ls architecture/adrs/ | sort | tail -1

# 2. Copy template
cp src/doctrine/templates/architecture/adr-template.md architecture/adrs/2026-02-15-1-your-decision.md

# 3. Fill it out
#    - Keep it concise (1-2 pages)
#    - Focus on why, not how
#    - Include all alternatives considered
#    - Document consequences (positive and negative)

# 4. Submit for review (status: Proposed)
# 5. After approval, set status: Accepted, add date
# 6. Commit (becomes immutable)
# 7. Update architecture/README.md table
```

### For Implementation Details

**Don't create separate spec docs.** Instead:

```python
# In your source file
def create_multi_parent_base(...):
    """Create merge commit combining all dependencies.

    This implements ADR-2026-01-23-4 (Auto-Merge Multi-Parent Dependencies).

    Algorithm:
    1. Sort dependencies for deterministic ordering
    2. Create temp branch from first dependency
    3. Merge remaining dependencies sequentially

    See ADR-2026-01-23-4 for decision rationale and alternatives considered.
    """
    # implementation...
```

---

## Questions?

- **"Should I create an ADR?"** - See "When to Create an ADR" section above
- **"What's the difference between ADR and spec?"** - ADR = why, Spec = how
- **"Can I edit an accepted ADR?"** - No, create new ADR that supersedes it
- **"How detailed should ADRs be?"** - 1-2 pages, focus on decision reasoning
