# Tracer: Approach

**Mission**: reliability-papercut-sweep-01KWD0V5
**Seeded**: 2026-06-30 (planning)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

Record the working strategy and how it evolves: the intended decomposition, what changed
once code was touched, dead ends, and re-scopes. Contrast plan-time intent vs implement-time
reality.

## Planning-phase approach (seed)

- **Two cohesive lanes, file-disjoint:**
  - **Lane A — operator coord/gate papercuts:** #2251 (dirty-tree allowlist) → #2250 (coord
    never-created vs deleted) → #2240 (doctor recovery hint + #1890 regression). #2250 and
    #2240 share `_coordination_doctor.py` → **sequenced, not concurrent** (C-002).
  - **Lane B — identity/surface residuals:** #2138 (slug→mission_id fail-closed) + #2139
    (target_branch reader-collapse) are file-disjoint from each other; #2091 (mint-once
    empty-mid8) shares the identity seam with #2138.
- **Red-first per issue** (NFR-001): each fix lands a regression test that fails on pre-fix
  code through the pre-existing operator entry point, then the fix.
- **Test discipline:** invert the stale `test_slug_fallback_when_no_mission_id`; re-pin the
  two doctor-hint tests; extend (not replace) the healthy self-bookkeeping-allowlist and
  orchestrator-merge-target tests (C-003).
- **Sizing reality (from pre-flight):** #2251 is the only clean S; #2240 is thin (mostly a
  regression-pin + stale sub-ask); #2250 is M-across-4-files; #2138 needs the flat-path ULID
  source; #2139 is the heaviest (shared primitive + 3 thin adapters). Lane B is the heavier lane.

## Implement-phase log (append below)

<!-- plan-vs-reality deltas, re-scopes, dead ends -->

## Close assessment (fill at mission close)

<!-- did the 2-lane/sequencing plan hold? what would you decompose differently? -->

## Planning-point-cut squad effectiveness (append @ pre-implement, 2026-06-30)

The pre-implement squad cadence (post-spec investigation → post-plan → post-tasks anti-laziness →
architecture-alignment, bearing in mind SSOT/dedup work) materially reshaped this mission BEFORE a
single line was implemented. Concrete catches, each of which would otherwise have surfaced painfully
mid-implementation or as a post-merge defect:

- **Post-PLAN squad** — caught the `read_topology` cross-lane coupling (Lane A edit would silently
  reclassify for Lane B), forced the **IC-04⇄IC-06 merge** (one identity contract, not two), found a
  **missed slug→mission_id site** (`prompt_metadata.py:149`), and expanded **IC-01 to a cross-gate
  authority** (accept + merge, not just record-analysis). Also corrected 2 wrong source paths + the
  `classify_topology` consumer count (8→6).
- **Post-TASKS anti-laziness squad** — caught **WP03's fakeable DoD** (red-first asserted command
  *existence*, which is green-today since the #1890 phantom was already removed — the real #2240
  defect is recovery *efficacy*). Re-anchored it.
- **Architecture-alignment squad (SSOT/dedup lens)** — the highest-value pass:
  - **WP01 owned the WRONG file** (`merge/preflight.py` has no dirty check; the real classifier is
    `merge/git_probes._classify_porcelain_lines`) AND missed a **4th** gate (`review/dirty_classifier`).
    A 2-of-4-gates partial fix masquerading as "single authority."
  - **WP04 bypassed the identity SSOT** (`resolve_mission_identity`) — would have hand-rolled a 4th
    meta read — AND **missed `lanes/compute.py:313/673`**, a live FR-004 violation (slug persisted as
    `mission_id` in the lanes manifest).
  - **WP02** would have added a 4th parallel coord-existence probe instead of reusing `probe_coord_state`.
  - **WP07** named a **non-invokable seam** (`resolve_planning_read_dir(kind=)` — review-cycle artifacts
    have no `MissionArtifactKind`); corrected to write-where-the-gate-reads symmetry.

Net: the mission grew from 6 issues / 5 WPs (undersized + 2 latent split-brains) to 8 issues / 7 WPs
with disjoint ownership, every WP consuming the canonical authority rather than reinventing it. The
squads' marginal cost was a few hundred K tokens; the avoided cost was shipping the very split-brains
this mission exists to eliminate. **Assessment at planning: high ROI — the architecture-alignment
lens (SSOT/dedup) in particular caught defects no single reviewer or the implementer would have.**

## Implement-phase log (append below)
