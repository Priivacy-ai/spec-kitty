# Implementation Plan: Session Presence Multi-Harness Orientation

**Branch**: `pr/session-presence-multi-harness` | **Date**: 2026-06-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/session-presence-multi-harness-01KTH57W/spec.md`

## Summary

Build a `session_presence` package that injects idempotent orientation blocks into each configured AI agent's native config files during `spec-kitty init` and `spec-kitty upgrade`. Phase 1 establishes the package foundation and covers Claude Code exclusively — CLAUDE.md orientation section, SessionStart hook in settings.json, `spec-kitty session-start` CLI command, and an upgrade migration. Phase 2 extends to all remaining harnesses via Pattern B/C/D writers and a second upgrade migration. All phases share the same `Writer` protocol, `SessionPresenceContent` value object, and `SessionPresenceManager` orchestrator defined in Phase 1.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (existing), rich (existing), importlib.metadata (stdlib), pathlib (stdlib), json (stdlib), subprocess (stdlib — background version check only), os.replace (stdlib — cross-platform atomic rename)
**Storage**: Local filesystem only — `.claude/CLAUDE.md` (section append/replace), `.claude/settings.json` (JSON merge), `~/.kittify/last-cli-check.json` (version check cache), harness-specific rules files per Pattern B/C/D
**Testing**: pytest; one test module per new source module; `tests/specify_cli/session_presence/conftest.py` for shared fixtures; all subprocess calls mocked in tests; no network calls during test execution
**Target Platform**: Linux, macOS, Windows 10+ — `os.replace()` used for all atomic writes; `Path.home()` for home directory resolution
**Project Type**: Single Python package
**Performance Goals**: `session-start` under 200ms on warm filesystem; version check background-only — zero blocking network calls on the hot path
**Constraints**: Exit 0 on all `session-start` code paths including all exceptions; atomic writes via temp-file + os.replace; no imports from `src/specify_cli/next/` shim; `__all__` required on all new public modules (C-007); zero ruff issues; zero mypy issues

## Charter Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

| Directive | Status | Note |
|---|---|---|
| DIR-001 Cross-platform | ✅ Compliant | `os.replace()` for atomic writes; `Path.home()` for home dir; no platform-specific APIs |
| DIR-002 Python 3.11+ | ✅ Compliant | `from __future__ import annotations`, `dataclasses`, `Literal`, `Protocol`, `runtime_checkable` |
| DIR-005 Tests added | ✅ Required | 10 test modules planned; must all pass before merge |
| DIR-006 Type annotations | ✅ Required | mypy --strict gate applies to all new modules |
| DIR-007 Docstrings | ✅ Required | All public classes and methods in `session_presence/` |
| DIR-008 No security issues | ✅ Compliant | No credentials handled; background subprocess spawns `uv`/`curl` with no user input |
| DIR-009 Breaking changes | ✅ N/A | New package; no existing public API modified |
| DIR-010 ASCII identifiers | ✅ Compliant | `project_slug` sanitized upstream by `AgentConfig`; rendered text only |
| DIR-012 Assign ticket to HiC | ⚠️ Required | Assign GitHub issues #1760 and #1761 to the Human-in-Charge before implementation begins |
| DIR-013 Pre-existing failures | ⚠️ Required | Run full test suite before first implementation commit; open issue if pre-existing failures found |
| C-004 Burn-down Policy | ✅ Compliant | Scope bounded by spec FR-001–017, NFR-001–004, C-001–005 |
| C-007 `__all__` Convention | ⚠️ Required | Every `__init__.py` in `session_presence/` and sub-packages must declare `__all__` |
| C-011 ATDD-First Discipline | ⚠️ Required | Test stubs with failing acceptance cases committed before or alongside each concern's implementation |

*Post-Phase-1 re-check: No new charter conflicts introduced by design.*

## Project Structure

### Documentation (this mission)

```
kitty-specs/session-presence-multi-harness-01KTH57W/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    ├── claude-md-section.md      # Orientation block file format
    ├── settings-json-hook.md     # SessionStart hook JSON structure
    └── version-cache.md          # ~/.kittify/last-cli-check.json format
```

### Source Code (repository root)

```
src/specify_cli/
├── session_presence/               # NEW package (Phase 1 foundation)
│   ├── __init__.py
│   ├── content.py                  # SessionPresenceContent value object + render()
│   ├── upgrade_check.py            # UpgradeChecker: TTL cache + background refresh
│   ├── manager.py                  # SessionPresenceManager: install() + update()
│   ├── writers/
│   │   ├── __init__.py
│   │   ├── base.py                 # Writer protocol (runtime_checkable)
│   │   ├── markdown_rules.py       # MarkdownRulesWriter (Phase 1)
│   │   ├── claude_code.py          # ClaudeCodeWriter extends MarkdownRulesWriter (Phase 1)
│   │   ├── agents_md.py            # AgentsMdWriter (Phase 2)
│   │   ├── skills_preamble.py      # SkillsPreambleWriter (Phase 2)
│   │   ├── null_writer.py          # NullWriter fallback (Phase 1)
│   │   └── registry.py             # WRITER_REGISTRY + get_writer() (Phase 1 entries)
│   └── hooks/
│       ├── __init__.py
│       ├── base.py                 # HookRegistrar protocol
│       └── claude_code_hook.py     # ClaudeCodeHookRegistrar for settings.json
├── cli/commands/
│   └── session_start.py            # NEW: `spec-kitty session-start` command (Phase 1)
└── upgrade/migrations/
    ├── m_3_3_0_session_presence_claude_code.py     # NEW: Phase 1 migration
    └── m_3_3_0_session_presence_all_harnesses.py   # NEW: Phase 2 migration

tests/specify_cli/
├── session_presence/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_content.py
│   ├── test_markdown_rules_writer.py
│   ├── test_claude_code_writer.py
│   ├── test_claude_code_hook.py
│   ├── test_upgrade_checker.py
│   ├── test_manager.py
│   ├── test_agents_md_writer.py         # Phase 2
│   └── test_skills_preamble_writer.py   # Phase 2
├── cli/commands/
│   └── test_session_start.py
└── upgrade/migrations/
    ├── test_m_session_presence_claude_code.py
    └── test_m_session_presence_all_harnesses.py
```

**Structure Decision**: Single project, extending existing `src/specify_cli/` tree. All new code in `session_presence/` sub-package plus one CLI command module and two migration files.

## Implementation Concern Map

### IC-01 — Session Presence Package Foundation

- **Purpose**: Define `SessionPresenceContent` (value object + render), `Writer` protocol, `NullWriter`, and `UpgradeChecker` with TTL cache — the shared foundation that all subsequent concerns depend on.
- **Relevant requirements**: FR-003, FR-006, FR-008, FR-009, NFR-001, NFR-002, C-003, C-007
- **Affected surfaces**: `src/specify_cli/session_presence/__init__.py`, `content.py`, `upgrade_check.py`, `writers/__init__.py`, `writers/base.py`, `writers/null_writer.py`, `writers/registry.py` (skeleton with `claude` → `NullWriter` placeholder)
- **Sequencing/depends-on**: none
- **Risks**: `UpgradeChecker.check_in_background()` must never raise; cache write must be atomic; test with subprocess mocked to fail silently

### IC-02 — Claude Code Writer and Hook Registrar

- **Purpose**: Implement `MarkdownRulesWriter` (generic Markdown section idempotency), `ClaudeCodeWriter` (extends MarkdownRulesWriter, adds hook management), and `ClaudeCodeHookRegistrar` (reads/merges/writes `.claude/settings.json` preserving all unrelated entries).
- **Relevant requirements**: FR-001, FR-002, FR-007, FR-008, C-002, C-003, NFR-003
- **Affected surfaces**: `writers/markdown_rules.py`, `writers/claude_code.py`, `hooks/__init__.py`, `hooks/base.py`, `hooks/claude_code_hook.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: No existing `settings.json` helper in codebase — `ClaudeCodeHookRegistrar` must handle: file absent, file present but malformed JSON, file with existing hooks. All writes atomic. `remove()` must not touch unrelated `SessionStart` entries.

### IC-03 — SessionPresenceManager, init.py Integration, and session-start Command

- **Purpose**: Build `SessionPresenceManager.install()` / `update()` that iterates configured agents and delegates to their writers; wire into `cli/commands/init.py`; implement the `session-start` CLI command that emits orientation to stdout.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-013, FR-014, NFR-001, C-004
- **Affected surfaces**: `session_presence/manager.py`, `cli/commands/session_start.py`, `src/specify_cli/__init__.py` (register command), `cli/commands/init.py` (add `SessionPresenceManager(...).install()` after agent setup)
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: `session-start` must exit 0 even on: no `.kittify/` found, `AgentConfig.load()` raises, `_build_content()` raises, `render()` raises. All code paths covered by tests including the exception-swallowing wrapper.

### IC-04 — Phase 1 Migration and Full Test Suite

- **Purpose**: Write the `m_3_3_0_session_presence_claude_code` migration (`detect()` checks CLAUDE.md section + settings.json hook; `apply()` calls `ClaudeCodeWriter.write()`; `runs_on_worktrees = False`) and all Phase 1 tests.
- **Relevant requirements**: FR-007, FR-008, C-011 (ATDD)
- **Affected surfaces**: `upgrade/migrations/m_3_3_0_session_presence_claude_code.py`, all `tests/specify_cli/session_presence/test_{content,markdown_rules_writer,claude_code_writer,claude_code_hook,upgrade_checker,manager}.py`, `tests/specify_cli/cli/commands/test_session_start.py`, `tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py`
- **Sequencing/depends-on**: IC-01, IC-02, IC-03
- **Risks**: `detect()` must check both artefacts independently (CLAUDE.md section AND settings.json hook); `dry_run=True` must produce zero filesystem changes; regression: idempotent re-apply must leave files unchanged

### IC-05 — Phase 2 Writers and Registry Population

- **Purpose**: Implement `AgentsMdWriter` (Pattern C: Codex/OpenCode/Antigravity → AGENTS.md at project root), `SkillsPreambleWriter` (Pattern D: Pi/Vibe/Letta → AGENTS.md default, refinable per research notes), and populate `WRITER_REGISTRY` with all 19 harness entries including Pattern E `NullWriter` stubs.
- **Relevant requirements**: FR-010, FR-011, FR-012, FR-013, FR-016, FR-017, C-005
- **Affected surfaces**: `writers/agents_md.py`, `writers/skills_preamble.py`, `writers/registry.py` (add Pattern B entries via `MarkdownRulesWriter`, Pattern C via `AgentsMdWriter`, Pattern D via `SkillsPreambleWriter`, Pattern E via `NullWriter`)
- **Sequencing/depends-on**: IC-01 through IC-04 must be merged before IC-05 begins
- **Risks**: `SkillsPreambleWriter` defaults to AGENTS.md; `architecture/3.x/research/session-presence-harness-gaps.md` may update this before implementation. Pattern E harnesses (qwen, kilocode, auggie, q) must have explicit `NullWriter` entries — no silent gaps in the registry.

### IC-06 — Phase 2 Migration and Test Suite

- **Purpose**: Write the `m_3_3_0_session_presence_all_harnesses` migration (`detect()` uses `get_agent_dirs_for_project()`, excludes `claude`, checks each configured non-Claude agent for missing presence; `apply()` calls `SessionPresenceManager(...).update(agents=..., dry_run=...)`) and all Phase 2 tests.
- **Relevant requirements**: FR-015, FR-016, FR-017, C-005
- **Affected surfaces**: `upgrade/migrations/m_3_3_0_session_presence_all_harnesses.py`, `tests/specify_cli/session_presence/test_agents_md_writer.py`, `tests/specify_cli/session_presence/test_skills_preamble_writer.py`, `tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py`
- **Sequencing/depends-on**: IC-05
- **Risks**: Never hardcode the agent list; `detect()` must return True only when at least one configured non-Claude agent has a non-NullWriter with missing presence; regression test that adding a new registry entry activates detection without requiring a new migration
