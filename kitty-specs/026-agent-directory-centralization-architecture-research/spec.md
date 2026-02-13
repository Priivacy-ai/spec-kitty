# Research Specification: Agent Directory Centralization Architecture

**Feature Branch**: `026-agent-directory-centralization-architecture-research`
**Created**: 2026-02-01
**Status**: Draft
**Research Type**: Architecture Analysis & Design Study

## Research Question & Scope

**Primary Research Question**: Should Spec Kitty's agent directories (.claude/, .codex/, .gemini/, etc.) be centralized at the user level (~/.spec-kitty/ or similar) instead of duplicated per project, and if so, what architecture enables this while maintaining backwards compatibility?

**Sub-Questions**:
1. What are the architectural trade-offs (user-level vs project-level) for each of the 6 primary workflow patterns (solo single-project, solo multi-project, team shared-repo, mono-repo, mixed agents, open source)?
2. What centralized architecture design supports all 14 documented agents, multi-project dashboard registration, and backwards compatibility?
3. What migration risks, conflict scenarios, and compatibility issues exist for transitioning from project-level to user-level agent directories?
4. What is the recommended approach (centralized, hybrid, or status quo) based on evidence from workflow analysis, architectural design, and feasibility assessment?

**Scope**:
- **In Scope**:
  - Analysis of all 6 workflow patterns individually
  - Architecture design for centralized agent directories (12 agent types)
  - Multi-project dashboard registration protocol
  - Migration strategy with backwards compatibility requirement (CRITICAL)
  - All 14 documented agents (Claude Code, GitHub Copilot, Google Gemini, Cursor, Qwen Code, OpenCode, Windsurf, GitHub Codex, Kilocode, Augment Code, Roo Cline, Amazon Q, Kimi Code CLI, Mistral Code)
  - Worktree sparse checkout implications
  - .gitignore management simplification
  - Template versioning and consistency across projects

- **Out of Scope**:
  - Implementation of the proposed architecture (research only)
  - Changes to .kittify/ or kitty-specs/ directory structure
  - Changes to .worktrees/ model (stays in project directory)
  - Non-agent configuration files
  - Jujutsu (jj) vs Git VCS considerations (orthogonal concern)

- **Boundaries**:
  - Current Spec Kitty architecture (v0.15.0+ codebase)
  - Agent discovery patterns documented in product-ideas/agent-command-discovery-and-skills.md
  - Existing pain points: installation/upgrade time, .gitignore maintenance, template versioning, worktree sparse checkout complexity

**Expected Outcomes**:
- `decision-framework.md`: Decision criteria and trade-off matrix for choosing user-level vs project-level based on workflow characteristics
- `architecture-proposal.md`: Complete architectural design for centralized agent directories including project registration protocol, backwards compatibility mechanism, and multi-project dashboard integration
- `feasibility-study.md`: Migration risk analysis, conflict scenarios, compatibility assessment across all 14 agents, and implementation complexity estimate
- `recommendation.md`: Evidence-based recommendation with implementation roadmap, prioritized by impact vs effort

## Research Methodology Outline

### Research Approach
- **Method**: Multi-method study combining:
  - **Systematic Workflow Analysis**: Evaluate 6 workflow patterns against centralization criteria
  - **Architecture Design**: Propose centralized design with backwards compatibility
  - **Compatibility Audit**: Review all 14 agent discovery mechanisms for centralization viability
  - **Feasibility Assessment**: Analyze migration risks, conflict scenarios, and edge cases
  - **Adversarial Debate**: Identify pros and cons of centralization for each workflow pattern

- **Data Sources**:
  - Current Spec Kitty codebase (`/Users/robert/ClaudeCowork/SpecKitty/spec-kitty/`)
  - Agent discovery documentation (`product-ideas/agent-command-discovery-and-skills.md`)
  - User pain points (installation time, .gitignore burden, template versioning, worktree complexity)
  - AGENT_DIRS constant (`src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`)
  - Agent config management (`src/specify_cli/orchestrator/agent_config.py`)
  - Init workflow (`src/specify_cli/cli/commands/init.py`)
  - Dashboard implementation (`src/specify_cli/dashboard/`)
  - Cross-agent compatibility matrix (14 agents × 3 discovery mechanisms)

- **Analysis Approach**:
  - **Workflow Analysis**: For each of 6 patterns, evaluate centralization impact on setup time, version control, team collaboration, contributor experience, and multi-project management
  - **Architecture Design**: Design centralized directory structure, registration protocol, fallback mechanisms, and migration strategy
  - **Compatibility Analysis**: Map each agent's discovery mechanism (file-based commands, MCP prompts, skills) to centralized architecture
  - **Feasibility Analysis**: Identify migration blockers, conflict scenarios (project-local vs user-global precedence), and backwards compatibility requirements
  - **Trade-off Analysis**: Weigh benefits (reduced duplication, simplified .gitignore, consistent versioning) against costs (migration complexity, per-project customization loss, potential conflicts)

### Success Criteria
- All 6 workflow patterns analyzed with specific trade-offs identified (not generic pros/cons)
- Complete architectural design addressing backwards compatibility, multi-project dashboard, and all 14 agents
- Migration risks and conflict scenarios documented with mitigation strategies
- Evidence-based recommendation with clear decision criteria
- All deliverables (decision-framework.md, architecture-proposal.md, feasibility-study.md, recommendation.md) completed with cited evidence

## Research Requirements

### Data Collection Requirements
- **DR-001**: Research MUST analyze all 6 workflow patterns individually (solo single-project, solo multi-project, team shared-repo, mono-repo, mixed agents, open source)
- **DR-002**: Research MUST document agent discovery mechanisms for all 14 agents from `product-ideas/agent-command-discovery-and-skills.md`
- **DR-003**: Research MUST identify current pain points from user feedback (installation time, .gitignore maintenance, template versioning, worktree sparse checkout complexity)
- **DR-004**: Research MUST analyze current codebase implementation (AGENT_DIRS, agent_config.py, init.py, dashboard/)
- **DR-005**: All findings MUST be documented in `research/evidence-log.csv` with confidence levels (HIGH/MEDIUM/LOW)
- **DR-006**: All sources MUST be documented in `research/source-register.csv` with file paths, relevance, and status

### Analysis Requirements
- **AR-001**: Decision framework MUST provide specific criteria for choosing user-level vs project-level based on measurable workflow characteristics
- **AR-002**: Architecture proposal MUST address backwards compatibility (CRITICAL requirement), multi-project dashboard registration, and all 14 agent compatibility
- **AR-003**: Feasibility study MUST identify migration risks, conflict scenarios (e.g., project-local customizations vs user-global defaults), and compatibility blockers
- **AR-004**: Recommendation MUST be evidence-based with clear rationale, implementation roadmap, and prioritization (impact vs effort)
- **AR-005**: All architectural decisions MUST consider migration path from current project-level model
- **AR-006**: Analysis MUST preserve .kittify/ and kitty-specs/ in project directories (not moving to user-level)

### Quality Requirements
- **QR-001**: All claims MUST be supported by cited evidence (codebase references, agent documentation, or user pain points)
- **QR-002**: Confidence levels MUST be assigned to all findings in `research/evidence-log.csv`
- **QR-003**: Alternative architectures (pure user-level, pure project-level, hybrid) MUST be considered with trade-offs
- **QR-004**: Edge cases MUST be identified (e.g., conflicting versions across projects, per-project customizations, team vs solo workflows)
- **QR-005**: Backwards compatibility mechanism MUST be clearly defined (not just "maintain compatibility")

## Key Concepts & Terminology

- **Agent Directories**: The 12 agent-specific directories (.claude/, .codex/, .gemini/, etc.) containing slash commands, prompts, workflows, and skills. Currently duplicated per project.
- **User-Level Centralization**: Storing agent directories in a user's home directory (~/.spec-kitty/agents/ or similar) instead of per-project, with projects registering with the central location.
- **Project-Level Duplication**: Current model where each project has its own copy of all agent directories, requiring installation/upgrade per project.
- **Hybrid Model**: Architecture where some agent assets are user-level (shared commands) and some are project-level (project-specific customizations).
- **Backwards Compatibility**: Existing Spec Kitty projects must continue working during/after migration without manual intervention (CRITICAL constraint).
- **Project Registration**: Mechanism for projects to register with centralized dashboard, enabling multi-project views and shared agent directories.
- **Sparse Checkout**: Git worktree feature that excludes specific directories (currently used to exclude agent directories from worktrees, adding complexity).
- **Template Versioning**: Keeping slash command templates synchronized across projects (current pain point with project-level duplication).
- **Agent Discovery**: Mechanism by which AI agents find slash commands (file-based in specific directories, MCP prompts, or skills - varies by agent).
- **Workflow Patterns**: The 6 distinct usage scenarios (solo single-project, solo multi-project, team shared-repo, mono-repo, mixed agents, open source) with different centralization implications.

## Evidence Tracking Guidance

- Log every analyzed code file in `research/source-register.csv` with file path, purpose, relevance (HIGH/MEDIUM/LOW), and review status (pending/reviewed/excluded).
- Capture each key finding in `research/evidence-log.csv` with finding ID, evidence source, confidence level (HIGH/MEDIUM/LOW), and supporting notes.
- Reference evidence row IDs within deliverable documents when making claims (e.g., "Installation time concern [EV-003]").
- Document all architectural trade-offs with pros, cons, and affected workflow patterns.
- Track migration risks in separate section of feasibility study with severity (CRITICAL/HIGH/MEDIUM/LOW) and mitigation strategy.

## Workflow Patterns for Analysis

### WF-001: Solo Developer, Single Project
- **Characteristics**: One developer, one active Spec Kitty project at a time
- **Centralization Impact**: Minimal benefit (no duplication across projects), but simpler .gitignore and no sparse checkout complexity
- **Analysis Focus**: Setup friction vs maintenance burden trade-off

### WF-002: Solo Developer, Multiple Projects
- **Characteristics**: One developer juggling multiple Spec Kitty projects simultaneously
- **Centralization Impact**: HIGH benefit - avoid duplicating agent dirs across N projects, enable multi-project dashboard
- **Analysis Focus**: Template versioning consistency, upgrade workflow simplification, dashboard multi-project features

### WF-003: Team, Shared Repository
- **Characteristics**: Multiple developers collaborating on same Spec Kitty project
- **Centralization Impact**: Complex - version control implications, per-developer vs shared configuration
- **Analysis Focus**: .gitignore management, agent selection coordination, custom command sharing

### WF-004: Mono-Repo with Multiple Features
- **Characteristics**: One repository with many concurrent feature worktrees
- **Centralization Impact**: HIGH benefit - eliminate worktree sparse checkout complexity, reduce disk usage
- **Analysis Focus**: Worktree setup time, sparse checkout overhead, disk space savings

### WF-005: Mixed Agent Environments
- **Characteristics**: Team members use different AI agents (some Claude Code, some Cursor, some Codex)
- **Centralization Impact**: Complex - agent selection per developer vs per project
- **Analysis Focus**: Heterogeneous tooling support, selective agent installation, config conflicts

### WF-006: Open Source Projects
- **Characteristics**: Public repositories where contributor setup friction matters
- **Centralization Impact**: Mixed - simpler .gitignore (no agent dirs), but contributors need user-level setup
- **Analysis Focus**: Contributor onboarding, public repo .gitignore cleanliness, setup documentation burden

## Deliverable Structure

Each deliverable document must follow this structure:

### decision-framework.md
- Decision tree or criteria matrix for choosing user-level vs project-level vs hybrid
- Workflow pattern characteristics (single vs multi-project, solo vs team, homogeneous vs mixed agents)
- Trade-off analysis for each pattern
- Recommended approach per workflow pattern

### architecture-proposal.md
- Centralized directory structure design (~/.spec-kitty/agents/ or alternative)
- Project registration protocol (how projects register with central location)
- Backwards compatibility mechanism (fallback to project-level if user-level missing)
- Multi-project dashboard integration (registration database, project discovery)
- Agent discovery compatibility (all 14 agents must work)
- Migration strategy (gradual vs big-bang, opt-in vs automatic)

### feasibility-study.md
- Migration risks (backwards compatibility, data loss, conflicts)
- Conflict scenarios (project-local customizations vs user-global defaults, version mismatches)
- Agent compatibility matrix (14 agents × centralization viability)
- Edge cases (mid-flight worktrees, legacy projects, custom commands)
- Implementation complexity estimate (low/medium/high per component)
- Blockers and mitigation strategies

### recommendation.md
- Evidence summary (key findings from analysis)
- Recommended approach (centralized, hybrid, or status quo) with clear rationale
- Implementation roadmap (phased approach with milestones)
- Prioritization (impact vs effort matrix)
- Success metrics (how to measure success post-implementation)
- Open questions requiring further investigation

## Constraints & Assumptions

### Hard Constraints
- **Backwards Compatibility**: Existing projects MUST continue working (1000% requirement)
- **All 14 Agents**: Solution MUST work for all documented agents
- **.worktrees/ Stays in Project**: Workspace-per-WP model not affected by this research
- **.kittify/ Stays in Project**: Project configuration and mission templates remain project-local
- **kitty-specs/ Stays in Project**: Feature specifications remain project-local

### Assumptions
- Agent directories contain only slash commands/prompts/workflows (no project-specific data)
- Template versioning across projects is desirable (consistent slash command behavior)
- Multi-project dashboard is a strategic direction (not just a nice-to-have)
- Installation/upgrade time per project is a significant pain point
- Sparse checkout complexity in worktrees is a real burden

### Open Questions (To Be Resolved by Research)
- Should user-level be opt-in or default for new projects?
- How to handle project-specific customizations (if any) in centralized model?
- What happens when different projects need different agent template versions?
- Should migration be gradual (coexistence) or big-bang (one-time cutover)?
- How to handle agents that don't support user-level directories (if any)?
