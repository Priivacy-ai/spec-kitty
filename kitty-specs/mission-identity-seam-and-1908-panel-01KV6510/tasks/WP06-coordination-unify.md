---
work_package_id: WP06
title: Unify ALL parallel composers — coordination/ + missions/ (#1878 slice)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T039
- T040
phase: Phase 2 - Route call sites
assignee: ''
agent: claude
shell_pid: '1073121'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_coord_dir_seam.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/workspace.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/missions/_create.py
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/missions/feature_dir_resolver.py
- tests/specify_cli/coordination/test_coord_dir_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Unify coordination/ compose/parse (#1878 slice)

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
Delegate **every** duplicate compose/parse algorithm — in `coordination/` AND `missions/` — to the
WP01 seam so exactly ONE implementation exists for the grammar (FR-010, paula F-2; squad-verified the
`missions/` composers were missed). Read [spec.md](../spec.md) FR-010/FR-001, [plan.md](../plan.md)
IC-07. **This is the #1878 strangler's surface — HIGH CARE.**

**Done when:** all coordination AND missions composers delegate to the seam; coordination/mission
dir/branch names are **byte-identical** (no coord-worktree churn); status/coord read-path tests green;
NO second algorithm (`endswith(f"-{mid8}")` / `[:8]` / `f"{slug}-{mid8}"`) survives in any owned file.

## Context & Constraints
- **Depends on WP01** — specifically its bare `mission_dir_name(slug, *, mid8)` + coord derivations
  (`coord_branch_name`/`coord_dir_name`). These (NOT the lane-suffixed `worktree_dir_name`) are the
  real delegation target for the bare `<slug>-<mid8>` coordination grammar. If WP01's bare primitive
  is missing, STOP — do not re-implement a local `endswith` dedup (the squad's "fake delegation" trap).
- TDD-first. Only the 7 named source files + the new test.
- **Two duplicate families:** (a) coordination/ functions (T025–T028); (b) the squad-verified
  `missions/` composers (T039–T040) — `_create.coordination_branch_name` (the LIVE coord-branch
  composer run at every `mission create`, with its own `endswith` dedup) and
  `_read_path_resolver._compose_mission_dir` / `feature_dir_resolver` (read-path mirrors that call the
  now-demoted `mid8_from_slug`). All compose the same `<slug>-<mid8>` grammar.
- **HIGH CARE:** status/coord READ paths AND `mission create` depend on these names. Changing a name
  silently would orphan coord worktrees / break status reads / break new-mission branch creation. The
  seam is idempotency-preserving, so delegation MUST emit byte-identical names — assert in T029.
- The mission itself runs on a coordination branch; do not destabilize the live coord surface.

## Subtasks
### T025 — `coordination/workspace._compose_mission_dir` (:93; +:154/:159 path/branch)
Delegate `_compose_mission_dir` to the seam's mission-dir compose (`worktree_dir_name`/the shared
`<slug>-<mid8>` primitive). Route the coord worktree path (:154) and the `kitty/mission-<slug>-<mid8>`
branch (:159) through the seam composers too.

### T026 — `coordination/transaction._mission_specs_dir_name` (:152)
Replace the duplicate body (its docstring admits it mirrors `_compose_mission_dir`) with a call to
the seam / `workspace._compose_mission_dir` now-delegating helper.

### T027 — `coordination/status_transition._transaction_dir_name` (:75)
Same: replace the third identical body with the seam delegate.

### T028 — `coordination/surface_resolver._coord_mid8` (:363)
Route mid8 derivation through the seam (`mid8(mission_id)` primitive), not a local `mission_id[:8]`.

### T039 — `missions/_create.coordination_branch_name` (:136-159) — the live coord-branch composer
Replace its body (`human_part = slug if slug.endswith(suffix) else f"{strip_numeric_prefix(slug)}{suffix}"`,
then `kitty/mission-{human_part}`) with a delegation to WP01's `coord_branch_name(slug, mission_id=…)`.
This runs at every `mission create` (`core/mission_creation.py:402`) — golden-value test it for
embedded + legacy slugs (byte-identical) so new-mission branch creation is unchanged.

### T040 — `missions/_read_path_resolver._compose_mission_dir` (:102) + `feature_dir_resolver`
Replace `_compose_mission_dir` (and the read-path callers at :125/:386 that pass
`mid8_from_slug(slug)`) with delegation to WP01's bare `mission_dir_name` + authoritative
`resolve_mid8(slug, mission_id=…)` — pass the declared `mission_id`, NOT the demoted heuristic. Do the
same for `feature_dir_resolver.py`'s mirror. Byte-identical names; no read-path regression.

### T029 — Byte-identical + read-path regression tests
Create `tests/specify_cli/coordination/test_coord_dir_seam.py`: assert ALL delegated functions
(coordination/ AND missions/) produce names byte-identical to the pre-change algorithm for embedded +
non-embedded slugs (a golden-value test referencing WP01's shared table), and run the existing
coordination status/read tests + a `mission create` smoke to prove no regression.
`ruff`+`mypy`; `PWHEADLESS=1 pytest tests/specify_cli/coordination/ tests/specify_cli/missions/ -q`.
- [ ] all 6 composer functions delegate to the seam; [ ] names byte-identical vs golden table;
  [ ] coordination read-path + mission-create tests green; [ ] no `endswith`/`[:8]`/`f"{slug}-{mid8}"`
  remains in any owned file; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
ALL parallel composers (4 coordination/ + `_create.coordination_branch_name` +
`_read_path_resolver._compose_mission_dir` + `feature_dir_resolver`) delegate to the single seam;
byte-identical names proven against the golden table; status/coord read paths + mission-create green;
ruff/mypy clean.

## Reviewer Guidance
HIGH CARE: confirm NO second algorithm remains in ANY of the 7 owned files (grep `endswith(f"-` /
`[:8]` / `f"{...}-{mid8}"` / `kitty/mission-{`); read-path callers pass declared `mission_id` to
`resolve_mid8`, NOT the demoted `mid8_from_slug`; golden-value test proves byte-identical names for
embedded + legacy; `mission create` smoke unaffected. Reject on any name drift or surviving local
dedup (that is the "fake delegation" failure mode the squad called out).
