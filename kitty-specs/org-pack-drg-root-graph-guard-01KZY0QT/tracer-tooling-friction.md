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

## SK-11 — canonical `plan-template.md` still carries the prohibited "Feature specification" wording

Live-verified during the plan-phase R4 fix round: `plan.md:4`'s "**Input**: Feature
specification from ..." line is verbatim canonical-template boilerplate —
`packs/built-in/missions/software-dev/templates/plan-template.md:4` carries the identical
phrase, character-for-character. The Terminology Canon prohibits `Feature`/`Features` in
canonical, operator, and user-facing language ("Mission specification" is correct here), but
the defect is upstream, in the template itself, not in this mission's copy: hand-editing only
this plan's instance would create non-canonical drift from the template every other mission
inherits. Left unfixed in `plan.md` deliberately (not silently ignored — recorded here) pending
an upstream doctrine fix to `plan-template.md` (and any sibling mission-type templates using
the same phrase) that replaces "Feature specification" with "Mission specification" at the
source.

## SK-12 — `check-prerequisites`'s `branch_matches_target` is a false positive on a mid-flight `lanes`-topology mission

Live-verified during this tasks phase: `spec-kitty agent mission check-prerequisites --json
--paths-only --include-tasks --mission org-pack-drg-root-graph-guard-01KZY0QT` reported
`branch_matches_target: false` while HEAD was `762f6f362` on
`kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT` — the exact, correct branch this
mission's spec and plan phases already committed to. `target_branch`/`planning_base_branch`/
`merge_target_branch` were all reported as `"main"` (correctly read from `meta.json`'s own
`target_branch` field, unlike SK-10's HEAD-derived defect), but the command then compares the
*current checked-out branch* against that literal value to compute `branch_matches_target`,
with no allowance for `lanes` topology's actual planning model: per `meta.json`
(`"topology": "lanes"`) and AGENTS.md's Execution Workspace Strategy, a mid-flight mission's
planning artifacts (spec.md, plan.md, and now tasks.md) land on the mission branch itself, not
literal `main` — `main` is only the eventual PR merge target, reached at mission close, not the
branch planning commands should be checked out on mid-mission. Verified by checking that `main`
does not contain this mission's `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/spec.md` at
all (`git show main:kitty-specs/.../spec.md` → `fatal: ... exists on disk, but not in 'main'`),
while the mission branch already carries four committed spec/plan-phase commits. Following the
canonical prompt's literal instruction ("if `branch_matches_target` is false, stop") would have
incorrectly halted valid, already-in-progress work on the one correct branch. Not worked around
by switching branches (there is nowhere correct to switch *to* — `main` lacks this mission's
own planning artifacts); tasks authoring proceeded on the verified-correct mission branch
instead, with this entry recording the false-positive field rather than silently ignoring it.
Same root family as SK-10 (branch-field/topology confusion), but the opposite failure
shape: SK-10's fields are wrong (HEAD-derived); here the raw `target_branch` value is right, but
the derived boolean comparing it against the working branch is wrong for `lanes` topology
mid-mission.

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->
- 2026-08-13 — `spec-kitty plan --mission <handle> --json` scaffolded `plan.md` from the
  template and reported `blocked` (Technical Context not yet substantive) on first invocation,
  as expected/documented behavior — not a defect, just confirms the scaffold-then-fill
  two-step is real and the tool's blocked-reason message is accurate and actionable.
