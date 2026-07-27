# Design Trace — loop-friction-quickwins-2-01KXBWA4

The design itself: the invariants that must hold under implementation (KEEP set) and forward alignment.
Seed → append → assess. (#2095)

## Seed (planning)

### KEEP set (invariants no WP may break)

- **K-1 (NFR-005, C-001): guards keep their true-positive.** Every fix removes a false positive only.
  Substantive spec/plan/task change still stales the analysis report; genuine bulk edit still trips;
  populated-but-insufficient plan still `blocked`; pre-review gate still enforces by default. Each pinned
  by a red-first regression.
- **K-2 (C-004): the interpreter fix must be un-maskable.** Existing real-subprocess gate tests run under
  a pytest-equipped interpreter and hide #2570.3 — a pytest-lacking regression is mandatory.
- **K-3 (NFR-004): manifest reader stays both-forms tolerant.** In-memory `output_path` + internal key
  stay absolute; only the on-disk JSON goes relative; legacy absolute manifests load with zero migration.
- **K-4 (C-002): STATUS_STATE placement is untouchable.** WP-E routes staging only; coord placement
  semantics (merged #168) must be byte-for-byte unchanged — no second split-brain.
- **K-5 (C-005): complement, don't re-tread the fast-follow.** Do not touch #2581/#2573-shipped/#2549B/
  #2577 surfaces; FR-003/004/005 complement #2573's skip-flag/progress, not duplicate.

### Forward alignment

- IC-01/IC-04 are incremental steps toward **#2093** (runtime state → event-log authority); keep the
  exclusion scoped to today's fields so the #2093 retirement is a clean follow-on, not a rework.
- IC-05 is scoped to stay *inside* the **#2160** coord-authority envelope, deferring to the draft
  coord mission on anything beyond planning-artifact staging.

## Append (implement)

- [2026-07-12][plan] **KEEP-set additions from post-plan squad:**
  - **K-6 (alphonso F3):** IC-07 must NOT add a `commit_guard.block_mission_specs` exemption — WP-file
    commits already route to primary via `commit_router`; an exemption weakens partition-lock #168's
    close-by-construction guard for zero benefit. Route at the staging layer only.
  - **K-7 (alphonso F5, Directive-044):** IC-07 reuses IC-01's `resolve_planning_artifact_staging` seam —
    the "should this kitty-specs diff block?" decision must live in ONE place, not fork into move-task.
  - **K-8 (priti F13):** FR-001's runtime field set comes from the canonical `frontmatter.py::WP_FIELD_ORDER`,
    not a fresh inline tuple (no 4th divergent definition).
  - **K-9 (priti F3):** the contention lock's acquire-timeout is DECOUPLED from the 300s subprocess timeout
    (a lock-wait charged to the run timeout re-creates the exact false `no_coverage` FR-004 removes).

<!-- record any further KEEP-set pressure during implement: a fix that tempted a guard-weakening shortcut -->

## Assess (close)

<!-- did all KEEP invariants hold? did the #2093 / #2160 forward alignment survive contact with code? -->
