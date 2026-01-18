# Work Packages: Autonomous Multi-Agent Orchestration Research

**Inputs**: Design documents from `/kitty-specs/019-autonomous-multi-agent-orchestration-research/`
**Prerequisites**: plan.md (research methodology), spec.md (research questions), data-model.md (schema templates), quickstart.md (CLI testing guide)

**Mission**: Research (no code implementation)

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package produces research artifacts that feed into synthesis phases.

**Parallelization Note**: WP01-WP05 are **fully independent** and can run simultaneously. WP06-WP08 have dependencies and must run sequentially after their prerequisites complete.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different agents/concerns).
- File paths reference `research/XX-agent-name.md` for individual findings.

---

## Work Package WP01: Research Known CLI Agents (Priority: P1) [P]

**Goal**: Investigate the 4 agents with known CLI tools: Claude Code, GitHub Codex, OpenCode, Amazon Q.
**Independent Test**: Each agent has a completed research file with working CLI commands verified locally.
**Prompt**: `tasks/WP01-research-known-cli-agents.md`

### Included Subtasks
- [x] T001 [P] Research Claude Code CLI - docs, install, `claude --help`, test invocation
- [x] T002 [P] Research GitHub Codex CLI - docs, install, `codex --help`, test invocation
- [x] T003 [P] Research OpenCode CLI - docs, install, `opencode --help`, test invocation
- [x] T004 [P] Research Amazon Q CLI - docs, install, `q --help`, test invocation
- [x] T005 Write research files: `research/01-claude-code.md`, `research/08-github-codex.md`, `research/06-opencode.md`, `research/12-amazon-q.md`

### Implementation Notes
- Follow research template from plan.md for each agent
- All 4 agents can be researched in parallel
- Must include: CLI availability, task specification method, completion detection, parallel constraints
- Local testing required: run `--help`, `--version`, and basic prompt

### Parallel Opportunities
- All 4 agents are independent - T001-T004 can run simultaneously

### Dependencies
- None (starting package)

### Risks & Mitigations
- CLI may require paid subscription → document free tier limitations
- Auth tokens needed → document setup without storing secrets

---

## Work Package WP02: Research Cursor CLI (Priority: P1 - User Priority) [P]

**Goal**: Specifically investigate Cursor's CLI capabilities as requested by user.
**Independent Test**: Cursor CLI documented with working invocation example or confirmed as IDE-only.
**Prompt**: `tasks/WP02-research-cursor-cli.md`

### Included Subtasks
- [x] T006 Search for Cursor CLI documentation and installation
- [x] T007 Check Cursor.app for embedded CLI tools (macOS: `/Applications/Cursor.app/Contents/Resources/`)
- [x] T008 Test `cursor --help` or equivalent command
- [x] T009 Document headless invocation method if available
- [x] T010 Write research file: `research/04-cursor.md`

### Implementation Notes
- User specifically requested finding Cursor's CLI
- Check if Cursor has shell command integration like VS Code (`cursor .`)
- Investigate agent mode capabilities vs basic editor commands
- If CLI exists, document full task specification method

### Parallel Opportunities
- T006-T009 are sequential investigation steps

### Dependencies
- None (independent research)

### Risks & Mitigations
- Cursor may be IDE-only → document API alternatives if available
- CLI may be undocumented → test empirically and note unofficial status

---

## Work Package WP03: Research IDE-Primary Agents (Priority: P2) [P]

**Goal**: Investigate GitHub Copilot and Windsurf (Codeium) for headless CLI options.
**Independent Test**: Both agents have completed research files documenting CLI availability or IDE-only status.
**Prompt**: `tasks/WP03-research-ide-agents.md`

### Included Subtasks
- [x] T011 [P] Research GitHub Copilot - check for `gh copilot` extension, API access
- [x] T012 [P] Research Windsurf/Codeium - check for `codeium` CLI, language server headless mode
- [x] T013 Document any headless workarounds (API calls, extension CLIs)
- [x] T014 Write research files: `research/02-github-copilot.md`, `research/07-windsurf.md`

### Implementation Notes
- Both are primarily IDE extensions, likely limited headless support
- Check GitHub CLI (`gh`) for Copilot extension capabilities
- Codeium has language server that might run headless

### Parallel Opportunities
- T011 and T012 can run simultaneously

### Dependencies
- None (independent research)

### Risks & Mitigations
- May be IDE-only → document and move on
- API-only access may have different rate limits

---

## Work Package WP04: Research Cloud/API Agents (Priority: P2) [P]

**Goal**: Investigate Google Gemini and Qwen Code for CLI/API access.
**Independent Test**: Both agents have completed research files with CLI or API invocation methods.
**Prompt**: `tasks/WP04-research-cloud-agents.md`

### Included Subtasks
- [x] T015 [P] Research Google Gemini - check for `gemini` CLI, `gcloud ai` commands, API SDK
- [x] T016 [P] Research Qwen Code - check Alibaba Cloud CLI, DashScope API, any standalone tools
- [x] T017 Document cloud authentication requirements for each
- [x] T018 Write research files: `research/03-google-gemini.md`, `research/05-qwen-code.md`

### Implementation Notes
- Both likely require cloud SDK or direct API calls
- Check for official CLI wrappers or third-party tools
- Document API endpoint structure if no CLI exists

### Parallel Opportunities
- T015 and T016 can run simultaneously

### Dependencies
- None (independent research)

### Risks & Mitigations
- May require cloud account setup → document requirements
- API-only may need wrapper script for orchestration

---

## Work Package WP05: Research VS Code Extensions (Priority: P2) [P]

**Goal**: Investigate Kilocode, Augment Code, and Roo Cline for headless capabilities.
**Independent Test**: All 3 agents have completed research files documenting capabilities.
**Prompt**: `tasks/WP05-research-vscode-extensions.md`

### Included Subtasks
- [x] T019 [P] Research Kilocode - check for CLI, API, extension command interface
- [x] T020 [P] Research Augment Code - check for CLI, API, headless mode
- [x] T021 [P] Research Roo Cline - check Cline project for CLI, fork differences
- [x] T022 Document VS Code extension command patterns if applicable
- [x] T023 Write research files: `research/09-kilocode.md`, `research/10-augment-code.md`, `research/11-roo-cline.md`

### Implementation Notes
- All three are VS Code extensions - may share patterns
- Roo Cline is a fork of Cline - check original project for CLI
- Look for `@command` patterns or task file conventions

### Parallel Opportunities
- T019, T020, T021 can run simultaneously

### Dependencies
- None (independent research)

### Risks & Mitigations
- Extensions typically IDE-only → document and note for orchestration limitations
- May need VS Code extension host to run → document as limitation

---

## Work Package WP06: Synthesize CLI Capability Matrix (Priority: P1)

**Goal**: Consolidate all research findings into comprehensive capability matrix.
**Independent Test**: `research.md` updated with complete matrix and orchestration assessment.
**Prompt**: `tasks/WP06-synthesize-capability-matrix.md`

### Included Subtasks
- [x] T024 Review all 12 agent research files for completeness
- [x] T025 Build CLI capability matrix (agent × capability columns)
- [x] T026 Identify orchestration-ready agents (can participate fully)
- [x] T027 Identify partially-capable agents (need workarounds)
- [x] T028 Identify non-capable agents (cannot participate)
- [x] T029 Update `research.md` with consolidated findings
- [x] T030 Verify quality gates: QG-001 (≥6 CLI agents), QG-002 (Cursor), QG-003 (sources), QG-004 (parallel constraints)

### Implementation Notes
- Cross-reference all research files
- Ensure every cell in matrix has data or explicit "N/A"
- Include source links for all findings

### Parallel Opportunities
- None - sequential synthesis

### Dependencies
- **Depends on**: WP01, WP02, WP03, WP04, WP05 (all research complete)

### Risks & Mitigations
- Missing data → flag incomplete research for follow-up
- Conflicting findings → verify with local testing

---

## Work Package WP07: Design Agent Orchestration Config (Priority: P2)

**Goal**: Propose concrete configuration schema for agent preferences based on findings.
**Independent Test**: `data-model.md` updated with realistic field values and working example config.
**Prompt**: `tasks/WP07-design-orchestration-config.md`

### Included Subtasks
- [x] T031 Review capability matrix for config requirements
- [x] T032 Refine AgentProfile schema with real data from research
- [x] T033 Design OrchestratorConfig with practical defaults
- [x] T034 Document fallback strategies based on agent availability
- [x] T035 Handle single-agent edge case (same agent for impl & review)
- [x] T036 Update `data-model.md` with concrete examples
- [x] T037 Create sample `.kittify/agents.yaml` config file

### Implementation Notes
- Schema must accommodate all CLI-capable agents discovered
- Include realistic rate limits and constraints from research
- Provide sensible defaults based on findings

### Parallel Opportunities
- T032-T35 can be developed incrementally

### Dependencies
- **Depends on**: WP06 (need capability matrix to design realistic config)

### Risks & Mitigations
- Few CLI-capable agents → simplify config, emphasize single-agent mode

---

## Work Package WP08: Final Report & Recommendations (Priority: P1)

**Goal**: Write executive summary, feasibility assessment, and architecture recommendations.
**Independent Test**: Complete research report ready for stakeholder review.
**Prompt**: `tasks/WP08-final-report.md`

### Included Subtasks
- [x] T038 Write executive summary in `research.md`
- [x] T039 Document feasibility assessment: can autonomous orchestration work?
- [x] T040 Identify minimum viable agent set for orchestration
- [ ] T041 Propose architecture approach for orchestrator implementation
- [ ] T042 Document gaps and future research needs
- [ ] T043 Final quality gate verification
- [ ] T044 Update all documentation with cross-references

### Implementation Notes
- Focus on actionable recommendations
- Be honest about limitations discovered
- Provide clear next steps for implementation phase

### Parallel Opportunities
- None - final synthesis

### Dependencies
- **Depends on**: WP06 (capability matrix), WP07 (config schema)

### Risks & Mitigations
- Findings may be disappointing → document honestly, suggest alternatives

---

## Dependency & Execution Summary

```
WP01 (Known CLI)     ─┐
WP02 (Cursor)        ─┼─→ WP06 (Synthesis) ─→ WP07 (Config) ─→ WP08 (Report)
WP03 (IDE Agents)    ─┤
WP04 (Cloud Agents)  ─┤
WP05 (VS Code Ext)   ─┘
```

- **Phase 1 (Parallel)**: WP01, WP02, WP03, WP04, WP05 - all independent
- **Phase 2**: WP06 - depends on Phase 1
- **Phase 3**: WP07 - depends on WP06
- **Phase 4**: WP08 - depends on WP06, WP07

**Parallelization**: 5 research WPs can run simultaneously, dramatically reducing research time.

**MVP Scope**: WP01 + WP02 + WP06 (Known CLI agents + Cursor + basic synthesis)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Research Claude Code CLI | WP01 | P1 | Yes |
| T002 | Research GitHub Codex CLI | WP01 | P1 | Yes |
| T003 | Research OpenCode CLI | WP01 | P1 | Yes |
| T004 | Research Amazon Q CLI | WP01 | P1 | Yes |
| T005 | Write Known CLI research files | WP01 | P1 | No |
| T006 | Search Cursor CLI docs | WP02 | P1 | No |
| T007 | Check Cursor.app CLI tools | WP02 | P1 | No |
| T008 | Test cursor --help | WP02 | P1 | No |
| T009 | Document Cursor headless method | WP02 | P1 | No |
| T010 | Write Cursor research file | WP02 | P1 | No |
| T011 | Research GitHub Copilot | WP03 | P2 | Yes |
| T012 | Research Windsurf/Codeium | WP03 | P2 | Yes |
| T013 | Document headless workarounds | WP03 | P2 | No |
| T014 | Write IDE agents research files | WP03 | P2 | No |
| T015 | Research Google Gemini | WP04 | P2 | Yes |
| T016 | Research Qwen Code | WP04 | P2 | Yes |
| T017 | Document cloud auth requirements | WP04 | P2 | No |
| T018 | Write cloud agents research files | WP04 | P2 | No |
| T019 | Research Kilocode | WP05 | P2 | Yes |
| T020 | Research Augment Code | WP05 | P2 | Yes |
| T021 | Research Roo Cline | WP05 | P2 | Yes |
| T022 | Document VS Code patterns | WP05 | P2 | No |
| T023 | Write VS Code ext research files | WP05 | P2 | No |
| T024 | Review all research files | WP06 | P1 | No |
| T025 | Build capability matrix | WP06 | P1 | No |
| T026 | Identify orchestration-ready agents | WP06 | P1 | No |
| T027 | Identify partially-capable agents | WP06 | P1 | No |
| T028 | Identify non-capable agents | WP06 | P1 | No |
| T029 | Update research.md | WP06 | P1 | No |
| T030 | Verify quality gates | WP06 | P1 | No |
| T031 | Review matrix for config needs | WP07 | P2 | No |
| T032 | Refine AgentProfile schema | WP07 | P2 | No |
| T033 | Design OrchestratorConfig | WP07 | P2 | No |
| T034 | Document fallback strategies | WP07 | P2 | No |
| T035 | Handle single-agent edge case | WP07 | P2 | No |
| T036 | Update data-model.md | WP07 | P2 | No |
| T037 | Create sample agents.yaml | WP07 | P2 | No |
| T038 | Write executive summary | WP08 | P1 | No |
| T039 | Feasibility assessment | WP08 | P1 | No |
| T040 | Minimum viable agent set | WP08 | P1 | No |
| T041 | Orchestrator architecture proposal | WP08 | P1 | No |
| T042 | Document gaps & future research | WP08 | P1 | No |
| T043 | Final quality gate verification | WP08 | P1 | No |
| T044 | Update cross-references | WP08 | P1 | No |
