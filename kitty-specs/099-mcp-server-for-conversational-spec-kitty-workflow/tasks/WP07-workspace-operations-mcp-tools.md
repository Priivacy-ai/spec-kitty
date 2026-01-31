---
work_package_id: WP07
title: Workspace Operations MCP Tools
lane: "done"
dependencies: [WP04]
base_branch: 099-mcp-server-for-conversational-spec-kitty-workflow-WP04
base_commit: e56ef1635c2c9dd6900c273e94eb86cb59ece9cb
created_at: '2026-01-31T12:59:45.493432+00:00'
subtasks:
- T045
- T046
- T047
- T048
- T049
- T050
- T051
phase: Phase 2 - MCP Tools
assignee: 'cursor'
agent: "cursor"
shell_pid: "7525"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
history:
- timestamp: '2026-01-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Workspace Operations MCP Tools

## Objectives & Success Criteria

**Goal**: Implement MCP tools for git worktree management (create, list, merge).

**Success Criteria**: Worktrees created for WPs, --base flag support works, merge with preflight validation

---

## Context & Constraints

**Prerequisites**:
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/spec.md
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/plan.md
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/data-model.md
- Dependencies completed: WP04

**Notes**: Delegates to existing workspace CLI commands

---

## Subtasks & Detailed Guidance

### Subtask T045 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T046 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T047 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T048 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T049 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T050 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust

### Subtask T051 – [Implementation Required]

**Purpose**: See tasks.md for subtask description

**Steps**:
1. Review corresponding entry in tasks.md
2. Implement according to plan.md technical approach
3. Follow data-model.md entity specifications
4. Add tests in tests/mcp/

**Files**: [To be determined during implementation]

**Validation**:
- [ ] Subtask complete and tested
- [ ] Integration with other components verified
- [ ] Error handling robust


---

## Test Strategy

**Unit Tests**: Tests for all subtasks in tests/mcp/

**Integration Tests**: End-to-end workflow tests

**Manual Verification**: Test with MCP client (Claude Desktop, Cursor, or MCP inspector)

---

## Risks & Mitigations

**Risk 1: Integration complexity**
- **Mitigation**: Follow adapter pattern from plan.md, reuse existing CLI code

**Risk 2: Error handling gaps**
- **Mitigation**: Comprehensive try/except, structured OperationResult errors

---

## Review Guidance

**Key Checkpoints**:
- [ ] All subtasks completed and tested
- [ ] No business logic duplication (uses CLIAdapter)
- [ ] Error messages actionable
- [ ] Documentation updated if needed

**Acceptance Criteria**: Success criteria met, all tests passing

---

## Activity Log

- 2026-01-31T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

**Implementation Command**:
```bash
spec-kitty implement WP07 --base WP04
```
- 2026-01-31T13:08:14Z – unknown – shell_pid=94896 – lane=for_review – Ready for review: Workspace operations MCP tools fully implemented. All 7 subtasks (T045-T051) completed. create_worktree with --base support, list_worktrees, and merge operations working. Tool registered with FastMCP server. Comprehensive test suite included.
- 2026-01-31T13:09:30Z – cursor – shell_pid=7525 – lane=doing – Started review via workflow command
- 2026-01-31T13:11:00Z – cursor – shell_pid=7525 – lane=done – Review passed: All 7 subtasks (T045-T051) completed successfully. workspace_operations tool fully implemented with create_worktree (--base support), list_worktrees, and merge operations. Clean code following adapter pattern, comprehensive test suite (15 tests), proper error handling, and FastMCP server registration. Contract compliant with workspace_operations.json schema. No issues found.
