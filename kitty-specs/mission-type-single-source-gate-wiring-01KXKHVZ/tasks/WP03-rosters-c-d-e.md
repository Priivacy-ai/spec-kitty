---
work_package_id: WP03
title: '#2669 — Charter Rosters C+D+E: migration live-read, sentinels, alias'
dependencies:
- WP01
requirement_refs:
- C-004
- C-011
- C-012
- FR-004
- FR-005
- FR-006
tracker_refs:
- '2669'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: "claude"
shell_pid: "3302811"
shell_pid_created_at: "1784145057.02"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — D body_hash refresh + E underscore-alias fidelity (paula MUST-FIX); C live-read (C-004).
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_interview_mapping_mission_alias.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_0rc35_activate_builtin_mission_types.py
- src/charter/activations.py
- src/charter/synthesizer/interview_mapping.py
- tests/architectural/test_no_dead_symbols.py
- tests/upgrade/test_activate_builtin_types_migration.py
- tests/charter/test_activations.py
- tests/charter/test_interview_mapping_mission_alias.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Route the three remaining mission-type rosters through the WP01 accessor (#2669):
- **Roster C** (`m_3_2_0rc35_activate_builtin_mission_types.py:33`) — live-read at `apply()`-time (C-004).
- **Roster D** `ALLOWED_MISSION_TYPES` (`activations.py:86`) — derive + keep frozenset + refresh body_hash.
- **Roster E** `_MISSION_IDENTIFIER_ANSWERS` (`interview_mapping.py:146`) — derive + preserve the underscore alias.

## Context — READ BEFORE CODING

- **Roster C, operator-confirmed live-read (C-004).** The rc35 migration is version-pinned; the operator
  chose to have it read `MissionTypeRepository.default().ids()` at `apply()` time (call-time, no import-time
  I/O) rather than stay a frozen literal. Trade-off recorded in `traces/design-decisions.md` (DD-3). Update
  `tests/upgrade/test_activate_builtin_types_migration.py` (currently `sorted(written) == sorted(_BUILTIN_MISSION_TYPES)`
  etc.) to assert derivation from the source.
- **Roster D — PRE-DECIDED form (C-012, resolves post-tasks HIGH-1):** `activations.py:86` =
  `frozenset({"software-dev","documentation","research","plan","any","generic"})` — exactly the 4 hyphen ids
  ∪ `{any, generic}`. **Keep it a module-level `frozenset` VALUE, derived from the accessor:**
  `ALLOWED_MISSION_TYPES = frozenset(builtin_mission_type_id_set() | {"any", "generic"})` at module scope.
  Do **NOT** convert it to a function. Rationale: `ALLOWED_MISSION_TYPES` is public and an **unowned** arch
  test `tests/architectural/test_activation_registry_schema.py:117` does
  `from charter.activations import ALLOWED_MISSION_TYPES` then `frozenset(ALLOWED_MISSION_TYPES)` (`:129`) —
  a function form would `ImportError`/`TypeError` that unowned test. Keeping it a derived frozenset VALUE
  leaves that test **green by construction (no edit to it)** and `test_activations.py:211` isinstance green.
  This triggers **one cached `mission_types/` read at import of `charter.activations`** — explicitly the
  NFR-001 carve-out (C-012); acceptable (bounded by NFR-002). The module-level accessor import is
  layer-legal (charter→doctrine) and cycle-free (doctrine never imports charter).
- **Roster D dead-symbol body_hash (paula MUST-FIX):** `ALLOWED_MISSION_TYPES` is baselined in
  `tests/architectural/test_no_dead_symbols.py:116` as a content-tier `SymbolKey("ALLOWED_MISSION_TYPES", "<body_hash>")`.
  Rewriting its body literal→derived **changes the body_hash**, so the baselined entry dangles → arch_shard_1
  goes RED. **Refresh that hash in THIS WP** (recompute and update line 116).
- **Roster E exact literal + transform (paula):** `interview_mapping.py:146` =
  `frozenset({"documentation","plan","research","software_dev","software-dev"})`. The sole consumer
  (`_section_answer_with_source`, `:247`) tests `_normalize_section_selector(canonical) in _MISSION_IDENTIFIER_ANSWERS`,
  and `_normalize_section_selector` (`:189`) does `.replace("-", "_")`. So the **functionally reachable**
  members are underscore forms; `software_dev` (underscore) is essential and the `software-dev` hyphen member
  is dead-but-harmless. **A naive `frozenset(builtin_mission_type_ids())` (hyphen-only) drops `software_dev`
  and silently breaks software-dev identifier matching.** Derive as `{id.replace("-","_") for id in builtin_mission_type_ids()}`
  (or `frozenset(builtin_mission_type_ids()) | {"software_dev"}` to preserve the literal incl. the dead hyphen
  member — behavior-identical). Keep it a **module-level `frozenset` value** derived from the accessor (C-012;
  E is private with a single internal consumer, so one cached import read is fine — do not over-engineer a
  lazy form). **No literal test guards E today** — add a behavioral test (T011).

## Subtasks

### T011 — [ATDD, RED FIRST] single-source pickup driver + characterization guard

Two tests in new file `tests/charter/test_interview_mapping_mission_alias.py`:
1. **Genuine RED-first single-source driver:** monkeypatch the accessor (`MissionTypeRepository.default`
   root → a tmp dir with a synthetic `analysis` type; `cache_clear()`) and assert `_MISSION_IDENTIFIER_ANSWERS`
   (and `ALLOWED_MISSION_TYPES`) then contain `analysis` — RED before T013/T014 (today they are hardcoded
   literals that ignore the accessor). This is the real red-first behavior for #2669's single-source claim in
   this WP. Restore via `cache_clear()` teardown.
2. **Characterization guard (green-stays-green):** drive the real entry point
   (`resolve_sections` / `_section_answer_with_source`) with a `software-dev` (hyphen) identifier answer and
   assert it resolves — this is a *regression guard* protecting the underscore-alias behavior across the
   derivation (it passes today and must keep passing; NOT a red-first driver — see C-008 note in DoD).

### T012 — Roster C live-read [P]

In `m_3_2_0rc35_activate_builtin_mission_types.py`, resolve the written set from
`MissionTypeRepository.default().ids()` inside `apply()` (call-time). Update the migration's tests to assert
derivation. Keep behavior otherwise identical (only-when-absent write). **Also (LOW-1):** update the stale
cross-reference comment at `:31` that says "Must match … `_BUILTIN_MISSION_TYPE_IDS`" — that constant is
removed by WP02; point the comment at the accessor/source instead so it doesn't dangle.

### T013 — Roster D derive + frozenset + body_hash

Derive `ALLOWED_MISSION_TYPES` from `builtin_mission_type_id_set() | {"any","generic"}`, keeping the
`frozenset` container. Then recompute and update the `ALLOWED_MISSION_TYPES` body_hash at
`test_no_dead_symbols.py:116` (run the arch pole to get the expected hash from the failure, or compute it the
way the gate does). Confirm `test_activations.py:211` (isinstance) and `test_activation_registry_schema.py`
stay green.

### T014 — Roster E derive + preserve alias

Derive `_MISSION_IDENTIFIER_ANSWERS` preserving the `software_dev` underscore alias (see Context). Keep the
frozenset. Confirm T011 goes green.

### T015 — Quality gate

- `uv run ruff check src/charter/ src/specify_cli/upgrade/ && uv run mypy --strict src/charter/activations.py src/charter/synthesizer/interview_mapping.py src/specify_cli/upgrade/migrations/m_3_2_0rc35_activate_builtin_mission_types.py`
- `uv run pytest tests/charter tests/upgrade -q`
- Arch pole (dead-symbol body_hash MUST be green): `uv run python -m pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' -q -n auto --dist loadfile`

## Branch Strategy

Base/merge target `feat/mission-type-single-source-gate-wiring`. Depends on WP01. Runs in parallel with WP02
(disjoint files). Execution worktree per `lanes.json` lane.

## Definition of Done

- [ ] Roster C reads the live repository at `apply()`; migration tests assert derivation (C-004); stale `:31` comment updated (LOW-1).
- [ ] Roster D derived as a module-level frozenset VALUE (C-012); `test_activation_registry_schema.py` stays green with no edit; `test_no_dead_symbols.py:116` body_hash refreshed → arch_shard_1 green.
- [ ] Roster E derived (module-level frozenset) preserving the `software_dev` underscore alias; characterization guard green.
- [ ] Hot modules stay lazy; D/E's ≤1 cached import read is the accepted C-012 carve-out; no hardcoded fallback (C-001).
- [ ] ruff + mypy --strict clean.
- [ ] ATDD: the T011 **single-source pickup driver** is committed RED first (the software-dev alias test is a green-stays-green characterization guard, per C-008 — not a red-first driver).

## Reviewer guidance

The two traps here: (1) a naive `frozenset(ids())` for Roster E silently drops `software_dev` — verify the
behavioral test would catch that; (2) the `ALLOWED_MISSION_TYPES` body_hash MUST be refreshed or arch_shard_1
reds. Confirm both. Confirm the migration live-read is call-time (no import-time I/O).

## Activity Log

- 2026-07-15T19:51:03Z – claude – shell_pid=3302811 – Assigned agent via action command
- 2026-07-15T20:25:34Z – claude – shell_pid=3302811 – WP03 Rosters C+D+E: reviewer-renata APPROVE; 4 traps (alias/D-form/body_hash/live-read) verified
- 2026-07-15T20:25:36Z – user – shell_pid=3302811 – reviewer-renata APPROVE
