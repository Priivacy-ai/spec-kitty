# Approach Trace — Mission-Lifecycle Tooling Friction

## Strategy
Reconcile spec-kitty lifecycle tooling friction (7 retrospective gaps → 6 active items)
across 6 file-disjoint lanes → `topology: lanes`. Pre-planning squad (priti/alphonso/
debbie/paula, live-repro'd on c44a4fa82) reshaped scope:
- #2219 DROPPED to verify-and-close (already fixed upstream #2070/#1814).
- #2220+#2221 FOLDED (one WP-authoring-contract SSOT, gated by a golden round-trip test).
- #2223 RE-SCOPED (no "every-#ref" rule exists; wire the existing rule-engine as a finalize-tasks lint).
- #2218 = the one hidden-depth item (coord-branch lifecycle), causally amplifies #2222.

## Operator decisions
- #2218: `--topology` accepts the 4 canonical `MissionTopology` enum values
  (single_branch|lanes|coord|lanes_with_coord); "flat" is NOT canonical; default stays coord.
- #2222: fix by STOP-GATING sibling claims on the vcs-lock self-write (not auto-commit).

## What worked / what we'd do differently
- _(append during implement)_
