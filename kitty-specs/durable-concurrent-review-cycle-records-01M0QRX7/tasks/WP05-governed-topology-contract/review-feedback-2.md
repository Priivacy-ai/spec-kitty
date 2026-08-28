# WP05 Review Feedback — Cycle 3

## Verdict

Rejected after the hosted architecture gate found a new frozen-cardinality assertion in the owned topology test.

## Evidence

- `tests/architectural/test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline` reports one mission-owned site in `tests/integration/review/test_verdict_save_topologies.py`.
- The site asserts `len(observation.deletion_paths) == 1`.

## Required correction

Express the single expected deletion path structurally (for example, by unpacking the collection) and retain the exact path assertion. Do not update the frozen baseline or add a golden-count escape.

## Required evidence

- Focused topology tests pass.
- The golden-count architecture test passes for this site.
- Ruff and strict mypy pass on the owned module.

