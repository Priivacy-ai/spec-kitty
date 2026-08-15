# Guard a Lane Base Against a Fixed SHA, Not a Moving Branch Tip

**Why it's here:** this cost a real mission a full wave of implementer agents (all
stopped, large token burn) chasing a false alarm — the guard shape is easy to get
wrong in the same way twice because the naive check *looks* correct until upstream
moves mid-mission.

## The gotcha

Do not detect a stale/stranded lane base with
`git merge-base --is-ancestor upstream/main HEAD`. `upstream/main` (or the mission's
target branch) keeps advancing *during* a mission — other missions land, background
sync fetches — so this check flips to "no" the moment upstream ticks forward **after**
the lane forked, even though the lane sits on the exact base it was correctly created
or rebased onto. That is a false "base stranded" verdict, not a real one.

## The correct guard

Pin to the **known-good rebase-target commit SHA** captured at the moment the lane was
based, and check that the lane still **descends from that fixed SHA**:

```
git -C <lane> merge-base --is-ancestor <REBASE_TARGET_SHA> HEAD
```

YES = the lane descends from the tree it was based on = good, regardless of where the
live branch tip has since moved. The real strand to catch is the *old*-base case:
`merge-base(lane, upstream) == the OLD pre-rebase base` — a live-tip compare cannot
distinguish "upstream moved" from "lane is stale" and will false-positive on the former
far more often than it catches the latter.

## Related, not restated here

Lanes also carry a *recorded planning-artifact commit* as an explicit extra git
ancestor, captured once at `finalize-tasks` and never re-derived from a live branch
read — see ADR
[`docs/adr/3.x/2026-07-29-1-lane-base-recorded-planning-commit.md`](../../docs/adr/3.x/2026-07-29-1-lane-base-recorded-planning-commit.md)
for that design. This note is about the *orchestrator-side freshness guard* used when
dispatching implementers against an already-created lane, which is a related but
distinct concern from how the lane's git parentage is constructed.
