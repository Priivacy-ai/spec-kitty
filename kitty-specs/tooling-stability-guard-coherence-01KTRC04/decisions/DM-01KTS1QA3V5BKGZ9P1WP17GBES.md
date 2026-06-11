# Decision Moment `01KTS1QA3V5BKGZ9P1WP17GBES`

- **Mission:** `01KTRC04`
- **Origin flow:** `plan`
- **Slot key:** `plan.drg.provenance-shape-revision`
- **Input key:** `provenance_shape_revision`
- **Status:** `resolved`
- **Created:** `2026-06-10T15:16:57.595265+00:00`
- **Resolved:** `2026-06-10T15:16:58.409571+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

WP09 T034 gate: Provenanced[T] cannot be confined (DRGGraph container reshape + 15 test sites). Revise D2?

## Options

- declared-optional-field
- keep-wrapper-reshape
- defer-1624

## Final answer

REVISED to declared-optional-field (operator, 2026-06-10): add provenance: str | None = None on DRGNode/DRGEdge (FR-007's sanctioned alternative). Evidence change: the wrapper reshapes the public DRGGraph container + convenience methods + 15 test read-sites — the original '2 consumers' right-sizing counted getattr call sites but missed the container flow (T034 gate, F-004). Field is excluded from graph.yaml serialization (provenance is runtime-overlay-only; extractor.py generates graph.yaml independently).

## Rationale

_(none)_

## Change log

- `2026-06-10T15:16:57.595265+00:00` — opened
- `2026-06-10T15:16:58.409571+00:00` — resolved (final_answer="REVISED to declared-optional-field (operator, 2026-06-10): add provenance: str | None = None on DRGNode/DRGEdge (FR-007's sanctioned alternative). Evidence change: the wrapper reshapes the public DRGGraph container + convenience methods + 15 test read-sites — the original '2 consumers' right-sizing counted getattr call sites but missed the container flow (T034 gate, F-004). Field is excluded from graph.yaml serialization (provenance is runtime-overlay-only; extractor.py generates graph.yaml independently).")
