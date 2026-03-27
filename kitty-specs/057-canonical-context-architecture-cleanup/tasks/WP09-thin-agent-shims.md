---
work_package_id: WP09
title: Thin Agent Shims
lane: "for_review"
dependencies: [WP01]
requirement_refs:
- C-007
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP01
base_commit: c59fdb7be18bffff79d158144cd072fca7673135
created_at: '2026-03-27T18:10:56.955315+00:00'
subtasks:
- T044
- T045
- T046
- T047
- T048
- T049
phase: Phase D - Surface and Migration
assignee: ''
agent: coordinator
shell_pid: '5682'
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Thin Agent Shims

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- `shims/` module generates thin 3-line shim files for all configured agents.
- `spec-kitty agent shim <command>` entrypoints resolve context internally and dispatch.
- Skill registry defines consumer-facing vs internal-only skills.
- Generated shim files contain ZERO workflow logic — only CLI passthrough.

## Context & Constraints

- **Spec**: FR-016 (thin shims), FR-017 (skill allowlist), C-007 (shim files still generated)
- **Plan**: Move 5 — Thin Agent Surface section
- **12 agent directories**: claude, codex, opencode, gemini, cursor, qwen, kilocode, augment, roo, amazonq, windsurf, copilot
- **Shim format**: 3 lines — invariant, prohibition, CLI call
- **Depends on**: WP01 (context token model)

## Subtasks & Detailed Guidance

### Subtask T044 – Create shims/__init__.py

- **Purpose**: Package initialization.
- **Steps**: Create `src/specify_cli/shims/__init__.py`, export `generate_shims`, `ShimTemplate`, `SkillRegistry`
- **Files**: `src/specify_cli/shims/__init__.py` (new, ~10 lines)

### Subtask T045 – Create shims/models.py

- **Purpose**: Dataclasses for shim configuration.
- **Steps**:
  1. Create `src/specify_cli/shims/models.py`
  2. Define `ShimTemplate`:
     ```python
     @dataclass(frozen=True)
     class ShimTemplate:
         command_name: str        # e.g., "spec-kitty.implement"
         cli_command: str          # e.g., "spec-kitty agent shim implement"
         agent_name: str           # e.g., "claude"
         filename: str             # e.g., "spec-kitty.implement.md"
     ```
  3. Define `AgentShimConfig`:
     ```python
     @dataclass(frozen=True)
     class AgentShimConfig:
         agent_key: str            # e.g., "claude"
         agent_dir: str            # e.g., ".claude"
         command_subdir: str       # e.g., "commands"
         templates: tuple[ShimTemplate, ...]
     ```
- **Files**: `src/specify_cli/shims/models.py` (new, ~40 lines)
- **Parallel?**: Yes

### Subtask T046 – Create shims/generator.py

- **Purpose**: Generate thin shim markdown files for all configured agents.
- **Steps**:
  1. Create `src/specify_cli/shims/generator.py`
  2. Implement `generate_shim_content(command: str, agent_name: str, arg_placeholder: str) -> str`:
     - The argument placeholder varies by agent runtime:
       - Claude Code: `"$ARGUMENTS"` (slash-command args)
       - Codex: `"$PROMPT"` (prompt text)
       - Other agents: `"$ARGUMENTS"` (default)
     - Define an `AGENT_ARG_PLACEHOLDERS` mapping for known agent-specific patterns
     - Return the 3-line shim format:
       ```
       Run this exact command and treat its output as authoritative.
       Do not rediscover context from branches, files, or prompt contents.

       `spec-kitty agent shim {command} --agent {agent_name} --raw-args "{arg_placeholder}"`
       ```
     - The CLI shim entrypoint normalizes all argument formats internally, so the placeholder is the only agent-specific variation. All workflow logic stays in the CLI.
  3. Implement `generate_all_shims(repo_root: Path) -> list[Path]`:
     - Get configured agents via `get_agent_dirs_for_project(repo_root)`
     - Get consumer-facing skills from registry (T047)
     - For each agent + each skill: generate shim file
     - Write to `<agent_dir>/<command_subdir>/spec-kitty.<skill>.md`
     - Return list of written file paths
  4. Handle agent-specific directory structures:
     - `.claude/commands/`, `.codex/prompts/`, `.opencode/command/`, `.windsurf/workflows/`, etc.
     - Use `AGENT_DIRS` mapping from existing codebase
- **Files**: `src/specify_cli/shims/generator.py` (new, ~80 lines)
- **Parallel?**: Yes

### Subtask T047 – Create shims/registry.py

- **Purpose**: Define which skills are consumer-facing vs internal-only.
- **Steps**:
  1. Create `src/specify_cli/shims/registry.py`
  2. Define `CONSUMER_SKILLS`:
     ```python
     CONSUMER_SKILLS = frozenset({
         "specify", "plan", "tasks", "tasks-outline", "tasks-packages",
         "tasks-finalize", "implement", "review", "accept", "merge",
         "status", "dashboard", "checklist", "analyze", "research",
         "constitution",
     })
     ```
  3. Define `INTERNAL_SKILLS`:
     ```python
     INTERNAL_SKILLS = frozenset({
         "doctor", "materialize", "debug",
     })
     ```
  4. Implement `is_consumer_skill(skill_name: str) -> bool`
  5. Implement `get_consumer_skills() -> frozenset[str]`
  6. Implement `get_all_skills() -> frozenset[str]`
- **Files**: `src/specify_cli/shims/registry.py` (new, ~40 lines)
- **Parallel?**: Yes

### Subtask T048 – Create shim entrypoints and CLI commands

- **Purpose**: `spec-kitty agent shim <command>` handlers that resolve context and dispatch.
- **Steps**:
  1. Create `src/specify_cli/shims/entrypoints.py`:
     - Implement `shim_dispatch(command: str, agent: str, raw_args: str, context: str | None, repo_root: Path)`:
       - Parse raw_args to extract wp_code, feature_slug, and any other params
       - If `context` provided: load it
       - If not: resolve from raw_args via `resolve_or_load()`
       - Dispatch to the appropriate workflow handler (implement, review, etc.)
     - Simple arg parser: extract `WP##` patterns, `--feature` values, etc.
  2. Create `src/specify_cli/cli/commands/shim.py`:
     - Register `spec-kitty agent shim` command group
     - Subcommands: `implement`, `review`, `status`, `specify`, `plan`, `tasks`, `merge`, `accept`
     - Each subcommand: `--agent <name>`, `--raw-args <string>`, `--context <token>` (optional)
     - Calls `shim_dispatch()` with parsed args
- **Files**: `src/specify_cli/shims/entrypoints.py` (new, ~80 lines), `src/specify_cli/cli/commands/shim.py` (new, ~60 lines)

### Subtask T049 – Tests for shims module

- **Purpose**: Verify shim generation, registry, and dispatch.
- **Steps**:
  1. `test_models.py`: ShimTemplate, AgentShimConfig creation
  2. `test_generator.py`: Shim content is exactly 3 lines + CLI call. All agents get files. Correct directory structure.
  3. `test_registry.py`: Consumer vs internal skills. Unknown skill handling.
  4. `test_entrypoints.py`: Dispatch with context token, dispatch with raw args (resolve internally), dispatch with invalid command
- **Files**: `tests/specify_cli/shims/` (new, ~150 lines total)
- **Parallel?**: Yes

## Risks & Mitigations

- **Agent-specific quirks**: Windsurf uses `workflows/` not `commands/`. Amazon Q uses `prompts/`. Use existing `AGENT_DIRS` mapping.
- **Arg parsing**: Raw args from agent slash commands may be inconsistent. Use a robust parser with fallback.

## Review Guidance

- Verify generated shim content is exactly the 3-line format — no workflow logic leaked in
- Verify all 12 agents get shim files (for configured agents)
- Verify internal skills are excluded from consumer installs
- Verify shim entrypoint resolves context internally before dispatching

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T18:10:57Z – coordinator – shell_pid=5682 – lane=doing – Assigned agent via workflow command
- 2026-03-27T18:17:20Z – coordinator – shell_pid=5682 – lane=for_review – Thin agent shim module complete with generator, registry, entrypoints, and tests
