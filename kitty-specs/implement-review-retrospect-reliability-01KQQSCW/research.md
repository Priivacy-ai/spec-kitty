# Research: Implement Review Retrospect Reliability

## Decision: Create a narrow `specify_cli.review.cycle` boundary

**Chosen**: Add a small domain module under `src/specify_cli/review/cycle.py` that owns rejected review-cycle artifact creation, required frontmatter validation, canonical pointer generation/resolution, legacy pointer normalization, and rejected `ReviewResult` derivation.

**Rationale**: #960, #962, #963, and fix-mode context loading are all failures of the same invariant: a rejected review cycle must be valid, canonical, and resolvable before state pointers change. Today that invariant is split between `src/specify_cli/cli/commands/agent/tasks.py`, `src/specify_cli/review/artifacts.py`, `src/specify_cli/cli/commands/agent/workflow.py`, and the status transition guard. One narrow boundary removes duplicated pointer and artifact rules while preserving the existing status pipeline.

**Alternatives considered**:

- Patch each CLI path locally. Rejected because it leaves the invariant spread across callers and makes future regressions likely.
- Redesign the review runtime. Rejected because the mission scope explicitly forbids a broad review-runtime redesign.
- Move the invariant into `status.emit`. Rejected because artifact files and pointer resolution are review-domain concerns; status should continue validating and persisting transitions only.

## Decision: Validate artifacts before pointer persistence

**Chosen**: The shared boundary validates the frontmatter shape before returning the canonical pointer to callers. Required fields are mission identity or slug, WP id, cycle number, verdict, created/reviewed timestamp, and artifact or feedback identity.

**Rationale**: Callers should not be able to write a review artifact, persist a pointer, and then discover that the artifact cannot be parsed. The existing `ReviewCycleArtifact.from_file` parser already rejects missing frontmatter and bad fields; the new boundary should make that validation explicit before returning state-changing outputs.

**Alternatives considered**:

- Trust `ReviewCycleArtifact.write`. Rejected because the current write path does not validate by reading back or checking required identity fields before pointer publication.
- Validate only during fix-mode resolution. Rejected because it still allows dangling or invalid pointers to become canonical state.

## Decision: Canonicalize `review-cycle://` and normalize `feedback://`

**Chosen**: Persist new rejection pointers as `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md`. Resolve `feedback://...` at read time with a deprecation warning or normalize it before persistence when the caller is mutating state.

**Rationale**: New state must be canonical and durable in `kitty-specs/`. Legacy `feedback://` references still exist in tests and historical data, so readers must remain tolerant enough for fix-mode to load old context.

**Alternatives considered**:

- Drop `feedback://` support. Rejected because existing missions and tests may still contain legacy pointers.
- Continue writing `feedback://` for some paths. Rejected because it directly preserves #962.

## Decision: Derive rejected `ReviewResult` before mutation

**Chosen**: `move-task --to planned --review-feedback-file` must receive both a canonical review pointer and a rejected `ReviewResult` before it calls `emit_status_transition` for outbound `in_review` transitions.

**Rationale**: The status transition guard already requires `review_result` for all outbound `in_review` transitions. #960 exists because rejection paths can create feedback artifacts and still fail the transition. Pre-deriving the result lets the command fail before mutation when the review cycle cannot be made valid.

**Alternatives considered**:

- Let `emit_status_transition` infer the result. Rejected because the emitter should not know how to create or resolve review-cycle artifacts.
- Use `--force` to bypass the guard. Rejected because the spec requires normal rejection through the normal CLI surface.

## Decision: Fix `spec-kitty next` in the runtime bridge

**Chosen**: Adjust the `next` bridge/helpers so finalized task board and canonical WP lane state override stale early mission phase state for implement-review routing.

**Rationale**: Current next code already has WP iteration helpers in `src/specify_cli/next/runtime_bridge.py` and public decision contracts in `src/specify_cli/next/decision.py`. Keeping the fix there preserves the runtime boundary and avoids replacing the event log.

**Alternatives considered**:

- Rewrite mission runtime state handling. Rejected as too broad for #961.
- Patch only one fixture path. Rejected because the behavior must hold for implement, review, merge, completion, and blocked outcomes.

## Decision: Add first-class missing-retrospective behavior

**Chosen**: Update `spec-kitty agent retrospect synthesize --mission <mission> --json` so missing `retrospective.yaml` returns a structured JSON outcome instead of a bare `record_not_found`. Prefer an explicit `capture` or `init` command when the missing record cannot be deterministically synthesized; allow synthesize to initialize when completed mission artifacts are sufficient.

**Rationale**: Existing `agent_retrospect.py` treats missing records as exit-code 3. #965 requires completed missions to have a usable CLI path without hand-creating `.kittify/missions/<id>/retrospective.yaml`.

**Alternatives considered**:

- Keep exit-code 3 and only improve text. Rejected because the spec requires parseable JSON states.
- Auto-create records for every missing mission. Rejected unless artifacts are sufficient, because a fabricated retrospective record would reduce trust in retrospective data.

## Decision: Defer #967, #966, #964, and #968 unless adjacent

**Chosen**: Do not schedule these as primary plan work. Include only if implementation naturally touches the same boundary and the fix is small.

**Rationale**: The mission goal is control-loop reliability. Broad test-runner hangs, progress display consistency, generated skill frontmatter validation, and retired-checklist cleanup are lower priority unless they become directly adjacent while touching command or registry tests.
