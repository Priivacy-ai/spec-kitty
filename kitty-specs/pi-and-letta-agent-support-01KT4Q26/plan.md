# Implementation Plan: Pi and Letta Code Agent Support

**Branch**: `main` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/pi-and-letta-agent-support-01KT4Q26/spec.md`

## Summary

This mission adds Pi (`pi-coding-agent`) and Letta Code (`letta`) as fully documented, first-class Spec Kitty agents. A codebase scan reveals that most implementation work (config registration, Agent Skills, init flow, gitignore, tests) has already landed on `main` via earlier development cycles. The remaining work is: (1) an upgrade migration to backfill gitignore entries and trigger a skill-pack repair in existing projects; (2) decision records documenting the key design choices; (3) documentation updates to CLAUDE.md's agent count and tables; and (4) closing the tracking issues.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (existing codebase); `BaseMigration` from `specify_cli.upgrade.migrations.base`; `command_installer` and `gitignore_manager` from existing modules
**Storage**: Files (`.kittify/config.yaml`, `.agents/skills/`, `.gitignore`, `architecture/adrs/`)
**Testing**: pytest with ≥ 90% line coverage for new migration code; `mypy --strict` must pass; integration test covering both agents
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform, same as existing codebase)
**Project Type**: Single Python CLI project
**Performance Goals**: Migration runs in < 5 seconds per project (same as existing skill-repair migrations)
**Constraints**: Migration must use `get_agent_dirs_for_project()` helper; must not recreate directories absent from the filesystem; pi and letta intentionally absent from `AGENT_COMMAND_CONFIG` (skill-only agents)

## Already Implemented (as of 2026-06-02 scan)

The following items are **complete** in the current `main` checkout and require no further implementation:

| Item | File | Evidence |
|------|------|----------|
| `AI_CHOICES` registration | `src/specify_cli/core/config.py:21-22` | `"pi": "Pi"`, `"letta": "Letta Code"` |
| `AGENT_TOOL_REQUIREMENTS` | `src/specify_cli/core/config.py:42-43` | `"pi"` and `"letta"` entries with docs URLs |
| `AGENT_SKILL_CONFIG` | `src/specify_cli/core/config.py:84-85` | `SKILL_CLASS_SHARED`, `.agents/skills/` + `.pi/skills/` |
| `SKILL_ONLY_AGENTS` set | `src/specify_cli/cli/commands/agent/config.py:39` | `{"codex", "vibe", "pi", "letta"}` |
| `command_renderer.SUPPORTED_AGENTS` | `src/specify_cli/skills/command_renderer.py:38` | includes `"pi"` and `"letta"` |
| `command_installer.SUPPORTED_AGENTS` | `src/specify_cli/skills/command_installer.py:43` | includes `"pi"` and `"letta"` |
| `init.py` agent-directory map | `src/specify_cli/cli/commands/init.py:866-867` | `.pi/` and `.letta/` entries |
| `agent/config.py` agent-directory map | `src/specify_cli/cli/commands/agent/config.py:866-867` | `.pi/` and `.letta/` entries |
| `gitignore_manager.py` | `src/specify_cli/gitignore_manager.py:61-62` | `AgentDirectory` entries for both agents |
| Tests — config registry | `tests/specify_cli/core/test_config_registry.py:39-40,54-55` | `AI_CHOICES`, `AGENT_TOOL_REQUIREMENTS` assertions |
| Tests — agent config pi/letta | `tests/specify_cli/cli/commands/test_agent_config_pi_letta.py` | parametrized for both keys |
| Tests — init pi/letta | `tests/specify_cli/cli/commands/test_init_pi_letta.py` | full init + skills + gitignore flow |
| Tests — skill installer | `tests/specify_cli/skills/test_command_installer.py:703` | `SUPPORTED_AGENTS` set assertion |
| Tests — parity regression | `tests/specify_cli/regression/test_twelve_agent_parity.py:203-204` | pi/letta absent from `AGENT_COMMAND_CONFIG` confirmed |

## Remaining Work

### 1. Upgrade Migration — Backfill Gitignore + Skill Repair for Existing Projects

Projects initialized before pi/letta support may be missing `.pi/` and `.letta/` gitignore entries. Although `m_2_1_1_repair_skill_pack` can re-install skill files for configured agents, it does not add gitignore entries. A dedicated migration is needed to:

- Add `.pi/` to `.gitignore` if `pi` is configured and the entry is absent
- Add `.letta/` to `.gitignore` if `letta` is configured and the entry is absent
- Trigger skill-pack repair for pi/letta if their `.agents/skills/spec-kitty.*` files are missing

**File**: `src/specify_cli/upgrade/migrations/m_3_3_0_pi_letta_backfill.py` (version number TBD via detector)

### 2. Decision Records — Pi and Letta Design Choices

DIRECTIVE_003 requires that material design decisions be captured. The following decisions from the two design spikes must be recorded in `architecture/adrs/`:

- **Pi**: Skill-only support chosen (no `.pi/prompts/` command templates); `pi` is a `SKILL_CLASS_SHARED` agent discovering `.agents/skills/` and `.pi/skills/`; orchestrator invoker deferred (external `spec-kitty-orchestrator` package scope)
- **Letta**: Skill-only support chosen (no `.letta/commands/` command templates); `letta` is a `SKILL_CLASS_SHARED` agent; persistent memory/session model deferred to orchestrator scope; `.letta/` gitignore entry covers runtime state, auth, and memory files

**Files**:
- `architecture/adrs/2026-06-02-1-pi-agent-skill-only-support.md`
- `architecture/adrs/2026-06-02-2-letta-agent-skill-only-support.md`

### 3. Documentation — Update Agent Count and Tables

CLAUDE.md currently states "17 AI agents total". With pi and letta it is 19. The agent support table in CLAUDE.md also needs the two new rows.

**File**: `CLAUDE.md` — update agent count (17 → 19) and Agent Skills Agents table

### 4. Close GitHub Issues

- Close issue #1050 (Pi CLI harness design spike) with a comment summarising what was implemented and what was deferred
- Close issue #1054 (Letta Code design spike) with a comment summarising what was implemented and what was deferred

## Charter Check

- **DIRECTIVE_001 (Architectural Integrity)**: ✅ Pi and letta follow the established `SKILL_CLASS_SHARED` pattern used by codex and vibe; no new architectural boundaries.
- **DIRECTIVE_003 (Decision Documentation)**: ⚠️ Decision records for Pi and Letta design choices are outstanding — addressed in work item 2.
- **DIRECTIVE_010 (Specification Fidelity)**: ✅ Implementation matches the agreed skill-only scope.
- **DIRECTIVE_024 (Locality of Change)**: ✅ Migration is isolated; decision records are additive.
- **DIRECTIVE_037 (Living Documentation Sync)**: ⚠️ CLAUDE.md agent count is stale — addressed in work item 3.

## Project Structure

### Documentation (this feature)

```
kitty-specs/pi-and-letta-agent-support-01KT4Q26/
├── plan.md              (this file)
├── research.md          (Phase 0 — inline, no open questions remain)
├── data-model.md        (not applicable — no new data entities)
└── tasks.md             (Phase 2 — generated by /spec-kitty.tasks)
```

### Source Code (repository root — new/modified files only)

```
src/specify_cli/upgrade/migrations/
└── m_3_3_0_pi_letta_backfill.py      (new — upgrade migration)

architecture/adrs/
├── 2026-06-02-1-pi-agent-skill-only-support.md    (new — decision record)
└── 2026-06-02-2-letta-agent-skill-only-support.md (new — decision record)

CLAUDE.md                              (update — agent count 17 → 19 + table rows)

tests/specify_cli/upgrade/migrations/
└── test_m_3_3_0_pi_letta_backfill.py (new — migration tests)
```

## Phase 0: Research

No blocking unknowns remain after the codebase scan. All design questions from the issues have been resolved by existing implementation choices:

| Question | Resolution | Source |
|----------|-----------|--------|
| Pi: skill-only, prompt-template, or orchestrator? | Skill-only (`SKILL_CLASS_SHARED`) chosen; `.pi/prompts/` not generated | `config.py:84`, `test_twelve_agent_parity.py:203` |
| Pi: `--mode json` vs `--mode rpc`? | Deferred — orchestrator invoker is external scope; not in this repo | No `PiInvoker` found in this codebase |
| Letta: stateless vs sticky session? | Deferred — orchestrator invoker is external scope | No `LettaInvoker` found in this codebase |
| Letta: `.letta/commands/` templates? | Not generated; skill-only like codex/vibe | `config.py:85`, `test_twelve_agent_parity.py:204` |
| `.agents/skills/` discovery without extra config? | Confirmed — both agents discover this root natively | `AGENT_SKILL_CONFIG`, `test_init_pi_letta.py` |
| Upgrade path for existing projects (skills)? | `m_2_1_1_repair_skill_pack` handles skill re-install; gitignore backfill migration is new work | `m_2_1_1_repair_skill_pack.py:141` |

**Output**: Findings captured inline above; no separate `research.md` file required.

## Phase 1: Design

### Upgrade Migration Design

The migration follows the `BaseMigration` + `MigrationRegistry.register` pattern established in `m_2_1_1_repair_skill_pack.py`. It:

1. Loads the agent config via `get_configured_agents(project_path)`.
2. For each of `pi` and `letta`, if configured:
   - Reads `.gitignore`, appends the agent directory entry if absent.
   - Checks `.agents/skills/spec-kitty.*/SKILL.md` presence; if any canonical skill is missing, delegates to `command_installer.install()`.
3. Returns a `MigrationResult` with `changes_made` list.
4. Is idempotent — running twice produces the same result.

### ADR Design

Each ADR follows the project's existing ADR template (see `architecture/adrs/`). It records:
- **Status**: Accepted
- **Context**: The design-spike questions from issues #1050 / #1054
- **Decision**: Skill-only support; no command template directories; orchestrator invoker deferred to external package
- **Consequences**: Pi and Letta users get `spec-kitty init --ai pi/letta` and `spec-kitty upgrade` support; orchestration via `spec-kitty next --agent pi/letta` requires the external `spec-kitty-orchestrator` package
