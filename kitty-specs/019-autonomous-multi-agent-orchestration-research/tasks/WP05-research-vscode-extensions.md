---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Research VS Code Extensions"
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

# Work Package Prompt: WP05 – Research VS Code Extensions

## Objectives & Success Criteria

Research the 3 agents that are primarily VS Code extensions:

1. **Kilocode** - VS Code extension
2. **Augment Code** - VS Code/JetBrains extension
3. **Roo Cline** - VS Code extension (fork of Cline)

**Success Criteria**:
- All 3 agents have completed research files
- CLI availability documented (likely limited for all)
- Any headless workarounds documented
- Clear assessment of orchestration viability

## Context & Constraints

- **Challenge**: All three are VS Code extensions - headless operation is unlikely
- **Opportunity**: Cline (Roo Cline's parent) may have CLI or API
- **Approach**: Check for CLIs, APIs, extension host options
- **Scope**: Headless/CLI only

Reference documents:
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/spec.md` - Research questions
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/plan.md` - Research template

## Subtasks & Detailed Guidance

### Subtask T019 – Research Kilocode [P]

**Purpose**: Determine if Kilocode can be used headlessly.

**Steps**:
1. Check for Kilocode CLI:
   ```bash
   which kilocode kilo
   npm search kilocode
   pip search kilocode
   ```
2. Visit Kilocode website/documentation
3. Check VS Code Marketplace for extension details
4. Look for API documentation
5. Search GitHub for Kilocode repositories
6. Document authentication if applicable

**Files**: Create `research/09-kilocode.md`

**Parallel?**: Yes - independent of other agents

**Key Questions**:
- Does Kilocode have any CLI component?
- Is there an API for programmatic access?
- What LLM does it use (own model or third-party)?

---

### Subtask T020 – Research Augment Code [P]

**Purpose**: Determine if Augment Code can be used headlessly.

**Steps**:
1. Check for Augment CLI:
   ```bash
   which augment augment-code
   npm search augment-code
   pip search augment
   ```
2. Visit Augment website/documentation
3. Check VS Code and JetBrains Marketplace listings
4. Look for API documentation
5. Search GitHub for Augment repositories
6. Document authentication requirements

**Files**: Create `research/10-augment-code.md`

**Parallel?**: Yes - independent of other agents

**Key Questions**:
- Does Augment have any CLI component?
- Is there an API for programmatic access?
- What's the relationship to their enterprise offering?
- Is there a language server component?

---

### Subtask T021 – Research Roo Cline [P]

**Purpose**: Determine if Roo Cline (or parent Cline project) can be used headlessly.

**Steps**:
1. Research Cline (original project):
   ```bash
   which cline
   npm search cline cline-ai
   pip search cline
   ```
2. Check Cline GitHub repository for CLI features
3. Research Roo Cline fork differences
4. Look for MCP (Model Context Protocol) integration
5. Check for any headless/server mode
6. Document what distinguishes Roo from standard Cline

**Files**: Create `research/11-roo-cline.md`

**Parallel?**: Yes - independent of other agents

**Key Questions**:
- Does Cline (parent project) have a CLI?
- What does Roo add to standard Cline?
- Is there an API or server mode?
- Can MCP servers be used for automation?

---

### Subtask T022 – Document VS Code Extension Patterns

**Purpose**: Capture common patterns for VS Code extension headless use.

**Steps**:
1. Research VS Code headless/server mode:
   - Can extensions run in VS Code Server?
   - What about code-server (browser-based VS Code)?
2. Document extension host API possibilities
3. Note any common CLI patterns for VS Code extensions
4. Research if extensions can be invoked via VS Code CLI:
   ```bash
   code --extensionDevelopmentPath=/path/to/extension
   ```
5. Document limitations of headless VS Code

**Files**: Add common patterns section to each research file

---

### Subtask T023 – Write Research Files

**Purpose**: Complete all 3 research files following template.

**Steps**:
1. Ensure all sections from plan.md template are filled
2. Be honest about IDE-only limitations
3. Document any workarounds discovered
4. Write orchestration assessment for each:
   - Likely "No" or "Partial" for most
   - Note integration complexity
5. Add source links

**Files**:
- `research/09-kilocode.md`
- `research/10-augment-code.md`
- `research/11-roo-cline.md`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| All are IDE-only | Document clearly, accept limitation |
| Limited documentation | Check GitHub issues, Discord, forums |
| Extensions change frequently | Note version/date tested |
| Headless VS Code is complex | Note as high integration complexity |

## Definition of Done Checklist

- [ ] Kilocode researched
- [ ] Augment Code researched
- [ ] Roo Cline researched (including Cline parent project)
- [ ] VS Code extension patterns documented
- [ ] Research files created: `research/09-kilocode.md`, `research/10-augment-code.md`, `research/11-roo-cline.md`
- [ ] Each file follows template from plan.md
- [ ] Source links included
- [ ] Orchestration assessment completed for each

## Review Guidance

- Verify Cline parent project was researched (key for Roo Cline)
- Check that VS Code headless options were explored
- Accept IDE-only verdict if thoroughly confirmed
- Ensure each extension's unique features noted

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:26:29Z – claude-opus – shell_pid=23155 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:32:30Z – claude-opus – shell_pid=23155 – lane=for_review – Ready for review: VS Code extensions research complete - Kilocode (full CLI), Augment (full CLI), Roo Cline (partial CLI via IPC/forks)
- 2026-01-18T15:33:10Z – opencode – shell_pid=21385 – lane=doing – Started review via workflow command
- 2026-01-18T15:34:34Z – opencode – shell_pid=21385 – lane=done – Review passed: VS Code extension research complete
