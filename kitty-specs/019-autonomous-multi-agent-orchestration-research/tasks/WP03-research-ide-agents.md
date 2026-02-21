---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Research IDE-Primary Agents"
phase: "Phase 1 - Agent Investigation"
lane: "done"
assignee: ""
agent: "opencode"
shell_pid: "21385"
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

# Work Package Prompt: WP03 – Research IDE-Primary Agents

## Objectives & Success Criteria

Research the 2 agents that are primarily IDE-based to determine if headless operation is possible:

1. **GitHub Copilot** (Microsoft/GitHub) - VS Code extension, possibly `gh copilot` extension
2. **Windsurf/Codeium** (Codeium) - IDE with AI features, may have language server

**Success Criteria**:

- Both agents have completed research files
- CLI availability documented (Yes/No/Partial)
- Any headless workarounds documented
- Clear assessment of orchestration viability

## Context & Constraints

- **Challenge**: Both are primarily IDE extensions - headless may be limited or unavailable
- **Approach**: Check for GitHub CLI extensions, language server modes, API access
- **Scope**: Headless/CLI only

Reference documents:

- `kitty-specs/019-autonomous-multi-agent-orchestration-research/spec.md` - Research questions
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/plan.md` - Research template

## Subtasks & Detailed Guidance

### Subtask T011 – Research GitHub Copilot [P]

**Purpose**: Determine if GitHub Copilot can be used headlessly.

**Steps**:

1. Check GitHub CLI for Copilot extension:

   ```bash
   gh extension list
   gh extension search copilot
   gh copilot --help
   ```

2. If `gh copilot` exists, test capabilities:

   ```bash
   gh copilot suggest "write a hello world function"
   gh copilot explain "what does this code do"
   ```

3. Search npm for Copilot CLI: `npm search copilot`
4. Check official Copilot documentation for API/CLI access
5. Research Copilot API (may be separate from extension)
6. Document authentication (GitHub token, Copilot subscription)

**Files**: Create `research/02-github-copilot.md`

**Parallel?**: Yes - independent of other agent

**Key Questions**:

- Does `gh copilot` exist and what can it do?
- Can it accept file-based prompts?
- Is there an API for programmatic access?
- What subscription tier is needed?

---

### Subtask T012 – Research Windsurf/Codeium [P]

**Purpose**: Determine if Windsurf (Codeium) can be used headlessly.

**Steps**:

1. Check for Codeium CLI:

   ```bash
   which codeium
   codeium --help
   ```

2. Check for language server headless mode:
   - Codeium uses a language server - can it run standalone?
   - Check for LSP commands
3. Search for Codeium API documentation
4. Check if Windsurf IDE has shell command integration
5. Explore Codeium npm/pip packages
6. Research Codeium authentication (API key, account)

**Files**: Create `research/07-windsurf.md`

**Parallel?**: Yes - independent of other agent

**Key Questions**:

- Does Codeium have a standalone CLI?
- Can the language server be used headlessly?
- Is there a REST/gRPC API?
- What about Windsurf specifically (vs general Codeium)?

---

### Subtask T013 – Document Headless Workarounds

**Purpose**: If direct CLI doesn't exist, document alternative approaches.

**Steps**:

1. For GitHub Copilot:
   - Can you use the OpenAI API directly (Codex)?
   - Is there a REST API for Copilot?
   - Can VS Code be run headlessly with Copilot extension?
2. For Windsurf/Codeium:
   - Can the language server accept prompts?
   - Is there an API endpoint?
   - Can VS Code headless mode work?
3. Document any third-party wrappers or tools
4. Note limitations of workarounds

**Files**: Add workaround sections to both research files

**Parallel?**: No - depends on T011, T012 findings

---

### Subtask T014 – Write Research Files

**Purpose**: Complete both research files following template.

**Steps**:

1. Ensure all sections from plan.md template are filled for both agents
2. Add source links (documentation URLs)
3. Write orchestration assessment for each:
   - Can participate in autonomous workflow? Yes/No/Partial
   - Limitations
   - Integration complexity
4. Be honest about IDE-only status if confirmed

**Files**:

- `research/02-github-copilot.md`
- `research/07-windsurf.md`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No headless option exists | Document clearly, move on |
| API access requires enterprise tier | Document tier requirements |
| Workarounds are fragile | Note stability concerns |
| Features require specific subscriptions | Document subscription requirements |

## Definition of Done Checklist

- [ ] GitHub Copilot researched (gh extension, API, docs)
- [ ] Windsurf/Codeium researched (CLI, language server, API)
- [ ] Headless workarounds documented if applicable
- [ ] Research files created: `research/02-github-copilot.md`, `research/07-windsurf.md`
- [ ] Each file follows template from plan.md
- [ ] Source links included
- [ ] Orchestration assessment completed for each agent

## Review Guidance

- Verify GitHub CLI Copilot extension was tested
- Check that Codeium language server options explored
- Confirm workarounds are practical (not just theoretical)
- Accept IDE-only verdict if thoroughly confirmed

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:27:46Z – claude – shell_pid=24707 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:33:07Z – claude – shell_pid=24707 – lane=for_review – GitHub Copilot CLI has full headless support (-p, --yolo). Windsurf GUI-only, not orchestration-ready.
- 2026-01-18T15:35:21Z – opencode – shell_pid=21385 – lane=doing – Started review via workflow command
- 2026-01-18T15:36:13Z – opencode – shell_pid=21385 – lane=done – Review passed: IDE-first agent research complete
