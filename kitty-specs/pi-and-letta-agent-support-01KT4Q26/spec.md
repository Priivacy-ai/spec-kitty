# Pi and Letta Code Agent Support

## Overview

Add Pi (`pi-coding-agent`) and Letta Code (`letta`) as first-class Spec Kitty-supported agents. Both agents use the existing `.agents/skills/` discovery path and support headless non-interactive automation, making them compatible with Spec Kitty's orchestration model. This mission is structured as a design spike with prototyping deliverables: working invokers, configuration, skills installation, optional prompt/command template directories, and documented design decisions for each agent's unique behavioral model.

## Problem Statement

Spec Kitty supports 17 AI agents but does not include Pi or Letta Code. Both agents have headless automation modes, JSON output, and native `.agents/skills/` support that align with Spec Kitty's integration pattern. Without registration in Spec Kitty's config and orchestrator, users of these agents cannot participate in the implement/review loop.

## Goals

- Register Pi and Letta Code in all agent configuration layers so they are available via `spec-kitty agent config add pi` and `spec-kitty agent config add letta`.
- Install Spec Kitty command skills into `.agents/skills/` for both agents at `spec-kitty init` / `spec-kitty upgrade` time.
- Provide working orchestrator invokers (`PiInvoker`, `LettaInvoker`) so the implement/review loop can dispatch work packages to these agents.
- Resolve the key design questions unique to each agent (Pi: JSON vs RPC output mode; Letta: stateless vs sticky session model) through prototyping and document the decisions.

## Non-Goals

- Full parity with every CLI flag for Pi and Letta (provider routing, model-per-step, etc.) — those can follow in subsequent missions.
- IDE or GUI surface for either agent.
- Changes to other agents already in the roster.

## User Scenarios & Testing

**Scenario 1 — Pi agent onboarding:**
A developer adds Pi to a Spec Kitty project with `spec-kitty agent config add pi`, runs `spec-kitty upgrade`, and sees `.agents/skills/spec-kitty.*/SKILL.md` populated. They then run `spec-kitty next --agent pi --mission <handle>`, and Pi receives and executes a `spec-kitty agent action implement WP01` prompt non-interactively.

**Scenario 2 — Letta Code agent onboarding:**
A developer adds Letta Code with `spec-kitty agent config add letta`, runs `spec-kitty upgrade`, and sees `.agents/skills/` populated and (if configured) `.letta/commands/` populated with slash commands. They run `spec-kitty next --agent letta --mission <handle>`, and the orchestrator dispatches work using `letta -p` in headless mode.

**Scenario 3 — Orchestrator error recovery:**
The Pi invoker receives a non-zero exit code or malformed JSON event stream; the orchestrator surfaces a structured error and does not mark the work package as complete. Same for Letta's stream-json events.

**Scenario 4 — Config-aware agent directories:**
A project configures only `pi` in `config.yaml`. Running `spec-kitty upgrade` creates `.agents/skills/` entries for Pi but does not create or touch Letta directories.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `pi` is a valid agent key in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_COMMAND_CONFIG`, and `AGENT_SKILL_CONFIG` in `src/specify_cli/core/config.py`. | Proposed |
| FR-002 | `letta` is a valid agent key in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_COMMAND_CONFIG`, and `AGENT_SKILL_CONFIG` in `src/specify_cli/core/config.py`. | Proposed |
| FR-003 | `src/specify_cli/agent_utils/directories.py` includes a directory mapping for Pi (`.pi/prompts/` subdirectory) so that `get_agent_dirs_for_project()` returns it when `pi` is configured. | Proposed |
| FR-004 | `src/specify_cli/agent_utils/directories.py` includes a directory mapping for Letta Code (`.letta/commands/` subdirectory) so that `get_agent_dirs_for_project()` returns it when `letta` is configured. | Proposed |
| FR-005 | `spec-kitty init` and `spec-kitty upgrade` install Spec Kitty command skills into `.agents/skills/spec-kitty.*/SKILL.md` for Pi when `pi` is in the configured agent list. (Pi already discovers `.agents/skills/` natively; no extra config file is required.) | Proposed |
| FR-006 | `spec-kitty init` and `spec-kitty upgrade` install Spec Kitty command skills into `.agents/skills/spec-kitty.*/SKILL.md` for Letta Code when `letta` is in the configured agent list. (Letta already discovers `.agents/skills/` natively.) | Proposed |
| FR-007 | The design decision for Pi prompt templates (generate `.pi/prompts/spec-kitty.<command>.md` or rely on skills only) is prototyped and documented, with the chosen approach implemented. | Proposed |
| FR-008 | The design decision for Letta slash commands (generate `.letta/commands/spec-kitty.<command>.md` or rely on skills only) is prototyped and documented, with the chosen approach implemented. | Proposed |
| FR-009 | A `PiInvoker` is implemented in `spec-kitty-orchestrator` that constructs a `pi -p` command, selects between `--mode json` and `--mode rpc` output, and parses modified-file list, errors, and final status from the output stream. | Proposed |
| FR-010 | A `LettaInvoker` is implemented in `spec-kitty-orchestrator` that constructs a `letta -p` command with `--output-format json` (or `stream-json`), parses system/message/usage/final-result events, and extracts modified files, errors, and final status. | Proposed |
| FR-011 | The Letta session model design decision (stateless `--new`/`--new-agent` per WP cycle vs. sticky project agent with per-conversation `--new`) is prototyped and documented, with the chosen approach implemented in `LettaInvoker`. | Proposed |
| FR-012 | `spec-kitty agent config add pi` and `spec-kitty agent config add letta` succeed and are reflected in `.kittify/config.yaml` without errors. | Proposed |
| FR-013 | Migrations that update slash commands respect the configured agent list: Pi and Letta directories are created only when those agents are configured; they are not created for unconfigured agents. | Proposed |
| FR-014 | Sandbox and security caveats for Pi (default tool set can read, write, edit, and run bash) are documented in the developer guide or agent configuration documentation. | Proposed |
| FR-015 | Permission model caveats for Letta Code (`--yolo`, `--permission-mode`, `--tools`, `--allowedTools`, `--disallowedTools`) relevant to Spec Kitty's orchestration use case are documented. | Proposed |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for new code paths (invokers, config entries, directory mappings). | ≥ 90% line coverage for new modules. | Proposed |
| NFR-002 | Static type correctness for all new Python code. | `mypy --strict` passes with zero new errors. | Proposed |
| NFR-003 | Invoker invocations must not block indefinitely when the underlying binary is absent. | Timeout or missing-binary error surfaced within 10 seconds. | Proposed |
| NFR-004 | Agent config additions are backward-compatible: existing projects without `pi` or `letta` in config continue to behave identically. | Zero regressions in existing agent config tests. | Proposed |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Pi requires Node.js and the `pi-coding-agent` npm package to be installed by the user; Spec Kitty does not install them. Presence is checked at invocation time, not at install time. | Proposed |
| C-002 | Letta Code requires Node.js 18+ and `@letta-ai/letta-code`; Spec Kitty does not install them. Presence is checked at invocation time, not at install time. | Proposed |
| C-003 | New migrations must use `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration` and must not recreate directories that don't exist (respect user deletions). | Proposed |
| C-004 | `AGENT_DIRS` must not be hardcoded in new migrations; import from `m_0_9_1_complete_lane_migration`. | Proposed |
| C-005 | Agent key mappings: `pi` maps to `.pi/prompts/`; `letta` maps to `.letta/commands/`. These keys are used in `AGENT_DIR_TO_KEY` and related structures. | Proposed |

## Key Entities

| Entity | Description |
|--------|-------------|
| `PiInvoker` | Orchestrator class that builds and executes `pi -p` commands and parses Pi's JSON event stream for work package results. |
| `LettaInvoker` | Orchestrator class that builds and executes `letta -p` commands and parses Letta's JSON or stream-JSON output for work package results. |
| Pi prompt templates | Files in `.pi/prompts/spec-kitty.<command>.md` — the Pi equivalent of slash commands; generated at `init`/`upgrade` time if the design decision confirms they add value beyond skills alone. |
| Letta slash commands | Files in `.letta/commands/spec-kitty.<command>.md` — the Letta equivalent of slash commands; generated at `init`/`upgrade` time if the design decision confirms they add value beyond skills alone. |
| Agent Skills | Shared skill packages in `.agents/skills/spec-kitty.*/SKILL.md` consumed natively by Pi, Letta, Codex, Vibe, and Pi without extra configuration. |

## Assumptions

- Pi's `.agents/skills/` discovery works without any `.pi/settings.json` entries, based on the issue's preliminary research confirming this path is in Pi's default skill search locations.
- Letta Code's `.agents/skills/` discovery works without extra configuration, based on the issue's preliminary research confirming this is Letta's preferred skill root.
- The orchestrator invoker protocol (as used by existing invokers) is sufficient to add `PiInvoker` and `LettaInvoker` without protocol-level changes.
- Letta's `agent_id` and `conversation_id` from JSON output are used by the invoker to maintain session continuity within a single WP cycle, not across cycles.

## Success Criteria

- A developer can add `pi` or `letta` to a Spec Kitty project and run a full implement/review loop work package dispatch without manual workarounds.
- The orchestrator correctly parses output from both agents and marks work packages with the right final status.
- Design decisions for Pi output mode and Letta session model are recorded in the mission artifacts and referenced from developer documentation.
- All new code passes `mypy --strict` and achieves ≥ 90% test coverage.
- Existing agent config tests continue to pass without modification.

## References

- GitHub issue #1050 — Pi CLI harness design spike
- GitHub issue #1054 — Letta Code design spike
- `src/specify_cli/core/config.py` — agent configuration registry
- `src/specify_cli/agent_utils/directories.py` — agent directory mappings
- `src/specify_cli/skills/command_renderer.py` and `command_installer.py` — skill package generation
- `spec-kitty-orchestrator/src/spec_kitty_orchestrator/agents/__init__.py` — invoker registry
- CLAUDE.md §Agent Management Best Practices — migration authoring rules
