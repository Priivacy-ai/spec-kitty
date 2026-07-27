---
work_package_id: WP05
title: 'Collision cluster 1: implement.py + _identity_audit.py (A+B co-owned)'
dependencies: []
requirement_refs:
- FR-001
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2804699"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/_identity_audit.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001, FR-005 + the Cross-Thread
Linearization section), `plan.md`. **Append to `traces/design-decisions.md` for each per-site kind
decision; `traces/tooling-friction.md` for friction.**

## Objective

Route BOTH the Thread-A feature_dir reads AND the Thread-B inline-meta reads in these two files, in
ONE WP. **These are cross-thread A∩B collision files** — their A-edit and B-edit MUST be co-owned
(never split across lanes with overlapping `owned_files`).

## Context

- **Thread A** (`resolve_feature_dir_for_mission` → `placement_seam(...).read_dir(kind)`): `implement.py`
  (~@1169), `_identity_audit.py` (~@55, ~@280). Route per-kind (NFR-001 kind-correct surface — do NOT
  pin the old kind-blind coord husk). `RETROSPECTIVE` kind routes to `resolve_retrospective_home`, not
  a uniform delegate.
- **Thread B** (`json.loads(<meta>)` → `load_meta`/`load_meta_strict`/`load_meta_or_empty`):
  `implement.py` (~@983), `_identity_audit.py` (~@261). Match each site's **POST-#2091** contract
  (FR-005): a site that now hard-fails routes to `load_meta_strict`/`allow_missing=False` — never
  `allow_missing=True` (would mask the #2091 guard).
- Line numbers drifted post-#2462 — match by construct/token.

## Subtasks

### T019 — implement.py A + B
Route the feature_dir read (A) onto `read_dir(kind)`; route the inline meta read (B) onto the
kind-correct `load_meta*` per its post-#2091 contract. `implement.py` is a large file — stay within
the two target sites; do not opportunistically refactor.

### T020 — _identity_audit.py A + B
Route both A sites (~@55, ~@280) onto `read_dir(kind)` and the B meta read (~@261) onto `load_meta*`.

### T021 — FR-005 adjudication + tracer
For each B site, record the chosen `allow_missing`/`on_malformed` and WHY (post-#2091 semantics) in
`traces/design-decisions.md`. ruff/mypy clean; complexity ≤15 for any touched function.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP05 --agent <name>`.

## Definition of Done
- [ ] Both files' A reads route via `read_dir(kind)` (kind-correct surface).
- [ ] Both files' B reads route via `load_meta*` with post-#2091 contract.
- [ ] No masking `allow_missing=True` on a now-hard-failing site; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm A+B are co-owned here (not split). Verify per-site kind correctness (NFR-001) and post-#2091
`allow_missing` derivation (FR-005). Spot-check no old-coord-dir pinning.

## Activity Log

- 2026-07-08T07:30:57Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Assigned agent via action command
- 2026-07-08T08:09:29Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Ready: A+B co-routed (SPEC/PRIMARY_METADATA kinds), post-#2091 load_meta contracts derived per-site, coord_authority/canonicalizer gate floors re-pinned shrink-only across 2 gate files (7->6 / 45->44), ruff/mypy clean, full tests/architectural/ + implement/identity_audit suites green
- 2026-07-08T08:12:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=2804699 – Started review via action command
- 2026-07-08T08:19:29Z – user – shell_pid=2804699 – Review passed: A+B routed kind-correct (SPEC/PRIMARY_METADATA, no coord-husk pinning) + post-#2091 load_meta contracts (implement.py hard-fail allow_missing=False/on_malformed=raise; _identity_audit soft-degrade allow_missing=True); gate re-pins (coord_authority_baseline 7->6, CANONICALIZER_FLOOR 45->44, COORD_AUTHORITY_WRITE_FLOOR 7->6) shrink-only + guard-mandated for WP05's own drained implement.py site; 4 workflow.py entries + 2 keepers (decisions/emit.py, widen/state.py) untouched; ruff/mypy clean; gate+479 impl/identity tests green
