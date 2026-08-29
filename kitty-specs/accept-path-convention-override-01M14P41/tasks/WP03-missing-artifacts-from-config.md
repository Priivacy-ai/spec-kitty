---
work_package_id: WP03
title: '#3785 optional-artifact SSOT fold [SEVERABLE, P3]'
dependencies:
- WP01
requirement_refs:
- C-003
- C-009
- FR-006
planning_base_branch: fix/accept-path-convention-override
merge_target_branch: fix/accept-path-convention-override
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-convention-override. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-convention-override unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/acceptance/test_missing_artifacts_from_config.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/__init__.py
- tests/specify_cli/acceptance/test_missing_artifacts_from_config.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load implementer-ivan`. Apply its initialization,
boundaries, and directives, then proceed.

## Objective

Fold tech-debt **#3785**: `_missing_artifacts` derives the optional-artifact set from the mission's declared
`artifacts.optional` instead of a hardcoded, drifted list (which omits software-dev's `checklists/`). Same
defect class #3016 names. **Severable P3** — different module from WP01/WP02.

**Split-tripwire (C-003/C-009):** if this fold forces ANY change to `contracts/` dedup/severity, or grows
beyond the `_missing_artifacts` signature + call-site reorder, STOP and split #3785 back to its own mission.

Read `spec.md` US3 + FR-006 + C-003, `data-model.md` OptionalArtifactSet.

## Branch Strategy

Base/merge: `fix/accept-path-convention-override`. Depends on WP01. Parallel with WP02 (owns
`acceptance/__init__.py`, no overlap). Enter via `spec-kitty agent action implement WP03 --agent claude`.

## Guidance per subtask

### T012 — Reorder call-site (acceptance/__init__.py)
Today `_missing_artifacts(planning_read_dir)` is called at ~:1178, BEFORE `mission = get_mission_for_feature(...)`
at ~:1181. Move the `try/except MissionError → None` mission fetch ABOVE the `_missing_artifacts` call and
thread `mission` (or its optional list) in. Nothing between depends on the ordering — safe reorder.

### T013 — Read `artifacts.optional` (FR-006, C-003)
`_missing_artifacts` reads the mission's declared optional artifacts (flat file/dir tokens:
`data-model.md`, `contracts/`, `quickstart.md`, `research.md`, `checklists/`). **Prefer the null-safe
accessor `Mission.get_optional_artifacts()` (mission.py:383)** over reaching `mission.config.artifacts.optional`
directly. Token→path is `feature_dir / token` (pathlib handles the trailing slash; `Path("contracts/") ==
Path("contracts")`).
- **FALLBACK GUARD (debugger HIGH — load-bearing):** fall back to today's hardcoded list when
  `mission is None` **OR** `mission.config` has no `artifacts` attribute. The #3783 regression at
  `test_acceptance_support.py:767` (and WP01 T006's new stub) inject a `SimpleNamespace` mission with **no
  `artifacts`** — a bare `mission.config.artifacts.optional` would raise `AttributeError` and break BOTH
  the existing #3783 test (a C-009 violation) and WP01's new test. Reuse the existing
  `getattr(mission.config, "artifacts", None)` pattern (paths.py:160).
- **Keep the hardcoded list referenced** as that fallback so it does not orphan into a dead symbol that
  trips `tests/architectural/test_no_dead_symbols.py` (a WP01-owned re-pin file WP03 CANNOT touch —
  planner MED). If the fold would orphan it, STOP.
- **C-003:** `contracts/` flows through the existing `_normalize_path_token` dedup unchanged.

### T014 — Tests (red-first, SC-004)
`tests/specify_cli/acceptance/test_missing_artifacts_from_config.py` — read an actual `mission.yaml`
(do not assume its declarations); dict/set-equality assertions:
- Optional set derived from the real declaration **including `checklists/`** (was omitted).
- **Severity, not membership (reviewer HIGH):** an **end-to-end strict accept** on a software-dev mission
  missing `contracts/` still emits `contracts` as a **blocking `path_violations`** entry (deduped out of
  `optional_missing`), byte-identical to the #3783 result. Assert the classification, not list membership
  (severity is decided downstream in `evaluate_path_conventions`, not in `_missing_artifacts`).
- `mission is None` ⇒ hardcoded fallback; **`mission` present but `.config.artifacts` absent** (artifacts-less
  stub) ⇒ hardcoded fallback, no `AttributeError`.

## Definition of Done
- `_missing_artifacts` config-driven via `get_optional_artifacts()`; `checklists/` now considered; the
  fallback fires for both `None` and artifacts-less missions (no `AttributeError`); hardcoded list stays
  referenced (no dead symbol).
- **`contracts/` severity checkable:** end-to-end strict accept still classifies `contracts/` as blocking
  (assert the classification), unchanged from #3783.
- **Split-tripwire (checkable):** `git diff` touches ONLY `acceptance/__init__.py` + the new test file. Any
  other file in the diff (e.g. `summary_core.py`/`validators/paths.py` for a dedup change) = tripwire →
  STOP and split #3785 to its own mission (C-003/C-009).
- All T012-T014 tests green; `ruff` + `mypy --strict` clean.

## Reviewer guidance
Confirm: the fallback guards BOTH `None` and artifacts-less missions (run the #3783 `:767` test — it must
stay green); `contracts/` blocking-severity asserted end-to-end (not list membership); hardcoded list still
referenced; `git diff` limited to the two owned files; no #3783 assertion weakened (C-009).
