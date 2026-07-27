---
work_package_id: WP05
title: Typed-error pass-through (cheapest behavioral slice)
dependencies:
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1861337"
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: 'WP authored from plan IC-04 (FR-005, #2010 bug #15).'
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- tests/mission_runtime/test_resolution_typed_errors.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/mission_runtime/resolution.py
- tests/mission_runtime/test_resolution_typed_errors.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Translate the **`MISSION_AMBIGUOUS_SELECTOR`** typed error through the `mission_runtime` boundary so an ambiguous handle surfaces its specific code instead of escaping untranslated. The cheapest behavioral slice — NO resolver change. (IC-04; FR-005, #2010 bug #15 family)

## ⚠️ Corrected premise (squad-verified, 2026-06-19)
The original WP05 framing ("`resolution.py` flattens to `MISSION_NOT_FOUND`") was **FALSE** — verify before implementing:
- `MISSION_NOT_FOUND` **does not exist** anywhere in `src/mission_runtime/` (`rg MISSION_NOT_FOUND src/mission_runtime/` → 0).
- `resolution.py:185-190` **already** translates `StatusReadPathNotFound` preserving `exc.error_code` via `ActionContextError(exc.error_code, …)`.
- The real flatten at `src/runtime/next/runtime_bridge.py:3163` (`raise MissionNotFoundError`) is **already guarded** by `_READ_PATH_ERROR_CODES` (`:245`, comment cites "disease #15") which includes `STATUS_READ_PATH_NOT_FOUND`, `COORDINATION_BRANCH_DELETED`, **and** `MISSION_AMBIGUOUS_SELECTOR`.
- **The genuine residual:** `MissionSelectorAmbiguous` is caught **nowhere** in `resolution.py` — the `try` at `:183-184` catches **only** `StatusReadPathNotFound`. So when the resolver raises `MissionSelectorAmbiguous`, it escapes `resolution.py` as a raw `specify_cli` exception (NOT an `ActionContextError`), so the `_is_read_path_error`/`MissionNotFoundError` guard in `runtime_bridge` never receives the ambiguous code through the intended channel.

## Context
- Boundary: `src/mission_runtime/resolution.py` — the `try/except StatusReadPathNotFound` at `:183-196`. The error classes (`MissionSelectorAmbiguous` `_read_path_resolver.py:37`, `StatusReadPathNotFound` `:59`) already exist.
- Fix = **extend the existing translation**, not a re-point: add an `except MissionSelectorAmbiguous` arm mirroring the `:185-190` `StatusReadPathNotFound` handling, re-raising `ActionContextError(exc.error_code, str(exc))` so `MISSION_AMBIGUOUS_SELECTOR` reaches the consumer boundary as the typed `ActionContextError` the bridge expects. This is consistent with the WP03 shared delegator if WP03 centralizes the try/except (coordinate, but the owned file is resolution.py).

## Subtasks
### T018 — Translate the ambiguous-selector error
- In `resolution.py`, add the missing `except MissionSelectorAmbiguous` arm (alongside the existing `StatusReadPathNotFound` translation at `:185-190`) → re-raise `ActionContextError(exc.error_code, str(exc))`. Do NOT touch the already-correct `StatusReadPathNotFound`/`runtime_bridge` paths.
### T019 — LIVE repro red→green (no born-green)
- **First**, run an ambiguous-handle resolution (two missions sharing a `mid8`/slug stem) against unmodified `main` and **paste the failing/mis-routed output into WP history** (per the live-evidence rule). The test must assert the **specific** code `MISSION_AMBIGUOUS_SELECTOR` survives to the `mission_runtime` consumer boundary — red pre-fix (raw escape / wrong code), green post-fix. If it is already green on `main`, STOP and re-scope (the residual is elsewhere) rather than shipping a born-green test.
### T020 — Gates
- `ruff` + `mypy --strict` clean; run `tests/mission_runtime/` + any `next` command tests.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP03** (delegator).

## Definition of Done
- [ ] `MissionSelectorAmbiguous` translated to `ActionContextError(MISSION_AMBIGUOUS_SELECTOR)` at the `resolution.py` boundary (new `except` arm); `StatusReadPathNotFound` path left unchanged (already correct).
- [ ] LIVE ambiguous-handle repro: red on unmodified `main` (output pasted in WP history) → green post-fix; the test asserts the **specific** `MISSION_AMBIGUOUS_SELECTOR` code reaches the consumer boundary.
- [ ] No resolver behavior changed (this is a caller-boundary translation only).
- [ ] ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk (born-green)**: if the implementer writes a test that passes on first run, the "fix" is a no-op. Require the red-on-`main` receipt in history; reject a born-green test.
- **Risk (wrong target)**: do NOT "fix" the already-guarded `StatusReadPathNotFound`/`runtime_bridge.py:3163` path — it preserves the code today. The residual is the **un-caught** `MissionSelectorAmbiguous` in `resolution.py`.
- **Reviewer**: independently `rg MISSION_NOT_FOUND src/mission_runtime/` → 0 (confirm the old premise was false); confirm the new `except` arm asserts the SPECIFIC code; confirm no resolver logic changed.

## Activity Log

- 2026-06-20T09:11:58Z – claude:opus:python-pedro:implementer – shell_pid=1837625 – Assigned agent via action command
- 2026-06-20T09:18:37Z – claude:opus:python-pedro:implementer – shell_pid=1837625 – Ambiguous-selector translation at 2 boundary sites (_resolve_mission_slug + resolve_placement_only); b5de550d0; red-state receipt captured (raw MissionSelectorAmbiguous escaping); 36 tests pass; ruff+mypy clean
- 2026-06-20T09:18:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1861337 – Started review via action command
- 2026-06-20T09:23:41Z – user – shell_pid=1861337 – reviewer-renata APPROVED: anti-born-green verified (pre-fix file → both tests fail red, raw MissionSelectorAmbiguous escaping at :184 + :817), specific-code assertion confirmed, 2 sites legit, StatusReadPathNotFound untouched, 36 pass, ruff+mypy clean, 0 deprecation warnings.
