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
| T004 | Unit tests for resolver: correct path, no-doctrine error | WP04 | |
| T005 | Replace flat `templates_dir.glob("*.md")` with per-step `iterdir()` → `step_dir/prompt.md` | WP01 | |
| T006 | Add guards: skip non-dirs, non-PROMPT_DRIVEN steps, missing `prompt.md` | WP01 | |
| T007 | Move version lock write to after all `_sync_agent_commands()` calls succeed | WP01 | |
| T008 | Integration test: all 8 prompt-driven + 7 CLI-driven commands written correctly | WP04 | |
| T009 | Add `_get_slash_command_agents()` helper scoped to `config.available ∩ AGENT_COMMAND_CONFIG` | WP02 | |
| T010 | Add `_load_slash_command_state()`: per-agent gap check for all canonical commands | WP02 | |
| T011 | Extend `doctor skills` output with "Slash Commands" section | WP02 | |
| T012 | Ensure `doctor skills` reports unhealthy when slash-command files are missing | WP02 | |
| T013 | Unit tests: audit logic, false-positive prevention, scope guard | WP05 | |
| T014 | Add `_repair_slash_command_state()` calling `ensure_global_agent_commands()` scoped to configured agents | WP02 | |
| T015 | Wire `--fix` path in `doctor skills` to call repair when gaps exist | WP02 | |
| T016 | Verify idempotency: `--fix` with no gaps is a no-op; with gaps fills them | WP02 | |
| T017 | Integration test: detect gap → `--fix` → verify clean | WP05 | |
| T018 | Create `Makefile` with `dev-setup` target | WP03 | [P] |
| T019 | Add `.PHONY` and `help` target to `Makefile` | WP03 | [P] |
| T020 | Update `CONTRIBUTING.md` with dev-setup bootstrap instructions | WP03 | [P] |
| T021 | Verify `make dev-setup` is idempotent | WP03 | |
| T022 | Test: resolver returns correct doctrine path (mocked doctrine) | WP04 | [P] |
| T023 | Test: per-step iteration writes all 15 commands, removes stale files | WP04 | [P] |
| T024 | Test: lock only written after successful full install | WP04 | [P] |
| T025 | Test: doctor audit false-positive prevention (missing file → reported gap) | WP05 | [P] |
| T026 | Test: `--fix` scope guard (only configured agents touched) | WP05 | [P] |
| T027 | Test: `--fix` idempotency (twice → identical state) | WP05 | [P] |
| T028 | Verify `mypy --strict` passes on all new/changed modules | WP05 | |

---

## Work Package 01 — agent_commands.py Fix (resolver, renderer, lock)

**Goal**: Fix all three broken behaviours in `agent_commands.py`: resolver returns doctrine-based `Path`, renderer iterates per-step subdirs, lock written only after all syncs succeed.  
**Priority**: P0 — all other WPs depend on this  
**Estimated prompt size**: ~280 lines  
**Requires**: nothing  
**Blocks**: WP02, WP04

### Subtasks

- [ ] T001 Replace `_get_command_templates_dir()` body with `doctrine.__file__`-based resolution (WP01)
- [ ] T002 Remove stale location checks and fallback; change return type to `Path` (WP01)
- [ ] T003 Update callers to remove `None` guards (WP01)
- [ ] T005 Replace flat glob with per-step `iterdir()` → `step_dir/prompt.md` (WP01)
- [ ] T006 Add guards: skip non-dirs, non-PROMPT_DRIVEN steps, missing prompt.md (WP01)
- [ ] T007 Move version lock write to after all sync calls succeed (WP01)

### Implementation Notes

Use `Path(doctrine.__file__).parent / "missions" / "mission-steps" / "software-dev"` — exact pattern from `command_installer._package_templates_dir()`. Return type changes from `Path | None` to `Path`. Iterate `sorted(templates_dir.iterdir())`; skip non-dirs, unknown commands, and step dirs missing `prompt.md`. Lock write moves to after the full sync loop.

---

## Work Package 02 — doctor.py slash-command audit and --fix

**Goal**: Add slash-command health check and repair to `doctor skills`; extend `ensure_global_agent_commands()` with `agent_keys` param.  
**Priority**: P1  
**Estimated prompt size**: ~340 lines  
**Requires**: WP01  
**Blocks**: WP03, WP05

### Subtasks

- [ ] T009 Add `_get_slash_command_agents()` helper (WP02)
- [ ] T010 Add `_load_slash_command_state()` gap check (WP02)
- [ ] T011 Extend `doctor skills` output with Slash Commands section (WP02)
- [ ] T012 Ensure doctor reports unhealthy on missing files (WP02)
- [ ] T014 Add `_repair_slash_command_state()` calling installer scoped to configured agents (WP02)
- [ ] T015 Wire `--fix` to call repair when slash-command gaps exist (WP02)
- [ ] T016 Verify idempotency: `--fix` no-op when healthy (WP02)

### Implementation Notes

`_get_slash_command_agents()` returns `sorted(set(config.available) & set(AGENT_COMMAND_CONFIG.keys()))`. Extend `ensure_global_agent_commands()` with `agent_keys: list[str] | None = None` (backward-compatible). Scope guard: never touch agents not in `config.available`.

---

## Work Package 03 — Dev Bootstrap (Makefile + Docs)

**Goal**: Add `Makefile` with `dev-setup` target and update contributor docs so developers can bootstrap a working environment in one step.  
**Priority**: P1  
**Estimated prompt size**: ~220 lines  
**Requires**: WP02  
**Blocks**: nothing

### Subtasks

- [ ] T018 Create `Makefile` with `dev-setup` target (WP03)
- [ ] T019 Add `.PHONY` and `help` target (WP03)
- [ ] T020 Update `CONTRIBUTING.md` with dev-setup bootstrap instructions (WP03)
- [ ] T021 Verify `make dev-setup` is idempotent (WP03)

### Implementation Notes

`make dev-setup` runs `uv sync --frozen --all-extras && uv run spec-kitty doctor skills --fix`. CONTRIBUTING.md gets a "Developer Setup" section near the top. Idempotent because `doctor skills --fix` is idempotent.

---

## Work Package 04 — Runtime tests (agent_commands)

**Goal**: Write unit and integration tests for the `agent_commands.py` fixes: resolver, per-step renderer, lock timing, stale-file removal.  
**Priority**: P1  
**Estimated prompt size**: ~320 lines  
**Requires**: WP01  
**Blocks**: nothing

### Subtasks

- [ ] T004 Unit tests for resolver (WP04)
- [ ] T008 Integration test: all commands written correctly (WP04)
- [ ] T022 Test: resolver returns correct doctrine path (mocked doctrine) (WP04)
- [ ] T023 Test: per-step iteration writes all 15 commands and removes stale files (WP04)
- [ ] T024 Test: lock written only after full install success (WP04)

### Implementation Notes

Target: `tests/specify_cli/runtime/test_agent_commands.py`. Use `tmp_path` and `monkeypatch`; never touch real `~/.claude/commands/`. Each test class maps to one behaviour.

---

## Work Package 05 — Doctor tests (slash-command audit, --fix, mypy)

**Goal**: Write unit and integration tests for the `doctor skills` slash-command audit and `--fix` repair path. Includes mypy clean-bill sign-off.  
**Priority**: P1  
**Estimated prompt size**: ~380 lines  
**Requires**: WP02  
**Blocks**: nothing

### Subtasks

- [ ] T013 Unit tests: audit logic, false-positive prevention, scope guard (WP05)
- [ ] T017 Integration test: detect gap → --fix → verify clean (WP05)
- [ ] T025 Test: doctor audit false-positive prevention (WP05)
- [ ] T026 Test: --fix scope guard — only configured agents (WP05)
- [ ] T027 Test: --fix idempotency (WP05)
- [ ] T028 mypy --strict passes on all changed modules (WP05)

### Implementation Notes

Target: `tests/specify_cli/cli/commands/test_doctor_slash_commands.py`. Mock `get_global_command_dir`, `_load_slash_command_state`, and `ensure_global_agent_commands` where appropriate. Tests must not touch real agent directories.

---

## Parallelization

```
WP01 → WP02 → WP03
WP01 → WP04
WP02 → WP05
```

WP04 can start as soon as WP01 merges (parallel with WP02). WP05 starts after WP02. WP03 starts after WP02. Maximum parallel fan-out: 2 (WP02 + WP04 concurrently after WP01).
