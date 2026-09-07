# Decision Moment `01M1VAHEBB54DDDVCEX2R4BMCJ`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.dsl.retirement-extent`
- **Input key:** `dsl_retirement_extent`
- **Status:** `resolved`
- **Created:** `2026-09-06T12:19:24.139987+00:00`
- **Resolved:** `2026-09-06T12:20:13.122561+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OD1: DSL retirement extent MIN (runner+compat+dispatch) vs FULL (+guards.py, schema.py, fold-gate entry, pack-DSL validator test halves)?

## Options

- FULL (recorded default)
- MIN
- Other

## Final answer

FULL. Delete runner.py, compat.py, guards.py, schema.py and the load_mission/load_mission_by_name dispatch; keep events.py. Same-WP gate edits: 3 dead-symbol pins at test_no_dead_symbols.py:720-727 PLUS the schema::strip_v1_keys pin at :3278 (missed by the spec), fold-gate entry test_wp_frontmatter_fold.py:60, _gate_coverage.py:1456 row, schema-validation halves of test_research_plan_missions_integration.py / test_mission_software_dev_integration.py; gate_registry.py docstrings re-pointed at git history. Rationale: guards.py's shape-precedent value is docstring prose; keeping 680 LOC of test-only code for a citation is the rot shape this mission removes.

## Rationale

_(none)_

## Change log

- `2026-09-06T12:19:24.139987+00:00` — opened
- `2026-09-06T12:20:13.122561+00:00` — resolved (final_answer="FULL. Delete runner.py, compat.py, guards.py, schema.py and the load_mission/load_mission_by_name dispatch; keep events.py. Same-WP gate edits: 3 dead-symbol pins at test_no_dead_symbols.py:720-727 PLUS the schema::strip_v1_keys pin at :3278 (missed by the spec), fold-gate entry test_wp_frontmatter_fold.py:60, _gate_coverage.py:1456 row, schema-validation halves of test_research_plan_missions_integration.py / test_mission_software_dev_integration.py; gate_registry.py docstrings re-pointed at git history. Rationale: guards.py's shape-precedent value is docstring prose; keeping 680 LOC of test-only code for a citation is the rot shape this mission removes.")
