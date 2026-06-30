# Tracer: Tooling Friction

**Mission**: reliability-papercut-sweep-01KWD0V5
**Seeded**: 2026-06-30 (planning)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

Log every point where Spec Kitty's own tooling (CLI, gates, guards, resolvers, hooks)
created friction during this mission. One entry per incident: what you were doing, what
blocked or surprised you, the workaround, and whether it warrants an upstream issue.

> Meta-note: this mission *is itself* a reliability-papercut sweep, so friction observed
> here is doubly relevant — it may be a new papercut to fold or file.

## Planning-phase observations (seed)

- **Stale `primary_branch` config in the reused clone.** `mission branch-context` reported
  `primary_branch: coord-read-residuals-2185-2186` (a leftover from this clone's prior
  mission), so `current_is_primary` read `false` on `main` and recommended "stay". Did not
  block (created on an explicit `fix/` start-branch anyway), but the recommendation would
  have misled a less-careful operator into authoring mission artifacts on `main`. Candidate
  papercut: branch-context should detect the real repo primary, not a stale per-clone pin.
- **Commit-hook interpreter pinning** (known, [[project_commit_hook_pins_interpreter]]) — watch
  for `spec-commit` / git commits failing on a pinned interpreter; `spec-commit` worked here.

## Implement-phase log (append below)

<!-- one entry per friction incident during implementation -->

## Close assessment (fill at mission close)

<!-- summarize: how many incidents, which became issues, net tooling-trust delta -->

## Implement/merge-phase: the mission dogfooded its own target bugs (2026-07-01)

The implement-review loop hit the EXACT bugs this mission fixes — strong live evidence they are real:

- **#2251 (dirty-tree gate on bookkeeping)** — `record-analysis` blocked with `DIRTY_WORKTREE` on
  uncommitted loop bookkeeping (agent stamps / status). The very gate WP01 hardens. Workaround:
  commit the bookkeeping before re-recording.
- **Gate-read coord-vs-primary split (#2275 class)** — the **issue-matrix**, **analysis-report**,
  and **acceptance-matrix** approval/accept gates all read from the **coord worktree**, while my
  edits + `record-analysis` wrote to the **primary**. Had to manually sync each into the coord
  worktree. This is the read/write authority split WP07 fixes.
- **#2275 itself blocked the merge** — `spec-kitty merge` failed
  `REJECTED_REVIEW_ARTIFACT_CONFLICT` for WP03 + WP05: both went reject→fix→approve, but the
  running (pre-fix) CLI persisted NO approved review-cycle artifact in the coord worktree, so the
  merge gate saw the coord-latest as cycle-1 `rejected`. Manual remediation: wrote the approved
  `review-cycle-2.md` into coord for both — exactly what WP07 now automates.

Net: every gate-read / dirty-tree / review-artifact bug in the mission scope manifested against the
mission itself before it was merged. The fixes are now in the branch; the next mission run on this
CLI should not hit them.

## Close assessment (fill at mission close)
- 3 distinct in-scope bugs reproduced live during the loop (#2251, #2275 ×2 surfaces). The mission
  is well-targeted: these are real operator papercuts, not theoretical. Tooling-trust delta:
  negative during this run (heavy manual coord-sync), expected positive once merged.
