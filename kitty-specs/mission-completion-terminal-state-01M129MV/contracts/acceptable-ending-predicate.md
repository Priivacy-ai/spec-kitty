# Contract — Acceptable-Ending Authority

**Symbol**: `specify_cli.status_lanes.is_acceptable_ending(lane: str, *, has_provenance: bool) -> bool`

Single authority deciding whether a work-package lane is an acceptable mission ending.
Consumed by `accept`, `merge`, and the dependency-readiness gate. Replaces the three
`_ACCEPTED_READY_LANES` definitions (`acceptance/__init__.py:145`, `gates_core.py:52`,
`summary_core.py:173,202`).

## Behavior

| Input `lane` | `has_provenance` | Returns |
|---|---|---|
| `approved` | ignored | `True` |
| `done` | ignored | `True` |
| `canceled` | `True` | `True` |
| `canceled` | `False` | `False` |
| `planned`/`claimed`/`in_progress`/`for_review`/`in_review`/`blocked` | ignored | `False` |

- MUST reference canonical `TERMINAL_LANES` only to classify `canceled`; MUST NOT
  redefine terminality or acceptability elsewhere (C-001, directive 044).
- MUST be pure (no I/O). Provenance is resolved by the caller from the reduced snapshot's
  `cancellation_reason`/`reason_source` (C-002).

## Consumer obligations

- **accept**: buckets each WP via the predicate; an acceptable canceled WP → `canceled_wps`
  report; a non-provenance canceled WP → structured blocker naming the missing provenance;
  all other non-terminal lanes → blockers (FR-006). Acceptance-matrix and issue-matrix
  verdict gates still run and can still fail (SC-005 gate-integrity).
- **merge**: excludes canceled WPs from `all_wp_ids` (`executor.py:1660`) and skips a
  branch only when every WP in the lane is canceled.
- **dependency gate**: a `canceled` dependency with provenance counts as resolved
  (`dependency_graph.py:59`).

## Non-fakeable tests (directive 034/036)

- Unit truth-table over all nine lanes × provenance.
- Command-level: approved+canceled(provenance) → eligible; canceled(synthetic) → blocker,
  both driven through the canonical `move-task` surface (not hand-edited events).
