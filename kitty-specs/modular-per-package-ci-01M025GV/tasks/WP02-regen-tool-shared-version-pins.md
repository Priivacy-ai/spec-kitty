---
work_package_id: WP02
title: Standalone regen tool + shared version pins
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-004
- NFR-005
- C-006
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-modular-per-package-ci-01M025GV
base_commit: b64f3b7902d9d2fa00993135b037efc6a1bc9d5c
created_at: '2026-08-15T08:54:45.178363+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Tooling
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/specify_cli/regression/test_twelve_agent_parity.py
create_intent:
- src/specify_cli/cli/commands/regen.py
- src/specify_cli/skills/render_versions.py
- tests/specify_cli/cli/commands/test_regen.py
execution_mode: code_change
owned_files:
- tests/specify_cli/regression/test_twelve_agent_parity.py
- tests/specify_cli/regression/_twelve_agent_baseline/**
- tests/specify_cli/skills/test_command_renderer.py
- tests/specify_cli/skills/__snapshots__/**
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Standalone regen tool + shared version pins

**Implements**: FR-003, FR-004, FR-005; NFR-004, NFR-005; C-006. IC-02. (Mission `research.md` D2.)

## Goal

Add `spec-kitty regen [--check] [--json]` that regenerates the 168 committed generated fixtures from source
templates, byte-identical to a `PYTEST_UPDATE_SNAPSHOTS=1` pytest run. Model the command on the existing
dual-mode `spec-kitty doctrine regenerate-graph --check` (`src/specify_cli/cli/commands/doctrine.py:211-294`).

## Scope

- NEW `src/specify_cli/cli/commands/regen.py`; register in `cli/commands/__init__.py` alongside `materialize`.
- **Command fixtures** (144): loop `AGENT_COMMAND_CONFIG.keys()` (12) × `PROMPT_BACKED_COMMANDS` (12); call
  `render_command_template()` (`src/specify_cli/template/asset_generator.py:117`); write
  `tests/specify_cli/regression/_twelve_agent_baseline/<agent>/<command>.<ext>`.
- **Skill snapshots** (24): loop `("codex","vibe")` × `PROMPT_BACKED_COMMANDS`; call
  `command_renderer.render(template_path, agent_key, version).to_skill_md()`
  (`src/specify_cli/skills/command_renderer.py:384`, `:124`); write
  `tests/specify_cli/skills/__snapshots__/<agent>/<command>.SKILL.md`.
- **FR-005 shared version pins**: create a shared constants module holding the two render versions (twelve-agent
  `3.1.2a3`, skills `3.0.0`) and refactor BOTH `test_twelve_agent_parity.py` and `test_command_renderer.py` to
  import them instead of hard-coding (`test_twelve_agent_parity.py:80`, `test_command_renderer.py:72`). `regen`
  imports the same constants — single source of truth.
- **Check mode**: render to memory/tempdir, `difflib` byte-diff vs committed fixtures, exit non-zero on drift,
  print offending `<agent>/<command>` + unified diff + literal `Run: spec-kitty regen`; `--json` structured output.
- Reuse existing render logic only — NO new render path (C-006).

## ATDD / red-first (C-008)

- **T001 (RED first)**: fidelity test — after an intentional stale edit to one fixture, `spec-kitty regen`
  restores it byte-identically and `pytest tests/specify_cli/regression/test_twelve_agent_parity.py
  tests/specify_cli/skills/test_command_renderer.py` passes. RED before the command exists, GREEN after.
- **T002**: `regen --check` exit-code test — stale fixture ⇒ exit 1 + message contains `Run: spec-kitty regen`;
  fresh ⇒ exit 0; `--json` shape asserted.
- **T003**: shared-pin test — asserts the two versions come from the shared constants and both suites + regen
  reference them (a divergence must fail a test, not silently mismatch).

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_regen.py tests/specify_cli/regression/test_twelve_agent_parity.py tests/specify_cli/skills/test_command_renderer.py -q
spec-kitty regen --check --json   # manual smoke
ruff check src/specify_cli/cli/commands/regen.py && mypy src/specify_cli/cli/commands/regen.py
```

## Acceptance (SC-002, SC-003)

- `spec-kitty regen` regenerates all 168 fixtures byte-identically to a `PYTEST_UPDATE_SNAPSHOTS=1` run (NFR-005).
- An edited source prompt + `spec-kitty regen` ⇒ green gate; same edit without regen ⇒ `--check` fails with the
  exact remediation command.
- Version pins are a single shared source of truth (FR-005).
