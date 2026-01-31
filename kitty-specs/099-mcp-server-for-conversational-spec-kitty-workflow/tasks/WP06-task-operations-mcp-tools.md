---
work_package_id: WP06
title: Task Operations MCP Tools
lane: "done"
dependencies:
- WP03
base_branch: 099-mcp-server-for-conversational-spec-kitty-workflow-WP04
base_commit: e56ef1635c2c9dd6900c273e94eb86cb59ece9cb
created_at: '2026-01-31T12:51:49.587564+00:00'
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
- T043
- T044
phase: Phase 2 - MCP Tools
assignee: 'cursor'
agent: "cursor"
shell_pid: "95501"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
history:
- timestamp: '2026-01-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Task Operations MCP Tools

## Objectives & Success Criteria

**Goal**: Implement MCP tools for task management (list, move, add_history, query_status).

**Success Criteria**: Tasks can be listed, moved between lanes with locking, history added, status queried

---

## Context & Constraints

**Prerequisites**:
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/spec.md
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/plan.md
- Review kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/data-model.md
- Dependencies completed: WP03, WP04

**Notes**: move_task requires locking from WP03

---

## Subtasks & Detailed Guidance

### Subtask T037 – [Implementation Required]

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

### Subtask T038 – [Implementation Required]

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

### Subtask T039 – [Implementation Required]

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

### Subtask T040 – [Implementation Required]

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

### Subtask T041 – [Implementation Required]

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

### Subtask T042 – [Implementation Required]

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

### Subtask T043 – [Implementation Required]

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

### Subtask T044 – [Implementation Required]

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
spec-kitty implement WP06 --base WP03
```
- 2026-01-31T12:59:13Z – unknown – shell_pid=84937 – lane=for_review – Ready for review: Implemented all task operations MCP tools with locking, comprehensive tests, and documentation
- 2026-01-31T13:00:17Z – cursor – shell_pid=95501 – lane=doing – Started review via workflow command
- 2026-01-31T13:02:01Z – cursor – shell_pid=95501 – lane=done – Review passed: All task operations implemented correctly with proper locking (WP03), CLIAdapter integration (WP04), comprehensive tests (823 lines), and excellent documentation. All 8 subtasks complete. Code quality is excellent with proper error handling and no business logic duplication.
