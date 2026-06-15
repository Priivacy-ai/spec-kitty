---
work_package_id: WP03
title: Registry-backed agent-config sets (#1941)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
tracker_refs:
- '1941'
planning_base_branch: feat/tool-surface-contract-residuals
merge_target_branch: feat/tool-surface-contract-residuals
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract-residuals unless the human explicitly redirects the landing branch.
created_at: '2026-06-15T05:20:00+00:00'
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3918532"
history:
- date: '2026-06-15'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/skills/_agent_roster.py
- tests/specify_cli/skills/test_agent_roster.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/config.py
- src/specify_cli/skills/command_renderer.py
- src/specify_cli/skills/command_installer.py
- src/specify_cli/skills/_agent_roster.py
- tests/specify_cli/skills/test_agent_roster.py
- tests/specify_cli/cli/commands/test_agent_config.py
- tests/specify_cli/cli/commands/test_agent_config_vibe.py
- tests/specify_cli/cli/commands/test_agent_config_pi_letta.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: **python-pedro**, role: implementer). Then return here.

## Objective

Close #1941: derive `SKILL_ONLY_AGENTS` and `VALID_AGENTS` from the canonical registry (`command_installer.SUPPORTED_AGENTS`) instead of standalone hardcoded literals, eliminating the duplicated tool-universe — a behavior-preserving **connascence reduction** (`connascence-analysis`, DIRECTIVE_001/024). Also fold the third byte-identical copy (`command_renderer.SUPPORTED_AGENTS`) into the same source. Add the missing "configured Claude with session presence" test (FR-004).

## Context

- THREE copies of the skill-only roster: `config.py:51` `SKILL_ONLY_AGENTS = {"codex","vibe","pi","letta"}`; `skills/command_installer.py:45 SUPPORTED_AGENTS`; `skills/command_renderer.py:38 SUPPORTED_AGENTS`. `config.py:53` `VALID_AGENTS = set(AGENT_DIR_TO_KEY.values()) | SKILL_ONLY_AGENTS`.
- **⚠️ Cycle correction (adversarial review):** `command_installer.py:37` ALREADY does `from specify_cli.skills import command_renderer`. So you must **NOT** make `command_renderer` import from `command_installer` (real cycle). Instead, **extract a dependency-free leaf module `src/specify_cli/skills/_agent_roster.py`** holding the single `SUPPORTED_AGENTS` authority; `command_installer`, `command_renderer`, and `config.py` all import from it. (`config.py → skills` is cycle-free; `_agent_roster` imports nothing from skills.)
- Values are **equal today**, so accept/reject must stay byte-identical — pinned by `test_agent_config_compat.py` (do not weaken). NFR-001 is a hard gate.

## Subtasks (ATDD — tests first)

### T010 — RED tests (must prove *derivation*, not coincidence)
- `tests/specify_cli/skills/test_agent_roster.py`: assert `command_installer.SUPPORTED_AGENTS is _agent_roster.SUPPORTED_AGENTS` (or `==` the same object) AND a **monkeypatch-derivation test** — patch `_agent_roster.SUPPORTED_AGENTS`, assert `config.SKILL_ONLY_AGENTS` and `command_renderer.SUPPORTED_AGENTS` reflect the change (proves single-source, defeats the "coincidental equal literal" shortcut).
- `test_agent_config.py`: the **"configured Claude with session presence"** scenario (FR-004) — concrete assertion: a project with `claude` configured + a session-presence artifact present resolves the claude session-presence surface through the registry path (mirror the existing skill-only/global presence tests; **not** an `assert True` stub).

### T011 — Extract the leaf authority + rewire `config.py`
- Create `_agent_roster.py` with `SUPPORTED_AGENTS = ("codex","vibe","pi","letta")`. **Delete** the `SKILL_ONLY_AGENTS` literal from `config.py` (grep-proof: no inline `{"codex"...}` roster literal remains) and derive it from `_agent_roster.SUPPORTED_AGENTS`; `VALID_AGENTS` stays the derived union. Use a top-level import (config.py→skills is cycle-free — no lazy-import dodge needed).

### T012 — Collapse installer + renderer onto the leaf
- `command_installer.py` and `command_renderer.py`: replace their local `SUPPORTED_AGENTS` literals with `from specify_cli.skills._agent_roster import SUPPORTED_AGENTS`. State the cycle result explicitly in the handoff (no cycle: `_agent_roster` is a leaf). One authority; the other two are imports.

### T013 — Compat green
- `pytest -k "agent_config" -q` (incl. frozen `test_agent_config_compat.py`) green; `set(config.VALID_AGENTS) == set(AGENT_DIR_TO_KEY.values()) | set(_agent_roster.SUPPORTED_AGENTS)` asserted; ruff + mypy --strict clean.

## Branch Strategy

Planning/merge branch: **`feat/tool-surface-contract-residuals`** (PR → `main`). Lane worktree from `lanes.json`. `safe-commit --to-branch feat/tool-surface-contract-residuals`; status transitions from primary CWD.

## Definition of Done

- `SKILL_ONLY_AGENTS`/`VALID_AGENTS` derive from `command_installer.SUPPORTED_AGENTS`; no standalone tool-universe literal remains in `config.py`; `command_renderer` copy folded.
- Accept/reject set byte-identical (frozen compat test green); "configured Claude with session presence" test present + passing.
- ruff + mypy --strict clean; #1941 acceptance criteria met.

## Risks

- **Cycle (verified real):** `command_installer` imports `command_renderer` already — do NOT reverse it. The leaf `_agent_roster.py` is the only safe authority. `config.py → skills` is cycle-free (top-level import OK).
- "Registry-backed" must be **derivation, not a coincidental equal literal** — the literal must be deleted from `config.py` (grep-proof) and the monkeypatch test must prove the link.
- Must not change which tool keys are accepted/rejected (NFR-001; frozen compat test).

## Reviewer Guidance

Recommended reviewer: **reviewer-renata** (standard) + **architect-alphonso sign-off** on the connascence reduction (confirm a single authority, no new cycle, no behavior drift). Resolves **#1941** → terminal issue-matrix verdict (`fixed`).

## Activity Log

- 2026-06-15T06:05:02Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – Assigned agent via action command
- 2026-06-15T06:14:18Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – WP03 #1941 complete. Grep-proof: inline {codex...} SKILL_ONLY_AGENTS literal DELETED from config.py (grep '"codex"' src/.../agent/config.py => NONE); installer+renderer have no standalone tuple literal (only the leaf does). Single authority = src/specify_cli/skills/_agent_roster.py. Cycle result: NO CYCLE — _agent_roster imports nothing from specify_cli.skills, so it sits below command_installer's pre-existing import of command_renderer; all four modules import cleanly in a fresh interpreter. Monkeypatch-derivation test present: patches _agent_roster.SUPPORTED_AGENTS, reloads config, asserts SKILL_ONLY_AGENTS/VALID_AGENTS reflect the sentinel (defeats coincidental-equal-literal); installer/renderer single-source proved by is-identity tests (stronger than reload, and reloading them would rebind SkillRenderError types). FR-004 configured-Claude session-presence tests exercise the real registry/presence path (present + absent), not a stub. Compat GREEN: frozen test_agent_config_compat.py passes byte-identical. Gates: ruff clean, mypy --strict clean (4 src files); 101 passed in -k agent_config/agent_roster; 292 passed across skills+agent_config+compat suites.
- 2026-06-15T06:15:14Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3918532 – Started review via action command
- 2026-06-15T06:18:34Z – user – shell_pid=3918532 – APPROVED (reviewer-renata + architect-alphonso boundary sign-off). Alphonso boundary: fresh-interpreter import of all 4 modules succeeds; _agent_roster is a true leaf (no specify_cli imports); command_installer.SUPPORTED_AGENTS IS _agent_roster.SUPPORTED_AGENTS (is-identity); command_renderer.SUPPORTED_AGENTS IS _agent_roster.SUPPORTED_AGENTS (is-identity); command_renderer does NOT import command_installer — cycle check clean. Grep-proof: no standalone {codex,...} set literal in config.py (grep exit 1). Monkeypatch-derivation test patches _agent_roster.SUPPORTED_AGENTS, reloads config, asserts SKILL_ONLY_AGENTS/VALID_AGENTS reflect sentinel-tool — not a tautology (a coincidental literal would fail it). FR-004 tests (TestConfiguredClaudeSessionPresence) exercise the real SurfacePresenceIndex.build path via side_effect=real_build spy — present and absent states covered, both assert spy.called + concrete output checks. Frozen compat: 5/5 pass byte-identical. ruff clean (0 issues), mypy --strict clean (0 issues) on all 4 source files. WP03 commit (d4befdbd9) touches only owned_files; model.py/test_model.py changes are from WP01 base commit. Worktree clean. Anti-pattern checklist: dead code PASS (3 production callers), synthetic-fixture PASS (no assert True), silent-empty-return PASS (no new except/return patterns), FR coverage PASS (FR-003 derivation + FR-004 session-presence), frozen surface PASS (WP03 commit touches no frozen files), locked-decision PASS (no MUST NOT violations), shared-file ownership PASS (WP03 owns lane-c alone), production fragility PASS (no new bare raises).
