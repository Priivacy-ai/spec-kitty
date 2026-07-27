---
work_package_id: WP02
title: Decision Records and Documentation
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-014
- FR-015
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 0 - Closure
agent: "claude:claude-sonnet-4-6:curator-carla:reviewer"
shell_pid: "33209"
history:
- timestamp: '2026-06-02T17:52:08Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: architecture/3.x/adr/
execution_mode: planning_artifact
mission_id: 01KT4Q26YT9B4ZNBC4GH0D2WNM
owned_files:
- architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md
- architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md
- CLAUDE.md
role: curator
tags: []
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load curator-carla
```

This profile configures your documentation authoring style and quality standards.

---

## Objective

Record the Pi and Letta design decisions as ADRs (DIRECTIVE_003), update `CLAUDE.md` to reflect 19 supported agents (DIRECTIVE_037), and close the two tracking GitHub issues that originated this work.

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent claude
```

No `--base` flag needed — this WP has no dependencies and can run in parallel with WP01.

## Branch Strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Your execution worktree is allocated per the lane computed from `lanes.json`

## Context

**Background**: Issues #1050 and #1054 are design spikes requesting Pi and Letta as Spec Kitty-supported agents. The implementation work (config, skills, init, gitignore, CLI, tests) has already landed on `main`. What remains is:

1. **DIRECTIVE_003** requires that material design decisions be captured with enough context for future contributors. The two key decisions — "Pi is skill-only" and "Letta is skill-only, with orchestrator invoker deferred" — are not yet documented in ADRs.

2. **DIRECTIVE_037** requires that documentation stay in sync with observable behavior. `CLAUDE.md` currently says "17 AI agents total" but the codebase now supports 19.

3. The tracking issues should be closed with a summary of what was implemented and what was deferred.

**ADR location**: `architecture/3.x/adr/` (canonical for 3.x decisions). Use the template at `architecture/adr-template.md`.

**GitHub auth note**: If `gh` commands fail with scope errors, `unset GITHUB_TOKEN` first to use the keyring token, which has full `repo` scope.

## Subtask Guidance

### T006 — Write ADR for Pi agent skill-only support

**File**: `architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md`

**Purpose**: Capture why Pi was added as a `SKILL_CLASS_SHARED` agent without command prompt templates or an orchestrator invoker in this release.

**Content outline** (follow `architecture/adr-template.md`):

- **Status**: Accepted
- **Date**: 2026-06-02
- **Technical Story**: GitHub issue #1050

**Context and Problem Statement**: Pi (`pi-coding-agent`) is a terminal coding harness that supports non-interactive automation via `pi -p`, JSON event streaming via `pi --mode json`, and RPC mode. The design spike (#1050) raised three questions: (a) Should Pi be skill-only, prompt-template-based, orchestrator-enabled, or all three? (b) Is `--mode json` reliable for extracting structured results? (c) Does `.pi/prompts/` add value beyond Agent Skills?

**Decision Drivers**:
- Pi natively discovers `.agents/skills/` without extra configuration
- Agent Skills provide identical skill content across all shared-root agents (codex, vibe, pi, letta)
- Orchestrator invoker (`PiInvoker`) is external scope (`spec-kitty-orchestrator` package)
- Generating `.pi/prompts/` templates would require a new migration and yield minimal additional value since Pi users can invoke skills directly

**Considered Options**:
- Option A: Skill-only (`.agents/skills/` only, no `.pi/prompts/`)
- Option B: Skills + prompt templates (`.agents/skills/` + `.pi/prompts/spec-kitty.<command>.md`)
- Option C: Full support (skills + prompt templates + `PiInvoker` in orchestrator)

**Decision Outcome**: Chosen option A (skill-only), because Pi discovers `.agents/skills/` natively and the incremental value of prompt templates is unclear without a live prototype. `PiInvoker` is deferred to the external `spec-kitty-orchestrator` package scope. This decision can be revisited once `pi --mode json` reliability is validated.

**Consequences**:
- Positive: No new migration required for prompt templates; Pi users get skills via `spec-kitty init --ai pi` immediately.
- Negative: `spec-kitty next --agent pi` is not yet supported without `spec-kitty-orchestrator`.
- Neutral: `.pi/prompts/` is intentionally absent; `AGENT_COMMAND_CONFIG` does not include `pi`.

**Files**: `architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md` (new, ~60 lines)

---

### T007 — Write ADR for Letta agent skill-only support

**File**: `architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md`

**Purpose**: Capture why Letta Code was added as a `SKILL_CLASS_SHARED` agent without slash-command templates or an orchestrator invoker in this release, and document the deferred persistent-memory design question.

**Content outline** (follow `architecture/adr-template.md`):

- **Status**: Accepted
- **Date**: 2026-06-02
- **Technical Story**: GitHub issue #1054

**Context and Problem Statement**: Letta Code (`letta`) is a memory-first coding agent supporting headless automation via `letta -p`, `--output-format json`, and `--output-format stream-json`. The design spike (#1054) raised: (a) skill-only vs. slash commands in `.letta/commands/` vs. full orchestrator support; (b) how to handle Letta's persistent memory and long-lived agent/conversation model for repeatable WP cycles.

**Decision Drivers**:
- Letta natively discovers `.agents/skills/` as its preferred skill root
- Letta's persistent memory model introduces state-management complexity that is out of scope for this CLI-layer integration
- `LettaInvoker` with session-model design is external `spec-kitty-orchestrator` scope
- `.letta/commands/` templates offer limited incremental value given skills are available

**Considered Options**:
- Option A: Skill-only (`.agents/skills/` only, no `.letta/commands/`)
- Option B: Skills + slash commands (`.agents/skills/` + `.letta/commands/spec-kitty.<command>.md`)
- Option C: Full support (skills + slash commands + `LettaInvoker` with session-model choice)

**Decision Outcome**: Chosen option A (skill-only). Letta's persistent memory/conversation model (stateless `--new` vs. sticky agent) is deferred until a prototype can validate the right approach. `AGENT_COMMAND_CONFIG` intentionally does not include `letta`.

**Consequences**:
- Positive: No new migration for slash commands; Letta users get skills immediately.
- Negative: `spec-kitty next --agent letta` is not yet supported without `spec-kitty-orchestrator`.
- Neutral: The deferred session-model question is tracked in issue #1054 until resolved.

**Files**: `architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md` (new, ~65 lines)

---

### T008 — Update CLAUDE.md agent count and tables

**File**: `CLAUDE.md`

**Purpose**: Bring `CLAUDE.md` into sync with the actual supported agent count and add Pi and Letta to the Agent Skills Agents table.

**Steps**:

1. Search for `"17 AI agents"` in `CLAUDE.md`. Update to `"19 AI agents"`.

2. Find the **Agent Skills Agents (4)** table (the table with columns `Agent | Skills Root | Command Surface | Key`). It currently lists 4 rows: Codex CLI, Mistral Vibe, Pi, Letta.

   Wait — check first. The issues say Pi and Letta were NOT in the table originally. Grep for `Pi` and `Letta` in CLAUDE.md. If they're already present, skip this step and just update the count.

   If they're absent, add:
   ```
   | Pi | `.agents/skills/` | `/skill:spec-kitty.<command>` | `pi` |
   | Letta Code | `.agents/skills/` | `Use spec-kitty.<command>` | `letta` |
   ```

3. If the narrative text says "13 use the slash-command pipeline", update the surrounding framing to mention that Pi and Letta use the Agent Skills pipeline.

4. Update `SKILL_ONLY_AGENTS` reference note in CLAUDE.md if present (should now list pi and letta explicitly).

**Validation**: After editing, grep for `"19 AI agents"` confirms the update. `pi` and `letta` appear in the Agent Skills Agents table.

**Files**: `CLAUDE.md` (update, ~5-10 lines changed)

---

### T009 — Close GitHub issues #1050 and #1054

**Purpose**: Complete the feedback loop by closing the originating design-spike issues with a summary of what was implemented.

**Steps**:

1. Post a comment on issue #1050:
   ```
   unset GITHUB_TOKEN && gh issue comment 1050 --repo Priivacy-ai/spec-kitty --body "..."
   ```
   Comment body (adjust as needed):
   > Closing this design spike. Pi (`pi-coding-agent`) has been added as a first-class Spec Kitty agent (skill-only, SKILL_CLASS_SHARED):
   > - Registered in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_SKILL_CONFIG`
   > - `spec-kitty init --ai pi` installs `.agents/skills/spec-kitty.*` and `.pi/skills/` entries
   > - `.pi/` gitignore entry added for runtime state and session logs
   > - `spec-kitty agent config add pi` supported
   > - Tests: `tests/specify_cli/cli/commands/test_init_pi_letta.py`, `test_agent_config_pi_letta.py`
   >
   > Deferred: `PiInvoker` (orchestrator invoker for `spec-kitty next --agent pi`) — out of scope for this repo; tracked in `spec-kitty-orchestrator`. `.pi/prompts/` slash-command templates not generated (see ADR `2026-06-02-1-pi-agent-skill-only-support`).

2. Close issue #1050:
   ```
   unset GITHUB_TOKEN && gh issue close 1050 --repo Priivacy-ai/spec-kitty
   ```

3. Post a comment on issue #1054 with the Letta equivalent:
   > Closing this design spike. Letta Code (`letta`) has been added as a first-class Spec Kitty agent (skill-only, SKILL_CLASS_SHARED):
   > - Registered in `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS`, `AGENT_SKILL_CONFIG`
   > - `spec-kitty init --ai letta` installs `.agents/skills/spec-kitty.*` entries
   > - `.letta/` gitignore entry added for runtime state, auth, and memory
   > - `spec-kitty agent config add letta` supported
   > - Tests: `tests/specify_cli/cli/commands/test_init_pi_letta.py`, `test_agent_config_pi_letta.py`
   >
   > Deferred: `LettaInvoker` and session-model design (stateless vs. sticky) — out of scope for this repo. `.letta/commands/` templates not generated (see ADR `2026-06-02-2-letta-agent-skill-only-support`).

4. Close issue #1054:
   ```
   unset GITHUB_TOKEN && gh issue close 1054 --repo Priivacy-ai/spec-kitty
   ```

**Validation**: Both issues show as closed in `gh issue view 1050 --repo Priivacy-ai/spec-kitty` and `gh issue view 1054 --repo Priivacy-ai/spec-kitty`.

---

## Definition of Done

- [ ] `architecture/3.x/adr/2026-06-02-1-pi-agent-skill-only-support.md` created with status Accepted
- [ ] `architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md` created with status Accepted
- [ ] `CLAUDE.md` shows "19 AI agents total"
- [ ] Pi and Letta appear in CLAUDE.md's Agent Skills Agents table
- [ ] GitHub issue #1050 is closed
- [ ] GitHub issue #1054 is closed

## Risks

- CLAUDE.md editing is error-prone for large files; use `grep` to locate exact text before editing.
- GitHub issue closure requires `repo` scope; use `unset GITHUB_TOKEN` to fall back to keyring auth if the default token is insufficient.
- The ADR index table in `architecture/3.x/adr/README.md` should also be updated with the two new ADR entries (add two rows to the `| Date | Title |` table).

## Reviewer Guidance

- Confirm ADRs follow the template structure (`## Context`, `## Decision Drivers`, `## Considered Options`, `## Decision Outcome`, `## Consequences`).
- Confirm ADR status is "Accepted" (not "Proposed").
- Confirm `CLAUDE.md` agent count is exactly 19 (not 18 or 20).
- Confirm both GitHub issues show as CLOSED.
- Confirm the ADR index README was updated.

## Activity Log

- 2026-06-02T20:18:31Z – user – shell_pid=18631 – Started implementation via action command
- 2026-06-02T20:21:44Z – user – shell_pid=18631 – ADRs written for Pi (2026-06-02-1) and Letta (2026-06-02-2), CLAUDE.md updated to 19 agents, ADR README index updated, GitHub issues #1050 and #1054 closed
- 2026-06-02T20:22:04Z – claude:claude-sonnet-4-6:curator-carla:reviewer – shell_pid=33209 – Started review via action command
- 2026-06-02T20:23:31Z – claude:claude-sonnet-4-6:curator-carla:reviewer – shell_pid=33209 – Review passed: ADRs well-formed, CLAUDE.md updated to 19 agents, both GitHub issues closed
