# Contract — Authoring-Time Un-Terminable-Work Warning (FR-007/FR-008)

Advisory warning surfaced during `tasks` authoring/finalization when a work package's
acceptance criteria can only be satisfied post-integration. **Advisory only — never blocks
authoring** (FR-008).

## Trigger

A work package matches when its acceptance-criteria / subtask text contains a phrase from
the enumerable post-integration trigger set. Initial set (extensible, versioned in code):

- "after merge" / "post-merge" / "once merged"
- "on a branch the forge will run" / "in CI once enabled"
- "consecutive runs" / "N consecutive"
- "merge-blocked-when-absent"

## Output

Per matched work package, a warning record: `{ wp_id, matched_phrase, criterion_excerpt }`,
rendered to the operator with guidance to re-home the content to a tracked post-merge
obligations document at planning time.

## Oracle (SC-003)

Validated against a **fixed labeled corpus** committed with the mission
(`tests/.../fixtures/authoring_warning_corpus/`):

- **Positive fixtures**: the #3590 shapes ("enable the real system", "prove it with
  controls") → MUST warn (100% recall).
- **Negative / adversarial-near-miss fixtures**: work packages that *mention* CI/merge but
  whose completion is observable in their own diff → MUST NOT warn (0 false positives).

The corpus is the measurement oracle; the metric is not an open-world claim.

## Non-goals

- No structured `completion_kind` field (deferred to #3550, C-003).
- No refusal / no gate. The warning cannot fail authoring.
