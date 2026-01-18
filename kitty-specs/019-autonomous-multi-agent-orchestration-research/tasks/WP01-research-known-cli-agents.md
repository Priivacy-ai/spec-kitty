---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Research Known CLI Agents"
phase: "Phase 1 - Agent Investigation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "24482"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: []
history:
  - timestamp: "2026-01-18T14:41:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Research Known CLI Agents

## Objectives & Success Criteria

Research the 4 agents with known CLI tools to produce comprehensive capability documentation:

1. **Claude Code** (Anthropic) - `claude` CLI
2. **GitHub Codex** (OpenAI) - `codex` CLI
3. **OpenCode** - `opencode` CLI
4. **Amazon Q** (AWS) - `q` CLI

**Success Criteria**:
- Each agent has a completed research file following the template in `plan.md`
- Working CLI commands verified locally (--help, --version, basic invocation)
- Task specification method documented (how to pass prompts)
- Completion detection documented (exit codes, output format)
- Parallel execution constraints documented

## Context & Constraints

- **Methodology**: Documentation review + local CLI testing
- **Scope**: Headless/CLI only (no IDE integration)
- **Template**: Use agent investigation template from `plan.md`
- **Output**: Individual research files in `research/` directory

Reference documents:
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/spec.md` - Research questions
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/plan.md` - Research template
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/quickstart.md` - CLI testing commands

## Subtasks & Detailed Guidance

### Subtask T001 – Research Claude Code CLI [P]

**Purpose**: Document Claude Code's CLI capabilities for autonomous orchestration.

**Steps**:
1. Check if installed: `which claude && claude --version`
2. If not installed: `npm install -g @anthropic-ai/claude-code` (or find correct package)
3. Run `claude --help` and capture full output
4. Test basic invocation: `claude "What is 2+2?"`
5. Test file-based prompt: `claude --file prompt.md` (if supported)
6. Document authentication: `ANTHROPIC_API_KEY` requirement
7. Check for JSON output mode
8. Document exit codes (test success and error cases)

**Files**: Create `research/01-claude-code.md`

**Parallel?**: Yes - independent of other agents

**Key Questions to Answer**:
- Can it accept a prompt file path as input?
- Does it support stdin for prompts?
- What's the output format (text, JSON, structured)?
- Are there rate limits documented?
- Can multiple instances run simultaneously?

---

### Subtask T002 – Research GitHub Codex CLI [P]

**Purpose**: Document GitHub Codex CLI capabilities.

**Steps**:
1. Check if installed: `which codex && codex --version`
2. If not installed: Research correct installation method (npm, pip, binary)
3. Run `codex --help` and capture full output
4. Test basic invocation with simple prompt
5. Document authentication: `OPENAI_API_KEY` requirement
6. Check for agentic modes (file editing, code generation)
7. Document exit codes and output formats

**Files**: Create `research/08-github-codex.md`

**Parallel?**: Yes - independent of other agents

**Key Questions to Answer**:
- Is this the same as OpenAI Codex or a GitHub-specific tool?
- What's the relationship to GitHub Copilot?
- Can it work on a codebase (vs single-file)?

---

### Subtask T003 – Research OpenCode CLI [P]

**Purpose**: Document OpenCode CLI capabilities.

**Steps**:
1. Check if installed: `which opencode && opencode --version`
2. If not installed: Research installation (npm, pip)
3. Run `opencode --help` and capture full output
4. Test basic invocation
5. Document authentication requirements
6. Check for workspace/project support
7. Document exit codes and output formats

**Files**: Create `research/06-opencode.md`

**Parallel?**: Yes - independent of other agents

**Key Questions to Answer**:
- What LLM does it use?
- How does it handle codebase context?
- Is it actively maintained?

---

### Subtask T004 – Research Amazon Q CLI [P]

**Purpose**: Document Amazon Q Developer CLI capabilities.

**Steps**:
1. Check if installed: `which q && q --version`
2. If not installed: Check AWS CLI v2 or dedicated install
3. Run `q --help` and capture full output
4. Test basic invocation (may require AWS auth)
5. Document authentication: AWS credentials requirement
6. Check for code transformation features
7. Document exit codes and output formats

**Files**: Create `research/12-amazon-q.md`

**Parallel?**: Yes - independent of other agents

**Key Questions to Answer**:
- Is Q part of AWS CLI or standalone?
- What AWS permissions are needed?
- Can it work offline (local models) or cloud-only?

---

### Subtask T005 – Write Research Files

**Purpose**: Ensure all 4 research files are complete and follow template.

**Steps**:
1. Review each research file for completeness
2. Ensure all sections from plan.md template are filled
3. Verify source links are included
4. Confirm working command examples are present
5. Add orchestration assessment (Yes/No/Partial)

**Files**:
- `research/01-claude-code.md`
- `research/08-github-codex.md`
- `research/06-opencode.md`
- `research/12-amazon-q.md`

**Parallel?**: No - depends on T001-T004

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CLI requires paid subscription | Document free tier limitations, test with available tier |
| Auth tokens needed | Document setup steps, never commit secrets |
| CLI is deprecated or renamed | Check release notes, document current status |
| Installation fails | Document error, try alternative install methods |

## Definition of Done Checklist

- [ ] All 4 agents researched with local CLI testing
- [ ] Research files created: `research/01-claude-code.md`, `research/08-github-codex.md`, `research/06-opencode.md`, `research/12-amazon-q.md`
- [ ] Each file follows template from plan.md
- [ ] Working CLI commands verified locally
- [ ] Source links included for all claims
- [ ] Orchestration assessment completed for each agent
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify CLI commands actually work (run them)
- Check that authentication steps are complete
- Confirm exit codes are documented
- Ensure parallel execution constraints noted

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:07:29Z – claude – shell_pid=15619 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:13:01Z – claude – shell_pid=15619 – lane=for_review – All 4 agents researched. Claude, Codex, OpenCode confirmed orchestration-ready. Amazon Q needs Kiro CLI install for full verification.
- 2026-01-18T15:27:32Z – claude-opus – shell_pid=24482 – lane=doing – Started review via workflow command
- 2026-01-18T15:28:36Z – claude-opus – shell_pid=24482 – lane=done – Review passed: All 4 agents researched. Claude, Codex, OpenCode confirmed orchestration-ready with low integration complexity. Amazon Q documented as transitional product (Q→Kiro) with high complexity - acceptable per risk mitigation. Template compliance verified, source links present.
