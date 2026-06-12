# E2E Execution Observations — tooling-stability-guard-coherence-01KTRC04

Running observations trace of tooling issues hit while executing THIS mission e2e (the 01KTPKST pattern). Doubles as a
closeout "did we fix it?" checklist. Legend: 🔴 open · 🟡 worked-around · 🟢 fixed · ⚪ deferred

## F-001 — finalize-tasks auto-creates a coordination branch and SPLITS the planning artifacts 🔴 (in-mission target)

- **When:** tasks step (2026-06-10), first `finalize-tasks` run for this mission.
- **What happened:** the mission was planned flattened on `fixups/code-engine-stabilization` (spec/plan/research
  committed there). The first `finalize-tasks` run silently (a) created `kitty/mission-tooling-stability-guard-coherence-01KTRC04`
  + a `-coord` worktree, (b) wrote `coordination_branch` into meta.json, and (c) committed tasks.md + WP files +
  lanes.json + acceptance-matrix to the **coordination branch** — while spec.md/plan.md stayed on fixups.
  Re-running finalize then failed `PLANNING_BRANCH_NOT_PERSISTED` → `spec.md not found` on the coord surface:
  the freshly-minted **#1784-class catch-22** (artifacts split across two refs, each gate reading a different one).
- **Class:** EXACTLY this mission's FR-003 (placement defined by ONE resolved authority; planning paths must not
  invent a second destination). The auto-coord-creation at finalize is another instance of the
  `_resolve_planning_branch`/meta.json second-authority root that WP05 retires.
- **Workaround:** 🟡 flattened per the 01KTPKST precedent — removed `coordination_branch` from meta.json,
  removed the coord worktree, committed the artifacts on fixups (e483ddf), re-ran finalize (a10d92f, clean).
  Coord branch `kitty/mission-tooling-stability-guard-coherence-01KTRC04` kept as backup (tip 2fbb1cd) — delete
  after the mission lands.
- **Acceptance check (closeout):** after WP05, `finalize-tasks` on a protected-target/flattened mission reads
  and writes the SAME resolved destination as specify/plan (SC-6 covers the protected case; add the
  finalize-re-run idempotency case to WP05's e2e if not already covered).
- **Status:** 🔴 open — in-mission (WP05/FR-003); workaround applied for this mission's own pipeline.

## Closeout acceptance summary (filled at 10/10, 2026-06-10)
| ID | Status | Fixed by / rationale |
|----|--------|----------------------|
| F-001 | 🟢 | WP05 (approved): single placement authority `resolve_placement_only`; `_resolve_planning_branch` commit-destination authority retired; #1784 catch-22 e2e repro green. Re-test the finalize re-run path live once the merged CLI is installed. Backup coord branch (tip 2fbb1cd) to delete after landing. |
| F-002 | ⚪ | NOT absorbed by a WP (prompt-file naming is out of this mission's FR scope) — file upstream: `/tmp/spec-kitty-implement-WPxx.md` must be keyed by mission, not WP id alone. |
| F-003 | ⚪ | NOT absorbed (claim's final reporting/prompt-regeneration step, distinct from the placement/status surfaces fixed here) — file upstream: claim succeeds but reports "no workspace could be resolved" and skips prompt regeneration. |
| F-004 | 🟢 | Resolved via formal D2 revision (operator, 2026-06-10): declared `provenance` field instead of Provenanced[T] wrapper; WP09 approved. The T034 STOP-gate worked exactly as designed. |
| F-005 | ⚪ | Worked around (husk dirs removed; canonical approvals succeeded) but the ROOT (review-claim mints mid8-slug husk dirs; move-task resolves them over real worktrees) is NOT fixed by this mission — file upstream; same #1619 resolution-divergence family. |
| F-006 | ⚪ | `spec-kitty accept` auto-runs negative-invariant `verification_command`s against the PRIMARY tree and overwrites the recorded results — pre-merge, that tree cannot contain the mission's changes, so honest invariants flip to `still_present` (WP01's suite doesn't exist on fixups yet). Followed 01KTPKST precedent (evidence in criteria, NIs empty). File upstream: the gate needs either a post-merge re-verify phase or a worktree-aware cwd for pre-merge runs. |

## F-002 — implement-claim prompt files collide across missions (`/tmp/spec-kitty-implement-WPxx.md`) 🔴

- **When:** implement loop (2026-06-10), WP09 dispatch.
- **What:** `agent action implement WP09` for THIS mission left `/tmp/spec-kitty-implement-WP09.md` containing the
  **previous mission's** WP09 prompt (01KTPKST "Dead-symbol deletion") — the generated prompt path is keyed by WP id
  only, not mission, so prompts collide across missions. The implementer detected the mismatch and used the canonical
  WP file instead. (Likely cause: the claim's trailing "no workspace could be resolved" error — see F-003 — aborted
  before regenerating the prompt.)
- **Workaround:** 🟡 implementers must verify the prompt's mission header; canonical source = `kitty-specs/<mission>/tasks/WPxx-*.md`.
- **Class:** tooling-stability (this mission's domain); file as follow-up if not absorbed.

## F-003 — `agent action implement` reports "no workspace could be resolved" while the worktree IS ready 🟡

- **When:** every claim in this mission's implement loop.
- **What:** the claim creates the lane worktree + branch ("Lane worktree ready") then errors
  `implement completed but no workspace could be resolved for WPxx` — and (per F-002) appears to skip prompt-file
  regeneration. The worktree/branch/status transition are all actually correct; the resolution failure is in the
  final reporting/prompt step.
- **Workaround:** 🟡 verify worktree + use the canonical WP prompt file; ignore the cosmetic error.
- **Class:** read-path/workspace resolution (this mission's domain).

## F-004 — WP09 T034 gate fired: Provenanced[T] cannot be confined (D2 evidence change) 🔴 → operator

- **What:** the carrier design can't stop at the 2 `getattr` consumers: `_tag_source`'s outputs populate the PUBLIC
  `DRGGraph(nodes/edges)` Pydantic container → `Provenanced[DRGNode]` reshapes `DRGGraph` + its convenience methods
  + 15 test read-sites across 5 files. The pedro/randy "2 consumers" right-sizing counted call sites but missed the
  container flow. graph.yaml is NOT affected either way (generated by `extractor.py`, provenance never serialized).
- **Disposition:** implementer STOPPED, no code changed (correct). Decision escalated to operator: declared-optional-field
  (FR-007's sanctioned alternative; ~17 mechanical sites, no public reshape) vs accept the container reshape.

## F-005 — review-claim creates mid8-slug HUSK dirs; move-task resolves them over the real worktrees 🔴

- **When:** review wave (2026-06-10). CONFIRMED MECHANISM: each `agent action review` claim recreates the husk (observed live on lane-i). `agent action review` created plain directories `.worktrees/01KTRC04-lane-{a,f,g,h}`
  (only a `.spec-kitty` marker inside, NO `.git`) — a **mid8-slug naming scheme**, while the real registered worktrees
  use the full slug (`tooling-stability-guard-coherence-01KTRC04-lane-X`). `move-task --to approved` then resolved the
  HUSK as the lane workspace: `git -C <husk>` falls through to the PRIMARY repo → false "no implementation commits on
  lane branch" + false "dirty worktree" (the primary's status bookkeeping). Blocked 3 of 4 approvals (WP01/WP08
  reviewers attested+forced with evidence; WP06/WP07 waited for the canonical fix).
- **Fix applied:** committed the primary status dirt + removed the 4 husk dirs → canonical approvals succeeded.
- **Class:** worktree/workspace resolution divergence (two naming schemes = two resolution paths) — squarely this
  mission's #1619 domain; adjacent to F-003. File upstream if not absorbed by a WP.
