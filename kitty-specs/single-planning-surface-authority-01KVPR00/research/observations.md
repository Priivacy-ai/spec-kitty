# Observations — dogfooding & friction (mission 01KVPR00)

Live friction witnessed while planning THIS mission — which exists to fix the very
coord/primary planning-surface split-brain it then hit. These are direct dogfooding
evidence for the mission's own FRs (#2063/#2064/#2062/#1716) and should feed the
implement loop's acceptance + the post-merge retro.

## O-01 — The mission hit its own bug while planning (meta-dogfooding)
During spec → plan → tasks, the planning commands resolved the artifact surface
inconsistently — the exact #2063/#2064 split this mission converges:
- `mission create` scaffolded `tasks/` (+ `.gitkeep`, `README.md`) on the **PRIMARY** checkout.
- `spec-commit` + `setup-plan` committed `spec.md` / `plan.md` / `research` / `data-model` /
  `quickstart` to the **COORDINATION** branch (`kitty/mission-…-01KVPR00`).
- `agent context resolve` / `check-prerequisites` returned the **COORD** worktree `feature_dir`.
- `finalize-tasks` reads the **PRIMARY** surface (debbie's pre-spec finding, `mission.py:2839`).
So the surfaces disagreed: tasks/ on primary, spec/plan on coord, finalize expecting primary.
**This is FR-001/FR-003 live evidence** — when each command picks its own authority, the next
command can't see what the previous one wrote.

## O-02 — `tasks/` unreachable on the coord worktree
`mission create` makes `tasks/` on the primary checkout, but `spec-commit` materializes the
coord worktree and commits artifacts there — so the coord worktree's `kitty-specs/<slug>/`
has spec/plan but **no `tasks/`**. `/spec-kitty.tasks` (resolving the coord `feature_dir`) had
nowhere to write WP files. The create-scaffold surface and the commit surface are different
authorities. (Directly motivates FR-001's "every planning write resolves ONE authority.")

## O-03 — Flatten as the routine workaround (the anti-pattern ADR 2026-06-19-1 warned about)
To make progress, the mission was **flattened** mid-planning: dropped `coordination_branch`
from primary `meta.json`, copied the coord-committed artifacts (plan/research/data-model/
quickstart/spec) to primary, removed the coord worktree, committed all on `feat` (`f79f0dc32`).
After flatten, every tool agreed on the primary surface and tasks finalized cleanly. This is
exactly the "the escape hatch became the normal path" pattern the coord-empty ADR flagged
(field-evidence already cited there for mission `01KVFTFV`). The mission's value proposition is
to make the canonical flow work WITHOUT needing this flatten.

## O-04 — Orphaned coord branch residue
After flatten + `git worktree remove`, the coord branch `kitty/mission-…-01KVPR00` still exists
in git carrying the committed spec/plan history — an orphan. Harmless here (nothing reads it),
but it is precisely the **orphaned-coord** state FR-004 (read-path gate) and FR-007 (the
`worktree repair` PRUNE arm) target. The mission would have cleaned this automatically.

## O-05 — After flatten, the commands agreed (FR-003 fix direction confirmed)
`map-requirements --batch` then `finalize-tasks --validate-only` both resolved the primary
surface and **agreed** (zero unmapped, validation passed). Live confirmation of FR-003's
direction: when the write surface and the read surface are the same authority, map-requirements
and finalize stop disagreeing. The bug is the surface split, not the coverage logic (FR-013
brownfield correction).

## O-06 — Implication for the implement loop (carry forward)
This mission is now flat, but the WPs that edit `setup_plan` / `finalize_tasks` / `spec-commit`
/ `map-requirements` (WP03/WP05/WP06) will be implemented in this flat mission and may still hit
coord/primary friction (the per-lane worktree topology, status reads). Carry the live-evidence
rule (NFR-001): drive status from the authoritative (primary) surface; re-flatten a lane if it
wedges; never close #2062 on static reading. The quickstart R1–R5 repros are the acceptance
gates.

## O-07 — Guard-coverage gap re-confirmed
The differential equivalence gate is green but under-feeds topologies (it never feeds
flattened-stale-coord — FR-005 adds it). Same class as the #2065 bare-mid8 BLOCKER and the
#1890 phantom-command guard gap (markdown-fences-only — FR-008 extends it to Python literals +
ADRs). Pattern: **a green guard that doesn't feed the broken case is a partial proof.**
