---
work_package_id: WP04
title: IC-WS1-RAWJOIN — highest-tax gate migration
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-013
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1591306"
history:
- created at planning (tasks) — WS1 raw-join (highest tax)
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_single_mission_surface_resolver.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read the plan's descriptor
table (RJ#1–4 rows) and the WP02 resolver contract. `_RAW_JOIN_SITES` re-anchored
~8 times (the highest tax in the suite, #3 CaaCS) — this WP removes that tax.

## Objective
Migrate `test_single_mission_surface_resolver.py::_RAW_JOIN_SITES` from line seeds
to content descriptors, convert its staleness twin-guard to descriptor-still-live,
and delete the 8-entry re-anchor fossil.

## Subtasks

### T016 — Migrate `_RAW_JOIN_SITES` (RJ#1-4)
Per the plan table:
- RJ#1 `_coord_mid8` / `coord_candidate = repo_root`
- RJ#2 `_coord_mid8` / `primary_candidate = repo_root / KITTY_SPECS_DIR / mission_slug`
- RJ#3 `primary_feature_dir_for_mission` / `primary_dir : Path = get_main_repo_root ( repo_root ) / KITTY_SPECS_DIR / mission_slug`
- RJ#4 `create_mission_core` / `feature_dir = resolved_root / KITTY_SPECS_DIR / mission_slug_formatted`
Note RJ#1/RJ#2 share qualname `_coord_mid8` — disambiguated by the distinct
`token_substring` (a live example of the two-axis descriptor). Author each substring
from the finding's own normalized token line (GAP-1).

### T017 — Convert the staleness twin-guard
**CLAIM-VERIFIED LOCATION** (squad): the guard is `test_allowlist_entries_are_not_stale()`
at **line ~502** (NOT `lineno in live_linenos` at ~1105 — that pattern does not
exist). The file is **already composite-key-based**: it builds keys via
`composite_key_from_file(_SRC_ROOT / row.rel_path, row.line)` and checks `key not in
live_raw_bypass_keys` (~:515-523). The residual positional coupling is that
`_RAW_JOIN_SITES` still **stores line numbers** (`(rel_path, int, rationale)`) fed
into `row.line`. Your real job: swap those seeded line numbers for content
descriptors (T016), then convert this guard to `descriptor_still_live(...)`
(exactly-one, key-equal) so no `row.line` int remains.

### T018 — Delete the 8-entry fossil
Remove the `518→472→487→494→499→493→494→495→499…` manual changelog NOTE block — it
documents exactly the tax this WP removes.

### T019 — Plant-and-catch + motion battery (FR-013, NFR-001/002)
- Motion battery: line insertion above a migrated site → green.
- Bite: a new un-allowlisted raw `KITTY_SPECS_DIR` join → red.
- Same-qualname sibling: RJ#1/RJ#2 are the natural fixture — plant a THIRD
  un-sanctioned raw join in `_coord_mid8` with a token line matching a sanctioned
  one → red (proves exactly-one didn't absorb it).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json`
via `spec-kitty agent action implement WP04 --agent <you>` (branches from WP02's approved base).

## Definition of Done
- All 4 `_RAW_JOIN_SITES` are content descriptors; twin-guard uses
  `descriptor_still_live`; 8-entry fossil deleted.
- Motion battery 0 false-reds; bite + same-qualname-sibling reds; full
  `tests/architectural/` 869/0; no line number in any authoritative comparand.

## Reviewer guidance
Verify RJ#1/RJ#2 disambiguate by substring (the same-qualname case). Confirm the
twin-guard is exactly-one/key-equal. Run the motion battery → 0 false-reds.

## Activity Log

- 2026-07-11T15:54:24Z – claude:sonnet:python-pedro:implementer – shell_pid=1501768 – Assigned agent via action command
- 2026-07-11T16:21:41Z – claude:sonnet:python-pedro:implementer – shell_pid=1501768 – Ready: WS1 raw-join — _RAW_JOIN_SITES (RJ#1-4) → content descriptors (RJ#1/RJ#2 same-qualname disambiguation), twin-guard descriptor_still_live, 8-entry fossil deleted, plant-and-catch incl same-qualname sibling; ruff exit 0; arch 850/0.
- 2026-07-11T16:21:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=1591306 – Started review via action command
- 2026-07-11T16:35:14Z – user – shell_pid=1591306 – Review passed: RJ#1-4 migrated to ContentDescriptors matching plan table; RJ#1/RJ#2 same-qualname _coord_mid8 disambiguate by distinct token_substring (coord_candidate vs primary_candidate) — both resolve exactly-one at import via _RAW_JOIN_SEEDED_KEYS. Twin-guard test_allowlist_entries_are_not_stale converted to descriptor_still_live (exactly-one + key-equal); no row.line int in authoritative allowlist comparand. 8-entry re-anchor fossil deleted. T019 battery green: motion(comment above RJ#1/RJ#2)→green, bite(new mission_creation join)→red, same-qualname-sibling(3rd _coord_mid8 with colliding coord_candidate substring)→red proving exactly-one rejects absorption. Owned-file 21 passed; full tests/architectural 850/0; ruff clean.
