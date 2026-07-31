# Tracer: approach — journal-project-consent-3030

## Wave order, and why it held

Containment (WP01/WP02) before the durable fix (WP04→WP06), because containment
needed no schema change. That ordering survived contact: WP02 deleted a whole
second leaking drain in a day, and WP04's migration was the load-bearing
prerequisite the plan predicted.

## T010 before T012 was not bureaucratic

The journal had no schema-migration mechanism at all, while all four SQL constants
derive from `_COLUMN_LIST`. Adding columns without the ALTER step would have raised
`no such column` on every journal file on disk. Landing T010 first meant T012 —
which changed `ORDERED_COLUMNS`, touching every derived statement — produced zero
regressions.

## Red-first, measured against the lane's own baseline

Every WP measured before and after. Two lane baselines were wrong on arrival and
would have produced false greens if trusted:

- **lane-c** was cut from a commit predating the #3031 absorption, WP01 and WP02,
  so it reported **0 failures because the acceptance pins did not exist**.
- **lane-d/e** needed the mission branch merged in to see prior WPs' work.

Merging the mission branch into a fresh lane before measuring is now the habit.

## Bugs the plan did not predict

- New captures never populated the identity columns (T012 added them and a
  backfill; `capture_teamspace_bound` built `Event()` without them). The drain
  would have gone silent for live traffic while history stayed deliverable.
- `_sync_once` silently lost its backoff reset and `last_sync` stamp in WP02's WIP.
- A guard's own `except` swallowed a wrong-arity call, so it reported "clean"
  unconditionally while every stub-based test passed.

Each was caught by measurement or by an anchor test, never by reading the diff.

## Test churn was re-basing, not weakening

Roughly 20 tests moved. Every one encoded the pre-amendment default (capture
unconditional, or selection without identity). Each was given a consented identity
and kept asserting what it always did; the non-consenting halves are pinned
separately. Two tests were deleted outright because their contract was removed, not
changed (event→body drain ordering, and the "events failed, skip bodies" gate).

## Pre-PR landing check (2026-07-30)

Done **before** the agents finished, so the merge is not a surprise at PR time.

- **Base is `origin/main`** (repo default; recent PRs all target it). Branch is **211 ahead, 51
  behind** and main is still moving.
- **Main touches none of this mission's packages** — no `sync/`, `delivery/`, `identity/`,
  `invocation/`, `tracker/`, `saas_client/`. Its diff is docs, ADRs, other missions' dossiers,
  and three files that do overlap.
- **`.github/workflows/ci-quality.yml`** — main added `src/specify_cli/tasks/**` to the
  `closeout` filter group; we added `src/specify_cli/identity/**` to `platform`. Different
  groups, different hunks.
- **`tests/architectural/_gate_coverage.py` + `ci_topology_census.json`** — **both branches
  changed the same derived artifact.** Main routed `tasks` → `closeout`/`misc`; we routed
  `identity` → `platform`/`specify-cli-rest`. Each regenerated the census independently, so both
  committed a 35-entry file derived from a *different* 35.

That last one is the hazard this mission already learned the expensive way (N2: a clean textual
merge that linted, carried no conflict markers, and crashed at runtime). A derived artifact merged
textually can end up matching **neither** derivation. So it was checked semantically rather than
trusted:

```
merged tree: entries 36 | identity present: True | tasks present: True
             unrouted: none | sorted correctly: True
_COMPOSITE_ROUTING in merged tree: both entries present
```

Both additions survive, the merged census matches the merged derivation, and nothing is unrouted.
**Still regenerate with `--emit-census` after the actual merge and confirm it is a no-op** — the
check above verifies the tree git *would* produce, not that a human resolving a later conflict
reproduces it.

## One incidental finding that bears on the canary

This repository's own `.kittify/config.yaml` has **no `sync:` section**, so its project-local
consent reads as **absent** — which under FR-002/FR-003 means **deny**. Anyone planning the live
two-project canary (WP10/SC-008) should know the host repo starts from default-deny, and that a
grant has to be recorded deliberately rather than assumed present. That is the correct posture,
and it is also exactly the state the incident's five victim projects were in.
