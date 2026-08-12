---
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reviewed_at: '2026-08-10T13:42:49Z'
reviewer_agent: reviewer-renata
wp_id: WP06
---

# WP06 reviewer findings — changes requested

## 1. Exact-outcome provenance is internally false

Every disposition cites raw artifact `67120f918ecef7e45791aa81d3c6823b1546820f478e53fa24d075f1adbfb60c`, but that exact capture records several claimed failure/error nodes as default passes. The earlier #3284 result is explicitly aggregate-only, not per-node identity evidence. Re-run owned #3284 nodes on immutable base+WP02 and HEAD; bind each exact outcome to its actual artifact.

## 2. Spent-sync deletions under-classify occurrences

The patch deletes 17 + 4 sync nodes, but each ledger row names one member. Nineteen deleted nodes have no disposition, and the named identity survivor does not cover all event/status/offline/lifecycle behavior. Classify every deleted node or valid family, name real survivors per contract, and restore anything without a stronger owner.

## 3. Flake evidence needs replayable rows

Persist seed, repetition, topology, command, outcome, and artifact hash for 20 isolated + 10 parallel runs, including the pre-repair failure. Do not change the FD-transfer repair; reviewer replay confirmed 10/10 parallel and 139/139 focused.

## Verified

- Frozen 177→139 nodes (`-38`); test diff `+78/-1872` (`-1794` LOC).
- No production changes; focused cohort 139 passed; 43 named survivors passed.
- Ruff/schema clean; post-repair daemon parallel matrix 10/10.
- Functional console/template/doctor/daemon assertions preserved; no masking.
