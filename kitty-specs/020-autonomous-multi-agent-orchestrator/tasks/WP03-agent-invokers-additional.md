---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Agent Invokers - Additional Agents"
phase: "Phase 1 - Components"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "46825"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
  - "WP02"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Agent Invokers - Additional Agents

## Objectives & Success Criteria

Complete the remaining 4 agent invokers (Qwen, OpenCode, Kilocode, Augment, Cursor) plus agent detection utilities.

**Success Criteria**:
- All 9 agent invokers implemented
- Cursor invoker includes timeout wrapper
- Agent registry maps agent_id → invoker class
- Detection utility returns list of installed agents

## Context & Constraints

**Reference Documents**:
- [plan.md](../plan.md) - Agent invocation patterns table
- [spec.md](../spec.md) - FR-007 (Cursor timeout workaround)

**Invocation Patterns**:

| Agent | Command | Task Input | Headless Flag | JSON Output |
|-------|---------|------------|---------------|-------------|
| Qwen Code | `qwen` | stdin | `-p` | `--output-format json` |
| OpenCode | `opencode run` | stdin or `-f` | (default) | `--format json` |
| Kilocode | `kilocode` | arg | `-a` | `-j` |
| Augment Code | `auggie` | arg | `--acp` | (exit code only) |
| Cursor | `cursor agent` | arg | `-p` | `--output-format json` |

**Implementation Command**:
```bash
spec-kitty implement WP03 --base WP02
```

## Subtasks & Detailed Guidance

### Subtask T011 – Implement Qwen Code invoker

**Purpose**: Invoker for Qwen Code CLI (`qwen`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/qwen.py`
2. Implement QwenInvoker:
   ```python
   class QwenInvoker(BaseInvoker):
       agent_id = "qwen"
       command = "qwen"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           return [
               "qwen",
               "-p",
               "--yolo",
               "--output-format", "json",
           ]
   ```

**Notes**:
- Qwen is a fork of Gemini CLI, similar flags
- Prompt via stdin

**Parallel?**: Yes

---

### Subtask T012 – Implement OpenCode invoker

**Purpose**: Invoker for OpenCode CLI (`opencode`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/opencode.py`
2. Implement OpenCodeInvoker:
   ```python
   class OpenCodeInvoker(BaseInvoker):
       agent_id = "opencode"
       command = "opencode"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           return [
               "opencode", "run",
               "--format", "json",
           ]
   ```

**Notes**:
- OpenCode uses `opencode run` subcommand
- Prompt via stdin
- Multi-provider support (can use various LLM backends)

**Parallel?**: Yes

---

### Subtask T013 – Implement Kilocode invoker

**Purpose**: Invoker for Kilocode CLI (`kilocode`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/kilocode.py`
2. Implement KilocodeInvoker:
   ```python
   class KilocodeInvoker(BaseInvoker):
       agent_id = "kilocode"
       command = "kilocode"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           return [
               "kilocode",
               "-a",                    # Autonomous mode
               "--yolo",
               "-j",                    # JSON output
               prompt,                  # Prompt as positional argument
           ]
   ```

**Notes**:
- Kilocode takes prompt as argument, not stdin
- `-a` enables autonomous agent mode
- `-j` for JSON output

**Parallel?**: Yes

---

### Subtask T014 – Implement Augment Code invoker

**Purpose**: Invoker for Augment Code CLI (`auggie`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/augment.py`
2. Implement AugmentInvoker:
   ```python
   class AugmentInvoker(BaseInvoker):
       agent_id = "augment"
       command = "auggie"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           return [
               "auggie",
               "--acp",                 # Autonomous coding prompt
               prompt,
           ]

       def parse_output(self, stdout: str, stderr: str, exit_code: int) -> InvocationResult:
           # Auggie doesn't support JSON output, use exit code only
           return InvocationResult(
               success=exit_code == 0,
               exit_code=exit_code,
               files_modified=None,
               commits_made=None,
               errors=[stderr] if exit_code != 0 else None,
               warnings=None,
               stdout=stdout,
               stderr=stderr,
               duration_seconds=0.0,
           )
   ```

**Notes**:
- Auggie uses `--acp` for autonomous coding prompt
- No JSON output - rely on exit code only
- Prompt as argument

**Parallel?**: Yes

---

### Subtask T015 – Implement Cursor invoker with timeout wrapper

**Purpose**: Invoker for Cursor CLI with timeout wrapper to handle hanging issue.

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/cursor.py`
2. Implement CursorInvoker with timeout:
   ```python
   class CursorInvoker(BaseInvoker):
       agent_id = "cursor"
       command = "cursor"
       default_timeout = 300  # 5 minutes

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           # Wrap with timeout to handle Cursor's hanging issue
           return [
               "timeout", str(self.default_timeout),
               "cursor", "agent",
               "-p", prompt,
               "--force",
               "--output-format", "json",
           ]
   ```

**Notes**:
- **CRITICAL**: Cursor CLI may hang indefinitely - always use timeout wrapper
- Uses `timeout` command (available on macOS/Linux)
- Exit code 124 from timeout means Cursor hung
- `--force` enables autonomous mode

**Parallel?**: Yes

---

### Subtask T016 – Implement agent registry and detection

**Purpose**: Create registry mapping agent IDs to invoker classes and detection utility.

**Steps**:
1. Update `src/specify_cli/orchestrator/agents/__init__.py`:
   ```python
   from .base import AgentInvoker, BaseInvoker, InvocationResult
   from .claude import ClaudeInvoker
   from .codex import CodexInvoker
   from .copilot import CopilotInvoker
   from .gemini import GeminiInvoker
   from .qwen import QwenInvoker
   from .opencode import OpenCodeInvoker
   from .kilocode import KilocodeInvoker
   from .augment import AugmentInvoker
   from .cursor import CursorInvoker

   AGENT_REGISTRY: dict[str, type[BaseInvoker]] = {
       "claude-code": ClaudeInvoker,
       "codex": CodexInvoker,
       "copilot": CopilotInvoker,
       "gemini": GeminiInvoker,
       "qwen": QwenInvoker,
       "opencode": OpenCodeInvoker,
       "kilocode": KilocodeInvoker,
       "augment": AugmentInvoker,
       "cursor": CursorInvoker,
   }

   def get_invoker(agent_id: str) -> BaseInvoker:
       """Get invoker instance for agent ID."""
       invoker_class = AGENT_REGISTRY.get(agent_id)
       if not invoker_class:
           raise ValueError(f"Unknown agent: {agent_id}")
       return invoker_class()

   def detect_installed_agents() -> list[str]:
       """Return list of installed agent IDs, sorted by default priority."""
       installed = []
       for agent_id, invoker_class in AGENT_REGISTRY.items():
           invoker = invoker_class()
           if invoker.is_installed():
               installed.append(agent_id)
       # Sort by default priority
       priority_order = [
           "claude-code", "codex", "copilot", "gemini",
           "qwen", "opencode", "kilocode", "augment", "cursor"
       ]
       return sorted(installed, key=lambda x: priority_order.index(x) if x in priority_order else 999)
   ```

**Notes**:
- Registry enables dynamic invoker lookup
- Detection utility used by default config generation
- Priority order matches feature 019 research recommendations

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cursor hanging | Timeout wrapper mandatory |
| timeout command not available | Check for timeout, fall back to Python timeout |
| Agent CLI changes | Document tested versions |

## Definition of Done Checklist

- [ ] QwenInvoker implemented
- [ ] OpenCodeInvoker implemented
- [ ] KilocodeInvoker implemented
- [ ] AugmentInvoker implemented
- [ ] CursorInvoker implemented with timeout wrapper
- [ ] Agent registry maps all 9 agent IDs
- [ ] `get_invoker()` returns correct invoker
- [ ] `detect_installed_agents()` returns sorted list

## Review Guidance

- Verify Cursor timeout wrapper is present
- Check all CLI flags match documented patterns
- Test registry lookup for all agents
- Verify detection returns correct installed agents

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T17:49:46Z – claude-opus – shell_pid=44333 – lane=doing – Started implementation via workflow command
- 2026-01-18T17:52:19Z – claude-opus – shell_pid=44333 – lane=for_review – Ready for review: 5 additional invokers (Qwen, OpenCode, Kilocode, Augment, Cursor with timeout), AGENT_REGISTRY with 9 agents, get_invoker() and detect_installed_agents()
- 2026-01-18T19:00:15Z – claude-opus – shell_pid=46825 – lane=doing – Started review via workflow command
