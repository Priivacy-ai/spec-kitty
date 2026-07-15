---
work_package_id: WP06
title: '#2668 — promote builtin_missions_root() + drop SLF001 (terminal campsite)'
dependencies:
- WP02
- WP03
- WP05
requirement_refs:
- C-005
- FR-012
tracker_refs:
- '2668'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
agent: "claude"
shell_pid: "3381969"
shell_pid_created_at: "1784147307.19"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — terminal WP (architect LOW-2); 2 SLF001 drops are documented out-of-map edits after file owners done.
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_builtin_missions_root.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/mission_type_profile_repository.py
- tests/charter/test_builtin_missions_root.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Promote `MissionTypeProfileRepository._default_built_in_dir` to a public `builtin_missions_root()` accessor
and remove the two `# noqa: SLF001` cross-class bypasses (#2668). Pure refactor, no behavior change. This is
the **terminal** WP — it consumes the promoted accessor and lands after the file owners (WP02, WP05) are done.

## Context — READ BEFORE CODING

- `MissionTypeProfileRepository._default_built_in_dir` (`src/charter/mission_type_profile_repository.py:94`)
  returns `Path(__file__).resolve().parents[1] / "doctrine" / "missions"` (`src/doctrine/missions`). Three
  consumers reach it:
  - `mission_type_profile_repository.py:70` — internal `__init__` (same class, no noqa).
  - `action_grain.py:202` — `MissionTypeProfileRepository._default_built_in_dir()  # noqa: SLF001` (**drop**).
  - `mission_type_profiles.py:649` — `repo._default_built_in_dir()  # noqa: SLF001` (**drop**).
- **Single-class scope (C-005):** 11 sibling doctrine repos have the same private `_default_built_in_dir`
  but call it intra-class with NO bypass — **do NOT touch them**. Only `MissionTypeProfileRepository`.
- **Out-of-map edits (documented leeway):** this WP OWNS only `mission_type_profile_repository.py`. Dropping
  the two noqa lines edits `action_grain.py` (owned by WP05) and `mission_type_profiles.py` (owned by WP02) —
  these are **small, well-justified out-of-map edits** made AFTER those WPs complete (hence the WP02/WP05
  dependencies). Record the one-line rationale in each edit ("consume the promoted `builtin_missions_root()`;
  the promotion lands here, WP06"). The no-overlap guard holds because WP06 is sequential after both.

## Subtasks

### T025 — [ATDD, RED FIRST] accessor test

New `tests/charter/test_builtin_missions_root.py`: assert `builtin_missions_root()` returns the path ending
`doctrine/missions` and that it equals the value the constructor uses. RED before T026.

### T026 — Promote the accessor

Add a public module-level `def builtin_missions_root() -> Path:` in `mission_type_profile_repository.py`
returning the same path; have the existing `_default_built_in_dir` classmethod delegate to it (or repoint
`__init__` to the function). Add `builtin_missions_root` to that module's `__all__`.

### T027 — Drop SLF001 in `action_grain.py` (out-of-map)

Replace `MissionTypeProfileRepository._default_built_in_dir()  # noqa: SLF001` (`action_grain.py:202`) with
`builtin_missions_root()` (import it). Remove the noqa. One-line rationale comment.

### T028 — Drop SLF001 in `mission_type_profiles.py` (out-of-map)

Replace `repo._default_built_in_dir()  # noqa: SLF001` (`mission_type_profiles.py:649`) with
`builtin_missions_root()`. Remove the noqa.

### T029 — Quality gate (full pre-hand-off)

- `uv run ruff check src/charter/ && uv run mypy --strict src/charter/mission_type_profile_repository.py src/charter/action_grain.py src/charter/mission_type_profiles.py`
- `grep -rn "_default_built_in_dir()  # noqa: SLF001" src/charter/` returns nothing.
- `uv run pytest tests/charter -q`
- **Full arch pole + terminology guard (mission is terminal — run the whole thing):**
  `uv run python -m pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' -q -n auto --dist loadfile`
  and `uv run python -m pytest tests/architectural/test_no_legacy_terminology.py -q`.

## Branch Strategy

Base/merge target `feat/mission-type-single-source-gate-wiring`. Terminal WP — depends on WP02, WP03, WP05.
Execution worktree per `lanes.json` lane.

## Definition of Done

- [ ] `builtin_missions_root()` public accessor added; classmethod delegates; behavior unchanged.
- [ ] Both `# noqa: SLF001` bypasses removed (`action_grain.py`, `mission_type_profiles.py`); grep clean.
- [ ] Only `MissionTypeProfileRepository` touched (C-005) — the 11 siblings untouched.
- [ ] ruff + mypy --strict clean; full arch_shard_1 pole + terminology guard green.
- [ ] ATDD: T025 committed RED first.

## Reviewer guidance

Pure refactor — verify byte-for-byte behavior (the returned path is identical). Confirm the two out-of-map
edits carry a rationale and that no sibling repo was swept. Confirm zero SLF001 bypasses of this accessor
remain.

## Activity Log

- 2026-07-15T20:28:34Z – claude – shell_pid=3381969 – Assigned agent via action command
