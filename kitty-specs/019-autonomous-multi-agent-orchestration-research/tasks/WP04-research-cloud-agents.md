---
work_package_id: "WP04"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Research Cloud/API Agents"
phase: "Phase 1 - Agent Investigation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "26919"
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

# Work Package Prompt: WP04 – Research Cloud/API Agents

## Objectives & Success Criteria

Research the 2 agents that are primarily cloud/API-based:

1. **Google Gemini** (Google) - Gemini API, possibly `gemini` CLI or `gcloud ai`
2. **Qwen Code** (Alibaba) - DashScope API, possibly Alibaba Cloud CLI

**Success Criteria**:

- Both agents have completed research files
- CLI or API invocation method documented
- Authentication requirements documented
- Clear assessment of orchestration viability

## Context & Constraints

- **Challenge**: Both may require cloud SDK or direct API calls
- **Approach**: Check for official CLIs, cloud SDK commands, API wrappers
- **Scope**: Headless/CLI only - API calls count if scriptable

Reference documents:

- `kitty-specs/019-autonomous-multi-agent-orchestration-research/spec.md` - Research questions
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/plan.md` - Research template

## Subtasks & Detailed Guidance

### Subtask T015 – Research Google Gemini [P]

**Purpose**: Document Gemini's CLI/API capabilities for automation.

**Steps**:

1. Check for Gemini CLI:

   ```bash
   which gemini
   gemini --help
   pip search google-generativeai
   npm search @google/generative-ai
   ```

2. Check Google Cloud CLI:

   ```bash
   gcloud ai --help
   gcloud ai models list
   ```

3. Research Gemini API:
   - Visit <https://ai.google.dev/docs>
   - Find API endpoint structure
   - Check for code-specific features
4. Check for Google AI Studio CLI tools
5. Document authentication (API key vs OAuth vs service account)
6. Test basic invocation if CLI exists

**Files**: Create `research/03-google-gemini.md`

**Parallel?**: Yes - independent of other agent

**Key Questions**:

- Is there a `gemini` CLI tool?
- Can `gcloud ai` invoke Gemini for code tasks?
- What's the API endpoint for code generation?
- Are there Python/Node SDKs for scripting?
- What about Gemini Code Assist specifically?

---

### Subtask T016 – Research Qwen Code [P]

**Purpose**: Document Qwen Code's CLI/API capabilities.

**Steps**:

1. Check for Qwen CLI:

   ```bash
   which qwen qwen-code
   pip search qwen dashscope
   ```

2. Check Alibaba Cloud CLI:

   ```bash
   aliyun --help
   aliyun ai --help
   ```

3. Research DashScope API (Alibaba's AI platform):
   - Visit <https://dashscope.aliyun.com/>
   - Find API documentation
   - Check for code-specific models
4. Search for third-party Qwen CLI wrappers
5. Document authentication (Alibaba Cloud credentials, API key)
6. Check if Qwen models available on other platforms (Hugging Face, etc.)

**Files**: Create `research/05-qwen-code.md`

**Parallel?**: Yes - independent of other agent

**Key Questions**:

- Is there a standalone Qwen CLI?
- Does Alibaba Cloud CLI have AI/Qwen commands?
- What's the DashScope API structure?
- Can Qwen-Coder models be accessed programmatically?
- Are there open-source Qwen CLI tools?

---

### Subtask T017 – Document Cloud Authentication Requirements

**Purpose**: Detail authentication setup for both cloud agents.

**Steps**:

1. For Google Gemini:
   - Document API key generation process
   - Note OAuth flow if needed
   - Service account setup for CI/CD
   - Environment variable names (GOOGLE_API_KEY, etc.)
2. For Qwen Code:
   - Document Alibaba Cloud account requirements
   - DashScope API key generation
   - Environment variable names
3. Compare authentication complexity
4. Note any regional restrictions

**Files**: Add authentication sections to both research files

---

### Subtask T018 – Write Research Files

**Purpose**: Complete both research files following template.

**Steps**:

1. Ensure all sections from plan.md template are filled
2. For API-only agents, document:
   - How to make API calls from scripts
   - Rate limits and quotas
   - Pricing tier information
3. Write orchestration assessment:
   - Can participate in autonomous workflow? Yes/No/Partial
   - If API-only: note that wrapper script may be needed
4. Add source links

**Files**:

- `research/03-google-gemini.md`
- `research/05-qwen-code.md`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Requires cloud account setup | Document requirements clearly |
| API-only (no CLI) | Note wrapper script needed for orchestration |
| Regional restrictions | Document availability |
| Pricing concerns | Note free tier limits |

## Definition of Done Checklist

- [ ] Google Gemini researched (CLI, gcloud, API)
- [ ] Qwen Code researched (CLI, Alibaba Cloud, DashScope)
- [ ] Authentication requirements documented
- [ ] Research files created: `research/03-google-gemini.md`, `research/05-qwen-code.md`
- [ ] Each file follows template from plan.md
- [ ] Source links included
- [ ] Orchestration assessment completed

## Review Guidance

- Verify cloud CLI options were tested
- Check that API documentation was reviewed
- Confirm authentication steps are actionable
- Accept API-only status if no CLI exists

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:26:17Z – claude-opus – shell_pid=22794 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:31:30Z – claude-opus – shell_pid=22794 – lane=for_review – Ready for review: Completed research on Google Gemini CLI and Qwen Code CLI. Both have full headless mode support, JSON output, auto-approval modes, and are orchestration-ready. Authentication documented for OAuth, API key, and cloud provider options.
- 2026-01-18T15:32:10Z – claude-opus – shell_pid=26919 – lane=doing – Started review via workflow command
- 2026-01-18T15:33:15Z – claude-opus – shell_pid=26919 – lane=done – Review passed: Excellent research. Both Gemini CLI (v0.24.0) and Qwen Code CLI (v0.7.1) verified locally with full headless support. Authentication options comprehensive (OAuth, API key, cloud provider). JSON output formats documented. Both rated orchestration-ready with low integration complexity. Fork relationship between Gemini/Qwen CLIs clearly documented.
