# Pi and Letta Code Agent Support

## Overview

Add Pi (`pi-coding-agent`) and Letta Code (`letta`) as first-class Spec Kitty-supported agents. Both agents use the existing `.agents/skills/` discovery path and support headless non-interactive automation, making them compatible with Spec Kitty's orchestration model. This mission delivers: agent configuration registration, Agent Skills installation, an upgrade migration to backfill existing projects, and documented design decisions (ADRs) for each agent's CLI model. Orchestrator invokers (`PiInvoker`, `LettaInvoker`) are explicitly out of scope for this mission and tracked in a follow-up (see FR-009, FR-010, FR-011).

## Problem Statement

Spec Kitty supports 17 AI agents but does not include Pi or Letta Code. Both agents have headless automation modes, JSON output, and native `.agents/skills/` support that align with Spec Kitty's integration pattern. Without registration in Spec Kitty's config and orchestrator, users of these agents cannot participate in the implement/review loop.

## Goals

- Register Pi and Letta Code in all agent configuration layers so they are available via `spec-kitty agent config add pi` and `spec-kitty agent config add letta`.
- Install Spec Kitty command skills into `.agents/skills/` for both agents at `spec-kitty init` / `spec-kitty upgrade` time.
- Document design decisions for each agent's CLI model (Pi: skill-only, no `.pi/prompts/` templates; Letta: skill-only, no `.letta/commands/` templates; orchestrator invokers deferred).
- Backfill existing projects that already have pi or letta configured via an upgrade migration.

## Non-Goals

- Full parity with every CLI flag for Pi and Letta (provider routing, model-per-step, etc.) — those can follow in subsequent missions.
- IDE or GUI surface for either agent.
- Changes to other agents already in the roster.

## User Scenarios & Testing

**Scenario 1 — Pi agent onboarding:**
A developer adds Pi to a Spec Kitty project with `spec-kitty agent config add pi`, runs `spec-kitty upgrade`, and sees `.agents/skills/spec-kitty.*/SKILL.md` populated. They then run `spec-kitty next --agent pi --mission <handle>`, and Pi receives and executes a `spec-kitty agent action implement WP01` prompt non-interactively.

**Scenario 2 — Letta Code agent onboarding:**
A developer adds Letta Code with `spec-kitty agent config add letta`, runs `spec-kitty upgrade`, and sees `.agents/skills/spec-kitty.*/SKILL.md` populated. The agent can invoke Spec Kitty skills via the `.agents/skills/` discovery root.

**Scenario 3 — Config-aware agent directories:**
A project configures only `pi` in `config.yaml`. Running `spec-kitty upgrade` creates `.agents/skills/` entries for Pi but does not create or touch Letta directories.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `pi` is a valid agent key in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, and `AGENT_SKILL_CONFIG` in `src/specify_cli/core/config.py`. Pi is a `SKILL_CLASS_SHARED` agent and is intentionally **absent** from `AGENT_COMMAND_CONFIG` (no slash-command directory). | Delivered |
| FR-002 | `letta` is a valid agent key in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, and `AGENT_SKILL_CONFIG` in `src/specify_cli/core/config.py`. Letta is a `SKILL_CLASS_SHARED` agent and is intentionally **absent** from `AGENT_COMMAND_CONFIG`. | Delivered |
| FR-003 | Pi is registered in `SKILL_ONLY_AGENTS` in `src/specify_cli/cli/commands/agent/config.py` and in `src/specify_cli/gitignore_manager.py` with a `.pi/` gitignore entry. No `.pi/prompts/` directory mapping is added to `AGENT_DIRS` — Pi is skill-only (see ADR 2026-06-02-1). | Delivered |
| FR-004 | Letta is registered in `SKILL_ONLY_AGENTS` and in `src/specify_cli/gitignore_manager.py` with a `.letta/` gitignore entry. No `.letta/commands/` directory mapping is added to `AGENT_DIRS` — Letta is skill-only (see ADR 2026-06-02-2). | Delivered |
| FR-005 | `spec-kitty init` and `spec-kitty upgrade` install Spec Kitty command skills into `.agents/skills/spec-kitty.*/SKILL.md` for Pi when `pi` is in the configured agent list. (Pi discovers `.agents/skills/` and `.pi/skills/` natively; no extra config required.) | Delivered |
| FR-006 | `spec-kitty init` and `spec-kitty upgrade` install Spec Kitty command skills into `.agents/skills/spec-kitty.*/SKILL.md` for Letta Code when `letta` is in the configured agent list. | Delivered |
| FR-007 | The design decision for Pi prompt templates (skill-only chosen; `.pi/prompts/` not generated) is documented in ADR `architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md`. | Delivered |
| FR-008 | The design decision for Letta slash commands (skill-only chosen; `.letta/commands/` not generated) is documented in ADR `architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md`. | Delivered |
| FR-009 | A `PiInvoker` is implemented in `spec-kitty-orchestrator`. | **Deferred** — out of scope for this mission; tracked in follow-up issue (see References). |
| FR-010 | A `LettaInvoker` is implemented in `spec-kitty-orchestrator`. | **Deferred** — out of scope for this mission; tracked in follow-up issue (see References). |
| FR-011 | The Letta session model design decision (stateless vs. sticky) is implemented in `LettaInvoker`. | **Deferred** — depends on FR-010; tracked in follow-up issue (see References). |
| FR-012 | `spec-kitty agent config add pi` and `spec-kitty agent config add letta` succeed and are reflected in `.kittify/config.yaml` without errors. | Delivered |
| FR-013 | The upgrade migration (`m_3_2_10_pi_letta_backfill`) respects the configured agent list: only configured agents receive gitignore backfill and skill repair. | Delivered |
| FR-014 | Sandbox and security caveats for Pi are documented in ADR `2026-06-02-1` (More Information section). | Delivered |
| FR-015 | Permission model caveats for Letta Code are documented in ADR `2026-06-02-2` (More Information section). | Delivered |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for new code paths (invokers, config entries, directory mappings). | ≥ 90% line coverage for new modules. | Proposed |
| NFR-002 | Static type correctness for all new Python code. | `mypy --strict` passes with zero new errors. | Proposed |
| NFR-003 | Invoker invocations must not block indefinitely when the underlying binary is absent. | Timeout or missing-binary error surfaced within 10 seconds. | **Deferred** — no invokers implemented in this mission; applies to follow-up FR-009/FR-010. |
| NFR-004 | Agent config additions are backward-compatible: existing projects without `pi` or `letta` in config continue to behave identically. | Zero regressions in existing agent config tests. | Proposed |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Pi requires Node.js and the `pi-coding-agent` npm package to be installed by the user; Spec Kitty does not install them. Presence is checked at invocation time, not at install time. | Proposed |
| C-002 | Letta Code requires Node.js 18+ and `@letta-ai/letta-code`; Spec Kitty does not install them. Presence is checked at invocation time, not at install time. | Proposed |
| C-003 | New migrations must use `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration` and must not recreate directories that don't exist (respect user deletions). | Proposed |
| C-004 | `AGENT_DIRS` must not be hardcoded in new migrations; import from `m_0_9_1_complete_lane_migration`. | Proposed |
| C-005 | Pi and Letta are skill-only agents. Neither `.pi` nor `.letta` appear in `AGENT_DIRS` or `AGENT_DIR_TO_KEY`. The `.pi/` and `.letta/` entries exist only as gitignore entries (managed by `GitignoreManager`), not as slash-command directories. | Delivered |

## Key Entities

| Entity | Description |
|--------|-------------|
| `PiInvoker` | Deferred. Orchestrator class for `pi -p` dispatch — tracked in follow-up issue (see References). |
| `LettaInvoker` | Deferred. Orchestrator class for `letta -p` dispatch — tracked in follow-up issue (see References). |
| `PiLettaBackfillMigration` | Upgrade migration (`m_3_2_10_pi_letta_backfill`) that adds `.pi/` / `.letta/` gitignore entries and repairs missing Agent Skills for existing projects with these agents configured. |
| Agent Skills | Shared skill packages in `.agents/skills/spec-kitty.*/SKILL.md` consumed natively by Pi, Letta, Codex, and Vibe without extra configuration. |

## Assumptions

- Pi's `.agents/skills/` discovery works without any `.pi/settings.json` entries, based on the issue's preliminary research confirming this path is in Pi's default skill search locations.
- Letta Code's `.agents/skills/` discovery works without extra configuration, based on the issue's preliminary research confirming this is Letta's preferred skill root.
- The orchestrator invoker protocol (as used by existing invokers) is sufficient to add `PiInvoker` and `LettaInvoker` without protocol-level changes.
- Letta's `agent_id` and `conversation_id` from JSON output are used by the invoker to maintain session continuity within a single WP cycle, not across cycles.

## Success Criteria

- A developer can add `pi` or `letta` to a Spec Kitty project and see `.agents/skills/spec-kitty.*/SKILL.md` populated after `spec-kitty init` or `spec-kitty upgrade`.
- Existing projects with pi or letta configured receive `.pi/` / `.letta/` gitignore entries and skill repair via `spec-kitty upgrade`.
- Design decisions (skill-only, deferred invoker) are recorded in accepted ADRs and referenced from CLAUDE.md.
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
- GitHub issue #1633 — follow-up: implement PiInvoker and LettaInvoker (deferred FR-009, FR-010, FR-011)
