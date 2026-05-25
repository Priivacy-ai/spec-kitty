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
| Curator (human) | HiC | Decides what patterns to include | — |
| Researcher | Agent | Validates sources, expands bibliography | sdd-researcher |
| Curator | Agent | Ensures conceptual coherence across collection | sdd-curator |
| Writer-Editor | Agent | Authors and polishes content | sdd-writer-editor |
| Lexical | Agent | Manages terminology, validates tone | sdd-lexical |
| Diagrammer | Agent | Creates PlantUML visualizations | sdd-diagrammer |
| Synthesizer | Agent | Reviews cross-pattern coherence | sdd-synthesizer |
| Build Automation | Agent | Runs validation and deployment | (project-local) |

### Phase 1: Discovery (spec-kitty: specify)

Human identifies a pattern worth documenting.
- Opens GitHub Issue using pattern proposal template (or starts discussion)
- Researcher agent validates: searches bibliography, checks overlap, identifies references
- Curator agent evaluates fit: alignment with philosophy, category, audience demand

Artifacts: GitHub Issue/Discussion, initial reference list, category assignment

### Phase 2: Research (spec-kitty: plan)

Researcher agent deep-dives into source material.
- Validates author credentials and publication reputation
- Gathers 3-5 primary references
- Creates bibliography.toml entries with UUID
- Lexical agent checks terminology: tags in glossary, new terms needed, alias conflicts

Artifacts: bibliography entries, generated book pages, glossary entries

### Phase 3: Drafting (spec-kitty: implement)

Writer-Editor agent creates content.
1. Template Selection (practice/concept/primer)
2. Metadata Generation (UUID, title, categories, tags, AMMERSE, related items)
3. Content Authoring (Problem/Intent/Solution/Forces/Rationale/Consequences/Examples)
4. Visualization (Diagrammer creates PlantUML diagrams)
5. Glossary Synchronization (Lexical verifies all tags exist)

Artifacts: pattern markdown, updated glossary, contextive files, diagrams

### Phase 4: Review (spec-kitty: review)

1. Branch and PR creation
2. Automated validation (front matter, tags, UUID, sections, images)
3. LEX tone and style review (score voice characteristics, flag deviations)
4. Content coherence review by Synthesizer
5. Preview deployment to GitHub Pages
6. Human review (visual inspection, readability, approval)

Artifacts: PR with review comments, LEX analysis report, preview URL

### Phase 5: Publication (spec-kitty: accept + merge)

1. Merge to develop (triggers preview update)
2. Merge to main (triggers production build: hugo --gc --minify)
3. Netlify publication (live at patterns.sddevelopment.be)
4. Post-publication updates (collection indexes, tag pages, cross-references)

## 3. Journey Map: Glossary Term Addition

Trigger: new pattern needs a tag not in glossary, or reader requests clarification.

1. Term Research: check for synonyms/overlaps, verify no alias conflicts
2. Entry Authoring: add to data/glossary.toml with proper fields
3. Contextive Update: regenerate .contextive/*.glossary.yml files
4. Hugo Content: auto-generates tag page
5. Validation: verify TOML syntax, no duplicates, domain consistency

In spec-kitty: creates team_domain entry, status=candidate, initial confidence

## 4. Journey Map: LEX Analysis Cycle

1. Tone Map Scoring (7 characteristics with targets)
2. Style Rule Compliance (active voice, prescriptive language, paragraph length, citations)
3. Delta Generation (file-by-file deviations, priority classification, before/after)
4. Remediation (Writer-Editor applies fixes, queues medium/low priority)

## 5. Spec-Kitty Mission Mapping

| SDD Patterns Phase | Spec-Kitty Action | Lane Transition | Agent Profiles |
|--------------------|-------------------|----------------|----------------|
| Discovery | specify | planned -> claimed | Researcher, Curator |
| Research | plan | claimed -> in_progress | Researcher, Lexical |
| Template Selection | plan | (within in_progress) | Curator |
| Content Authoring | implement | in_progress | Writer-Editor, Diagrammer |
| Metadata Assignment | implement | (within in_progress) | Lexical, Curator |
| Glossary Sync | implement | (within in_progress) | Lexical |
| Validation | review | in_progress -> for_review | (automated) |
| Tone Review | review | for_review -> in_review | Lexical, Synthesizer |
| Human Approval | accept | in_review -> approved | HiC |
| Publication | merge | approved -> done | Build Automation |

## 6. Agent Collaboration Patterns

### Sequential Handoff
Researcher -> Curator -> Writer-Editor -> Lexical -> Synthesizer -> (Human Review)

### Parallel Lanes
Lane A: Writer-Editor (content), Lane B: Researcher (bibliography), Lane C: Diagrammer
Merge point: Lexical (tone + terminology) -> Synthesizer -> Human Review

### Review Loop
Writer-Editor <-> Lexical (iterative refinement) -> Synthesizer -> Human Approval

## 7. References

- AGENTS.md — Agent governance and profiles
- docs/templates/TEMPLATE_PRACTICE.md — Practice template
- docs/styleguide/LEX_TONE_MAP.md — Tone characteristics
- data/glossary.toml — Terminology registry
- data/bibliography.toml — Reference management
- spec-kitty status model — Lane state machine
- spec-kitty mission types — Mission type profiles
