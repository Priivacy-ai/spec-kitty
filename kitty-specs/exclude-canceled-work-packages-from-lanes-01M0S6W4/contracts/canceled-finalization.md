# Contract: Cancellation-Aware `finalize-tasks`

## Eligibility contract

`finalize-tasks` determines cancellation only from current canonical event-derived lifecycle state. Exactly `canceled` work packages are absent from ownership validation, execution-lane membership, collapse/risk reporting, and validate-only previews. Static definitions and lifecycle events remain intact.

## Stale dependency refusal

If an eligible work package directly depends on a canceled work package, finalization exits nonzero before any finalization mutation.

JSON mode emits one object with this additive contract:

```json
{
  "error": "Active work packages depend on canceled work packages; remove or repoint each dependency before finalizing.",
  "error_code": "CANCELED_WP_DEPENDENCY",
  "stale_dependencies": [
    {
      "dependent_wp_id": "WP04",
      "canceled_dependency_wp_id": "WP03",
      "recovery": "Remove the dependency or repoint WP04 to a non-canceled prerequisite."
    }
  ]
}
```

Rules:

- `stale_dependencies` contains every direct eligible-to-canceled edge.
- Records sort by `dependent_wp_id`, then `canceled_dependency_wp_id`.
- Both IDs and recovery are mandatory in every record.
- Human mode renders the same complete record set.
- No `lanes.json`, target-branch metadata, generated task artifact, event, matrix, dossier, frontmatter, or Git commit is written on this refusal path.

## All-canceled success

When a nonempty, structurally valid Mission has no eligible work packages:

- normal finalization succeeds and writes the existing `LanesManifest` shape with `lanes: []`;
- validate-only succeeds without writes and reports `validation.lanes_preview.computed: true` and `count: 0`;
- all work-package prompts, task-outline entries, and lifecycle events remain present.

This exception does not apply when any eligible work exists. Existing `LANE_COMPUTATION_ABORTED_EMPTY_INPUTS` behavior remains authoritative for genuinely missing ownership/graph inputs.

## Compatibility contract

- `done` work packages remain eligible.
- A governed reopened work package participates according to its current state.
- Missions without canceled work preserve current ownership, execution-lane, collapse, dependency, and post-collapse cycle behavior.
- Corrupt or unreadable status authority causes explicit failure; no secondary source is used to infer cancellation.
