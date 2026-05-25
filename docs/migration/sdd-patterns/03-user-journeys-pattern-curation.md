# User Journeys: Pattern Curation Flow

_Migration research document — from concept to website, and which agents to use_
_Date: 2025-05-25_

## 1. Overview

This document describes the end-to-end user journeys for curating patterns in the
penguin-pragmatic-patterns repository, from initial concept through to published website
content. Each journey identifies the human and agent actors involved, the artifacts produced,
and how the flow maps to spec-kitty mission phases.

## 2. Journey Map: New Practice Pattern

### Actors

| Actor | Type | Role | Agent Profile |
|-------|------|------|---------------|
| **Curator (human)** | HiC | Decides what patterns to include | — |
| **Researcher** | Agent | Validates sources, expands bibliography | sdd-researcher |
| **Curator** | Agent | Ensures conceptual coherence across collection | sdd-curator |
| **Writer-Editor** | Agent | Authors and polishes content | sdd-writer-editor |
| **Lexical** | Agent | Manages terminology, validates tone | sdd-lexical |
| **Diagrammer** | Agent | Creates PlantUML visualizations | sdd-diagrammer |
| **Synthesizer** | Agent | Reviews cross-pattern coherence | sdd-synthesizer |
| **Build Automation** | Agent | Runs validation and deployment | (project-local) |

### Phase 1: Discovery (spec-kitty: specify)

```
Human identifies a pattern worth documenting
    │
    ├─→ Opens GitHub Issue using pattern proposal template
    │   └─ OR starts discussion in GitHub Discussions
    │
    ├─→ [Researcher agent] validates the concept:
    │   ├─ Searches existing bibliography for prior art
    │   ├─ Checks if pattern overlaps with existing content
    │   └─ Identifies key references and source materials
    │
    └─→ [Curator agent] evaluates fit:
        ├─ Does it align with repository philosophy?
        ├─ Which category? (learning/productivity/communication/software-development)
        └─ Is there audience demand?
```

**Artifacts produced:**
- GitHub Issue or Discussion thread
- Initial reference list
- Category assignment decision

**Spec-kitty mapping:** This is the `specify` action. The discovery interview questions
would be:
- What problem does this pattern address?
- In what contexts is it applicable?
- What sources support it?
- Which content type best fits? (practice/concept/primer)

### Phase 2: Research (spec-kitty: plan)

```
[Researcher agent] deep-dives into source material
    │
    ├─→ Validates author credentials and publication reputation
    ├─→ Gathers 3-5 primary references
    ├─→ Creates bibliography.toml entries:
    │   │
    │   │  [[books]]
    │   │  id = "uuid-here"
    │   │  title = "Source Title"
    │   │  authors = ["Author Name"]
    │   │  publisher = "Publisher"
    │   │  year = "2024"
    │   │  link = "https://..."
    │   │  levels = ["intermediate"]
    │   │  tags = ["relevant", "tags"]
    │   │
    │   └─→ Runs: bash src/scripts/ops/generate_books.sh
    │
    └─→ [Lexical agent] checks terminology:
        ├─ Are proposed tags in glossary.toml?
        ├─ Do any new terms need glossary entries?
        └─ Are there alias conflicts with existing terms?
```

**Artifacts produced:**
- Bibliography entries in `data/bibliography.toml`
- Generated book pages in `content/books/`
- Glossary entries for new terms (if needed)
- Research notes (optional, in working directory)

**Spec-kitty mapping:** This is the `plan` action. The research phase corresponds to
spec-kitty's Phase-0 research documents where unknowns are resolved before implementation.

### Phase 3: Drafting (spec-kitty: implement)

```
[Writer-Editor agent] creates the pattern content
    │
    ├─→ Step 1: Template Selection
    │   ├─ Practice → docs/templates/TEMPLATE_PRACTICE.md
    │   ├─ Concept → docs/templates/TEMPLATE_CONCEPT.md
    │   └─ Primer  → docs/templates/primers/TEMPLATE_PROGRAMMING_PRIMER.md
    │
    ├─→ Step 2: Metadata Generation
    │   ├─ UUID: uuidgen
    │   ├─ Title, author, description, summary
    │   ├─ Categories (exactly one of: learning/productivity/communication/software-development)
    │   ├─ Tags (MUST exist in data/glossary.toml)
    │   ├─ AMMERSE evaluation (7 dimensions, each with delta + rationale)
    │   ├─ Publication date
    │   ├─ Related concepts and practices (by UUID cross-reference)
    │   └─ Further exploration entries (biblio references + raw links)
    │
    ├─→ Step 3: Content Authoring
    │   ├─ Problem Statement — what pain point does this address?
    │   ├─ Intent — what is the desired outcome?
    │   ├─ Solution — core idea and how to apply it
    │   ├─ Contextual Forces
    │   │   ├─ Enablers — factors that increase viability
    │   │   └─ Deterrents — factors that decrease viability
    │   ├─ Rationale — reasoning behind the pattern
    │   ├─ Consequences — what changes after applying (incl. unintended effects)
    │   └─ Examples / Use Cases / Testimonials
    │
    ├─→ Step 4: Visualization
    │   └─→ [Diagrammer agent] creates PlantUML diagrams where applicable
    │
    └─→ Step 5: Glossary Synchronization
        └─→ [Lexical agent] verifies all tags exist in glossary.toml
            ├─ Adds missing terms with proper domain/description/aliases/references
            └─ Updates contextive glossary files (.contextive/*.glossary.yml)
```

**Artifacts produced:**
- Pattern markdown file in `content/practices/` (or `content/concepts/`, etc.)
- Updated `data/glossary.toml` (if new terms added)
- Updated `.contextive/*.glossary.yml` (regenerated)
- PlantUML diagram files (if applicable)
- Updated image assets (if applicable)

**Example practice frontmatter:**
```toml
+++
title = "Pattern Name"
author = "Stijn Dejongh"
problem = "One-line problem statement"
description = "One-paragraph description"
summary = "SEO-friendly summary paragraph"
categories = ["software development"]
tags = ["Clean Code", "Testing", "Design"]
uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
aliases = ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
outputs = ['html', 'json']
ammerse = [
  {name = "agile", delta = "0.3", rationale = "..."},
  {name = "minimal", delta = "0.5", rationale = "..."},
  {name = "maintainable", delta = "0.4", rationale = "..."},
  {name = "environmental", delta = "0.2", rationale = "..."},
  {name = "reachable", delta = "0.1", rationale = "..."},
  {name = "solvable", delta = "0.8", rationale = "..."},
  {name = "extensible", delta = "0.3", rationale = "..."}
]
pubdate = "2025-05-25"
image = "practices/pattern_name"
related_concepts = []
related_practices = ["uuid-of-related-practice"]
further_exploration = [
  {type="biblio", id="uuid-of-book"},
  {type="raw", author="Author", year="2024", title="Title", site="Site", link="https://..."}
]
+++
```

### Phase 4: Review (spec-kitty: review)

```
Content enters review cycle
    │
    ├─→ Step 1: Branch and PR
    │   ├─ Create feature branch from develop
    │   └─ Open PR with description and checklist
    │
    ├─→ Step 2: Automated Validation
    │   ├─ TOML front matter syntax check
    │   ├─ Tag existence verification (all tags in glossary.toml)
    │   ├─ UUID uniqueness check
    │   ├─ Required section presence
    │   │   ├─ Practices: Problem/Intent/Solution/Consequences
    │   │   ├─ Concepts: Definition/Background/Examples
    │   │   └─ Primers: Philosophy/Syntax/Tooling/Testing
    │   └─ Image reference validation
    │
    ├─→ Step 3: Tone and Style Review
    │   └─→ [Lexical agent] runs LEX analysis:
    │       ├─ Score each voice characteristic against tone map
    │       ├─ Flag deviations below 85% threshold
    │       ├─ Check for prescriptive language ("must", "should", "always")
    │       ├─ Verify "when NOT to use" clarifications present
    │       └─ Generate LEX_DELTAS report
    │
    ├─→ Step 4: Content Coherence Review
    │   └─→ [Synthesizer agent] checks:
    │       ├─ Does this pattern complement existing collection?
    │       ├─ Are cross-references accurate?
    │       ├─ Is terminology consistent with glossary?
    │       └─ Are AMMERSE deltas reasonable given the pattern's nature?
    │
    ├─→ Step 5: Preview Deployment
    │   └─ GitHub Actions deploys to GitHub Pages preview
    │       URL: https://sddevelopment-be.github.io/penguin-pragmatic-patterns/
    │
    └─→ Step 6: Human Review
        ├─ Visual inspection of rendered content
        ├─ Readability and flow assessment
        └─ Final approval or revision request
```

**Artifacts produced:**
- PR with review comments
- LEX analysis report (if deviations found)
- Preview deployment URL
- Revision commits (if changes requested)

### Phase 5: Publication (spec-kitty: accept + merge)

```
Pattern approved and published
    │
    ├─→ Step 1: Merge to develop
    │   └─ Triggers GitHub Pages preview update
    │
    ├─→ Step 2: Merge to main
    │   └─ Triggers production build via GitHub Actions
    │       ├─ hugo --gc --minify --buildDrafts=false
    │       └─ Artifact uploaded for Netlify deployment
    │
    ├─→ Step 3: Netlify Publication
    │   └─ Live at: https://patterns.sddevelopment.be
    │
    └─→ Step 4: Post-Publication
        └─→ [Curator agent] updates:
            ├─ Collection index pages (if category changed)
            ├─ Tag pages (auto-generated by Hugo)
            └─ Cross-reference links in related patterns
```

**Final artifacts:**
- Published pattern page on production website
- Updated tag/category index pages
- Updated cross-reference links

## 3. Journey Map: Glossary Term Addition

### Trigger

A new term is needed because:
- A new pattern introduces domain-specific vocabulary
- A tag is required that doesn't exist in `glossary.toml`
- A reader or contributor requests a term clarification

### Flow

```
[Lexical agent] receives glossary addition request
    │
    ├─→ Step 1: Term Research
    │   ├─ Check existing glossary for synonyms/overlaps
    │   ├─ Verify no alias conflicts
    │   └─ Research authoritative definition sources
    │
    ├─→ Step 2: Entry Authoring
    │   │
    │   │  [[terminology]]
    │   │  name = "Term Name"
    │   │  abbreviation = "TN"
    │   │  domain = "software development"
    │   │  description = """
    │   │  Clear, concise definition following LEX style rules.
    │   │  Functional over compositional. No circular definitions.
    │   │  """
    │   │  aliases = ["Synonym 1", "Synonym 2"]
    │   │  references = [
    │   │    { title = "Source", link = "https://..." }
    │   │  ]
    │   │
    │   └─→ Add to data/glossary.toml
    │
    ├─→ Step 3: Contextive Update
    │   └─ Regenerate .contextive/*.glossary.yml files
    │       (auto-generated from glossary.toml by domain)
    │
    ├─→ Step 4: Hugo Content
    │   └─ Hugo auto-generates tag page at /tags/<term-name>/
    │
    └─→ Step 5: Validation
        ├─ Verify TOML syntax
        ├─ Verify no duplicate names
        └─ Verify domain assignment consistency
```

### Spec-Kitty Glossary Mapping

In spec-kitty's scoped glossary model, this flow would:
1. Create a `team_domain` scoped entry
2. Set status to `candidate` (requires HiC promotion to `canonical`)
3. Set confidence to initial value (e.g., 0.8)
4. Add `see_also` cross-references to related terms

## 4. Journey Map: LEX Analysis Cycle

### Trigger

Periodic style review, or as part of pattern review, or after batch content updates.

### Flow

```
[Lexical agent] initiates LEX analysis
    │
    ├─→ Step 1: Tone Map Scoring
    │   └─ For each content file:
    │       ├─ Score: Calm (target: 94%)
    │       ├─ Score: Clear (target: 91%)
    │       ├─ Score: Sincere (target: 96%)
    │       ├─ Score: Humble (target: 93%)
    │       ├─ Score: Collaborative (target: 90%)
    │       ├─ Score: Practical (target: 92%)
    │       └─ Score: Balanced (target: 95%)
    │
    ├─→ Step 2: Style Rule Compliance
    │   ├─ Active voice usage rate
    │   ├─ Prescriptive language detection ("must"/"should"/"always")
    │   ├─ Paragraph length check (max 3-4 sentences)
    │   ├─ Heading hierarchy validation
    │   └─ Citation format compliance (IEEE)
    │
    ├─→ Step 3: Delta Generation
    │   └─ LEX_DELTAS.md report:
    │       ├─ File-by-file deviation list
    │       ├─ Priority classification (high/medium/low)
    │       ├─ Before/after suggestions
    │       └─ Aggregate compliance metrics
    │
    └─→ Step 4: Remediation
        ├─→ [Writer-Editor agent] applies high-priority fixes
        ├─→ Medium-priority fixes queued for next review cycle
        └─→ Low-priority fixes documented for future reference
```

## 5. Journey Map: Bibliography Expansion

### Trigger

A new reference source is identified, either during pattern research or through community
contribution.

### Flow

```
[Researcher agent] identifies new reference
    │
    ├─→ Step 1: Source Validation
    │   ├─ Verify author credentials
    │   ├─ Check publication reputation
    │   ├─ Confirm accuracy of claims
    │   └─ Assess relevance to collection
    │
    ├─→ Step 2: Entry Creation
    │   ├─ Generate UUID: uuidgen
    │   ├─ Fill all bibliography.toml fields
    │   ├─ Assign appropriate levels (beginner/intermediate/advanced)
    │   ├─ Assign tags (MUST exist in glossary.toml)
    │   └─ Write description (neutral, concise)
    │
    ├─→ Step 3: Page Generation
    │   └─ Run: bash src/scripts/ops/generate_books.sh data/bibliography.toml
    │       └─ Generates content/books/<uuid>.md
    │
    ├─→ Step 4: Cross-Linking
    │   └─ Update relevant patterns' further_exploration:
    │       {type="biblio", id="<new-uuid>"}
    │
    └─→ Step 5: Validation
        ├─ Verify TOML syntax
        ├─ Verify link accessibility
        └─ Verify tag existence in glossary
```

## 6. Spec-Kitty Mission Mapping

### Complete Phase Alignment

| SDD Patterns Phase | Spec-Kitty Action | Lane Transition | Agent Profiles Active |
|--------------------|-------------------|----------------|----------------------|
| Discovery | specify | planned → claimed | Researcher, Curator |
| Research | plan | claimed → in_progress | Researcher, Lexical |
| Template Selection | plan | (within in_progress) | Curator |
| Content Authoring | implement | in_progress | Writer-Editor, Diagrammer |
| Metadata Assignment | implement | (within in_progress) | Lexical, Curator |
| Glossary Sync | implement | (within in_progress) | Lexical |
| Validation | review | in_progress → for_review | (automated) |
| Tone Review | review | for_review → in_review | Lexical, Synthesizer |
| Human Approval | accept | in_review → approved | HiC |
| Publication | merge | approved → done | Build Automation |

### Spec-Kitty Commands for Pattern Curation

```bash
# Initialize a pattern curation mission
spec-kitty specify "New practice: Fail Fast Feedback"

# Plan the research and structure
spec-kitty plan

# Generate work packages for the curation steps
spec-kitty tasks

# Implement the pattern content
spec-kitty implement WP01   # Research and bibliography
spec-kitty implement WP02   # Content authoring
spec-kitty implement WP03   # Glossary synchronization
spec-kitty implement WP04   # Diagram creation (if applicable)

# Review cycle
spec-kitty review WP01
spec-kitty review WP02
spec-kitty review WP03

# Accept and merge
spec-kitty accept
spec-kitty merge
```

## 7. Agent Collaboration Patterns

### Sequential Handoff

Most common pattern for single-pattern curation:

```
Researcher → Curator → Writer-Editor → Lexical → Synthesizer → (Human Review)
```

### Parallel Lanes

For batch content updates or primer creation:

```
Lane A: Writer-Editor (content authoring)
Lane B: Researcher (bibliography expansion)
Lane C: Diagrammer (visualization creation)
         ↓ merge point
     Lexical (tone + terminology review)
         ↓
     Synthesizer (coherence check)
         ↓
     Human Review
```

### Review Loop

When LEX analysis reveals deviations:

```
Writer-Editor ←→ Lexical (iterative refinement)
                    ↓ (when compliant)
              Synthesizer (final coherence)
                    ↓
              Human Approval
```

## 8. References

- [AGENTS.md](/AGENTS.md) — Agent governance and profiles
- [docs/templates/TEMPLATE_PRACTICE.md](/docs/templates/TEMPLATE_PRACTICE.md) — Practice template
- [docs/templates/TEMPLATE_CONCEPT.md](/docs/templates/TEMPLATE_CONCEPT.md) — Concept template
- [docs/styleguide/LEX_TONE_MAP.md](/docs/styleguide/LEX_TONE_MAP.md) — Tone characteristics
- [docs/styleguide/LEX_STYLE_RULES.md](/docs/styleguide/LEX_STYLE_RULES.md) — Writing rules
- [data/glossary.toml](/data/glossary.toml) — Terminology registry
- [data/bibliography.toml](/data/bibliography.toml) — Reference management
- [spec-kitty status model](https://github.com/Priivacy-ai/spec-kitty/blob/main/docs/status-model.md) — Lane state machine
- [spec-kitty mission types](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/doctrine/missions/) — Mission type profiles
