# Tasks: Session Presence Multi-Harness Orientation

**Mission**: session-presence-multi-harness-01KTH57W
**Branch**: `pr/session-presence-multi-harness` → target `pr/session-presence-multi-harness`
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `session_presence/__init__.py`, `writers/__init__.py`, `hooks/__init__.py` with `__all__` | WP01 | — |
| T002 | Implement `SessionPresenceContent` + `render()` in `content.py` | WP01 | [P] |
| T003 | Implement `UpgradeChecker` in `upgrade_check.py` | WP01 | [P] |
| T004 | Define `Writer` protocol (runtime_checkable) in `writers/base.py` | WP01 | [P] |
| T005 | Implement `NullWriter` in `writers/null_writer.py` | WP01 | [P] |
| T006 | Implement skeleton `writers/registry.py` with `get_writer()` (all → NullWriter) | WP01 | — |
| T007 | Implement `MarkdownRulesWriter` in `writers/markdown_rules.py` | WP02 | — |
| T008 | Implement `ClaudeCodeWriter` in `writers/claude_code.py` | WP02 | — |
| T009 | Define `HookRegistrar` protocol in `hooks/base.py` | WP02 | [P] |
| T010 | Implement `ClaudeCodeHookRegistrar` in `hooks/claude_code_hook.py` | WP02 | — |
| T011 | Wire `claude → ClaudeCodeWriter()` in `writers/registry.py` | WP02 | — |
| T012 | Implement `SessionPresenceManager` in `manager.py` | WP03 | — |
| T013 | Implement `session-start` CLI command in `cli/commands/session_start.py` | WP03 | — |
| T014 | Register `session-start` in `__init__.py`; add `install()` call to `init.py` | WP03 | — |
| T015 | Write `m_3_3_0_session_presence_claude_code.py` upgrade migration | WP03 | — |
| T016 | Run full existing test suite; open GitHub issue if pre-existing failures found (DIR-013) | WP03 | — |
| T017 | Write `conftest.py` + `test_content.py` | WP04 | — |
| T018 | Write `test_upgrade_checker.py` | WP04 | [P] |
| T019 | Write `test_markdown_rules_writer.py` | WP04 | [P] |
| T020 | Write `test_claude_code_writer.py` + `test_claude_code_hook.py` | WP04 | [P] |
| T021 | Write `test_manager.py` + `test_session_start.py` | WP04 | [P] |
| T022 | Write `test_m_session_presence_claude_code.py` | WP04 | — |
| T023 | Implement `AgentsMdWriter` in `writers/agents_md.py` | WP05 | — |
| T024 | Implement `SkillsPreambleWriter` in `writers/skills_preamble.py` | WP05 | — |
| T025 | Add Pattern B entries to `WRITER_REGISTRY` (cursor, windsurf, copilot, roo, kiro, gemini) | WP05 | — |
| T026 | Add Pattern C + D + E entries to `WRITER_REGISTRY` | WP05 | — |
| T027 | Write `test_agents_md_writer.py` + `test_skills_preamble_writer.py` | WP05 | [P] |
| T028 | Write `m_3_3_0_session_presence_all_harnesses.py` upgrade migration | WP06 | — |
| T029 | Write `test_m_session_presence_all_harnesses.py` | WP06 | — |
| T030 | Integration smoke: verify all harnesses write orientation + idempotency in full test run | WP06 | — |

---

## Work Package 1 — Session Presence Package Foundation

**Goal**: Create the `session_presence` package skeleton: package init files, `SessionPresenceContent`, `UpgradeChecker`, `Writer` protocol, `NullWriter`, and a skeleton registry.
**Priority**: P0 — blocks everything
**Success criteria**: `from specify_cli.session_presence.content import SessionPresenceContent` works; `UpgradeChecker().get_available_version()` returns None without raising; `get_writer("any")` returns a `NullWriter`
**Estimated prompt size**: ~350 lines
**Depends on**: none

- [ ] T001 Create package init files with `__all__` (WP01)
- [ ] T002 Implement `SessionPresenceContent` + `render()` (WP01)
- [ ] T003 Implement `UpgradeChecker` (WP01)
- [ ] T004 Define `Writer` protocol (WP01)
- [ ] T005 Implement `NullWriter` (WP01)
- [ ] T006 Implement skeleton registry with `get_writer()` (WP01)

**Prompt**: [WP01-session-presence-package-foundation.md](tasks/WP01-session-presence-package-foundation.md)

---

## Work Package 2 — Claude Code Writer and Hook Registrar

**Goal**: Implement `MarkdownRulesWriter` (generic section idempotency), `ClaudeCodeWriter` (extends it with hook management), `HookRegistrar` protocol, and `ClaudeCodeHookRegistrar` (settings.json merge). Wire `claude` in registry.
**Priority**: P0
**Success criteria**: `ClaudeCodeWriter().write(project_root, content)` appends orientation section to `.claude/CLAUDE.md` and registers the hook in `.claude/settings.json`; calling write() twice produces no duplicates
**Estimated prompt size**: ~420 lines
**Depends on**: WP01

- [x] T007 Implement `MarkdownRulesWriter` (WP02)
- [x] T008 Implement `ClaudeCodeWriter` (WP02)
- [x] T009 Define `HookRegistrar` protocol (WP02)
- [x] T010 Implement `ClaudeCodeHookRegistrar` (WP02)
- [x] T011 Wire `claude → ClaudeCodeWriter()` in registry (WP02)

**Prompt**: [WP02-claude-code-writer-and-hook-registrar.md](tasks/WP02-claude-code-writer-and-hook-registrar.md)

---

## Work Package 3 — Manager, CLI Command, init Integration, and Phase 1 Migration

**Goal**: Build `SessionPresenceManager` (orchestrates all writers), `session-start` CLI command (exit-0 orientation emitter), wire into `spec-kitty init`, and write the Phase 1 upgrade migration.
**Priority**: P0
**Success criteria**: `spec-kitty session-start` outputs orientation in a spec-kitty project and exits 0; `spec-kitty init --ai claude` writes orientation to `.claude/CLAUDE.md` and `.claude/settings.json`; migration detects and backfills existing projects
**Estimated prompt size**: ~450 lines
**Depends on**: WP01, WP02

- [x] T012 Implement `SessionPresenceManager` (WP03)
- [x] T013 Implement `session-start` command (WP03)
- [x] T014 Register command + wire `install()` in `init.py` (WP03)
- [x] T015 Write Phase 1 upgrade migration (WP03)
- [x] T016 Pre-implementation test suite check (DIR-013) (WP03)

**Prompt**: [WP03-manager-cli-command-init-integration.md](tasks/WP03-manager-cli-command-init-integration.md)

---

## Work Package 4 — Phase 1 Test Suite

**Goal**: Full test coverage for all Phase 1 modules: content, upgrade checker, markdown rules writer, Claude Code writer, hook registrar, manager, session-start command, and Phase 1 migration.
**Priority**: P0
**Success criteria**: `pytest tests/specify_cli/session_presence/ tests/specify_cli/cli/commands/test_session_start.py tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py` all pass; zero ruff/mypy issues
**Estimated prompt size**: ~480 lines
**Depends on**: WP01, WP02, WP03

- [ ] T017 Write `conftest.py` + `test_content.py` (WP04)
- [ ] T018 Write `test_upgrade_checker.py` (WP04)
- [ ] T019 Write `test_markdown_rules_writer.py` (WP04)
- [ ] T020 Write `test_claude_code_writer.py` + `test_claude_code_hook.py` (WP04)
- [ ] T021 Write `test_manager.py` + `test_session_start.py` (WP04)
- [ ] T022 Write `test_m_session_presence_claude_code.py` (WP04)

**Prompt**: [WP04-phase1-test-suite.md](tasks/WP04-phase1-test-suite.md)

---

## Work Package 5 — Phase 2 Writers and Registry Population

**Goal**: Implement `AgentsMdWriter` (Pattern C) and `SkillsPreambleWriter` (Pattern D), populate the registry with all Pattern B/C/D entries and Pattern E NullWriter stubs, and write the Pattern B–D test suite.
**Priority**: P1 — depends on Phase 1 merge
**Success criteria**: `get_writer("cursor")` returns a `MarkdownRulesWriter`; `get_writer("codex")` returns an `AgentsMdWriter`; `get_writer("qwen")` returns a `NullWriter`; writing orientation for a Cursor project creates `.cursor/rules/spec-kitty.mdc`
**Estimated prompt size**: ~440 lines
**Depends on**: WP01, WP02, WP03, WP04

- [ ] T023 Implement `AgentsMdWriter` (WP05)
- [ ] T024 Implement `SkillsPreambleWriter` (WP05)
- [ ] T025 Add Pattern B registry entries (WP05)
- [ ] T026 Add Pattern C + D + E registry entries (WP05)
- [ ] T027 Write tests for new writers (WP05)

**Prompt**: [WP05-phase2-writers-and-registry.md](tasks/WP05-phase2-writers-and-registry.md)

---

## Work Package 6 — Phase 2 Migration and Tests

**Goal**: Write and test the `m_3_3_0_session_presence_all_harnesses` upgrade migration that backfills orientation for all non-Claude harnesses on existing projects; verify full end-to-end idempotency.
**Priority**: P1
**Success criteria**: `spec-kitty upgrade` backfills orientation for all configured Pattern B/C/D harnesses; running upgrade twice produces no duplicates; migration's `detect()` returns True only when configured non-Claude harnesses are missing presence
**Estimated prompt size**: ~320 lines
**Depends on**: WP05

- [ ] T028 Write Phase 2 upgrade migration (WP06)
- [ ] T029 Write `test_m_session_presence_all_harnesses.py` (WP06)
- [ ] T030 Integration smoke + full test run verification (WP06)

**Prompt**: [WP06-phase2-migration-and-tests.md](tasks/WP06-phase2-migration-and-tests.md)
