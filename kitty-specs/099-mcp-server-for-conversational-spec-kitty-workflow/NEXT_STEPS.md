# Next Steps: MCP Server Implementation

**Feature**: 099-mcp-server-for-conversational-spec-kitty-workflow  
**Status**: Planning Complete, Ready for Implementation  
**Total Work**: 12 Work Packages, 90 Subtasks

---

## 🎯 Quick Start

**To begin implementation immediately**:

```bash
# Start with the foundation
spec-kitty implement WP01
```

---

## 📋 Implementation Roadmap

### Phase 1: Foundation (Sequential - Must Complete First)

These work packages build the core infrastructure and must be done in order:

```bash
# 1. Core MCP Server Foundation (6 subtasks)
spec-kitty implement WP01
# Creates: FastMCP server, stdio/SSE transports, server.py
# Time estimate: ~4-6 hours

# 2. Project Context & State Management (7 subtasks)
spec-kitty implement WP02 --base WP01
# Creates: ProjectContext, ConversationState, JSON persistence
# Time estimate: ~5-7 hours

# 3. File Locking & Concurrency Control (6 subtasks)
spec-kitty implement WP03 --base WP02
# Creates: ResourceLock, filelock integration, stale cleanup
# Time estimate: ~4-5 hours

# 4. CLI Adapter Layer (7 subtasks)
spec-kitty implement WP04 --base WP02
# Creates: OperationResult, CLIAdapter wrapping existing code
# Time estimate: ~5-6 hours
```

**Foundation Total**: ~18-24 hours (sequential)

---

### Phase 2: MCP Tools (Parallel - High Velocity!)

After Phase 1 completes, these 6 work packages can run **in parallel**:

```bash
# Run in separate terminals/worktrees/agents simultaneously:

# Terminal 1: Feature Operations (10 subtasks)
spec-kitty implement WP05 --base WP04
# Creates: feature_tools.py, specify/plan/tasks/implement/review/accept operations
# Time estimate: ~6-8 hours

# Terminal 2: Task Operations (8 subtasks)
spec-kitty implement WP06 --base WP04
# Creates: task_tools.py, list/move/add_history/query_status operations
# Time estimate: ~4-6 hours

# Terminal 3: Workspace Operations (7 subtasks)
spec-kitty implement WP07 --base WP04
# Creates: workspace_tools.py, worktree management operations
# Time estimate: ~4-5 hours

# Terminal 4: System Operations (8 subtasks)
spec-kitty implement WP08 --base WP02
# Creates: system_tools.py, health/validation/missions/config operations
# Time estimate: ~4-5 hours

# Terminal 5: API Key Authentication (7 subtasks)
spec-kitty implement WP09 --base WP01
# Creates: auth module, API key validation, middleware
# Time estimate: ~3-4 hours

# Terminal 6: CLI Integration (7 subtasks)
spec-kitty implement WP12 --base WP01
# Creates: mcp CLI commands (start/status/stop), PID management
# Time estimate: ~4-5 hours
```

**Parallel Total**: ~6-8 hours (if 6 agents work simultaneously)  
**Sequential Total**: ~25-33 hours (if one agent does all)

**Parallelization Savings**: 75-80% time reduction! 🚀

---

### Phase 3: Finalization (Sequential)

After Phase 2 completes:

```bash
# 7. Integration Tests (9 subtasks)
spec-kitty implement WP10 --base WP08
# Creates: Comprehensive test suite for all MCP tools
# Time estimate: ~6-8 hours

# 8. Documentation (8 subtasks)
spec-kitty implement WP11 --base WP09
# Creates: Complete quickstart.md with client examples
# Time estimate: ~4-6 hours
```

**Finalization Total**: ~10-14 hours (sequential)

---

## 📊 Timeline Summary

| Approach | Duration | Notes |
|----------|----------|-------|
| **Sequential** (1 agent) | ~53-71 hours | All WPs done one at a time |
| **Partial Parallel** (3 agents) | ~28-36 hours | Phase 2 parallelized across 3 agents |
| **Full Parallel** (6 agents) | ~34-46 hours | Phase 2 fully parallelized across 6 agents |

**Recommended**: Partial parallel with 3 agents for optimal cost/speed balance.

---

## 🎯 MVP Scope (Minimum Viable Product)

For fastest time-to-value, complete these 7 WPs first:

```bash
# MVP work packages (49 subtasks):
WP01 - Core MCP Server Foundation ✓
WP02 - Project Context & State ✓
WP03 - File Locking ✓
WP04 - CLI Adapter Layer ✓
WP05 - Feature Operations Tools ✓
WP06 - Task Operations Tools ✓
WP12 - CLI Integration ✓
```

**MVP Deliverable**: Users can create features and manage tasks conversationally via MCP.

**MVP Timeline**: ~30-40 hours (sequential) or ~18-24 hours (with 3 agents)

---

## 📁 File Locations

All work package prompts are in:
```
kitty-specs/099-mcp-server-for-conversational-spec-kitty-workflow/tasks/
├── WP01-core-mcp-server-foundation.md (detailed, 500 lines)
├── WP02-project-context-and-state-management.md (detailed, 650 lines)
├── WP03-file-locking-and-concurrency-control.md (detailed, 350 lines)
├── WP04-cli-adapter-layer.md (detailed, 630 lines)
├── WP05-feature-operations-mcp-tools.md (concise, 200 lines)
├── WP06-task-operations-mcp-tools.md (concise, 150 lines)
├── WP07-workspace-operations-mcp-tools.md (concise, 150 lines)
├── WP08-system-operations-and-health-check.md (concise, 160 lines)
├── WP09-api-key-authentication.md (concise, 150 lines)
├── WP10-mcp-client-integration-tests.md (concise, 180 lines)
├── WP11-documentation-and-quickstart-guide.md (concise, 170 lines)
└── WP12-cli-command-integration-and-server-management.md (concise, 150 lines)
```

**Master checklist**: `tasks.md` (12 WPs, 90 subtasks)

---

## 🔍 Implementation Tips

### Before Starting Any WP

1. **Read the prompt file thoroughly** - Contains all implementation details
2. **Review dependencies** - Check frontmatter for required WPs
3. **Check tasks.md** - Understand how your WP fits into overall plan
4. **Review design docs**:
   - `spec.md` - User stories and requirements
   - `plan.md` - Technical approach and architecture
   - `data-model.md` - Entity specifications

### During Implementation

1. **Follow the subtask order** - They're sequenced for optimal flow
2. **Mark subtasks complete** - Check off boxes in prompt file as you go
3. **Write tests as you code** - Don't defer testing to end
4. **Commit frequently** - Small, atomic commits with clear messages
5. **Update activity log** - Record progress in WP frontmatter

### Code Quality Standards

- **No business logic duplication** - Use CLIAdapter to wrap existing CLI code
- **Type hints everywhere** - Python 3.11+ type annotations
- **Docstrings for all classes/methods** - Google style
- **Error handling** - All exceptions → OperationResult with errors
- **Tests for every subtask** - Unit + integration coverage

### When You're Stuck

1. Check if dependency WPs are complete
2. Review plan.md for architectural guidance
3. Look at existing CLI code for patterns
4. Ask clarifying questions (don't guess)

---

## 🧪 Testing Strategy

### Unit Tests (Per WP)

Each WP includes specific test requirements in the prompt. Create tests in:
```
tests/mcp/
├── test_server.py           # WP01
├── test_context.py           # WP02
├── test_state.py             # WP02
├── test_locking.py           # WP03
├── test_cli_adapter.py       # WP04
├── test_feature_tools.py     # WP05
├── test_task_tools.py        # WP06
├── test_workspace_tools.py   # WP07
├── test_system_tools.py      # WP08
└── test_auth.py              # WP09
```

### Integration Tests (WP10)

End-to-end tests using FastMCP test client:
- Server startup/shutdown
- Tool invocation via MCP protocol
- Multi-turn conversations
- Concurrent client access
- Error handling

### Manual Verification

After each WP:
```bash
# Start server
spec-kitty mcp start --transport stdio

# Use MCP inspector (if available)
# Or configure Claude Desktop/Cursor to connect
```

---

## 📦 Dependencies to Install

These will be added during implementation:

```toml
# In src/specify_cli/pyproject.toml
dependencies = [
    # ... existing ...
    "fastmcp>=1.0.0,<2.0.0",     # WP01
    "filelock>=3.12.0,<4.0.0",   # WP03
]
```

---

## 🚀 Success Criteria

### Per-WP Acceptance

Each WP frontmatter includes specific success criteria. General checklist:

- [ ] All subtasks completed
- [ ] All tests passing (unit + integration where applicable)
- [ ] No linter errors
- [ ] Docstrings complete
- [ ] Activity log updated
- [ ] Ready for review

### Feature-Level Acceptance (SC-001 to SC-011)

From spec.md:
- [ ] **SC-001**: Create feature specification conversationally without docs
- [ ] **SC-003**: 100% CLI workflow parity via MCP tools
- [ ] **SC-004**: Manage 3+ concurrent projects without state corruption
- [ ] **SC-006**: 95% conversational commands correctly interpreted
- [ ] **SC-007**: Server startup <2s, read operations <500ms
- [ ] **SC-011**: Core workflow changes auto-benefit MCP interface

---

## 📝 Workflow Commands

### Moving Through Lanes

```bash
# When starting implementation
spec-kitty agent tasks move-task WP01 --to doing --note "Starting implementation"

# When ready for review
spec-kitty agent tasks move-task WP01 --to for_review --note "Implementation complete"

# After review approval
spec-kitty agent tasks move-task WP01 --to done --note "Review passed"
```

### Checking Status

```bash
# See kanban board
spec-kitty agent tasks status

# See what's ready to work on
spec-kitty agent tasks list-tasks --lane planned

# See what's in review
spec-kitty agent tasks list-tasks --lane for_review
```

---

## 🎓 Learning Resources

### MCP Protocol
- FastMCP docs: https://fastmcp.dev
- MCP spec: https://modelcontextprotocol.io

### Spec Kitty Patterns
- Review existing CLI commands in `src/specify_cli/cli/commands/`
- Review agent utilities in `src/specify_cli/agent_utils/`
- Check AGENTS.md for development guidelines

### Testing
- FastMCP test utilities: Check FastMCP documentation
- Pytest fixtures: `tests/conftest.py`

---

## 🤝 Collaboration

### For Multiple Agents

1. **Claim a WP**: Move to "doing" lane with your agent ID in assignee field
2. **Communicate dependencies**: If you need output from another WP, coordinate
3. **Don't block others**: Parallelize Phase 2 across different agents
4. **Review each other's work**: Cross-agent review catches more issues

### Git Workflow

```bash
# Each WP gets its own worktree
spec-kitty implement WP01  # Creates .worktrees/099-mcp-server-WP01/

# Work in the worktree
cd .worktrees/099-mcp-server-WP01/

# Commit frequently
git commit -m "WP01: Implement MCPServer class"

# When done, return to main and merge
spec-kitty merge --feature 099-mcp-server-for-conversational-spec-kitty-workflow
```

---

## ✅ Ready to Start?

**First command to run**:

```bash
spec-kitty implement WP01
```

This creates a worktree for WP01, branches from main, and displays the full implementation prompt.

**Good luck! 🚀**

---

*Generated: 2026-01-31*  
*Feature: 099-mcp-server-for-conversational-spec-kitty-workflow*  
*Total effort: 12 WPs, 90 subtasks, ~34-71 hours depending on parallelization*
