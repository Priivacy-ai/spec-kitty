# Tracer: tooling friction — org-pack-drg-root-graph-guard

Charter standing order 3. Every place the tooling fought this mission, so it feeds the
tooling-gap backlog — seeded at plan time with three known-broken surfaces this mission hit
first-hand while driving the plan phase (all three are already documented in
`/home/jeroennouws/dev/SK-missions/SPEC-KITTY-LEDGER.md`; restated here in public-repo-safe,
class-level terms, no private downstream detail).

## SK-09 — nothing mints the mission branch during `specify`

`safe_commit`'s prescribed remedy when it refuses a commit is `spec-kitty mission create
--start-branch` — a flag that does not exist on this checkout. Nothing in the `specify` phase
actually creates the mission branch for you; an agent following the tool's own suggested
recovery path hits a second wall (an unrecognised flag) instead of an unblock.

## SK-09b — `spec-commit` refuses on the resolved placement ref, not on `HEAD`

`spec-commit` checks `meta.json`'s own `target_branch` (here, `main` — a protected primary)
before deciding whether to refuse, rather than checking the branch actually checked out
(`HEAD`, the mission lane branch). Under `lanes` topology with a protected primary, this makes
`spec-commit` structurally unusable no matter which branch is checked out at invocation time —
refusing on the *placement* ref means it refuses even when `HEAD` is the correct, unprotected
mission branch. `spec-kitty safe-commit` is the working path and was used throughout this
phase (see the commit at the end of this plan phase).

## SK-10 — `branch-context`/`setup-plan` branch fields derive from `HEAD`, not from `meta.json`

Live-verified during this plan phase: `spec-kitty plan --mission
org-pack-drg-root-graph-guard-01KZY0QT --json` returned `target_branch`,
`base_branch`, `planning_base_branch`, and `merge_target_branch` **all equal to the current
branch name** (`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT`) — even though this
mission's own `meta.json` declares `"target_branch": "main"`. `branch_matches_target` was
reported `true` by construction, not because the branches actually agree. This means
`spec-kitty agent mission branch-context --json` (and the equivalent fields surfaced by
`plan`/`setup-plan`) **cannot ever report a genuine target-branch mismatch** — it derives every
branch field from whatever is currently checked out rather than reading `meta.json`'s own
`target_branch`. This plan's own branch-contract statement (top of `plan.md`) was written by
reading `meta.json` directly instead of trusting this command's branch fields, precisely
because of this defect.

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->
- 2026-08-13 — `spec-kitty plan --mission <handle> --json` scaffolded `plan.md` from the
  template and reported `blocked` (Technical Context not yet substantive) on first invocation,
  as expected/documented behavior — not a defect, just confirms the scaffold-then-fill
  two-step is real and the tool's blocked-reason message is accurate and actionable.
