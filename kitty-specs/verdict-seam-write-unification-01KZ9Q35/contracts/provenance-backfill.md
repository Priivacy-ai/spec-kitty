# Contract — Verdict-Provenance Backfill + Gate (FR-012 / SC-008)

**Owner**: new `migration/verdict_provenance_backfill.py` + a provenance gate (extends
`doctor review-cycle-reconcile` predicate or a sibling surface).

## Backfill

For each mission/WP with a **terminal `.md` verdict** and **no event `review_result` slot**: reduce
the `.md` verdict into `status.events.jsonl` via `append_events_atomic_verified`
(`status/store.py:509`) with a **hand-constructed** `review_result` event — **not**
`emit_status_transition` (D-PLAN-10: it derives `from_lane` from the WP's *current* lane and runs
`validate_transition`, so it cannot replay a historical edge onto a settled WP). The event's `at`
**MUST** be the **historical** verdict timestamp from the `.md`/git record, never `now()`.

- **G1 (idempotent)**: keyed on `(mission_id, wp_id, verdict, cycle)` — a re-run adds nothing.
- **G2 (provenance, not location)**: the predicate examines *verdict provenance* (event slot vs `.md`),
  distinct from the reconcile doctor's two physical-*location* classes
  (`deleted_coord_branch_absorption`, `live_coord_pre_adr_primary_record`).

## Gate

- **G3 (blocks reader deletion)**: IC-03's frontmatter-reader deletion is blocked while any WP has a
  terminal `.md` verdict and no event slot. Parses `--json`; asserts zero findings as a test artifact.

## Sequencing

Lands in IC-02, **before** IC-03. *(C-008)*

## Verified by

A seeded mission whose only rejection is a pre-event `.md`: after backfill + reader deletion, the
approval guard still refuses. *(SC-008; US6)*
