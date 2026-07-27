# Tracer: subtask-row canonicalization (IC-ROWS)

**Concern**: one `_walk_wp_section` generator; guard == dashboard == rollback agree on "what is a
WP subtask row"; canonical section-boundary = the guard's break-semantic.

## Planning intent
- Aggregate left TWO divergent walks in `core/subtask_rows.py`: counter `break`s on section-exit;
  `uncheck_wp_section_subtask_rows` sets `in_wp_section=False` and continues → re-enters a
  re-appearing `## WPnn` heading. Not byte-identical-able. Decision: **guard's break wins.**
- Bite battery MUST include: re-appearing WP heading, content-after-section-end, nested headings,
  `depends: WPnn` mention, fenced code block, id past T999.

## Implementation log
_(append during IC-ROWS implementation: which fixtures added, the walker's final semantic, any
behavior delta from the aggregate writer)_

## Close-out assessment
_(at mission close: did the unify change bite anywhere unexpected? one canonical definition confirmed?)_
