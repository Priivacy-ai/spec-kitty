# Decision Moment `01M1VS1KMB4M0RXR66RWA2GAKC`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.emitter.adr-execution-home`
- **Input key:** `emitter_adr_execution_home`
- **Status:** `resolved`
- **Created:** `2026-09-06T16:32:53.901325+00:00`
- **Resolved:** `2026-09-06T16:32:57.368825+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

PR #3898 merged 2026-09-06 with the ADR Accepted (rewire-ready consolidation). FR-012 is executable. Execute it inside WP03 or mint WP05?

## Options

- Mint WP05 (own lane, after WP03)
- Extend WP03
- Other

## Final answer

Mint WP05 (depends on WP03). The Accepted ADR's execution is a code change across runtime_bridge.py, runtime_bridge_engine.py, _internal_runtime/events.py and the retrospective buffer call site, plus two red-first bug fixes (flush target, both paths) and seam-consolidation tests — too large and different in kind for WP03's residue slice. WP03 keeps its shrunk emitter items (docstring + FR-011 record), which WP05 supersedes. OD7 (01M1VAHPARWJKB35F6E1VH8ZTW) is superseded by this decision.

## Rationale

_(none)_

## Change log

- `2026-09-06T16:32:53.901325+00:00` — opened
- `2026-09-06T16:32:57.368825+00:00` — resolved (final_answer="Mint WP05 (depends on WP03). The Accepted ADR's execution is a code change across runtime_bridge.py, runtime_bridge_engine.py, _internal_runtime/events.py and the retrospective buffer call site, plus two red-first bug fixes (flush target, both paths) and seam-consolidation tests — too large and different in kind for WP03's residue slice. WP03 keeps its shrunk emitter items (docstring + FR-011 record), which WP05 supersedes. OD7 (01M1VAHPARWJKB35F6E1VH8ZTW) is superseded by this decision.")
