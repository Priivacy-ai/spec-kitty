# Data Model: Autonomous Runtime Safety Follow-ups

## RetrospectiveRecord

Existing on-disk YAML record at `.kittify/missions/<mission_id>/retrospective.yaml`.

Relevant fields:

- `mission_id`
- `mission_slug`
- `mission_type`
- `target_branch`
- `created_at`
- `created_by`
- `policy_source`
- `findings_status`
- `evidence_refs`
- `generator_version`
- `provenance_history`
- proposal/findings fields already consumed by synthesize

Invariant: any field written by `retrospect create` must be accepted by
`agent retrospect synthesize`.

## DecisionRecord

Existing persisted decision state used by `decision open`, `defer`, `resolve`,
`cancel`, `verify`, and acceptance gates.

Relevant statuses:

- `open`
- `deferred`
- `resolved`
- `canceled`
- optional new `resolved_with_default` only if implementation chooses the
  explicit closure-verb approach

Invariant: a decision that was `deferred` may be terminally closed by an
explicit final/default answer. Closed decisions do not require an inline
`[NEEDS CLARIFICATION]` marker.

## WorkPackageFrontmatter

Existing YAML frontmatter on `kitty-specs/<slug>/tasks/WP##-*.md`.

Relevant fields:

- `work_package_id`
- `dependencies`
- `owned_files`
- `authoritative_surface`
- `execution_mode`
- `requirement_refs`

Invariant: code-change WP `owned_files` must not include `kitty-specs/` paths
unless the runtime has a first-class mission-branch routing model for those
paths. This mission plans rejection at finalization time.

## BulkEditPlanningClassification

Derived runtime classification for one claimed WP during implementation
pre-flight.

Inputs:

- mission `meta.json` `change_mode`
- spec bulk-edit inference score
- claimed WP id
- claimed WP `owned_files`
- presence/validity of `occurrence_map.yaml`

Invariant: a WP that authors `occurrence_map.yaml` is a planning-artifact WP,
not an active rewrite WP. Active rewrite WPs still require the existing
bulk-edit gate.

## LanesManifest

Existing `lanes.json` structure.

Relevant fields:

- `lanes[].lane_id`
- `lanes[].wp_ids`
- `lanes[].write_scope`
- `lanes[].depends_on_lanes`
- `lanes[].parallel_group`
- `collapse_report.events[]`

Invariant: lane collapse must prevent write conflicts but should not serialize
disjoint upstream workstreams solely because they feed a downstream fan-in WP.
