# Approach Trace — Doctrine Governance Fidelity

What we tried, what worked, what we'd do differently.

## Strategy

- **One defect class, three file-disjoint lanes.** All three issues are
  "governance signal present, consumer doesn't read it." Decomposed into Lane A
  (#2153 charter interpolation), Lane B (#2156+#2166 org-pack profile
  consolidation), Lane C (#2082 override-policy runtime wiring). Lanes are
  independently testable MVP slices → `topology: lanes`.
- **Pre-planning adversarial squad (4 lenses, profile-loaded)** run before the
  spec: planner-priti (related-issues/foldability), architect-alphonso
  (seams/split-brain), paula-patterns (duplication/campsite-fold), debugger-debbie
  (live repro/code-state). Convergent findings reshaped scope: #2156 is 3 legs not
  1; #2166 folded in as the projection leg; #2082 needs test→production promotion
  first; #2153 is the only true one-liner. Sizing verdict: undersized ~2–3×.
- **Red-first per lane through pre-existing entry points** (C-005): `charter
  generate --from-interview` (A), `ProfileRegistry`/`dispatch` catalog (B),
  `doctor doctrine --json` (C).

## Execution approach

- **Parallel lane sprint**: 4 dependency-free roots (WP01 charter, WP02 resolver, WP06 layout, WP07 promote) dispatched simultaneously as **isolated-worktree** `python-pedro` subagents (each its own `.venv`). Cascade as approvals land: WP02→{WP03, WP04}→WP05; WP07→WP08→WP09. `approved` (not `done`) unblocks dependents.
- **Review** via `reviewer-renata` (per role-separation: pedro implements, renata reviews); cycle cap 3 → arbiter.
- Each WP red-first through its pre-existing surface; the post-tasks-squad BINDING remediations are embedded in every WP prompt.

## What worked

- _(append as WPs land)_

## What we'd do differently

- _(append as WPs land)_
