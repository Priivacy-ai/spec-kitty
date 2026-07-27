---
work_package_id: WP05
title: '#2666 — wire FR-013 scan into doctor doctrine + CI gate'
dependencies:
- WP04
requirement_refs:
- C-003
- FR-009
- FR-010
- FR-011
tracker_refs:
- '2666'
planning_base_branch: feat/mission-type-single-source-gate-wiring
merge_target_branch: feat/mission-type-single-source-gate-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-single-source-gate-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-single-source-gate-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: "claude"
shell_pid: "3302811"
shell_pid_created_at: "1784145057.02"
history:
- at: '2026-07-15T19:00:00Z'
  actor: claude
  note: WP authored post-plan squad — __all__ re-add coupled with src caller (C-003 dead-symbol gate); depends on WP04 for non-vacuity.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_doctor_doctrine_integrity.py
- tests/architectural/test_cross_grain_builtin_gate.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/charter/action_grain.py
- tests/specify_cli/cli/commands/test_doctor_doctrine_integrity.py
- tests/architectural/test_cross_grain_builtin_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. You are the **implementer**.

## Objective

Make the FR-013 cross-grain integrity scan load-bearing OUTSIDE pytest (#2666): invoke
`scan_builtin_cross_grain_duplicates` from `spec-kitty doctor doctrine` (RC=1 + `--json` finding on
collision) and a dedicated CI structural gate, and re-add the symbol to `action_grain.__all__` now that it
has a real `src/` caller. **Depends on WP04** — without fail-loud indexes the gate is partially vacuous.

## Context — READ BEFORE CODING

- `scan_builtin_cross_grain_duplicates` (`action_grain.py:155`) already enumerates every shipped mission type
  from `MissionTypeRepository` and raises `CrossGrainDoubleDeclarationError` on a type-vs-action URN
  collision. It has **no `src/` caller** today (only pytest), and was removed from `__all__` (`action_grain.py:53-62`
  tracking comment names #2666).
- **Wiring target:** `doctrine_check()` at `src/specify_cli/cli/commands/doctor.py:1066`. Its structure:
  `report = _collect_profile_health(...)` → `exit_code = 0 if report.healthy else 1` (`:1120`) →
  `_emit_doctrine_json(...)` / `_emit_doctrine_human(...)` → `raise typer.Exit(exit_code)`. The
  `_render_unsanctioned_override_findings` block (`:1158`) is the human-renderer template for loud findings.
- **C-003 coupling (CI dead-symbol gate):** re-adding `scan_builtin_cross_grain_duplicates` to
  `action_grain.__all__` only passes `test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`
  (arch_shard_1) once a real `src/` importer exists. **The `__all__` re-add (T022) and the doctor caller
  (T021) MUST land together in this WP.**
- **Scope boundary (spec Out of Scope):** built-in tree only. Project/org override collision coverage needs
  the multi-root action-index engine `action_grain.py` declares out of scope — tracked follow-up, NOT here.

## Subtasks

### T020 — [ATDD, RED FIRST] doctor CLI test

New `tests/specify_cli/cli/commands/test_doctor_doctrine_integrity.py`: construct a synthetic collision via
`MissionTypeProfileRepository(built_in_dir=tmp)` (the integrity-gate twin pattern — a tmp built-in root where
one artifact URN is declared in both the type grain and an action grain), monkeypatch the scan's root to it,
invoke `doctor doctrine --json`, and assert RC=1 + a structured collision finding in the JSON. Add a healthy
(clean tree) case asserting RC=0 and no finding. RED before T021.

### T021 — Wire the scan into `doctrine_check`

Import `scan_builtin_cross_grain_duplicates` from `charter.action_grain` and call it in `doctrine_check`
before computing `exit_code`. On `CrossGrainDoubleDeclarationError`: mark the report unhealthy (or force
`exit_code=1`) and add a structured finding to the `--json` payload + a loud human line (mirror
`_render_unsanctioned_override_findings`). On success, contribute a healthy result without changing the exit
code. Keep `doctrine_check` complexity ≤ 15 (extract a `_run_cross_grain_check()` helper).

### T022 — Re-add to `__all__` (C-003)

Add `"scan_builtin_cross_grain_duplicates"` back to `__all__` in `action_grain.py` and update the tracking
comment (`:53-62`) to note the runtime caller now exists (doctor). This MUST be in the same WP as T021.

### T023 — Dedicated CI structural gate

New `tests/architectural/test_cross_grain_builtin_gate.py`: a structural test that calls
`scan_builtin_cross_grain_duplicates()` on the shipped tree and asserts it returns every shipped type
(disjoint), independent of the broad suite. Keep the existing `tests/doctrine/drg/test_cross_grain_integrity.py`
as the finer-grained structural home (owned elsewhere — do not edit it here).

### T024 — Quality gate

- `uv run ruff check src/specify_cli/cli/commands/doctor.py src/charter/action_grain.py && uv run mypy --strict src/specify_cli/cli/commands/doctor.py src/charter/action_grain.py`
- `uv run pytest tests/specify_cli/cli/commands/test_doctor_doctrine_integrity.py tests/architectural/test_cross_grain_builtin_gate.py -q`
- **Dead-symbol gate MUST be green (C-003):** `uv run python -m pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' -q -n auto --dist loadfile`
- Smoke: `uv run spec-kitty doctor doctrine --json` returns RC=0 on the clean repo.

## Branch Strategy

Base/merge target `feat/mission-type-single-source-gate-wiring`. Depends on WP04. Execution worktree per
`lanes.json` lane.

## Definition of Done

- [ ] `doctor doctrine` runs the scan; RC=1 + json finding on a synthetic collision; RC=0 on a clean tree.
- [ ] `scan_builtin_cross_grain_duplicates` re-added to `action_grain.__all__` in the SAME change (C-003).
- [ ] Dead-symbol gate green (the `__all__` member now has a src caller).
- [ ] Dedicated CI structural gate added.
- [ ] ruff + mypy --strict clean; complexity ≤ 15.
- [ ] ATDD: T020 committed RED first.

## Reviewer guidance

Verify the synthetic-collision test actually drives RC=1 through the real CLI (not just a unit call). Verify
the `__all__` re-add + src caller land together (else arch_shard_1 reds). Confirm the scope stays built-in
(no project-override engine sneaks in).

## Activity Log

- 2026-07-15T19:51:11Z – claude – shell_pid=3302811 – Assigned agent via action command
- 2026-07-15T20:28:09Z – claude – shell_pid=3302811 – WP05 doctor+gate: reviewer-renata APPROVE; arch_shard_2 red is pre-existing test_no_parity_scaffold (#2651), not WP05
- 2026-07-15T20:28:12Z – user – shell_pid=3302811 – reviewer-renata APPROVE
