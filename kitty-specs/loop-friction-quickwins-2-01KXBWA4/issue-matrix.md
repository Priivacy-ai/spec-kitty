# Issue matrix — loop-friction-quickwins-2-01KXBWA4

One row per issue referenced in spec.md.

`in-mission` = being fixed by a WP in this mission (non-terminal; must reach a terminal state before mission
`done`). Context / parent / merged-dependency / explicitly-excluded issues carry `deferred-with-followup`
with a follow-up handle, since this mission does not close them.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2570 | Multi-lane /implement loop friction (allocator self-dirty; interpreter; staging) | in-mission | WP01 (FR-001), WP03 (FR-003/FR-004), WP07 (FR-010) |
| #2493 | Implement-review frictions (analysis re-stale; gate contention) | in-mission | WP02 (FR-002), WP03 (FR-004) |
| #1862 | Analysis-freshness hashes tasks.md wholesale (strip checkbox state) | in-mission | WP02 (FR-002) — pipe-table normalization completes it |
| #2589 | upgrade writes machine-absolute output_path into committed manifest | in-mission | WP04 (FR-006) |
| #2555 | Coord-topology implement-review loop friction (matrix error; bulk-edit; recovery) | in-mission | WP05 (FR-007/FR-008), WP07 (FR-010 §1), WP08 (surface) |
| #2566 | setup-plan/specify scaffold-then-block-then-rerun dance | in-mission | WP06 (FR-009) |
| #2580 | 4th shell_pid writer bypasses claim/liveness baseline | in-mission | WP07 (T026) — routed through canonical write_shell_pid_claim |
| #2533 | Solo PR-bound coord mission strands empty coord husk → split-brain fallback | in-mission | WP08 (FR-011) — consequence-only |
| #2017 | Epic: workflow guards that block legitimate actions / self-write guarded artifacts | deferred-with-followup | Follow-up: #2017 — umbrella epic; this mission is one slice, stays open |
| #2093 | WP-metadata authority split (retire dynamic runtime state to event-log) | deferred-with-followup | Follow-up: #2093 — WP01 advances the runtime-frontmatter line; epic stays open |
| #2160 | Coord topology: unify artifact authority for task/status surfaces | deferred-with-followup | Follow-up: #2160 — coord-authority epic; stays open |
| #1764 | Analysis-report freshness ignores bullet checkbox churn (prior fix) | deferred-with-followup | Follow-up: #1862 — prior art extended by WP02 (pipe-table); #1764 already closed |
| #168 | coord-primary-partition-lock (STATUS_STATE placement) | deferred-with-followup | Follow-up: #2160 — merged dependency; context only, not modified here |
| #846 | specify/plan auto-commit should include populated content or block clearly | deferred-with-followup | Follow-up: #2566 — closed root gate; WP06 fixes its UX cost |
| #2194 | Coord-authority: route implement-loop reads onto resolve_planning_read_dir | deferred-with-followup | Follow-up: #2160 — merged into base; context for WP07 |
| #2222 | vcs-lock-only meta.json diff dropped from claim guard | deferred-with-followup | Follow-up: #2570 — merged; the seam WP01 mirrors |
| #2300 | Unify coord+protected skip-vs-refuse across move-task/mark-status | deferred-with-followup | Follow-up: #2300 — cross-ref for WP07; stays open |
| #2534 | Pre-review gate authorities-unavailable in consumer repos | deferred-with-followup | Follow-up: #2534 — distinct root cause from WP03's #2570.3; stays open |
| #2545 | coord-authority-trio-degod | deferred-with-followup | Follow-up: #2160 — merged into base; context for WP07 |
| #2549 | move-task --force from lane commits status.* to lane branch | deferred-with-followup | Follow-up: #2549 — facet A deferred by the fast-follow; stays open |
| #2573 | move-task synchronous pre-review gate reads as a hang (skip flag shipped) | deferred-with-followup | Follow-up: #2573 — merged fast-follow; WP03 builds on it (async redesign deferred) |
| #2577 | charter synthesize over-demands companion tactics (merged fast-follow) | deferred-with-followup | Follow-up: #2577 — merged; context only |
| #2581 | PR-bound mission mints redundant coord topology (derivation) | deferred-with-followup | Follow-up: #2602 — derivation revisit split out; WP08 fixes only the consequence |
| #2583 | Issue-matrix gate blocks first per-WP approval (scope-conflation) | deferred-with-followup | Follow-up: #2583 — excluded per C-003 (distinct approve-gate defect); stays open |
