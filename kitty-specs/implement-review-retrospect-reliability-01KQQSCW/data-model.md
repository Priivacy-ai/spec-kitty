# Data Model: Implement Review Retrospect Reliability

## ReviewCycleInvariant

Purpose: The pre-mutation result returned by the shared review-cycle boundary.

Fields:

- `artifact_path`: Absolute path to the written `review-cycle-N.md`.
- `pointer`: Canonical `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md` URI.
- `review_result`: Structured `ReviewResult` with `verdict="changes_requested"`, reviewer, reference, and resolved feedback path.
- `cycle_number`: Positive integer review cycle number.
- `wp_slug`: WP task file stem used in the canonical pointer.

Invariants:

- The artifact exists before the result is returned.
- The artifact parses as a valid review-cycle artifact before the pointer is returned.
- The pointer resolves to the artifact path before status mutation.
- The `review_result.reference` equals the canonical pointer.
- Failure returns no pointer to persist and no `review_result` to emit.

## ReviewCycleArtifact

Existing home: `src/specify_cli/review/artifacts.py`

Required frontmatter fields for this mission:

- `mission_slug` or canonical mission identity.
- `wp_id`.
- `cycle_number`.
- `verdict`.
- `reviewed_at` or created timestamp.
- `reviewer_agent`.
- Artifact or feedback identity sufficient to resolve the artifact.

State transitions:

- Created only by the shared review-cycle boundary for rejected review feedback.
- Read by fix-mode and review consistency checks.
- Invalid artifacts fail validation before pointer publication.

## ReviewCyclePointer

Canonical form:

`review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md`

Legacy form:

`feedback://<mission>/<task-id>/<filename>`

Rules:

- New persisted rejection state uses the canonical form.
- Legacy pointers resolve for read paths and emit a deprecation warning where the caller can surface warnings.
- Mutating paths normalize before persistence when possible.
- Sentinels such as `force-override` and `action-review-claim` are not review-cycle pointers and resolve to no artifact.

## ReviewResult

Existing home: `src/specify_cli/status/models.py`

Fields used by this mission:

- `reviewer`: Non-empty reviewer or actor identity.
- `verdict`: `changes_requested` for rejection.
- `reference`: Canonical review-cycle pointer for rejection.
- `feedback_path`: Resolved artifact path for rejection when available.

Invariants:

- Outbound `in_review -> planned` rejection transitions receive a non-empty rejected `ReviewResult`.
- Approval paths continue to use approval evidence and approved `ReviewResult` behavior.
- The shared review-cycle boundary derives rejected results; `emit_status_transition` remains the status validator and persistence gateway.

## WorkPackageLaneState

Source: canonical `status.events.jsonl` reduced through status reducer/lane reader.

Relevant lanes:

- `planned`.
- `claimed`.
- `in_progress`.
- `for_review`.
- `in_review`.
- `approved`.
- `done`.
- `blocked`.
- `canceled`.

Routing rules:

- Finalized tasks and WP lane state override stale early mission phase state for implement-review routing.
- Implement can advance only when WPs are handed off or terminal according to existing bridge semantics.
- Review can advance only when WPs are approved or done.
- Blocked or unknown lanes produce blocked decisions instead of discovery reroutes.

## RetrospectiveRecordState

Existing homes:

- `src/specify_cli/retrospective/schema.py`.
- `src/specify_cli/retrospective/reader.py`.
- `src/specify_cli/retrospective/writer.py`.
- `src/specify_cli/cli/commands/agent_retrospect.py`.

Required JSON outcome states for missing-record handling:

- `retrospective_record_created`.
- `retrospective_synthesized`.
- `insufficient_mission_artifacts`.
- `mission_not_found`.

Rules:

- Missing retrospective records on completed missions no longer collapse to only `record_not_found`.
- If a record is created, it is written through the existing retrospective writer and schema validation path.
- If artifacts are insufficient, JSON output names the missing evidence and the next command to run.
