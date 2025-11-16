---
work_package_id: "WP04"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Research Mission Templates"
phase: "Phase 3 - Research Mission"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "76722"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Research Mission Templates

## Objectives & Success Criteria

**Goal**: Update research mission templates to be production-ready with complete sections, research-specific prompts, and integrated CSV tracking guidance.

**Success Criteria**:
- Research templates guide users through research methodology (not software development)
- All templates complete and self-consistent (no broken references)
- Templates prompt for research question, methodology, data sources, findings synthesis
- CSV files (evidence-log.csv, source-register.csv) have correct columns and examples
- Full research workflow works end-to-end (init → specify → plan → tasks → implement → review → accept)
- No software-dev terminology in research templates
- All 6 subtasks (T025-T030) completed

## Context & Constraints

**Problem Statement**: Current research mission has "cosmetic changes only":
- Renamed labels ("research question" instead of "user story") but same structure
- CSV templates exist but aren't integrated into workflow
- Command prompts don't guide agents to populate CSVs
- Templates reference software concepts (contracts/, TDD, user stories)

**User Story** (Spec User Story 3):
> "I want the research mission to have complete, validated templates and bibliography/citation management hooks so I can conduct systematic literature reviews with the same rigor as software development workflows."

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 3, FR-008 through FR-012)
- Research: `kitty-specs/005-refactor-mission-system/research.md` (R2: Citation validation approach)
- Data Model: `kitty-specs/005-refactor-mission-system/data-model.md` (Evidence and Source schema)
- Existing: `.kittify/missions/research/mission.yaml` (current configuration)

**Research Workflow Phases** (from research mission.yaml):
1. **question** - Define research question and scope
2. **methodology** - Design research methodology
3. **gather** - Collect data and sources
4. **analyze** - Analyze findings
5. **synthesize** - Synthesize results and draw conclusions
6. **publish** - Prepare findings for publication

**Required Artifacts** (from research mission.yaml):
- spec.md (research question and scope)
- plan.md (methodology plan)
- tasks.md (research tasks)
- findings.md (research findings)

**CSV Schemas** (to integrate):
- evidence-log.csv: timestamp, source_type, citation, key_finding, confidence, notes
- source-register.csv: source_id, citation, url, accessed_date, relevance, status

## Subtasks & Detailed Guidance

### Subtask T025 – Update spec-template.md for research

**Purpose**: Transform spec template from software user stories to research question format.

**Steps**:
1. Locate file: `.kittify/missions/research/templates/spec-template.md`
2. Update header section:
   ```markdown
   # Research Specification: [RESEARCH QUESTION]

   **Feature Branch**: `[###-research-name]`
   **Created**: [DATE]
   **Status**: Draft
   **Research Type**: Literature Review | Empirical Study | Case Study | Meta-Analysis

   ## Research Question & Scope

   **Primary Research Question**: [What specific question does this research aim to answer?]

   **Sub-Questions**:
   1. [Supporting question 1]
   2. [Supporting question 2]

   **Scope**:
   - **In Scope**: [What will be investigated]
   - **Out of Scope**: [What will NOT be investigated]
   - **Boundaries**: [Time period, geographic region, specific domains]

   **Expected Outcomes**:
   - [What findings or artifacts will this research produce?]
   - [How will results be applied?]
   ```

3. Replace "User Scenarios & Testing" with "Research Methodology Outline":
   ```markdown
   ## Research Methodology Outline

   ### Research Approach
   - **Method**: Systematic Literature Review | Survey | Experiment | Case Study
   - **Data Sources**: [Where will data/sources come from?]
   - **Analysis Approach**: [How will data be analyzed?]

   ### Success Criteria
   - [Measurable criterion 1: e.g., "Review at least 50 peer-reviewed sources"]
   - [Measurable criterion 2: e.g., "Identify 3+ validated patterns"]
   - [Quality criterion: e.g., "All sources cited in APA/BibTeX format"]
   ```

4. Replace "Functional Requirements" with "Research Requirements":
   ```markdown
   ## Research Requirements

   ### Data Collection Requirements
   - **DR-001**: Research MUST collect data from [specific sources]
   - **DR-002**: All sources MUST be documented in source-register.csv
   - **DR-003**: Citations MUST follow [BibTeX | APA | other] format

   ### Analysis Requirements
   - **AR-001**: Findings MUST be synthesized into [specific output]
   - **AR-002**: Methodology MUST be clearly documented and reproducible
   - **AR-003**: Limitations MUST be explicitly identified

   ### Quality Requirements
   - **QR-001**: All claims MUST be supported by cited evidence
   - **QR-002**: Confidence levels MUST be assigned to findings
   - **QR-003**: Alternative interpretations MUST be considered
   ```

5. Add "Key Concepts & Terminology" section:
   ```markdown
   ## Key Concepts & Terminology

   - **[Concept 1]**: [Definition in research context]
   - **[Concept 2]**: [Definition relevant to research question]
   ```

6. Remove software-specific sections (contracts, user stories, API requirements)

**Files**: `.kittify/missions/research/templates/spec-template.md`

**Parallel?**: Yes (independent from other templates)

**Notes**: Research spec should read like academic research proposal, not software requirements doc.

---

### Subtask T026 – Update plan-template.md for research methodology

**Purpose**: Transform plan template from technical architecture to research methodology.

**Steps**:
1. Locate file: `.kittify/missions/research/templates/plan-template.md`
2. Update to research-focused structure:
   ```markdown
   # Research Plan: [RESEARCH QUESTION]

   **Branch**: `[###-research-name]` | **Date**: [DATE] | **Spec**: [link]

   ## Summary
   [One paragraph: research question + methodology + expected outcomes]

   ## Research Context

   **Research Question**: [Primary question]
   **Research Type**: Literature Review | Empirical Study | Case Study
   **Domain**: [Academic field or industry domain]
   **Time Frame**: [When research will be conducted]
   **Resources Available**: [Databases, tools, budget, time]

   **Key Background**:
   - [Context point 1]
   - [Context point 2]

   ## Methodology

   ### Research Design

   **Approach**: [Systematic Literature Review | Survey | Experiment | Mixed Methods]

   **Phases**:
   1. **Question Formation** (Week 1)
      - Define precise research question
      - Identify sub-questions
      - Establish scope and boundaries

   2. **Methodology Design** (Week 1-2)
      - Select data collection methods
      - Define analysis framework
      - Establish quality criteria

   3. **Data Gathering** (Week 2-4)
      - Search academic databases
      - Screen sources for relevance
      - Extract key findings
      - Populate evidence-log.csv

   4. **Analysis** (Week 4-5)
      - Code and categorize findings
      - Identify patterns and themes
      - Assess evidence quality

   5. **Synthesis** (Week 5-6)
      - Draw conclusions
      - Address research question
      - Identify limitations

   6. **Publication** (Week 6)
      - Write findings report
      - Prepare presentation
      - Share results

   ### Data Sources

   **Primary Sources**:
   - [Database 1: e.g., IEEE Xplore, PubMed, arXiv]
   - [Database 2]

   **Secondary Sources**:
   - [Gray literature, industry reports, etc.]

   **Search Strategy**:
   - **Keywords**: [List search terms]
   - **Inclusion Criteria**: [What qualifies for review]
   - **Exclusion Criteria**: [What will be filtered out]

   ### Analysis Framework

   **Coding Scheme**: [How findings will be categorized]
   **Synthesis Method**: [Thematic analysis | Meta-analysis | Narrative synthesis]
   **Quality Assessment**: [How source quality will be evaluated]

   ## Data Management

   ### Evidence Tracking

   **File**: `research/evidence-log.csv`

   **Purpose**: Track all evidence collected with citations and findings

   **Columns**:
   - timestamp: When evidence collected (ISO format)
   - source_type: journal | conference | book | web | preprint
   - citation: Full citation (BibTeX or APA format)
   - key_finding: Main takeaway from this source
   - confidence: high | medium | low
   - notes: Additional context or caveats

   **Agent Guidance**: For each source reviewed:
   1. Read source and extract key finding
   2. Add row to evidence-log.csv
   3. Assign confidence level based on source quality and clarity
   4. Note any limitations or alternative interpretations

   ### Source Registry

   **File**: `research/source-register.csv`

   **Purpose**: Maintain master list of all sources for bibliography

   **Columns**:
   - source_id: Unique identifier (e.g., "smith2025")
   - citation: Full citation
   - url: Link to source (if available)
   - accessed_date: When source was accessed
   - relevance: high | medium | low (to research question)
   - status: reviewed | pending | archived

   **Agent Guidance**:
   1. Add source to register when first discovered
   2. Update status as research progresses
   3. Maintain relevance ratings to prioritize review

   ## Project Structure

   ### Documentation (this research project)
   ```
   kitty-specs/[###-research]/
   ├── spec.md              # Research question and scope
   ├── plan.md              # This file - methodology
   ├── tasks.md             # Research work packages
   ├── findings.md          # Final synthesized findings
   ├── research/
   │   ├── evidence-log.csv      # All evidence with citations
   │   ├── source-register.csv   # Master source list
   │   └── methodology.md        # Detailed methodology (optional)
   └── data/                # Raw data (if empirical)
   ```

   ### Deliverables
   ```
   findings/
   ├── report.md           # Main research report
   ├── bibliography.md     # Formatted bibliography
   └── presentation/       # Slides or summary (optional)
   ```

   ## Quality Gates

   *Checkpoints ensuring research rigor*

   ### Before Data Gathering
   - [ ] Research question is clear and focused
   - [ ] Methodology is documented and reproducible
   - [ ] Data sources identified and accessible
   - [ ] Analysis framework defined

   ### During Data Gathering
   - [ ] All sources documented in source-register.csv
   - [ ] Evidence logged with proper citations
   - [ ] Confidence levels assigned
   - [ ] Quality threshold maintained

   ### Before Synthesis
   - [ ] All sources reviewed
   - [ ] Findings coded and categorized
   - [ ] Patterns identified
   - [ ] Limitations documented

   ### Before Publication
   - [ ] Research question answered
   - [ ] All claims cited
   - [ ] Methodology clear and reproducible
   - [ ] Findings synthesized
   - [ ] Bibliography complete
   ```

3. Remove software-specific sections:
   - Delete "Technical Context" (Language/Version, Dependencies, Testing)
   - Delete "Constitution Check" (TDD, Library-First)
   - Delete sections about src/, tests/, contracts/

4. Add research-specific sections:
   - Methodology validation
   - Source quality criteria
   - Synthesis approach

**Files**: `.kittify/missions/research/templates/plan-template.md`

**Parallel?**: Yes (independent from spec and tasks templates)

**Notes**: Reference academic research methodology standards. Template should guide rigorous research process.

---

### Subtask T027 – Update tasks-template.md for research work packages

**Purpose**: Transform tasks template from software tasks to research work packages.

**Steps**:
1. Locate file: `.kittify/missions/research/templates/tasks-template.md`
2. Update work package examples for research:
   ```markdown
   # Work Packages: [RESEARCH QUESTION]

   **Organization**: Research work packages organized by methodology phase

   ## Work Package WP01: Literature Search & Source Collection

   **Goal**: Identify and collect all relevant sources for the research question
   **Independent Test**: Source-register.csv contains minimum required sources
   **Prompt**: `/tasks/planned/WP01-literature-search.md`

   ### Included Subtasks
   - [ ] T001 Define search keywords and inclusion/exclusion criteria
   - [ ] T002 [P] Search academic database 1 (IEEE, PubMed, etc.)
   - [ ] T003 [P] Search academic database 2
   - [ ] T004 [P] Search gray literature and industry sources
   - [ ] T005 Screen sources for relevance
   - [ ] T006 Populate source-register.csv with all sources
   - [ ] T007 Prioritize sources by relevance rating

   ## Work Package WP02: Source Review & Evidence Extraction

   **Goal**: Review prioritized sources and extract key findings
   **Independent Test**: Evidence-log.csv contains findings from all high-relevance sources
   **Prompt**: `/tasks/planned/WP02-source-review.md`

   ### Included Subtasks
   - [ ] T008 [P] Review high-relevance sources (parallel by source)
   - [ ] T009 Extract key findings to evidence-log.csv
   - [ ] T010 Assign confidence levels to findings
   - [ ] T011 Document limitations and caveats
   - [ ] T012 Identify patterns and themes

   ## Work Package WP03: Analysis & Synthesis

   **Goal**: Synthesize findings and answer research question
   **Independent Test**: Findings.md contains synthesized conclusions with citations
   **Prompt**: `/tasks/planned/WP03-analysis-synthesis.md`

   ### Included Subtasks
   - [ ] T013 Code findings by theme/category
   - [ ] T014 Identify patterns across sources
   - [ ] T015 Assess strength of evidence
   - [ ] T016 Draw conclusions
   - [ ] T017 Document limitations
   - [ ] T018 Write findings.md with synthesis
   ```

3. Update path conventions:
   - Change src/ → research/
   - Change tests/ → data/
   - Change contracts/ → findings/

4. Update terminology throughout:
   - Remove "user stories", "features", "TDD", "implementation"
   - Use "research phases", "methodology", "evidence", "synthesis"

**Files**: `.kittify/missions/research/templates/tasks-template.md`

**Parallel?**: Yes (independent from other templates)

**Notes**: Research work packages should reflect academic research process, not software development sprints.

---

### Subtask T028 – Verify evidence-log.csv template

**Purpose**: Ensure CSV template has correct structure and helpful examples.

**Steps**:
1. Locate file: `.kittify/missions/research/templates/research/evidence-log.csv`
2. Verify column headers match schema (from data-model.md):
   ```csv
   timestamp,source_type,citation,key_finding,confidence,notes
   ```

3. Add example rows demonstrating each source type:
   ```csv
   timestamp,source_type,citation,key_finding,confidence,notes
   2025-01-15T10:00:00,journal,"Smith, J. (2024). AI Code Assistants. Nature Comp Sci, 10(2), 123-145.",AI assistants improve productivity 30%,high,Meta-analysis of 50 studies
   2025-01-15T11:30:00,conference,"@inproceedings{jones2024copilot,author={Jones et al.},title={Copilot Study},year={2024}}",65% code acceptance rate,medium,GitHub internal data
   2025-01-15T14:00:00,web,"GitHub Copilot Stats. https://github.blog/copilot-stats-2024",35M developers using Copilot,medium,Self-reported usage numbers
   2025-01-15T15:30:00,preprint,"Lee, K. (2024). AI Pair Programming. arXiv:2024.12345",Real-time suggestions key factor,low,Preprint not peer-reviewed
   2025-01-16T09:00:00,book,"Brown, A. (2023). The AI Developer. O'Reilly.",Context-aware tools reduce cognitive load,high,Chapter 7 empirical study
   ```

4. Add inline documentation:
   ```csv
   # Evidence Log: Track all research findings with citations
   #
   # Column Definitions:
   # - timestamp: When evidence was collected (ISO format: YYYY-MM-DDTHH:MM:SS)
   # - source_type: journal | conference | book | web | preprint
   # - citation: Full citation (BibTeX, APA, or Simple format)
   # - key_finding: Main takeaway from this source (1-2 sentences)
   # - confidence: high | medium | low (based on source quality and clarity)
   # - notes: Additional context, caveats, or methodological notes
   #
   # Validation: Citations must be non-empty, source_type must be valid
   # Format: BibTeX (@article{...}) or APA (Author (Year). Title.) recommended
   ```

5. Verify file is UTF-8 encoded with Unix line endings

**Files**: `.kittify/missions/research/templates/research/evidence-log.csv`

**Parallel?**: Yes (independent from source-register)

**Notes**: CSV examples should demonstrate best practices for citation formatting.

---

### Subtask T029 – Verify source-register.csv template

**Purpose**: Ensure source registry has correct structure and examples.

**Steps**:
1. Locate file: `.kittify/missions/research/templates/research/source-register.csv`
2. Verify column headers:
   ```csv
   source_id,citation,url,accessed_date,relevance,status
   ```

3. Add example rows:
   ```csv
   source_id,citation,url,accessed_date,relevance,status
   smith2024,"Smith, J. (2024). AI Code Assistants. Nature Comp Sci, 10(2), 123-145.",https://doi.org/10.1038/example,2025-01-15,high,reviewed
   jones2024,"@inproceedings{jones2024copilot,author={Jones et al.},title={Copilot Study},booktitle={ICSE 2024},year={2024}}",https://dl.acm.org/example,2025-01-15,high,reviewed
   github2024,"GitHub Copilot Statistics. GitHub Blog.",https://github.blog/copilot-stats-2024,2025-01-15,medium,reviewed
   lee2024,"Lee, K. (2024). AI Pair Programming. arXiv:2024.12345",https://arxiv.org/abs/2024.12345,2025-01-15,low,pending
   brown2023,"Brown, A. (2023). The AI Developer: Human-Machine Collaboration. O'Reilly Media.",https://oreilly.com/example,2025-01-16,high,archived
   ```

4. Add inline documentation:
   ```csv
   # Source Register: Master list of all research sources
   #
   # Column Definitions:
   # - source_id: Unique identifier (lowercase, no spaces, e.g., "smith2024")
   # - citation: Full citation (BibTeX or APA format)
   # - url: Direct link to source (DOI, arXiv, or web URL)
   # - accessed_date: Date source was accessed (YYYY-MM-DD)
   # - relevance: high | medium | low (to primary research question)
   # - status: reviewed | pending | archived
   #
   # Usage: Add sources when discovered, update status as research progresses
   # Validation: source_id must be unique, citation must be non-empty
   ```

**Files**: `.kittify/missions/research/templates/research/source-register.csv`

**Parallel?**: Yes (independent from evidence-log)

**Notes**: Source register is the master bibliography - must be complete and accurate.

---

### Subtask T030 – Update research mission.yaml

**Purpose**: Ensure research mission configuration is complete and accurate.

**Steps**:
1. Locate file: `.kittify/missions/research/mission.yaml`
2. Verify all required sections present (will be validated by WP02 Pydantic schema)
3. Ensure validation rules are research-specific:
   ```yaml
   validation:
     checks:
       - all_sources_documented
       - methodology_clear
       - findings_synthesized
       - no_unresolved_questions
     custom_validators: true  # Uses validators from WP05
   ```

4. Verify artifacts list is complete:
   ```yaml
   artifacts:
     required:
       - spec.md              # Research question
       - plan.md              # Methodology
       - tasks.md             # Research work packages
       - findings.md          # Synthesized results
     optional:
       - sources/             # Source documents
       - data/                # Raw data
       - analysis/            # Analysis outputs
       - literature-review.md
       - methodology.md       # Detailed methodology
       - synthesis.md         # Synthesis notes
   ```

5. Verify path conventions:
   ```yaml
   paths:
     workspace: "research/"
     data: "data/"
     deliverables: "findings/"
     documentation: "reports/"
   ```

6. Update agent_context to emphasize research rigor:
   ```yaml
   agent_context: |
     You are a research agent conducting systematic literature reviews and empirical research.
     Your mission is to maintain research integrity and methodological rigor.

     Key Practices:
     - Document ALL sources in source-register.csv with proper citations
     - Extract findings to evidence-log.csv with confidence levels
     - Clearly articulate research methodology for reproducibility
     - Distinguish evidence from interpretation
     - Identify limitations and alternative explanations
     - Synthesize findings to directly address research question

     Citation Standards:
     - Use BibTeX or APA format
     - Include DOI or URL when available
     - Track access dates for web sources
     - Assign confidence levels (high/medium/low)

     Workflow Phases: question → methodology → gather → analyze → synthesize → publish
   ```

**Files**: `.kittify/missions/research/mission.yaml`

**Parallel?**: No (should come after template updates to ensure consistency)

**Notes**: This is the master configuration - must align with templates and validation rules.

---

## Test Strategy

**Template Validation Approach**:

1. **Completeness Test**:
   - Read each template file
   - Verify no [PLACEHOLDER] or [TODO] markers remain
   - Verify all section headers make sense for research
   - Verify no software-dev terminology leaked through

2. **Integration Test** (most important):
   ```bash
   # Create research project
   spec-kitty init test-research --mission research --ai claude

   # Run through full workflow
   cd test-research
   /spec-kitty.specify "impact of AI code assistants on developer productivity"
   # → Verify spec.md has research question format

   /spec-kitty.plan
   # → Verify plan.md has methodology sections

   /spec-kitty.tasks
   # → Verify tasks.md has research work packages

   # Manually populate CSVs following guidance
   echo "..." >> research/evidence-log.csv

   /spec-kitty.review
   # → Verify validation checks citations

   /spec-kitty.accept
   # → Verify all research requirements checked
   ```

3. **CSV Validation Test**:
   - Open evidence-log.csv, verify columns correct
   - Open source-register.csv, verify columns correct
   - Add sample data, verify parseable by Python csv module
   - Test with various citation formats (BibTeX, APA, Simple)

4. **Cross-Reference Test**:
   - mission.yaml validation.checks → must match actual research workflow needs
   - mission.yaml artifacts → must match what templates create
   - mission.yaml paths → must match directory structure in templates

**Test Files Created**:
- Will be tested in WP10 (Integration Testing)
- Manual testing during this WP to verify completeness

---

## Risks & Mitigations

**Risk 1**: Templates too academic, confuse non-researcher users
- **Mitigation**: Include inline examples and guidance, test with diverse users

**Risk 2**: CSV schema doesn't match actual research needs
- **Mitigation**: Based on established evidence synthesis practices, but gather feedback

**Risk 3**: Templates incomplete, missing key sections
- **Mitigation**: Compare against academic research proposal standards

**Risk 4**: Software terminology leaked into research templates
- **Mitigation**: Thorough review, search for terms like "user story", "TDD", "contract"

**Risk 5**: CSV files not integrated into workflow
- **Mitigation**: Explicit guidance in command prompts (WP05 handles this)

---

## Definition of Done Checklist

- [ ] spec-template.md updated with research question format
- [ ] plan-template.md updated with methodology sections
- [ ] tasks-template.md updated with research work package examples
- [ ] evidence-log.csv has correct columns and examples
- [ ] source-register.csv has correct columns and examples
- [ ] research mission.yaml configuration complete and accurate
- [ ] No software-dev terminology in research templates
- [ ] All templates internally consistent (cross-references work)
- [ ] CSV files parseable by Python csv module
- [ ] Manual end-to-end test passed (init → specify → plan → tasks)
- [ ] mission.yaml will pass WP02 Pydantic validation

---

## Review Guidance

**Critical Checkpoints**:
1. Research templates must guide actual research methodology
2. CSV schemas must support real research workflows
3. Templates must be complete (no broken references)
4. Terminology must be research-focused (not software-dev)
5. Integration must work (templates → CSVs → validation)

**What Reviewers Should Verify**:
- Initialize research project: `spec-kitty init test --mission research`
- Run `/spec-kitty.specify` → verify research question prompt
- Run `/spec-kitty.plan` → verify methodology sections
- Check CSV files → correct columns, good examples
- Search for "user story", "TDD", "contract" → should find none in research templates
- Verify mission.yaml aligns with templates

**Acceptance Criteria from Spec**:
- User Story 3, Acceptance Scenarios 1-6 all must pass
- FR-008 and FR-012 satisfied (templates complete and consistent)

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:00:56Z – codex – shell_pid=60030 – lane=doing – Started implementation
- 2025-11-16T13:05:04Z – codex – shell_pid=60030 – lane=doing – Completed research template implementation
- 2025-11-16T13:06:28Z – codex – shell_pid=60030 – lane=for_review – Ready for review
- 2025-11-16T13:13:00Z – claude – shell_pid=76722 – lane=done – Code review complete: APPROVED. Excellent research templates transformation. All 3 templates (spec, plan, tasks) fully rewritten for research methodology. No software-dev terminology found. CSV templates have correct columns with inline documentation. Templates guide systematic literature review process. Production-ready for research workflows.
