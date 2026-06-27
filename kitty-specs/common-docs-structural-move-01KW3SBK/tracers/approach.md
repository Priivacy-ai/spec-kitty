# Tracer: Approach — Mission B (Common Docs Structural Move)

> Standing-orders tracer (experiment #2095). How we sequenced the work + what we'd repeat.

## Seeded at implement-start (2026-06-27)

- **Pre-implement gauntlet:** 3-lens post-tasks anti-laziness squad (renata fakeability /
  debbie code-truth / alphonso decomposition) on the 15-WP set → synthesized + remediated
  in one pass BEFORE touching code. Caught the kitty-specs 3-layer contradiction, the
  WP08 missing-tool gap, the WP12 ~580-page over-scope, the 71-symlink reality, and the
  lane cycles. High ROI — every finding was real and would have bitten mid-implement.

- **Empirical over theoretical on topology.** Rather than reason about whether the lane
  cycles "would" deadlock, ran `finalize-tasks` + a DFS cycle-check on the actual
  `lanes.json` `depends_on_lanes` after each ownership fix. Two iterations (WP10/WP04/WP12)
  converged to 0 collapses. Verifying the generated artifact beat arguing about the model.

- **Serial spine, one WP at a time.** The dependency graph is largely linear
  (WP01→WP02→WP03→{branches}→WP14→WP15). Dispatch implement → review per WP via isolated
  subagents in the lane worktree; lifecycle `move-task` run from the PRIMARY checkout
  (lane worktree status is stale — see tooling-friction). `approved` releases dependents
  immediately (don't wait for `done`).

- **Gate-driven correction loop.** The review diff-compliance gate is doing real work:
  WP01's claim surfaced two occurrence-map under-classifications (the cli_commands blanket
  + the generated-vs-tracked surface) that the squads missed. Treat a gate rejection as a
  map-correction signal, fold the fix back into the occurrence_map, re-claim — don't work
  around it.
