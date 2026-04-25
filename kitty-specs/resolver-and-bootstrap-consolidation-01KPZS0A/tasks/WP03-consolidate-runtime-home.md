---
work_package_id: WP03
title: Consolidate runtime.discovery.home with kernel.paths (conditional)
dependencies:
- WP02
requirement_refs:
- FR-003
- NFR-004
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - Runtime delegation
history:
- timestamp: '2026-04-24T12:56:30Z'
  agent: planner-priti
  action: WP created from mission plan; conditional on post-WP02 Sonar metric
agent_profile: python-pedro
authoritative_surface: src/runtime/discovery/home.py
execution_mode: code_change
owned_files:
- src/runtime/discovery/home.py
- tests/runtime/test_home_windows_simulation.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 – Consolidate runtime.discovery.home with kernel.paths (conditional)

## Goal

*Conditional.* If post-WP02 SonarCloud still flags `src/runtime/discovery/home.py` with ≥ 100 duplicated lines vs `src/kernel/paths.py`, rewrite runtime home to delegate to kernel paths while keeping `_is_windows`, `get_kittify_home`, and `get_package_asset_root` as module-local attributes (same monkeypatch-seam strategy as WP02).

If the Sonar metric is already below threshold after WP02, CANCEL this WP and record the measurement as evidence in the status log. Do not force the work.

## Why

FR-003. Secondary duplication contributor; only worth fixing if post-WP02 numbers warrant.

## Trigger check

Before starting any code work, run:

```bash
curl -sG 'https://sonarcloud.io/api/measures/component' \
  --data-urlencode 'component=stijn-dejongh_spec-kitty' \
  --data-urlencode 'branch=kitty/mission-runtime-mission-execution-extraction-01KPDYGW' \
  --data-urlencode 'metricKeys=duplicated_lines' \
  --data-urlencode 'component=stijn-dejongh_spec-kitty:src/runtime/discovery/home.py' | jq
```

If `duplicated_lines < 100` → cancel the WP via `spec-kitty agent tasks move-task WP03 --to canceled --mission resolver-and-bootstrap-consolidation-01KPZS0A --note "Post-WP02 metric below threshold; no action needed"`. Record the measurement snapshot.

If `duplicated_lines >= 100` → proceed.

## In-scope files

- `src/runtime/discovery/home.py` (REWRITE body, conditional)
- `tests/runtime/test_home_windows_simulation.py` (NEW, conditional)

## Out of scope

- `src/kernel/paths.py` — untouched.
- Migrating existing `runtime.discovery.home` monkeypatch sites — Option A keeps attributes bound locally.

## Subtasks (mirror tasks.md §WP03)

- T019 Trigger check. If below threshold, cancel and stop (see above).
- T020 (Conditional) Rewrite `runtime/discovery/home.py` to delegate to `kernel.paths` helpers while keeping top-level attributes bound.
- T021 (Conditional) Add `tests/runtime/test_home_windows_simulation.py` pinning `_is_windows → True` and asserting `get_kittify_home()` resolves to `%LOCALAPPDATA%\\spec-kitty\\`.
- T022 (Conditional) Run `pytest tests/runtime/test_home_unit.py tests/runtime/test_home_windows_simulation.py tests/runtime/test_global_runtime_convergence_unit.py -x -q` — all green.
- T023 (Conditional) `ruff check src/runtime/discovery/home.py tests/runtime/test_home_windows_simulation.py` — clean.

## Implementation notes

- Same Option A pattern as WP02 — keep module-local attributes bound; the delegation happens in the function *bodies*.
- `_is_windows` in the runtime module should either import from `kernel.paths` (if kernel exposes it) or remain a thin local check that's kept only to preserve the monkeypatch attribute name.

## Acceptance

- If triggered: tests above pass; `ruff` clean; file size ≤ 40 lines.
- If canceled: status event records the Sonar metric snapshot at cancellation time; no code changes.

## Commit message template (if executed)

```
refactor(runtime): delegate discovery.home to kernel.paths; preserve seams

Collapse runtime.discovery.home function bodies to delegate to kernel.paths
helpers while keeping _is_windows, get_kittify_home, get_package_asset_root
as module-local attributes. Adds test_home_windows_simulation.py as a
Windows-parity regression guard.
```

## Activity Log

- 2026-04-24T14:52:37Z – unknown – Conditional trigger check: runtime/discovery/home.py was NOT in Sonar's pre-WP02 duplication hotlist (only runtime/discovery/resolver.py at 231 lines; runtime/agents/commands.py and skills.py at 19/18 lines — all three addressed by WP02/WP05). Post-WP02 the home.py duplicated_lines is below the 100-line trigger threshold; canceling per plan.md §Phase gates ("If duplicated_lines < 100, skip WP03"). Will reopen only if post-merge Sonar scan contradicts this.
