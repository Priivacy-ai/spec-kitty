# Approach Evolution

> Track how your approach changed as the mission progressed.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

**Starting approach (from plan.md)**: two seams delivered strangler-style — a
`GateExecutionContext` handed to gates so they judge a declared surface or refuse, and a
tool-artifact owner generalising `BookkeepingTransaction` so generated writes are committed or
reverted rather than exempted. Nine implementation concerns, IC-01 (#2795 live repro) first
because coord topology means the mission cannot merge itself otherwise.

---

## Entries

2026-07-23 — The mission's *premise* changed before a line was written. The brief named four
P0s (#2160, #2367, #1834, #2573); a pre-spec squad verified three of them had their stated asks
already delivered (`35f3a2206`, `f217d4272`, `b918e66df`, #2786, and five closed #2160
residuals). Scope was rewritten against verified live gaps only. Lesson to carry: for a
brownfield cluster drawn from tracker prose, re-ground against the code *before* specifying —
it changed this mission's scope by roughly half.

2026-07-23 — Abandoned the "coord-topology remediation" framing entirely. #1834 reproduces
identically on a flat `SINGLE_BRANCH` mission, so the unifying axis is *which surface a gate
judges*, not *coordination topology*. Constraint C-004 now forbids any coord-conditioned fix,
because the obvious framing would have shipped a fix that leaves flat missions broken.

2026-07-23 — Rejected candidate direction (b) for #1834 (workspace-aware verification cwd)
after establishing that "the integrated lane/mission tree" does not exist pre-merge for a
multi-lane mission. Implementing it would have meant designating one lane's worktree as the
integrated tree — fabricating exactly the false authority this mission exists to remove.
