# Tooling-Friction Trace — loop-friction-quickwins-2-01KXBWA4

Running log of spec-kitty friction witnessed while executing THIS mission (a dogfooding mission that
is itself *about* implement-loop friction — expect meta-witnesses). Append live; do not batch at close.

Entry format: `[YYYY-MM-DD][phase] SYMPTOM — anchor — disposition (fixed PR#/ticket#/workaround/open)`

> #2095 experiment. Placed on the **coordination branch** (coord topology) so it does not re-stale the
> analysis-freshness guard or block per-WP move-task on the planning branch (the very frictions
> #2493.1 / #2555.1 this mission fixes — placement lesson from mission 01KW3Q6M).

## Seed (planning)

- [2026-07-12][specify] `setup-plan`/`mission create` returned `blocked` on the first happy-path
  scaffold write — anchor `mission_setup_plan.py::_emit_setup_plan_result` — disposition: **this
  mission's WP-D / #2566** (witnessed live during our own planning; the fix targets exactly this).
- [2026-07-12][plan] Mission minted **coord** topology on a `feat/` branch via `--pr-bound` — anchor
  `mission_create` topology default — disposition: open question (weigh simpler topology at
  tasks-finalize; related to fast-follow #2581 which fixed the non-primary default).

## Append (implement)

- [2026-07-12][tasks] **LIVE #2533 witness (this very mission).** `spec-kitty agent context resolve --action
  tasks` returned the mission read-dir as the **coord worktree** path (`.worktrees/…-coord/kitty-specs/…`)
  even though spec/plan/tasks live on the PRIMARY feat branch — the coord worktree carries only the tracer
  files, not the mission dir. This is exactly #2533's stranded-empty-coord split-brain, hit by our own
  solo PR-bound `--start-branch` coord mission — anchor `coordination/surface_resolver.py` `CoordState.EMPTY`
  arm — disposition: **folded into this mission WP08 (consequence)** + derivation split to **#2602**.
- [2026-07-12][tasks] OUT campsite items surfaced by the Sonar/campsite census: `next_step`/`next_cmd` C901
  suppression de-god (WP06-adjacent); `_mt_commit_wp_file` complexity-11 de-god (WP07-adjacent) —
  disposition: **FILED #2603 + #2604** (tech-debt+tidy-up, milestone 3.2.x, parented under epic #1797).
- [2026-07-12][implement] **`spec-kitty implement --json` does not emit clean machine-readable JSON.** During
  parallel lane allocation, `spec-kitty implement WP## --mission … --acknowledge-not-bulk-edit --json` interleaved
  rich/human panels on stdout — the bulk-edit warning box, the "Lane worktree ready" tree, the "cd to the lane"
  CRITICAL banner, and the lane test-env `export` block — alongside/instead of the JSON object; the JSON that
  did emit put ANSI-escaped rich text INTO the `error` field with `result: null`. Net: `json.load(stdin)` failed
  for ~4/6 allocations (silent empty parse), even though the allocations themselves SUCCEEDED — anchor
  `cli/commands/implement.py` output path — disposition: **FILED #2605** (bug/workflow/usability/P1, 3.2.x, parent #2017; distinct facet from #2570) — breaks any programmatic
  `--json` orchestration of the allocator; workaround = ignore `--json`, run plain + scrape `git worktree list`).
- [2026-07-12][implement] **`spec-kitty doctor tool-surfaces --fix` is worktree-unaware** (found during WP04).
  Run from inside a lane worktree, `locate_project_root()` resolves to the PRIMARY checkout, so `--fix`
  silently modified the PRIMARY repo's `.kittify/agent_profiles_manifest.json` (152 ins/34 del) instead of
  the lane's — a cross-checkout mutation landmine for any `doctor`/`upgrade` command run from a lane. Reverted
  in the primary immediately; WP04 regenerated the manifest via a scoped direct-API script with an explicit
  lane `project_root` instead — anchor `locate_project_root()` / `doctor tool-surfaces --fix` — disposition:
  **NEW, OPEN → to file (worktree-unaware project-root resolution)**; also noted `--fix` won't self-heal a
  foreign-absolute manifest without a manual regen (only saves when an entry is `actionable`). Distinct from
  the #2589 fix WP04 lands.
- [2026-07-12][implement] `spec-kitty implement WP01` tripped the **bulk-edit inference gate** (score 11/4)
  on this mission's OWN spec — because the spec quotes bulk-edit trigger phrases ("bulk edit", "rename all
  occurrences", "across the codebase") while DESCRIBING the FR-008 fix — anchor `bulk_edit/inference.py` /
  `implement.py` claim gate — disposition: **acknowledged via `--acknowledge-not-bulk-edit` (correct — these
  are HIGH-weight phrases; FR-008 only drops LOW-weight verbs, so the guard rightly fires here; NOT a bug,
  a meta-false-positive on a self-describing spec).

<!-- append further `[date][phase] SYMPTOM — anchor — disposition` entries as they occur -->

## Assess (close)

<!-- at mission close: which entries became fixes here vs new tickets; ROI of catching them live -->
