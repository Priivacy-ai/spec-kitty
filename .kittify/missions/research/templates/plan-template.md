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
   - Populate `research/evidence-log.csv`
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
- `timestamp`: When evidence collected (ISO format)
- `source_type`: journal | conference | book | web | preprint
- `citation`: Full citation (BibTeX or APA format)
- `key_finding`: Main takeaway from this source
- `confidence`: high | medium | low
- `notes`: Additional context or caveats

**Agent Guidance**:
1. Read source and extract key finding.
2. Add row to evidence-log.csv.
3. Assign confidence level based on source quality and clarity.
4. Note limitations or alternative interpretations.

### Source Registry

**File**: `research/source-register.csv`  
**Purpose**: Maintain master list of all sources for bibliography

**Columns**:
- `source_id`: Unique identifier (e.g., "smith2025")
- `citation`: Full citation
- `url`: Link to source (if available)
- `accessed_date`: When source was accessed
- `relevance`: high | medium | low
- `status`: reviewed | pending | archived

**Agent Guidance**:
1. Add source to register when first discovered.
2. Update status as research progresses.
3. Maintain relevance ratings to prioritize review.

## Project Structure

### Documentation (this research project)
```
kitty-specs/[###-research]/
├── spec.md              # Research question and scope
├── plan.md              # This file - methodology
├── tasks.md             # Research work packages
├── findings.md          # Research findings
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
