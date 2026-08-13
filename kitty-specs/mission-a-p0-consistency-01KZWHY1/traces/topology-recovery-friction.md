# Tracer: coord/primary split-brain + lane-seed recovery friction

**Mission:** mission-a-p0-consistency-01KZWHY1
**When:** 2026-08-13, at `/spec-kitty.implement` (lane allocation)
**Severity:** blocked implementation for a multi-step recovery; no data loss.

## Symptom

`spec-kitty agent action implement WP01/02/03` failed for every lane:

```
Workspace allocation failed: cannot auto-merge the recorded planning commit
'<sha>' into lane 'lane-a': the merge conflicts.
```

The conflict was an **add/add on `lanes.json`** (after an earlier layer on
`status.json`). Re-running finalize and backing out files did NOT converge —
the allocator regenerates coord's planning-artifact snapshot on each claim.

## Root cause (two layers)

1. **Structural (tooling):** this mission was created with `--start-branch
   fix/mission-a-p0-consistency` (pr-bound feature branch) **and** got **coord
   topology**. The coord branch (`kitty/mission-…`) was branched from the old
   base (`b7c080c`) and given its **own** planning-artifact snapshot, while the
   real planning (spec/plan/tasks/**lanes.json**) landed on the **fix** branch.
   Result: **coord never contained the primary `planning_commit_sha`.** Lanes
   seed from coord and merge the primary planning commit → `lanes.json`
   (which embeds `planning_commit_sha`) is an add/add conflict every time.
   This is the #3311 chicken-and-egg (FR-009 / ADR 2026-07-29-1) the mission
   itself exists to fix, surfacing in the allocator.

2. **Operator-contributed:** during "commit & push" I committed the primary
   working tree's **`status.json` + `status.events.jsonl`** to the fix branch
   (commit `10747bea`) to get a clean tree, over-generalizing the "362 missions
   track `status.events.jsonl`" convention. Those 362 are mostly **non-coord**
   (SINGLE_BRANCH / LANES) missions where the primary IS the status surface;
   under **coord topology** `status.*` are **coord-authority** and must not live
   on the primary branch. `status.json` has **no merge driver**, so it became
   the first add/add conflict layer. (finalize-tasks *also* listed `status.*` in
   its `files_committed` to the primary — see "Upstream gap" below.)

## Recovery that worked (operator-approved)

- Removed primary-committed `status.{json,events.jsonl}` (coord-authority).
- Removed the stale `lanes.json` from coord (primary artifact).
- **Reconcile coord←primary:** `git merge fix/mission-a-p0-consistency` in the
  coord worktree. spec-kitty **union merge-drivers** auto-reconciled
  `status.events.jsonl` / `issue-matrix.json` / `meta.json`; `lanes.json`
  auto-merged; the 7-row issue-matrix was preserved. Coord now **contains** the
  planning commit → lane seeding is a **no-op merge** → allocation succeeds.

Sync fan-out also hung the CLI (needed `SPEC_KITTY_SYNC_DISABLE=1` on every
`implement`/`finalize` call; claims still took 60–120 s each).

## Upstream gaps to consider filing

1. **pr-bound feature-branch + coord topology should not diverge at create** —
   the coord branch must be created so it contains (or fast-forwards to) the
   primary planning commit; otherwise every lane-seed conflicts. (Adjacent to
   #3311 / FR-009 provenance.)
2. **finalize-tasks commits `status.{json,events.jsonl}` onto the PRIMARY branch
   under coord topology** (`files_committed` includes them) — that is the
   split-brain seed; status should be coord-only under coord topology.
3. **`re-finalize` re-captures `planning_commit_sha` to the tip-*before* its own
   commit**, so the recorded SHA references a commit whose embedded `lanes.json`
   points at a different SHA (self-inconsistent) — the exact #3311 defect.
4. **Prompt/skill guidance gap:** neither the commit guidance nor the
   implement-review skill warns against committing `status.*` to primary under
   coord topology, nor surfaces the `SPEC_KITTY_SYNC_DISABLE` need for slow
   claims.

## Lesson for next mission

- Do **not** `git add` `status.*` on the primary branch of a coord-topology
  mission. Check topology (`meta.json` / `lanes.json`) before treating status
  files as trackable.
- Seed tracer files at **planning**, not retroactively (this file is late).
