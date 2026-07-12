# Implementation Plan: Close #2160 Coord-Shadows Read/Gate Arm

**Branch**: `rework/ray-cluster-aggregation` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/coord-shadows-arm-closeout-01KXAST2/spec.md`

## Summary

Align the faithful aggregate of the five rayjohnson coord-shadows fixes (already on this branch)
into one coherent slice that **genuinely closes the read/gate arm of epic #2160**. Four concerns:
collapse the duplicated subtask-row semantics onto one canonical section walk; close the
fail-open in the shared `_infer_subtasks_complete` emit layer at all four production callers (and
retire #2511's now-redundant per-door patch); fix the #2514 lane-recovery regression that
re-leaks status files into a coord-topology worktree; and add a live `shell_pid` liveness check
(promoting the existing psutil helper into `core/process_liveness.is_process_alive`) so live agents
are never flagged stale.
The design is squad-verified (a 3-lens code squad produced the findings, a 2-lens post-spec squad
hardened the spec); this plan translates that into an IC map. No new subsystems — every fix
consolidates onto an existing canonical seam.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, psutil (for `sync/daemon._is_process_alive`); pytest / pytest-xdist for tests
**Storage**: filesystem planning artifacts (`tasks.md`), append-only `status.events.jsonl`; no DB
**Testing**: pytest through the **production** entry points (emit path, allocator, stale indicator, gate check) — not standalone helpers; `tests/architectural/` suite must stay 0-failed incl. the dead-code gate; `PWHEADLESS=1`, `-n auto --dist loadfile` for parallel local runs
**Target Platform**: Linux/macOS dev + CI (cross-platform liveness must not crash on any)
**Project Type**: single (Python CLI package `src/specify_cli/`)
**Performance Goals**: N/A — correctness/hygiene mission; the liveness call must be O(1) per WP, no measurable board slowdown
**Constraints**: all work stays on `rework/ray-cluster-aggregation`; consolidate onto canonical seams only (C-002), no parallel implementations; preserve Ray Johnson attribution on the aggregate commits; no version-number prescription
**Scale/Scope**: ~7 source modules across 4 concerns; ~4-5 WPs forecast

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — PASS/enforced: the whole mission is a consolidation *onto*
  canonical seams (`core.subtask_rows`, `resolve_planning_read_dir(kind=TASKS_INDEX)`,
  `core/process_liveness.is_process_alive`); C-002 forbids new parallel implementations.
- **Architectural alignment** — PASS: closes the read/gate arm of epic #2160 in the direction the
  already-merged write/validate authority work established (coord/primary partition).
- **ATDD-first** — PASS: every FR has a production-path acceptance test in its WP DoD; the
  class-closure regression (native `agent status --to for_review` blocked) is the headline test.
- **Tiered rigour** — the status/emit + allocator seams are core (higher rigour); the issue-matrix
  and freshness regression-guard are glue.
- **Terminology** — PASS: canonical `Mission`/`status commit`; no `feature`/`ceremony`.
- No charter violations to justify; Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-shadows-arm-closeout-01KXAST2/
├── plan.md              # This file
├── spec.md              # Committed (546c694)
├── checklists/requirements.md
├── tracers/             # Seeded this phase (3 files)
├── research.md          # Phase 0 (this command) — thin: brownfield, decisions pre-made
├── data-model.md        # Phase 1 — the entities the fixes touch
├── issue-matrix.md      # Authored at /tasks or IC-TIDY WP
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── subtask_rows.py          # IC-ROWS — unify the two section walks
│   └── stale_detection.py       # IC-LIVENESS — consult liveness in the stale indicator
├── status/
│   ├── emit.py                  # IC-EMIT — _infer_subtasks_complete (2 callers) + row semantics
│   └── aggregate.py            # IC-EMIT — caller ~:717 (native agent-status door)
├── coordination/
│   └── status_transition.py    # IC-EMIT — caller ~:444 (must precede FR-005)
├── orchestrator_api/
│   └── commands.py             # IC-EMIT — remove #2511 per-door pre-derivation ~:1418-1430
├── lanes/
│   └── worktree_allocator.py    # IC-LANE — sparse-checkout on lane recovery (FR-006)
├── cli/commands/agent/
│   └── tasks_move_task.py       # IC-TIDY — single _mt_reset_for_planned_rollback seam
└── analysis_report.py           # IC-TIDY — FR-009 regression-guard target (#1764, no change)

tests/specify_cli/{core,lanes,status,orchestrator_api,cli/commands/agent}/  # per-WP tests
```

**Structure Decision**: single Python package; each concern owns a disjoint file set (see IC map
Affected surfaces) so WPs never collide on ownership.

## Complexity Tracking

*No charter violations — none to justify.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs. Post-plan squad decision (see Sequencing): IC-EMIT **splits** into two WPs
> (caller-threading WP02 → FR-005-removal WP03); IC-LIVENESS and IC-TIDY stay **separate** WPs
> (thematically disjoint, no merge). Resulting graph is 6 WPs.

### IC-ROWS — Canonical subtask-row walk

- **Purpose**: Collapse the two divergent section-walk loops in `core/subtask_rows.py` onto one
  private `_walk_wp_section(lines, wp_id) -> Iterator[(index, text, checked)]` consumed by the
  counters (`iter_wp_section_subtask_rows`, `count_wp_section_subtask_rows`, `count_subtask_rows`)
  and the writer (`uncheck_wp_section_subtask_rows`), so "what is a WP subtask row" has exactly one
  definition shared by guard, dashboard, and rollback.
- **Relevant requirements**: FR-001, NFR-005.
- **Affected surfaces**: `src/specify_cli/core/subtask_rows.py`; `tests/specify_cli/core/*`.
- **Sequencing/depends-on**: none — **keystone**; IC-EMIT consumes its `count_wp_section_subtask_rows`.
- **Design decision (pinned)**: the canonical section-boundary semantic is the **guard's** — a
  re-appearing `## WPnn` heading does **not** re-enter a closed section (the counter's `break`
  behavior is canonical; the uncheck writer's current `re-enter` behavior is corrected to match).
  This is a real behavior change to the aggregate's writer and must be justified in the WP.
- **Risks**: NFR-005 bite battery must include the divergence fixtures (re-appearing WP heading,
  content-after-section-end, nested headings, `depends: WPnn` mentions, fenced blocks, ids past
  T999) or the semantic change ships unverified. Do not weaken the fence/first-WPxx-token rules.

### IC-EMIT — Close the emit-layer fail-open (the class-closer)

- **Purpose**: Reimplement `_infer_subtasks_complete` (`status/emit.py` ~:272-295) row semantics on
  `core.subtask_rows.count_wp_section_subtask_rows` (delete the divergent regex/heading/no-fence +
  the tasks.md-absent fail-open) and resolve the **primary** surface via
  `resolve_planning_read_dir(..., kind=TASKS_INDEX)` at **all four** production callers, then retire
  #2511's per-door pre-derivation.
- **Relevant requirements**: FR-002, FR-003, FR-004, FR-005.
- **Affected surfaces**: `status/emit.py` (callers ~:535 and ~:690), `status/aggregate.py` (~:717),
  `coordination/status_transition.py` (~:444), `orchestrator_api/commands.py` (~:1418-1430 removal);
  their tests. **Do NOT touch** the already-correct `tasks_shared._check_unchecked_subtasks` guard.
- **Sequencing/depends-on**: **IC-ROWS** (consumes the canonical counter).
- **WP decomposition (MANDATED by the post-plan squad — split into two WPs):**
  - **WP-A (caller-threading + row semantics)** — FR-002 + FR-003 + FR-004; owns `status/emit.py`,
    `status/aggregate.py`, `coordination/status_transition.py`.
  - **WP-B (FR-005 removal)** — owns `orchestrator_api/commands.py` ONLY; **depends-on WP-A.**
  The split turns the "FR-005 only after FR-003 fixes `status_transition.py:444`" ordering into a
  structural WP dep edge, and the ownership is clean (`commands.py` vs `status_transition.py` are
  never co-owned). FR-005-after-FR-003 is **necessary, not just preferred**: the orchestrator door
  (`commands.py:1437` → `_prepare_event:444`) blocks *solely* through `:444` once the per-door
  pre-derivation is gone. Removal is dead-code-safe: `_infer_subtasks_complete` keeps 3 callers,
  `_planning_read_dir` has 15+ other uses, and the function-local import at `:1426` vanishes with the block.
- **Per-caller primary-surface resolution (code-verified — the plan's earlier "each caller has
  repo_root" was imprecise):**
  - `status/aggregate.py:717` — introduce `resolve_planning_read_dir(self.repo_root, self.mission_slug,
    kind=TASKS_INDEX)` (the site currently passes `self.read_dir`; this is a **new** introduction, not a
    swap). `MissionStatus` is a dataclass with required `repo_root`/`mission_slug` (docstring: primary
    checkout) — guaranteed present.
  - `status/emit.py` — the nullable-`repo_root` fallback sites are `:532` and `:685`
    (`context_root = repo_root if repo_root is not None else feature_dir`), feeding the
    `_infer_subtasks_complete` calls at `:535`/`:690`. `request.repo_root` is **nullable**, so derive the
    primary root from `feature_dir`. **Gotcha (code-verified):** `resolve_canonical_root` (`core/paths.py:381`,
    param `cwd`, returns the primary checkout) **raises `WorkspaceRootNotFound` outside a git repo**, whereas
    the current `else feature_dir` fallback never raises — so guard it (try/fallback) or the swap breaks
    tmp-dir/non-repo unit tests. Note `emit.py` does NOT currently use `resolve_canonical_root` (it uses
    `canonicalize_feature_dir` + `_feature_status_lock_root`); this introduces the primitive.
  - `coordination/status_transition.py:444` — already imports `resolve_planning_read_dir` (proven
    in-file pattern, `:769`); on the orchestrator door `request.repo_root` is populated (`commands.py:1437`).
  - Behavior when the resolved **primary** `tasks.md` is genuinely absent → **block, never fail open**.
- **Risks**: 4-caller threading; two things to nail in WP-A: (1) the `emit.py` `WorkspaceRootNotFound`
  guard (don't regress non-repo unit tests), (2) confirm the `aggregate.py` `self.repo_root` route as the
  first subtask. DoD headline: native `agent status --to for_review` w/o `--subtasks-complete` on a coord
  mission with unchecked rows is BLOCKED, driven through the production emit path (via `aggregate.py:717`).

### IC-LANE — Lane-recovery sparse-checkout + allocator liveness

- **Purpose**: In `allocate_lane_worktree` (`lanes/worktree_allocator.py`) the fresh-create path
  registers sparse-checkout at `:201-212` under two guards (`coordination_branch is not None` @:197
  AND `short_id is not None` @:210-211); the recovery branch `:172-184` omits it (the #2514 re-leak).
  **Close-by-construction (not "mirror the guards"):** the recovery branch sits *above* `:195` where
  `coordination_branch` is computed, so **hoist** the `coordination_branch`/`short_id` computation
  above `:172` (both recomputable from params already in scope — `_read_coordination_branch(repo_root,
  mission_slug)` and `resolve_mid8(mission_slug, mission_id=lanes_manifest.mission_id)`) and extract
  ONE `_register_sparse_checkout_if_coord(...)` helper that **both** the create and recovery paths
  call, so a recovered coord-topology lane materializes no `status.events.jsonl`/`status.json`, the
  non-coord path stays a byte-identical no-op, and the two paths cannot drift again. **(FR-008 was
  withdrawn post-tasks — the allocator has no stale-claim decision; this concern is FR-006 only.)**
- **Relevant requirements**: FR-006 (single-owned — C-003; `worktree_allocator.py` is one WP's).
- **Affected surfaces**: `src/specify_cli/lanes/worktree_allocator.py`; `tests/specify_cli/lanes/*`.
- **Sequencing/depends-on**: **none** — fully parallel with IC-ROWS/IC-EMIT and IC-LIVENESS. No import
  of `core/process_liveness` (the withdrawn FR-008 was its only consumer here).
- **Risks**: must not change the non-coord (flat/single-branch) path; test both a recovered
  coord-topology lane (sparse registered, no status files) and a non-coord lane (no-op).

### IC-LIVENESS — Promote the claim-liveness helper (sole new consumer: the stale indicator)

- **Purpose**: The cross-platform psutil helper already exists as `sync/daemon._is_process_alive`
  (conservative, never raises — satisfies NFR-004). **Do NOT import it from `sync/daemon` into `core/`**
  — that inverts layering (drags a 1500-line socket/HTTPServer module into a low-level indicator, and
  invites a future cycle). **Promote it to a new low-level module
  `src/specify_cli/core/process_liveness.py`** (public `is_process_alive(pid) -> bool`); repoint
  `core/stale_detection.py` and `sync/daemon.py` to import from there. **`sync/daemon.py` MUST keep
  re-exporting `_is_process_alive`** (a thin alias to the new helper) because `dashboard/lifecycle.py`
  (out of scope) imports `from specify_cli.sync.daemon import _is_process_alive` — moving the symbol
  without the alias breaks that import. No new `os.kill` parse. Read the claiming `shell_pid` via
  `task_utils` frontmatter readers; the stale-WP indicator (`core/stale_detection.py`, today
  git-commit-timestamp-based) suppresses "stale" when the claiming process is live.
- **Relevant requirements**: FR-007 (indicator) + NFR-004. The stale indicator is the **sole new
  consumer**; the daemon keeps the pre-existing consumption via its re-export alias.
- **Affected surfaces**: NEW `src/specify_cli/core/process_liveness.py` (owned here); the
  `sync/daemon.py` repoint + re-export alias; `src/specify_cli/core/stale_detection.py`; tests.
  `core` is the correct home — the lowest layer both `stale_detection` and `daemon` already depend on,
  and psutil is already a hard dependency.
- **Sequencing/depends-on**: **none** — parallel with every other WP.
- **Risks**: NFR-004 — never raise for absent/unparseable/dead/recycled PIDs (conservative
  not-provably-alive). Exactly one liveness definition survives after the promotion; no second parse.

### IC-TIDY — Rollback-reset seam, freshness regression-guard, issue-matrix

- **Purpose**: Route the existing rollback resets (agent/shell_pid clear + subtask uncheck, both
  already in `tasks_move_task.py`) through one `_mt_reset_for_planned_rollback` seam (no new
  behavior); pin #1764's checkbox-insensitive freshness hash with a regression guard (no new logic);
  author the issue-matrix.
- **Relevant requirements**: FR-009 (regression-guard), FR-010, FR-011.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks_move_task.py` (FR-010); a freshness
  regression test against `analysis_report._normalize_tasks_md` (FR-009, source unchanged);
  `kitty-specs/coord-shadows-arm-closeout-01KXAST2/issue-matrix.md` (FR-011).
- **Sequencing/depends-on**: none. Owns `tasks_move_task.py` exclusively (no other WP touches it).
- **Risks**: FR-010 is pure consolidation — assert the rolled-back WP ends fully re-implementable
  (no `[x]` rows, no dangling claim). FR-009 must exercise BOTH the write and gate-check paths.

## Sequencing (post-plan squad verified — 6 WPs)

Post-plan squad (planner-priti + architect-alphonso) verdict: **READY to decompose.** Resulting graph:

```
WP01 (IC-ROWS) ──▶ WP02 (IC-EMIT-CORE, FR-002/003/004) ──▶ WP03 (IC-EMIT-DEDUP, FR-005)   critical path
WP04 (IC-LANE, FR-006)          ┐
WP05 (IC-LIVENESS, FR-007)      ├─ fully parallel with the WP01→WP02→WP03 spine (3 lanes wide)
WP06 (IC-TIDY, FR-009/010/011)  ┘
```

- **Keystone**: WP01 before WP02 (WP02 consumes `count_wp_section_subtask_rows`).
- **IC-EMIT split**: WP02 (3 emit doors) → WP03 (FR-005 removal in `orchestrator_api/commands.py`);
  the FR-003-before-FR-005 ordering is a structural dep edge. Removal is dead-code-safe.
- **No cross-WP liveness edge**: `core/process_liveness.py` (WP05) has a single new consumer — the
  stale indicator (also WP05) — plus the daemon via its re-export alias. WP04 does NOT import it
  (FR-008 withdrawn). All of WP04/WP05/WP06 are independent.
- **Disjoint ownership**: `subtask_rows.py` (WP01) / {`emit`,`aggregate`,`status_transition`} (WP02) /
  `orchestrator_api/commands.py` (WP03) / `worktree_allocator.py` (WP04) / `core/process_liveness.py`+
  `stale_detection.py`+`sync/daemon.py`-repoint (WP05) / `tasks_move_task.py` (WP06) — no overlaps.
- **WP05 hard constraint**: keep `sync/daemon.py` re-exporting `_is_process_alive` (alias) so the
  out-of-scope `dashboard/lifecycle.py` import is not orphaned.
- **DoD sharpening**: WP01's bite battery must assert the *uncheck writer* (not just the counter) no
  longer re-enters a re-appearing `## WPnn` heading; WP02's first subtask confirms the aggregate-door
  `self.repo_root` route + pins "primary tasks.md absent → block, never fail open"; WP03 corrects the
  dead-code tally to **four** remaining `_infer_subtasks_complete` callers after removal.
