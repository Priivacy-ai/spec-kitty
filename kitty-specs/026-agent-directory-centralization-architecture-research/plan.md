# Research Plan: Agent Directory Centralization Architecture

**Branch**: `026-agent-directory-centralization-architecture-research` | **Date**: 2026-02-01 | **Spec**: [spec.md](spec.md)

## Summary

This research investigates whether Spec Kitty's agent directories (.claude/, .codex/, .gemini/, etc.) should be centralized at the user level instead of duplicated per project. Using a sequential phased methodology with deep research per work package, the study will analyze 6 workflow patterns individually, design a centralized architecture supporting all 14 agents with backwards compatibility, assess migration feasibility, and synthesize findings into 4 comprehensive deliverables: decision framework, architecture proposal, feasibility study, and evidence-based recommendation.

## Research Context

**Research Question**: Should Spec Kitty centralize agent directories at the user level (~/.spec-kitty/ or similar) instead of duplicating per project, and if so, what architecture enables this while maintaining backwards compatibility?

**Research Type**: Architecture Analysis & Design Study (combining case study analysis, empirical study, and architecture design)

**Domain**: Software architecture, developer tooling, multi-agent AI systems

**Time Frame**: Sequential phased research with synthesis at completion

**Resources Available**:
- Current Spec Kitty codebase (v0.15.0+) at `/Users/robert/ClaudeCowork/SpecKitty/spec-kitty/`
- Agent discovery documentation (`product-ideas/agent-command-discovery-and-skills.md`)
- User pain point data (installation time, .gitignore burden, template versioning, worktree complexity)
- Access to all 14 agent documentation sources
- Existing implementation code (AGENT_DIRS, agent_config.py, init.py, dashboard/)

**Key Background**:
- Spec Kitty currently duplicates 12 agent directories across every project
- Primary pain points: installation/upgrade time per project, .gitignore maintenance burden, template versioning consistency, worktree sparse checkout complexity
- Backwards compatibility is CRITICAL constraint (1000% requirement)
- Multi-project dashboard is strategic direction (centralization could enable)
- 6 distinct workflow patterns with different centralization implications
- 14 documented agents with varying discovery mechanisms (file-based, MCP, skills)

## Methodology

### Research Design

**Approach**: Sequential phased study with deep research per work package and synthesis phases

**Phases**:

1. **Phase 0: Data Collection & Baseline Analysis** (WP01)
   - Analyze current codebase implementation (AGENT_DIRS, agent_config.py, init.py, template.py, dashboard/)
   - Document all 14 agent discovery mechanisms from cross-agent documentation
   - Extract user pain points and quantify impact (installation time, .gitignore entries, template count, worktree sparse paths)
   - Establish evidence tracking baseline (populate initial source-register.csv and evidence-log.csv)
   - **Output**: Baseline evidence foundation for all subsequent analysis

2. **Phase 1: Workflow Pattern Analysis** (WP02-WP07 - Sequential)
   - **WP02**: Deep dive into WF-001 (Solo Dev, Single Project) - setup friction vs maintenance burden
   - **WP03**: Deep dive into WF-002 (Solo Dev, Multi-Project) - HIGH benefit analysis, dashboard implications
   - **WP04**: Deep dive into WF-003 (Team, Shared Repo) - version control, .gitignore, collaboration patterns
   - **WP05**: Deep dive into WF-004 (Mono-Repo, Multi-Feature) - HIGH benefit analysis, worktree complexity
   - **WP06**: Deep dive into WF-005 (Mixed Agent Environments) - heterogeneous tooling, selective installation
   - **WP07**: Deep dive into WF-006 (Open Source) - contributor onboarding, public repo cleanliness
   - **Each WP**: Adversarial debate (pros vs cons), trade-off matrix, impact quantification
   - **Output**: Workflow-specific findings for decision framework

3. **Phase 2: Agent Compatibility Audit** (WP08)
   - Systematic review of all 14 agents (Claude Code, Copilot, Gemini, Cursor, Qwen, OpenCode, Windsurf, Codex, Kilocode, Augment, Roo, Amazon Q, Kimi, Mistral)
   - Map discovery mechanisms (file-based commands, MCP prompts, skills) to centralization scenarios
   - Identify agents with mandatory project-level directories vs compatible with user-level
   - Document compatibility blockers and workarounds
   - **Output**: 14×3 compatibility matrix (agent × discovery mechanism × centralization viability)

4. **Phase 3: Architecture Design** (WP09)
   - Design centralized directory structure (~/.spec-kitty/agents/ or alternative)
   - Design project registration protocol (how projects register with central location)
   - Design backwards compatibility mechanism (fallback to project-level if user-level missing)
   - Design multi-project dashboard integration (registration database, project discovery)
   - Design migration strategy (gradual vs big-bang, opt-in vs automatic)
   - Address precedence rules (project-local customizations vs user-global defaults)
   - **Output**: Complete architectural specification with diagrams

5. **Phase 4: Feasibility Assessment** (WP10)
   - Identify migration risks (backwards compatibility, data loss, conflicts)
   - Document conflict scenarios (version mismatches, per-project customizations, mid-flight worktrees)
   - Assess edge cases (legacy projects, active worktrees, custom commands)
   - Estimate implementation complexity (low/medium/high per component: init, upgrade, dashboard, worktree)
   - Identify blockers and mitigation strategies
   - **Output**: Risk assessment with severity ratings and mitigation plans

6. **Phase 5: Synthesis & Recommendation** (WP11-WP14)
   - **WP11**: Synthesize decision framework from workflow analyses (trade-off matrix, criteria, per-pattern recommendations)
   - **WP12**: Synthesize architecture proposal from design phase (consolidate spec, diagrams, migration strategy)
   - **WP13**: Synthesize feasibility study from compatibility audit and risk assessment (consolidate matrix, risks, complexity estimates)
   - **WP14**: Generate final recommendation (evidence summary, approach selection, implementation roadmap, prioritization, success metrics)
   - **Output**: 4 comprehensive deliverable documents

### Data Sources

**Primary Sources**:
- Spec Kitty codebase (Python 3.11+, typer, rich, ruamel.yaml, pytest)
- Agent discovery documentation (14 agents)
- Git repository analysis (current .gitignore patterns, worktree configurations)

**Secondary Sources**:
- User pain point reports (installation time, .gitignore maintenance, template versioning, worktree complexity)
- Agent ecosystem patterns (common practices for user-level vs project-level tooling)
- Industry patterns (how other CLIs handle centralization: npm, poetry, cargo, homebrew)

**Search Strategy**:
- **Keywords**: agent directories, user-level configuration, project-level duplication, centralized tooling, backwards compatibility, multi-project dashboard
- **Inclusion Criteria**: Relevant to Spec Kitty architecture, addresses one of 6 workflow patterns, covers agent discovery mechanisms, relates to migration feasibility
- **Exclusion Criteria**: Not applicable to Spec Kitty context, purely theoretical without practical implementation path, violates hard constraints (backwards compatibility, 14 agent support)

### Analysis Framework

**Coding Scheme**:
- Workflow pattern characteristics (solo/team, single/multi-project, homogeneous/mixed agents)
- Centralization impact dimensions (setup time, version control, collaboration, contributor experience, multi-project management)
- Agent discovery categories (file-based commands, MCP prompts, skills, hybrid)
- Migration risk severity (CRITICAL, HIGH, MEDIUM, LOW)
- Implementation complexity (low/medium/high per component)

**Synthesis Method**: Thematic analysis across workflow patterns, architectural design, and feasibility assessment → integrated recommendation

**Quality Assessment**:
- Evidence confidence levels (HIGH: codebase facts, documented agent specs; MEDIUM: inferred from patterns; LOW: assumptions requiring validation)
- Trade-off validity (pros/cons must be specific to workflow pattern, not generic)
- Architecture completeness (addresses backwards compatibility, all 14 agents, migration path)
- Feasibility accuracy (risks must have severity rating and mitigation strategy)

## Data Management

### Evidence Tracking

**File**: `research/evidence-log.csv`
**Purpose**: Track all evidence collected with citations and findings

**Columns**:
- `evidence_id`: Unique identifier (EV-001, EV-002, ...)
- `timestamp`: When evidence collected (ISO format)
- `source_type`: codebase | agent_doc | user_pain_point | industry_pattern
- `source_reference`: File path, URL, or citation
- `key_finding`: Main takeaway from this source
- `confidence`: HIGH | MEDIUM | LOW
- `workflow_patterns_affected`: WF-001, WF-002, etc. (comma-separated)
- `notes`: Additional context or caveats

**Agent Guidance**:
1. Read source code or documentation and extract key finding
2. Add row to evidence-log.csv with next sequential evidence_id
3. Assign confidence level based on source quality (codebase = HIGH, inferred = MEDIUM, assumed = LOW)
4. Tag affected workflow patterns for cross-referencing
5. Note limitations or alternative interpretations

### Source Registry

**File**: `research/source-register.csv`
**Purpose**: Maintain master list of all sources for bibliography

**Columns**:
- `source_id`: Unique identifier (SRC-001, SRC-002, ...)
- `source_type`: codebase_file | agent_documentation | user_feedback | industry_reference
- `file_path_or_url`: Absolute path or URL
- `purpose`: Brief description of what this source provides
- `relevance`: HIGH | MEDIUM | LOW
- `review_status`: pending | reviewed | excluded
- `notes`: Additional context

**Agent Guidance**:
1. Add source to register when first discovered during data collection
2. Update review_status as research progresses (pending → reviewed)
3. Maintain relevance ratings to prioritize deep analysis
4. Mark excluded if determined out of scope

## Research Deliverables Location

**Deliverables Path**: `docs/research/026-agent-directory-centralization/`

This location is SEPARATE from `kitty-specs/` planning artifacts.

This path will:
- Be created in each WP worktree during implementation
- Contain the actual research findings (4 markdown deliverables)
- Be merged to main when WPs complete

### Why Two Locations?

| Type | Location | Purpose |
|------|----------|---------|
| **Planning Artifacts** | `kitty-specs/026-*/research/` | Evidence/sources collected DURING planning (shared across WPs) |
| **Research Deliverables** | `docs/research/026-agent-directory-centralization/` | Actual research OUTPUT (created in worktrees, merged to main) |

## Project Structure

### Sprint Planning Artifacts (in kitty-specs/)
```
kitty-specs/026-agent-directory-centralization-architecture-research/
├── spec.md                        # Research question and scope
├── plan.md                        # This file - methodology
├── tasks.md                       # Research work packages (generated by /spec-kitty.tasks)
├── meta.json                      # Contains deliverables_path setting
├── research/
│   ├── evidence-log.csv           # Evidence collected DURING PLANNING
│   ├── source-register.csv        # Sources cited DURING PLANNING
│   └── methodology-notes.md       # Detailed methodology notes (optional)
└── tasks/                         # WP prompt files (generated by /spec-kitty.tasks)
```

### Research Deliverables (in deliverables_path)
```
docs/research/026-agent-directory-centralization/
├── decision-framework.md          # WP11 synthesis output
│   ├── Trade-off matrix (6 workflows × user/project/hybrid)
│   ├── Decision criteria (measurable workflow characteristics)
│   ├── Per-pattern recommendations
│   └── Workflow characteristics analysis
├── architecture-proposal.md       # WP12 synthesis output
│   ├── Centralized directory structure design
│   ├── Project registration protocol
│   ├── Backwards compatibility mechanism
│   ├── Multi-project dashboard integration
│   ├── Agent discovery compatibility (14 agents)
│   └── Migration strategy (gradual vs big-bang)
├── feasibility-study.md           # WP13 synthesis output
│   ├── Migration risks (severity ratings + mitigation)
│   ├── Conflict scenarios (project-local vs user-global)
│   ├── Agent compatibility matrix (14 agents × centralization viability)
│   ├── Edge cases (worktrees, legacy, custom commands)
│   ├── Implementation complexity estimates
│   └── Blockers and mitigation strategies
├── recommendation.md              # WP14 final synthesis output
│   ├── Evidence summary (key findings from all phases)
│   ├── Recommended approach (centralized/hybrid/status quo + rationale)
│   ├── Implementation roadmap (phased milestones)
│   ├── Prioritization (impact vs effort matrix)
│   ├── Success metrics
│   └── Open questions for further investigation
└── data/
    ├── workflow-analysis/         # Raw analysis from WP02-WP07
    ├── agent-compatibility/       # Raw audit from WP08
    ├── architecture-diagrams/     # Design artifacts from WP09
    └── risk-assessment/           # Risk data from WP10
```

## Constitution Check

**Constitution Status**: Spec Kitty Constitution exists at `.kittify/memory/constitution.md`

### Relevant Constitution Principles

**Language/Framework**:
- ✅ Python 3.11+ (research involves codebase analysis, not new implementation)
- ✅ No code implementation in this research phase

**Testing**:
- ⚠️ N/A for pure research (no code changes)
- ✅ Research methodology is documented and reproducible

**Architecture Pattern**:
- ✅ Research examines potential changes to agent directory management
- ✅ No private dependency changes (spec-kitty-events not affected)
- ✅ Research considers backwards compatibility (CRITICAL constraint aligns with constitution)

**Branch Strategy**:
- ✅ Research targets current architecture (not tied to 1.x vs 2.x split)
- ℹ️ Findings may inform future 2.x architecture if centralization adopted

**Quality Standards**:
- ✅ All research findings will be evidence-based with citations
- ✅ Confidence levels assigned to all evidence
- ✅ Reproducible methodology documented

### Gate Validation

**Before Phase 0 (Data Collection)**:
- [x] Research question is clear and focused
- [x] Methodology is documented and reproducible
- [x] Data sources identified and accessible (codebase, agent docs, user pain points)
- [x] Analysis framework defined (coding scheme, synthesis method, quality assessment)
- [x] No constitution violations (pure research, no implementation)

**Re-check After Phase 1 (Workflow Analysis)**:
- [ ] All 6 workflow patterns analyzed with specific findings
- [ ] Evidence logged with proper citations and confidence levels
- [ ] Trade-offs documented (pros/cons per pattern)
- [ ] Findings support decision framework synthesis

**Re-check After Phase 5 (Synthesis)**:
- [ ] All 4 deliverables complete (decision-framework, architecture-proposal, feasibility-study, recommendation)
- [ ] All claims cited with evidence IDs
- [ ] Recommendation includes implementation roadmap
- [ ] Success metrics defined for measuring adoption

## Work Package Dependencies

**Sequential execution with dependencies**:

- **WP01** (Phase 0: Data Collection) → No dependencies (foundation)
- **WP02** (WF-001 Analysis) → Depends on WP01 (requires baseline evidence)
- **WP03** (WF-002 Analysis) → Depends on WP02 (builds on solo dev patterns)
- **WP04** (WF-003 Analysis) → Depends on WP03 (team patterns build on solo)
- **WP05** (WF-004 Analysis) → Depends on WP04 (mono-repo extends team patterns)
- **WP06** (WF-005 Analysis) → Depends on WP05 (mixed agents extends mono-repo)
- **WP07** (WF-006 Analysis) → Depends on WP06 (open source extends all prior patterns)
- **WP08** (Phase 2: Agent Compatibility) → Depends on WP07 (requires workflow analysis complete)
- **WP09** (Phase 3: Architecture Design) → Depends on WP08 (design informed by compatibility constraints)
- **WP10** (Phase 4: Feasibility Assessment) → Depends on WP09 (assess feasibility of proposed architecture)
- **WP11** (Synthesis: Decision Framework) → Depends on WP07 (all workflow analyses complete)
- **WP12** (Synthesis: Architecture Proposal) → Depends on WP09 (architecture design complete)
- **WP13** (Synthesis: Feasibility Study) → Depends on WP10 (feasibility assessment complete)
- **WP14** (Synthesis: Final Recommendation) → Depends on WP11, WP12, WP13 (all deliverables synthesized)

**Parallelization**: None - sequential execution ensures each phase builds on previous findings

## Quality Gates

### Before Data Gathering (Phase 0 - WP01)
- [x] Research question is clear and focused
- [x] Methodology is documented and reproducible
- [x] Data sources identified and accessible
- [x] Analysis framework defined
- [x] Evidence tracking files prepared (source-register.csv, evidence-log.csv)

### During Data Gathering (Phase 0 - WP01)
- [ ] All codebase sources documented in source-register.csv (AGENT_DIRS, agent_config.py, init.py, template.py, dashboard/)
- [ ] All 14 agent discovery mechanisms documented from cross-agent doc
- [ ] User pain points quantified (installation time, .gitignore entries, template count, worktree sparse paths)
- [ ] Evidence logged with proper citations and confidence levels
- [ ] Quality threshold maintained (HIGH confidence for codebase facts, MEDIUM for inferred patterns)

### During Workflow Analysis (Phase 1 - WP02-WP07)
- [ ] All 6 workflow patterns analyzed with specific trade-offs (not generic)
- [ ] Adversarial debate conducted for each pattern (pros vs cons)
- [ ] Impact quantified on setup time, version control, collaboration, contributor experience, multi-project management
- [ ] Findings documented in evidence-log.csv with workflow pattern tags
- [ ] Trade-off matrices populated per pattern

### During Agent Compatibility Audit (Phase 2 - WP08)
- [ ] All 14 agents reviewed (Claude, Copilot, Gemini, Cursor, Qwen, OpenCode, Windsurf, Codex, Kilocode, Augment, Roo, Q, Kimi, Mistral)
- [ ] Discovery mechanisms mapped (file-based, MCP, skills) to centralization scenarios
- [ ] Compatibility matrix populated (14 agents × centralization viability)
- [ ] Blockers identified with workarounds
- [ ] Findings support architecture design phase

### During Architecture Design (Phase 3 - WP09)
- [ ] Centralized directory structure designed
- [ ] Project registration protocol specified
- [ ] Backwards compatibility mechanism defined (not just "maintain compatibility")
- [ ] Multi-project dashboard integration designed
- [ ] Migration strategy documented (gradual vs big-bang, opt-in vs automatic)
- [ ] All 14 agents addressed in design

### During Feasibility Assessment (Phase 4 - WP10)
- [ ] Migration risks identified with severity ratings (CRITICAL/HIGH/MEDIUM/LOW)
- [ ] Conflict scenarios documented (project-local vs user-global precedence)
- [ ] Edge cases identified (mid-flight worktrees, legacy projects, custom commands)
- [ ] Implementation complexity estimated (low/medium/high per component)
- [ ] Blockers identified with mitigation strategies
- [ ] Findings support feasibility study synthesis

### Before Synthesis (Phase 5 - WP11-WP14)
- [ ] All workflow analyses complete (WP02-WP07)
- [ ] Agent compatibility audit complete (WP08)
- [ ] Architecture design complete (WP09)
- [ ] Feasibility assessment complete (WP10)
- [ ] Evidence-log.csv contains all findings with confidence levels
- [ ] Source-register.csv contains all sources with review status

### Before Publication (Phase 5 - WP14)
- [ ] Research question answered in recommendation.md
- [ ] All claims cited with evidence IDs (e.g., [EV-042])
- [ ] Methodology clear and reproducible
- [ ] All 4 deliverables complete (decision-framework, architecture-proposal, feasibility-study, recommendation)
- [ ] Bibliography complete in source-register.csv
- [ ] Implementation roadmap provided with prioritization
- [ ] Success metrics defined

## Research Execution Principles

**Deep Research per Work Package**:
- Each WP must conduct thorough investigation, not surface-level analysis
- Adversarial debate required for workflow analyses (challenge assumptions, identify trade-offs)
- Evidence must be cited with confidence levels (no unsupported claims)
- Limitations and alternative interpretations must be documented

**Sequential Dependencies**:
- Each phase builds on previous findings (no parallel execution)
- Later WPs synthesize earlier research (integration of findings)
- Quality gates enforce completeness before progression

**Evidence-Based**:
- All findings logged in evidence-log.csv with source references
- Confidence levels assigned (HIGH/MEDIUM/LOW)
- Claims must reference evidence IDs in deliverables
- Trade-offs must be specific to workflow patterns (not generic pros/cons)

**Backwards Compatibility**:
- CRITICAL constraint in all architectural decisions
- Migration risks must be identified with mitigation strategies
- Existing projects must continue working (1000% requirement)

**Comprehensive Agent Coverage**:
- All 14 agents must be addressed in compatibility audit
- Agent discovery mechanisms mapped to centralization scenarios
- Compatibility blockers identified with workarounds

## Next Steps

**After planning complete**:
1. Run `/spec-kitty.tasks` to generate work packages (WP01-WP14)
2. Finalize task dependencies with `spec-kitty agent feature finalize-tasks`
3. Begin implementation with `spec-kitty implement WP01` (Data Collection)
4. Progress sequentially through phases
5. Synthesize findings in final phase (WP11-WP14)

**Expected Timeline**:
- Phase 0 (WP01): Data Collection & Baseline Analysis
- Phase 1 (WP02-WP07): Workflow Pattern Analysis (sequential)
- Phase 2 (WP08): Agent Compatibility Audit
- Phase 3 (WP09): Architecture Design
- Phase 4 (WP10): Feasibility Assessment
- Phase 5 (WP11-WP14): Synthesis & Recommendation (4 deliverables)

**Deliverable Targets**:
- `decision-framework.md`: Trade-off matrix for user-level vs project-level by workflow
- `architecture-proposal.md`: Centralized design with backwards compatibility + multi-project dashboard
- `feasibility-study.md`: Migration risks, conflict scenarios, agent compatibility (14 agents)
- `recommendation.md`: Evidence-based recommendation with implementation roadmap
