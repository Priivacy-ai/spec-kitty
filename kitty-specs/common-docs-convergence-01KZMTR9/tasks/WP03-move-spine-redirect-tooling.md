---
work_package_id: WP03
title: Collapsed cumulative move spine + redirect tooling repoint
dependencies: []
requirement_refs:
- FR-021
- NFR-010
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/redirect_stub_generator.py
create_intent:
- tests/docs/test_redirect_spine.py
execution_mode: code_change
owned_files:
- scripts/docs/redirect_stub_generator.py
- tests/docs/test_redirect_spine.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
Confirm TDD/red-first; run pytest+ruff+mypy before handoff.

## Objective
Make the redirect tooling driveable by THIS mission and author a **collapsed cumulative** occurrence-map
spine so `regenerate-map` reproduces all prior redirect entries + the new ones (no coverage regression).
See [contracts/redirect-tooling-contract.md](../contracts/redirect-tooling-contract.md), [plan.md](../plan.md) IC-02 (OB-1).

## Context
`derive_redirect_map` overwrites the whole map from ONE occurrence-map; `_relocate` applies a single move
(no transitive closure). `redirect_map.yaml` has 151 entries from the closed `common-docs-structural-move`
mission; `redirect_baseline_urls.json` (180 URLs) is immutable. `--occurrence-map`, `coverage`,
`check-map`, `regenerate-map` ALREADY exist — the only code change is the closed-mission **default**.

## Subtasks
- **T008** — In `occurrence_map.yaml`, carry/collapse the prior mission's 29 moves as baseline→FINAL
  entries (source: `scripts/docs/redirect_map.yaml`), so every prior baseline URL still resolves to its
  FINAL destination after this mission's moves; resolve every remaining placeholder destination. Movers
  append per-WP fragments later; WP13 merges.
- **T009** — Repoint `MISSION_SLUG`/`DEFAULT_OCCURRENCE_MAP` (`redirect_stub_generator.py:75-77`) off the
  closed mission (to this mission or a neutral sentinel), so no invocation silently uses the closed map;
  document that IC-11/PR gates always pass `--occurrence-map <this mission>`.
- **T010** — `tests/docs/test_redirect_spine.py`: assert `regenerate-map` from the collapsed spine
  reproduces every prior `redirect_map.yaml` key + the new moves, and `coverage` reports zero
  `dead_targets` (NFR-010). Red-first.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- `regenerate-map --occurrence-map <this mission>` reproduces all 151 prior entries + new; `coverage`
  clean; default no longer points at the closed mission. Tests green; ruff/mypy clean.

## Risks
- OB-1: if the collapsed-data spine proves infeasible for twice-moved files, escalate to the code path
  (union multiple maps / iterate `_relocate` to a fixed point) — record the decision in
  `traces/design-decisions.md`.
- `redirect_map.yaml` itself is WP13-owned (do not regenerate it here; only the spine + tool default).
