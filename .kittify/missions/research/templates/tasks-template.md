---
description: "Work package task list template for research methodology execution"
---

# Work Packages: [RESEARCH QUESTION]

**Inputs**: Research documents from `/kitty-specs/[###-research]/`  
**Prerequisites**: plan.md (methodology), spec.md (research question), research.md (background), data-model.md, quickstart.md

**Evidence Tracking**: All sources MUST be recorded in `research/source-register.csv` and findings in `research/evidence-log.csv`.

**Organization**: Research work packages organized by methodology phase. Each work package must be independently deliverable and testable (e.g., literature search complete before analysis).

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different sources/analysts).
- Always reference the file or artifact impacted (e.g., `research/evidence-log.csv`).
- Use research terminology: phases, findings, synthesis, methodology.

## Path Conventions
- **Workspace**: `research/`
- **Data**: `data/`
- **Deliverables**: `findings/`
- Adjust additional paths to match mission.yaml definitions.

---

## Work Package WP01: Literature Search & Source Collection (Priority: P1) 🎯 Foundation

**Goal**: Identify and collect all relevant sources for the research question.  
**Independent Test**: `research/source-register.csv` contains the minimum required high-quality sources with relevance ratings.  
**Prompt**: `/tasks/WP01-literature-search.md`

### Included Subtasks
- [ ] T001 Define search keywords and inclusion/exclusion criteria
- [ ] T002 [P] Search academic database 1 (IEEE, PubMed, arXiv, etc.)
- [ ] T003 [P] Search academic database 2
- [ ] T004 [P] Search gray literature and industry sources
- [ ] T005 Screen collected sources for relevance
- [ ] T006 Populate source-register.csv with all candidate sources
- [ ] T007 Prioritize sources by relevance rating and status

### Implementation Notes
- Document search queries and filters.
- Capture DOIs/URLs and access dates in the source register.

---

## Work Package WP02: Source Review & Evidence Extraction (Priority: P1)

**Goal**: Review prioritized sources and extract key findings.  
**Independent Test**: `research/evidence-log.csv` contains findings from all high-relevance sources with confidence levels.  
**Prompt**: `/tasks/WP02-source-review.md`

### Included Subtasks
- [ ] T008 [P] Review high-relevance sources (parallelizable by researcher/source)
- [ ] T009 Extract key findings into evidence-log.csv
- [ ] T010 Assign confidence levels to findings
- [ ] T011 Document limitations and caveats in notes column
- [ ] T012 Identify patterns/themes emerging from evidence

### Implementation Notes
- Reference source IDs from source-register.csv within each evidence row.
- Flag contradictory findings for deeper analysis.

---

## Work Package WP03: Analysis & Synthesis (Priority: P1)

**Goal**: Synthesize findings and answer the research question.  
**Independent Test**: findings.md contains synthesized conclusions backed by citations.  
**Prompt**: `/tasks/WP03-analysis-synthesis.md`

### Included Subtasks
- [ ] T013 Code findings by theme/category
- [ ] T014 Identify patterns across sources and confidence levels
- [ ] T015 Assess strength of evidence supporting each claim
- [ ] T016 Draw conclusions mapped to sub-questions
- [ ] T017 Document limitations and threats to validity
- [ ] T018 Write findings.md with synthesis and bibliography references

### Implementation Notes
- Link every conclusion to evidence rows.
- Summarize methodology adherence and outstanding questions.

---

## Additional Work Packages (Add as needed)

- **WP0X – Methodology Refinement**: Update plan.md, adjust phases, incorporate new data collection methods.
- **WP0Y – Publication Prep**: Create findings/report deliverables, prepare presentation, finalize bibliography.
- **WP0Z – Empirical Study Support**: For empirical work, capture experiment setup, data collection logs, statistical analysis.

---

## Dependency & Execution Summary

- **Sequence**: WP01 (literature search) → WP02 (evidence extraction) → WP03 (analysis & synthesis) → WP0X (publication/polish).
- **Parallelization**: Database searches, source reviews, and evidence extraction subtasks can run concurrently when using clear ownership per source.
- **Quality Gates**: Do not advance phases until acceptance criteria for the current work package are satisfied.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001       | Define search parameters | WP01 | P1 | No |
| T002       | Search academic database 1 | WP01 | P1 | Yes |
| T008       | Review high-relevance sources | WP02 | P1 | Yes |
| T013       | Code findings by theme | WP03 | P1 | No |

---

> Replace placeholder text with research-specific content. Keep this structure so downstream automation can parse work packages and maintain rigorous research workflows.