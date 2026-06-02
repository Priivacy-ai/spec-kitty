# Tasks: Slash Command Install Pipeline Repair

**Mission**: slash-command-install-pipeline-repair-01KT3H00  
**Branch**: kitty/mission-slash-command-install-pipeline-repair-01KT3H00 → merges to: main  
**GitHub issues**: #1608, #1609, #1610  
**Generated**: 2026-06-02

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Replace `_get_command_templates_dir()` body with `doctrine.__file__`-based resolution | WP01 | |
| T002 | Remove stale location checks and fallback logic; change return type to `Path` | WP01 | |
| T003 | Update callers of `_get_command_templates_dir()` to remove `None` guards | WP01 | |
| T004 | Unit tests for resolver: correct path, no-doctrine error | WP01 | |
| T005 | Replace flat `templates_dir.glob("*.md")` with per-step `iterdir()` → `step_dir/prompt.md` | WP02 | |
| T006 | Add guards: skip non-dirs, non-PROMPT_DRIVEN steps, missing `prompt.md` | WP02 | |
| T007 | Move version lock write to after all `_sync_agent_commands()` calls succeed | WP02 | |
| T008 | Integration test: all 8 prompt-driven + 7 CLI-driven commands written correctly | WP02 | |
| T009 | Add `_get_slash_command_agents()` helper scoped to `config.available ∩ AGENT_COMMAND_CONFIG` | WP03 | |
| T010 | Add `_load_slash_command_state()`: per-agent gap check for all canonical commands | WP03 | |
| T011 | Extend `doctor skills` output with "Slash Commands" section | WP03 | |
| T012 | Ensure `doctor skills` reports unhealthy when slash-command files are missing | WP03 | |
| T013 | Unit tests: audit logic, false-positive prevention, scope guard | WP03 | |
| T014 | Add `_repair_slash_command_state()` calling `ensure_global_agent_commands()` scoped to configured agents | WP04 | |
| T015 | Wire `--fix` path in `doctor skills` to call repair when gaps exist | WP04 | |
| T016 | Verify idempotency: `--fix` with no gaps is a no-op; with gaps fills them | WP04 | |
| T017 | Integration test: detect gap → `--fix` → verify clean | WP04 | |
| T018 | Create `Makefile` with `dev-setup` target | WP05 | [P] |
| T019 | Add `.PHONY` and `help` target to `Makefile` | WP05 | [P] |
| T020 | Update `CONTRIBUTING.md` with dev-setup bootstrap instructions | WP05 | [P] |
| T021 | Verify `make dev-setup` is idempotent | WP05 | |
| T022 | Test: resolver returns correct doctrine path (mocked doctrine) | WP06 | [P] |
| T023 | Test: per-step iteration writes all 15 commands, removes stale files | WP06 | [P] |
| T024 | Test: lock only written after successful full install | WP06 | [P] |
| T025 | Test: doctor audit false-positive prevention (missing file → reported gap) | WP06 | [P] |
| T026 | Test: `--fix` scope guard (only configured agents touched) | WP06 | [P] |
| T027 | Test: `--fix` idempotency (twice → identical state) | WP06 | [P] |
| T028 | Verify `mypy --strict` passes on all new/changed modules | WP06 | |

---

## Work Package 01 — Resolver Fix

**Goal**: Replace the broken `_get_command_templates_dir()` with a doctrine-based resolver that always returns a valid `Path`.  
**Priority**: P0 — all other WPs depend on this  
**Estimated prompt size**: ~280 lines  
**Requires**: nothing  
**Blocks**: WP02, WP03, WP04

### Subtasks

- [ ] T001 Replace `_get_command_templates_dir()` body with `doctrine.__file__`-based resolution (WP01)
- [ ] T002 Remove stale location checks and fallback; change return type to `Path` (WP01)
- [ ] T003 Update callers to remove `None` guards (WP01)
- [ ] T004 Unit tests for resolver (WP01)

### Implementation Notes

Use `Path(doctrine.__file__).parent / "missions" / "mission-steps" / "software-dev"` — exact pattern from `command_installer._package_templates_dir()`. Return type changes from `Path | None` to `Path`. The single caller is `ensure_global_agent_commands()`; its `None` branch becomes unreachable and is removed.

---

## Work Package 02 — Renderer + Lock Fix

**Goal**: Fix the template iteration pattern in `_sync_agent_commands()` and move the version lock write to post-install.  
**Priority**: P0  
**Estimated prompt size**: ~300 lines  
**Requires**: WP01  
**Blocks**: WP04

### Subtasks

- [ ] T005 Replace flat glob with per-step `iterdir()` → `step_dir/prompt.md` (WP02)
- [ ] T006 Add guards: skip non-dirs, non-PROMPT_DRIVEN steps, missing prompt.md (WP02)
- [ ] T007 Move version lock write to after all sync calls succeed (WP02)
- [ ] T008 Integration test: all 15 commands written correctly (WP02)

### Implementation Notes

Iterate `sorted(templates_dir.iterdir())`. For each `step_dir`: skip if not a directory; skip if `step_dir.name not in PROMPT_DRIVEN_COMMANDS`; skip if `step_dir / "prompt.md"` absent (log warning). Lock write moves from inside the fast-path branch to after the slow-path install loop.

---

## Work Package 03 — Doctor Slash-Command Audit

**Goal**: Add a slash-command health check path to `doctor skills` that detects gaps for configured agents.  
**Priority**: P1  
**Estimated prompt size**: ~320 lines  
**Requires**: WP01  
**Blocks**: WP04

### Subtasks

- [ ] T009 Add `_get_slash_command_agents()` helper (WP03)
- [ ] T010 Add `_load_slash_command_state()` gap check (WP03)
- [ ] T011 Extend `doctor skills` output with Slash Commands section (WP03)
- [ ] T012 Ensure doctor reports unhealthy on missing files (WP03)
- [ ] T013 Unit tests for audit logic (WP03)

### Implementation Notes

`_get_slash_command_agents()` returns `sorted(set(config.available) & set(AGENT_COMMAND_CONFIG.keys()))`. For each agent, call `get_global_command_dir(agent_key)` and check existence of each `spec-kitty.{command}.{ext}` file. Expose results under a new "Slash Commands" table in doctor output. Aggregate into overall health: healthy only if ALL configured agents have ALL canonical commands.

---

## Work Package 04 — Doctor --fix Repair Path

**Goal**: Wire `doctor skills --fix` to call `ensure_global_agent_commands()` for configured agents, with scope guard and idempotency.  
**Priority**: P1  
**Estimated prompt size**: ~300 lines  
**Requires**: WP02, WP03  
**Blocks**: WP05

### Subtasks

- [ ] T014 Add `_repair_slash_command_state()` calling installer scoped to configured agents (WP04)
- [ ] T015 Wire `--fix` to call repair when slash-command gaps exist (WP04)
- [ ] T016 Verify idempotency (WP04)
- [ ] T017 Integration test: detect gap → --fix → clean (WP04)

### Implementation Notes

`_repair_slash_command_state()` calls `ensure_global_agent_commands(agent_keys=configured_slash_agents)` — extend `ensure_global_agent_commands()` to accept an optional `agent_keys` parameter to limit scope. Scope guard: never touch agents not in `config.available`. Idempotency: if all commands already present, skip write; return repaired-files count (0 = no-op).

---

## Work Package 05 — Dev Bootstrap (Makefile + Docs)

**Goal**: Add `Makefile` with `dev-setup` target and update contributor docs so developers can bootstrap a working environment in one step.  
**Priority**: P1  
**Estimated prompt size**: ~220 lines  
**Requires**: WP04  
**Blocks**: nothing

### Subtasks

- [ ] T018 Create `Makefile` with `dev-setup` target (WP05)
- [ ] T019 Add `.PHONY` and `help` target (WP05)
- [ ] T020 Update `CONTRIBUTING.md` with dev-setup bootstrap instructions (WP05)
- [ ] T021 Verify `make dev-setup` is idempotent (WP05)

### Implementation Notes

`make dev-setup` runs `uv sync --frozen --all-extras && uv run spec-kitty doctor skills --fix`. This is idempotent because Fix 2 (`doctor skills --fix`) is idempotent. CONTRIBUTING.md gets a "Developer Setup" section near the top explaining that `make dev-setup` must be run after cloning or after any spec-kitty template change.

---

## Work Package 06 — Test Coverage

**Goal**: Write all remaining unit and integration tests to satisfy NFR-004 (100% branch coverage on new code) and DIR-005.  
**Priority**: P1  
**Estimated prompt size**: ~400 lines  
**Requires**: WP01, WP02, WP03, WP04  
**Blocks**: nothing

### Subtasks

- [ ] T022 Test: resolver correct path (mocked doctrine) (WP06)
- [ ] T023 Test: per-step iteration writes all 15 commands and removes stale files (WP06)
- [ ] T024 Test: lock written only after full install success (WP06)
- [ ] T025 Test: doctor audit false-positive prevention (WP06)
- [ ] T026 Test: --fix scope guard — only configured agents (WP06)
- [ ] T027 Test: --fix idempotency (WP06)
- [ ] T028 mypy --strict passes on all changed modules (WP06)

### Implementation Notes

Use `tmp_path` and `monkeypatch` to mock `doctrine.__file__`, config, and `AGENT_COMMAND_CONFIG`. Tests should not depend on actual filesystem state of `~/.claude/commands/`. Each test class maps to one behaviour: resolver, renderer, lock, audit, fix-scope, fix-idempotency.

---

## Parallelization

```
WP01 → WP02 ─┐
WP01 → WP03 ─┤→ WP04 → WP05 → [done]
              └→ WP06 (can start after WP01-04 all done)
```

WP02 and WP03 can run in parallel after WP01. WP05 and WP06 can run in parallel after WP04 completes. Maximum parallel fan-out: 2 (WP02 + WP03 concurrently).
