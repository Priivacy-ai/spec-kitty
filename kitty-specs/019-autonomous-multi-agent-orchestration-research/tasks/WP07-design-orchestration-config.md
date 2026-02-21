---
work_package_id: "WP07"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Design Agent Orchestration Config"
phase: "Phase 3 - Configuration Design"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "31941"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP06"
history:
  - timestamp: "2026-01-18T14:41:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Design Agent Orchestration Config

## Objectives & Success Criteria

Design a practical configuration schema for agent preferences based on actual research findings.

**Success Criteria**:

- AgentProfile schema refined with real data from research
- OrchestratorConfig designed with practical defaults
- Fallback strategies documented
- Single-agent mode handled
- Sample `agents.yaml` config created
- `data-model.md` updated with concrete examples

## Context & Constraints

**IMPORTANT**: This WP depends on WP06. The capability matrix must be complete before designing config.

**Design Goals**:

- Config must accommodate all CLI-capable agents discovered
- Must be practical for real-world use
- Should handle graceful degradation when agents unavailable

Reference documents:

- `kitty-specs/019-autonomous-multi-agent-orchestration-research/research.md` - Capability matrix
- `kitty-specs/019-autonomous-multi-agent-orchestration-research/data-model.md` - Schema templates

## Subtasks & Detailed Guidance

### Subtask T031 – Review Capability Matrix for Config Requirements

**Purpose**: Extract config requirements from research findings.

**Steps**:

1. Open `research.md` and review capability matrix
2. For each orchestration-ready agent, note:
   - Required config fields (auth, rate limits, commands)
   - Optional fields based on capabilities
3. Identify common patterns across agents
4. Note agent-specific quirks that need config support
5. List constraints that affect config design

---

### Subtask T032 – Refine AgentProfile Schema

**Purpose**: Update AgentProfile with realistic field values.

**Steps**:

1. Open `data-model.md` and locate AgentProfile schema
2. For each CLI-capable agent discovered, create concrete example:

   ```yaml
   claude-code:
     cli:
       available: true
       command: "claude"
       installation:
         method: "npm"
         package: "@anthropic-ai/claude-code"
     # ... fill from research
   ```

3. Remove fields that no agent uses
4. Add fields discovered during research
5. Ensure schema accommodates all orchestration-ready agents

---

### Subtask T033 – Design OrchestratorConfig

**Purpose**: Create practical user-facing configuration.

**Steps**:

1. Design defaults based on research findings:
   - Which agents are best for implementation?
   - Which agents are best for review?
   - What's a sensible default order?
2. Define priority/preference mechanism
3. Design role assignment (implementation vs review)
4. Handle agents with limited capabilities differently
5. Consider subscription tiers (some users may not have all agents)

**Example structure**:

```yaml
version: "1.0"
defaults:
  implementation: [claude-code, codex, opencode]  # Most capable first
  review: [codex, claude-code]  # Different agents preferred for review
agents:
  claude-code:
    enabled: true
    roles: [implementation, review]
    priority: 100
```

---

### Subtask T034 – Document Fallback Strategies

**Purpose**: Define behavior when preferred agent is unavailable.

**Scenarios to handle**:

1. Preferred agent not installed
2. Preferred agent rate-limited
3. Preferred agent authentication failed
4. Preferred agent returned error

**Fallback options**:

- `next_in_list`: Try next agent in defaults list
- `same_agent`: Use same agent for both roles
- `fail`: Stop and alert user
- `queue`: Wait and retry later

**Steps**:

1. Document each fallback strategy
2. Define default fallback behavior
3. Note implications of each strategy
4. Provide config examples for each

---

### Subtask T035 – Handle Single-Agent Edge Case

**Purpose**: Design for users with only one agent available.

**Scenario**: User has only Claude Code installed and subscribed.

**Requirements**:

- Same agent handles both implementation and review
- No fallback needed (or fail gracefully)
- Config should be simple

**Steps**:

1. Design `single_agent_mode` config section
2. Define auto-detection (only one agent enabled)
3. Handle review-of-own-work implications
4. Provide example config for single-agent setup

---

### Subtask T036 – Update data-model.md

**Purpose**: Replace template schemas with concrete implementations.

**Steps**:

1. Update AgentProfile with real examples from research
2. Update OrchestratorConfig with practical defaults
3. Add concrete example for each CLI-capable agent
4. Document validation rules based on actual constraints
5. Update entity relationships if needed

---

### Subtask T037 – Create Sample agents.yaml

**Purpose**: Provide a working example configuration file.

**Steps**:

1. Create `sample-agents.yaml` in feature directory
2. Include all CLI-capable agents discovered
3. Set sensible defaults based on research
4. Add comments explaining each section
5. Include single-agent mode example (commented)

**File location**: `kitty-specs/019-.../sample-agents.yaml`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Few CLI-capable agents | Simplify config, emphasize single-agent mode |
| Config too complex | Start minimal, add fields as needed |
| Agent capabilities change | Note version/date, design for extensibility |

## Definition of Done Checklist

- [ ] Capability matrix reviewed for config requirements
- [ ] AgentProfile schema refined with real data
- [ ] OrchestratorConfig designed with practical defaults
- [ ] Fallback strategies documented
- [ ] Single-agent mode handled
- [ ] `data-model.md` updated with concrete examples
- [ ] `sample-agents.yaml` created

## Review Guidance

- Verify config accommodates all CLI-capable agents
- Check that defaults are sensible based on research
- Confirm fallback strategies are practical
- Ensure single-agent mode is well-supported

## Activity Log

- 2026-01-18T14:41:27Z – system – lane=planned – Prompt created.
- 2026-01-18T15:42:43Z – claude-opus – shell_pid=30730 – lane=doing – Started implementation via workflow command
- 2026-01-18T15:47:39Z – claude-opus – shell_pid=30730 – lane=for_review – Ready for review: Designed AgentProfile and OrchestratorConfig schemas with concrete examples for all 12 agents, fallback strategies, and single-agent mode handling
- 2026-01-18T15:48:02Z – claude-opus – shell_pid=31941 – lane=doing – Started review via workflow command
- 2026-01-18T15:48:54Z – claude-opus – shell_pid=31941 – lane=done – Review passed: Comprehensive AgentProfile schema for all 12 agents, OrchestratorConfig with practical defaults, 4 fallback strategies documented, single-agent mode with auto-detection, sample-agents.yaml with full/minimal/enterprise examples.
