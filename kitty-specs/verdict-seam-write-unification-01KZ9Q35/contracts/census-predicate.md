# Contract — Census Predicate (FR-010 / SC-006)

**Owner**: `tests/architectural/test_verdict_seam_census.py::_derive_census` + `verdict_seam_census.yaml`.

## Guarantees

- **G1 (completeness)**: a new writer/resolver/reader of the review-cycle verdict — including a record
  constructed via a `.from_dict`/factory helper (concrete prior gap:
  `backfill_runtime_state.py::_runtime_repair_delta`) — reds the census. *(SC-006)*
- **G2 (no over-match)**: event-authority deserializers (`status/reducer.py`, `status/models.py`,
  `status/wp_review.py`, `_snapshot_review_override`) and the new provenance-backfill migration stay
  **excluded** via named `_EXCLUDED_MODULE_REASONS`, so `test_review_slot_is_event_authoritative…`
  stays green.
- **G3 (shrinkage-red)**: the derived active set must equal the fixture exactly; retirements land in
  the yaml in the same change. *(C-004)*

## Predicate extension

Recognize `<Record>.from_dict(` in the scope regex and the writer classifier (reuse `_call_base_name`);
optionally key the reader predicate on "opens a path matching `review-cycle-*.md` by name" rather than
a fixed verb list.

## Sequencing

Lands **before** IC-03 so the census can prove reader retirement during the collapse. *(C-008)*

## Verified by

≥1 synthetic `.from_dict` poison test (red today) + ≥1 real-data test asserting `_runtime_repair_delta`
is classified + a negative control asserting an event-authority deserializer stays excluded.
