# Architecture Documentation Navigation Guide

## 🗺️ Where to Start?

### New to Spec Kitty Architecture?

**Start here:** [`README.md`](README.md)
- Quick overview of what's in this directory
- Table of all ADRs with topics
- Quick reference for common questions

**Then read:** [`ARCHITECTURE_DOCS_GUIDE.md`](ARCHITECTURE_DOCS_GUIDE.md)
- Complete guide to ADRs
- When to create an ADR
- How to write good ADRs
- Maintenance and lifecycle

---

## 🎯 What Do You Want to Do?

### Understand Why a Decision Was Made

**→ Read the relevant ADR in [`adrs/`](adrs/)**

**Example questions:**
- "Why do we track base branch in frontmatter?" → [ADR-2026-01-23-2](adrs/2026-01-23-2-explicit-base-branch-tracking.md)
- "Why auto-merge instead of manual merge?" → [ADR-2026-01-23-4](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md)
- "Why use decorators for validation?" → [ADR-2026-01-23-5](adrs/2026-01-23-5-decorator-based-context-validation.md)
- "Why do feature planning artifacts live on `feature_branch` instead of `target_branch`?" → [ADR-2026-03-20-1](adrs/2026-03-20-1-separate-feature-planning-branch-from-merge-target.md)

**What you'll find:**
- Problem being solved
- Options that were considered
- Why the chosen option was selected
- Tradeoffs that were accepted

---

### Understand How a Feature Works

**→ Read the ADR, then follow code references**

**Example questions:**
- "How does auto-merge work?" → Read [ADR-2026-01-23-4](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md), then check `src/specify_cli/core/multi_parent_merge.py`
- "What's the API for workspace context?" → Read [ADR-2026-01-23-3](adrs/2026-01-23-3-centralized-workspace-context-storage.md), then check `src/specify_cli/workspace_context.py`
- "How do I use context validation decorators?" → Read [ADR-2026-01-23-5](adrs/2026-01-23-5-decorator-based-context-validation.md), then check code references

**What you'll find:**
- **In ADR:** Decision context, alternatives, tradeoffs, brief implementation summary
- **In code:** Detailed implementation, API, docstrings
- **In tests:** Usage examples, edge cases

---

### Get Complete Picture of a Feature

**→ Read all related ADRs, then explore code**

**Example: Git Repository Management**

**Step 1:** Read ADRs (the decisions)
1. [ADR-2026-01-23-2](adrs/2026-01-23-2-explicit-base-branch-tracking.md) - Why explicit tracking?
2. [ADR-2026-01-23-3](adrs/2026-01-23-3-centralized-workspace-context-storage.md) - Why centralized storage?
3. [ADR-2026-01-23-4](adrs/2026-01-23-4-auto-merge-multi-parent-dependencies.md) - Why auto-merge?
4. [ADR-2026-01-23-5](adrs/2026-01-23-5-decorator-based-context-validation.md) - Why decorators?
5. [ADR-2026-03-20-1](adrs/2026-03-20-1-separate-feature-planning-branch-from-merge-target.md) - Why separate planning state from final merge target?

**Step 2:** Explore implementation
- Check code references in each ADR
- Read docstrings in referenced files
- Run tests to see examples
- Experiment with APIs

**Step 3:** Understand relationships
- See how ADRs reference each other
- Understand how decisions build on each other
- Follow code references to see complete implementation

---

### Create New Documentation

**For an architectural decision:**

**→ Use [`adr-template.md`](adr-template.md)**

```bash
# 1. Find next ADR number
ls architecture/adrs/ | sort | tail -1
# If last today is 2026-01-23-5, next is 2026-01-23-6 (or start with 1 for new date)

# 2. Copy template
cp architecture/adr-template.md architecture/adrs/2026-02-15-1-your-decision.md

# 3. Fill it out (focus on why, not how)
# 4. Follow the process in README.md
```

**For implementation details:**

**→ Document in code, not in architecture/**

- Comprehensive docstrings
- Code comments for complex logic
- Test files for usage examples
- User guides in docs/ if needed

---

## 📚 Documentation Decision Tree

```
Do you need to document something?
│
├─ Is it an ARCHITECTURAL DECISION?
│  (Choosing between significant alternatives)
│  │
│  YES → Create ADR
│  │     - Use adr-template.md
│  │     - Focus on why, not how
│  │     - Include alternatives
│  │     - 1-2 pages max
│  │     - Reference code in "More Information"
│  │
│  NO → Continue below
│
├─ Is it IMPLEMENTATION DETAILS?
│  (API, algorithms, data structures)
│  │
│  YES → Document in code
│  │     - Docstrings (comprehensive)
│  │     - Type hints
│  │     - Code comments
│  │     - Test examples
│  │
│  NO → Continue below
│
├─ Is it USER DOCUMENTATION?
│  (How to use a feature)
│  │
│  YES → Add to docs/ directory
│  │     - Tutorials, how-to guides
│  │     - Reference documentation
│  │     - Explanations
│  │
│  NO → Continue below
│
└─ Is it CODE-LEVEL DETAIL?
   (Implementation specifics, edge cases)
   │
   YES → Document in code comments/docstrings
         - Explain why, not what
         - Document edge cases
         - Note tradeoffs made
```

---

## 🔍 Finding What You Need

### By Topic

**Git/VCS:**
- ADRs: 0002, 0003, 0004, 0005, 0013, 0017, 2026-03-20-1
- Code: `src/specify_cli/workspace_context.py`, `src/specify_cli/core/multi_parent_merge.py`, `src/specify_cli/core/context_validation.py`

**Future topics will be organized similarly**

### By Question Type

**"Why did we choose X?"**
→ Read relevant ADR in `adrs/`

**"How does X work?"**
→ Read ADR for overview, then check code references

**"How do I use X?"**
→ Check ADR "More Information", then read docstrings and tests

**"What are the tradeoffs of X?"**
→ Read ADR "Consequences" and "Pros and Cons" sections

---

## 📖 Reading Recommendations

### For New Contributors

**Day 1:** Read all ADRs (5 documents, ~30 minutes)
- Understand key architectural decisions
- Learn why the system is designed this way

**Day 2:** Skim spec overviews
- Get sense of major features
- Identify areas relevant to your work

**Ongoing:** Reference as needed
- Check ADRs before making architectural changes
- Read specs when working on specific features

### For AI Agents

**Before implementing features:**
1. Search ADRs for relevant decisions
2. Read specs for technical details
3. Reference code locations listed in docs
4. Follow patterns established in ADRs

**When creating new features:**
1. Check if architectural decision needed
2. Create ADR if significant choice required
3. Create spec for complex implementations
4. Link new docs from existing ADRs/specs

---

## 🛠️ Maintenance

### Keeping Documentation Current

**ADRs:**
- **Immutable once accepted** - never edit
- If decision changes → Create new ADR superseding the old one
- Update old ADR status to "Superseded" with link to new ADR
- Add date to status change

**Code/Tests:**
- **Update as implementation evolves**
- Keep docstrings current
- Update test examples
- Document breaking changes in code comments

**README:**
- **Update when adding new ADRs**
- Keep ADR table current (add new rows)
- Update topic groupings

---

## Quick Links

- [Main README](README.md) - Start here
- [Complete Guide](ARCHITECTURE_DOCS_GUIDE.md) - Comprehensive ADR guide
- [ADR Template](adr-template.md) - Template for new ADRs
- [All ADRs](adrs/) - Browse all architectural decisions

---

**Questions?** See [README.md](README.md) or [ARCHITECTURE_DOCS_GUIDE.md](ARCHITECTURE_DOCS_GUIDE.md)
