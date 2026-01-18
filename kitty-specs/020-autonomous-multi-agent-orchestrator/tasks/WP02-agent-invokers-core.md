---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Agent Invokers - Core Agents"
phase: "Phase 1 - Components"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "44441"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Agent Invokers - Core Agents

## Objectives & Success Criteria

Implement the base AgentInvoker protocol and invokers for the 5 most common agents (Claude Code, GitHub Codex, GitHub Copilot, Google Gemini, Qwen Code).

**Success Criteria**:
- AgentInvoker Protocol defines standard interface
- Each invoker correctly builds CLI commands for its agent
- Installation detection works via `shutil.which()`
- Output parsing extracts success/failure from agent responses

## Context & Constraints

**Reference Documents**:
- [plan.md](../plan.md) - Agent invocation patterns table
- [data-model.md](../data-model.md) - AgentInvoker protocol, InvocationResult
- [spec.md](../spec.md) - FR-006, FR-009 (agent support requirements)

**Invocation Patterns** (from plan.md):

| Agent | Command | Task Input | Headless Flag | JSON Output |
|-------|---------|------------|---------------|-------------|
| Claude Code | `claude` | stdin | `-p` | `--output-format json` |
| GitHub Codex | `codex exec` | stdin or arg | `-` | `--json` |
| GitHub Copilot | `copilot` | arg | `-p` | `--silent` |
| Google Gemini | `gemini` | stdin | `-p` | `--output-format json` |
| Qwen Code | `qwen` | stdin | `-p` | `--output-format json` |

**Implementation Command**:
```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T006 – Implement AgentInvoker protocol

**Purpose**: Define the standard interface all agent invokers must implement.

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/base.py`
2. Define Protocol class:
   ```python
   from typing import Protocol
   from pathlib import Path
   from dataclasses import dataclass

   @dataclass
   class InvocationResult:
       success: bool
       exit_code: int
       files_modified: list[str] | None
       commits_made: list[str] | None
       errors: list[str] | None
       warnings: list[str] | None
       stdout: str
       stderr: str
       duration_seconds: float

   class AgentInvoker(Protocol):
       agent_id: str
       command: str

       def is_installed(self) -> bool:
           """Check if agent CLI is available."""
           ...

       def build_command(
           self,
           prompt: str,
           working_dir: Path,
           role: str,
       ) -> list[str]:
           """Build full command with agent-specific flags."""
           ...

       def parse_output(
           self,
           stdout: str,
           stderr: str,
           exit_code: int,
       ) -> InvocationResult:
           """Parse agent output into structured result."""
           ...
   ```

3. Create base implementation class with common functionality:
   ```python
   class BaseInvoker:
       def is_installed(self) -> bool:
           return shutil.which(self.command) is not None
   ```

**Files**:
- `src/specify_cli/orchestrator/agents/base.py`

---

### Subtask T007 – Implement Claude Code invoker

**Purpose**: Invoker for Claude Code CLI (`claude`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/claude.py`
2. Implement ClaudeInvoker:
   ```python
   class ClaudeInvoker(BaseInvoker):
       agent_id = "claude-code"
       command = "claude"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           cmd = [
               "claude",
               "-p",                    # Headless mode
               "--output-format", "json",
               "--allowedTools", "Read,Write,Edit,Bash,Glob,Grep",
           ]
           # Prompt passed via stdin
           return cmd

       def parse_output(self, stdout: str, stderr: str, exit_code: int) -> InvocationResult:
           # Parse JSON output
           ...
   ```

**Notes**:
- Claude accepts prompt via stdin
- JSON output includes conversation turns
- Exit code 0 = success

**Parallel?**: Yes - independent of other invokers

---

### Subtask T008 – Implement GitHub Codex invoker

**Purpose**: Invoker for GitHub Codex CLI (`codex`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/codex.py`
2. Implement CodexInvoker:
   ```python
   class CodexInvoker(BaseInvoker):
       agent_id = "codex"
       command = "codex"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           cmd = [
               "codex", "exec",
               "-",                     # Read from stdin
               "--json",
               "--full-auto",
           ]
           return cmd
   ```

**Notes**:
- `codex exec -` reads prompt from stdin
- `--full-auto` enables autonomous mode
- JSON output for structured results

**Parallel?**: Yes

---

### Subtask T009 – Implement GitHub Copilot invoker

**Purpose**: Invoker for GitHub Copilot CLI (`copilot`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/copilot.py`
2. Implement CopilotInvoker:
   ```python
   class CopilotInvoker(BaseInvoker):
       agent_id = "copilot"
       command = "copilot"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           cmd = [
               "copilot",
               "-p", prompt,            # Prompt as argument
               "--yolo",                # Autonomous mode
               "--silent",              # Minimal output
           ]
           return cmd
   ```

**Notes**:
- Copilot takes prompt as `-p` argument, not stdin
- `--silent` reduces noise in output
- Returns exit code only (no structured JSON)

**Parallel?**: Yes

---

### Subtask T010 – Implement Google Gemini invoker

**Purpose**: Invoker for Google Gemini CLI (`gemini`).

**Steps**:
1. Create `src/specify_cli/orchestrator/agents/gemini.py`
2. Implement GeminiInvoker:
   ```python
   class GeminiInvoker(BaseInvoker):
       agent_id = "gemini"
       command = "gemini"

       def build_command(self, prompt: str, working_dir: Path, role: str) -> list[str]:
           cmd = [
               "gemini",
               "-p",                    # Headless mode
               "--yolo",                # Autonomous
               "--output-format", "json",
           ]
           # Prompt via stdin
           return cmd
   ```

**Notes**:
- Gemini uses `-p` for headless, prompt via stdin
- Exit codes: 0 (success), 41 (auth error), 42 (rate limit), 52 (general error), 130 (interrupted)
- JSON output available

**Parallel?**: Yes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CLI flag changes between versions | Document tested versions, add version detection |
| Different output formats | Flexible parsing with fallbacks |
| Auth failures | Clear error messages with setup instructions |

## Definition of Done Checklist

- [ ] AgentInvoker Protocol defined in `agents/base.py`
- [ ] InvocationResult dataclass implemented
- [ ] BaseInvoker with common `is_installed()` implemented
- [ ] ClaudeInvoker builds correct command, parses output
- [ ] CodexInvoker builds correct command, parses output
- [ ] CopilotInvoker builds correct command, parses output
- [ ] GeminiInvoker builds correct command, parses output
- [ ] All invokers handle missing agent gracefully

## Review Guidance

- Verify CLI flags match documented patterns
- Check that prompt is passed correctly (stdin vs arg)
- Test `is_installed()` returns correct result
- Verify output parsing extracts key fields

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T17:44:05Z – claude-opus – shell_pid=43277 – lane=doing – Started implementation via workflow command
- 2026-01-18T17:46:58Z – claude-opus – shell_pid=43277 – lane=for_review – Ready for review: AgentInvoker protocol, InvocationResult dataclass, and 4 core invokers (Claude, Codex, Copilot, Gemini)
- 2026-01-18T17:49:55Z – claude-opus – shell_pid=44441 – lane=doing – Started review via workflow command
- 2026-01-18T17:51:05Z – claude-opus – shell_pid=44441 – lane=done – Review passed: AgentInvoker protocol with all required methods, InvocationResult dataclass, BaseInvoker with common helpers, 4 invokers (Claude, Codex, Copilot, Gemini) with correct CLI flags. All imports and instantiation tested successfully.
