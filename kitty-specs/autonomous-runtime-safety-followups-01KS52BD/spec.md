# Feature Specification: Autonomous Runtime Safety Follow-ups

**Feature Branch**: `autonomous-runtime-safety-followups-01KS52BD`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: Mission brief ingested from `start-here.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrospective synthesis works after capture (Priority: P1)

As a Spec Kitty operator, I need `retrospect create` and
`agent retrospect synthesize` to agree on the retrospective YAML contract so
that every completed mission can run the documented retrospective learning loop
without schema failures.

**Why this priority**: The current schema mismatch breaks the post-merge flow
for every mission that captures a retrospective record.

**Independent Test**: Create or fixture a retrospective record with the fields
written by `retrospect create`, then run synthesize in dry-run and `--apply`
paths and verify no pydantic `extra_forbidden` validation error occurs.

**Acceptance Scenarios**:

1. **Given** a freshly written `retrospective.yaml`, **When**
   `spec-kitty agent retrospect synthesize --mission <slug>` runs, **Then** it
   reads the record and reports the dry-run outcome.
2. **Given** the same record, **When** synthesize runs with `--apply`, **Then**
   proposals are applied or reported through the existing apply outcome without
   reader-schema rejection.

---

### User Story 2 - Deferred decisions can be closed cleanly (Priority: P1)

As an autonomous mission runner, I need a decision deferred during planning to
be resolvable at terminus when the plan default is accepted so that decision
verification and acceptance do not permanently disagree.

**Why this priority**: The current `deferred` terminal state forces either a
permanent `[NEEDS CLARIFICATION]` marker or permanent verifier drift.

**Independent Test**: Open a decision, defer it, close it with a final answer or
default rationale, remove the marker, then run `decision verify` and the
acceptance gate.

**Acceptance Scenarios**:

1. **Given** a deferred decision, **When** the operator resolves it with a final
   answer, **Then** the state transition succeeds and the decision is terminally
   closed.
2. **Given** the marker was removed after closure, **When** verification runs,
   **Then** it does not report `DEFERRED_WITHOUT_MARKER` drift.

---

### User Story 3 - Planning catches invalid WP ownership before implementation (Priority: P1)

As a planner, I need `finalize-tasks` to reject WP-owned `kitty-specs/` files
that lane branches cannot commit so that implementers do not discover the
contract conflict during `move-task`.

**Why this priority**: The current split between finalization and lane-branch
gates creates split-brain WP deliverables and review ambiguity.

**Independent Test**: Finalize a fixture mission where a WP declares
`kitty-specs/<slug>/occurrence_map.yaml` in `owned_files`; verify validation
fails with a structured WP/path error.

**Acceptance Scenarios**:

1. **Given** a WP frontmatter `owned_files` entry under `kitty-specs/`, **When**
   `finalize-tasks --validate-only` runs, **Then** it fails before writing lane
   metadata.
2. **Given** the same invalid entry, **When** full finalization runs, **Then** it
   fails with the same actionable error and does not commit finalized tasks.

---

### User Story 4 - Bulk-edit planning WPs are not blocked as if they were active rewrites (Priority: P2)

As a planner of future bulk edits, I need a WP whose deliverable is
`occurrence_map.yaml` to pass implementation pre-flight without claiming the
mission is not a bulk edit so that planning artifacts can be authored honestly.

**Why this priority**: The current pre-flight creates a false-positive for the
exact planning artifact the bulk-edit guardrail expects.

**Independent Test**: Claim a WP whose `owned_files` includes
`occurrence_map.yaml` and whose spec text triggers bulk-edit inference; verify
the pre-flight is informational for that WP, while active rewrite WPs still
require normal bulk-edit coverage.

**Acceptance Scenarios**:

1. **Given** a WP authors the occurrence map, **When** `agent action implement`
   runs, **Then** it does not require `--acknowledge-not-bulk-edit`.
2. **Given** a later WP touches target paths declared by the occurrence map,
   **When** implementation starts, **Then** the normal bulk-edit gate still
   applies.

---

### User Story 5 - Disjoint workstreams retain planned parallelism (Priority: P2)

As a mission planner, I need lane computation to respect disjoint
`owned_files` across upstream workstreams so that fan-in tasks synchronize
parallel lanes instead of serializing the entire mission.

**Why this priority**: The current dependency-only collapse algorithm preserves
correctness but loses wall-clock parallelism for autonomous missions.

**Independent Test**: Finalize a fixture mission with six disjoint workstreams
and one downstream fan-in WP; verify lane computation produces six lanes and
the fan-in WP is sequenced after its prerequisites.

**Acceptance Scenarios**:

1. **Given** upstream WPs have disjoint `owned_files`, **When** they only share a
   downstream fan-in dependency, **Then** they remain in separate lanes.
2. **Given** direct dependencies with overlapping `owned_files`, **When** lane
   computation runs, **Then** those WPs still collapse for safety.

---

### User Story 6 - Autonomous focused-PR fallback is documented (Priority: P3)

As an autonomous run operator, I need the mission workflow and official docs to
describe the focused-PR fallback when local `main` is ahead of `origin/main` so
that `TARGET_BRANCH_NOT_SYNCHRONIZED` is a documented path, not a handoff
surprise.

**Why this priority**: This is documentation-only, but it closes the final
operator workaround from PR #1251.

**Independent Test**: Review the updated docs and verify they cite the runtime
error and commands for creating a PR from the mission branch or optional
focused branch.

**Acceptance Scenarios**:

1. **Given** `spec-kitty merge` refuses with `TARGET_BRANCH_NOT_SYNCHRONIZED`,
   **When** the operator follows Phase 9 docs, **Then** they can create a PR
   without reset, rebase, or force-push.
2. **Given** an autonomous run has many orchestration commits, **When** the PR
   is opened, **Then** the docs recommend squash-merge for a clean `main`
   history.

### Edge Cases

- A retrospective record may include informational fields not used by
  synthesis; those fields must not break reading.
- Malformed retrospective YAML and missing records must keep their existing
  error classifications.
- A deferred decision with no final answer must not be silently treated as
  resolved.
- `kitty-specs/` ownership validation must report all offending WP/path pairs
  rather than hiding later invalid entries behind the first failure when
  practical.
- Bulk-edit planning recognition must not allow active rewrite WPs to bypass
  occurrence-map validation.
- Lane computation must continue to collapse WPs when ownership overlaps,
  regardless of the requested lane labels.

### Domain Language *(include when terminology precision matters)*

- **Deferred decision**: A decision opened during specify or plan that was
  intentionally postponed with an inline `[NEEDS CLARIFICATION]` marker.
- **Closed with default**: A formerly deferred decision that is later resolved
  by accepting a documented plan default.
- **Owned files**: The WP frontmatter paths/globs that define the files an
  implementer may change.
- **Bulk-edit planning WP**: A WP that authors planning artifacts such as
  `occurrence_map.yaml` for a later bulk edit but does not perform the live
  rewrite itself.
- **Fan-in WP**: A downstream WP depending on multiple upstream workstreams and
  acting as their synchronization point.
- **Focused-PR path**: The documented fallback for opening a PR from a mission
  or focused branch when local `main` is not synchronized with `origin/main`.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retrospective reader/writer compatibility | As an operator, I want synthesize to accept records created by `retrospect create` so that retrospective learning is runnable after every mission. | High | Open |
| FR-002 | Synthesize dry-run coverage | As an operator, I want the default synthesize path covered by tests so that preview behavior stays safe. | High | Open |
| FR-003 | Synthesize apply coverage | As an operator, I want the `--apply` path covered by tests so that proposal application stays compatible with created records. | High | Open |
| FR-004 | Deferred decision closure | As an autonomous runner, I want a deferred decision to be closeable with a final/default answer so that terminus can record accepted plan defaults. | High | Open |
| FR-005 | Decision verifier closure awareness | As an autonomous runner, I want `decision verify` to recognize closed deferred decisions so that removed markers are not reported as drift. | High | Open |
| FR-006 | Acceptance gate closure awareness | As a release operator, I want acceptance checks not to block on markers backed by closed decisions so that completed missions can merge. | High | Open |
| FR-007 | `kitty-specs/` ownership validation | As a planner, I want `finalize-tasks` to reject WP `owned_files` under `kitty-specs/` so that lane-branch failures are caught before implementation. | High | Open |
| FR-008 | Structured ownership error | As a planner, I want ownership validation errors to name the WP and offending path so that the task file can be fixed directly. | High | Open |
| FR-009 | Architectural ownership regression test | As a maintainer, I want an architectural test preventing `kitty-specs/` in WP `owned_files` so that future missions do not reintroduce the mismatch. | Medium | Open |
| FR-010 | Bulk-edit planning pre-flight recognition | As a planner, I want WPs authoring `occurrence_map.yaml` to receive an informational bulk-edit warning instead of a blocking false-positive. | Medium | Open |
| FR-011 | Active bulk-edit gate preservation | As a maintainer, I want active rewrite WPs to keep the full bulk-edit gate so that planning recognition does not weaken safety. | High | Open |
| FR-012 | Disjoint fan-in lane preservation | As a planner, I want disjoint upstream workstreams to remain in parallel lanes when their only relationship is a downstream fan-in WP. | Medium | Open |
| FR-013 | Overlap collapse preservation | As a maintainer, I want overlapping owned-file dependencies to keep collapsing into shared lanes so that parallelism does not create write conflicts. | High | Open |
| FR-014 | Focused-PR workflow docs | As an operator, I want mission workflow docs to document the `TARGET_BRANCH_NOT_SYNCHRONIZED` focused-PR fallback so that autonomous runs have a clear roll-up path. | Medium | Open |
| FR-015 | Official autonomous-run docs | As an operator, I want the same focused-PR path in official how-to docs so that the guidance is discoverable outside a single mission artifact. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Test focus | Each WP must run the affected test packages for its touched behavior; the mission does not require a full-suite run for every WP. | Quality | High | Open |
| NFR-002 | Coverage bar | New code must have pytest coverage at or above 90% for the added or changed behavior. | Quality | High | Open |
| NFR-003 | Strict typing | New or changed typed code must remain clean under the repo's `mypy --strict` expectations for the touched modules. | Maintainability | High | Open |
| NFR-004 | No new dependencies | The implementation must not add new pip dependencies. | Maintainability | High | Open |
| NFR-005 | Error clarity | New validation failures must include stable machine-readable details or JSON fields where the surrounding command already supports JSON output. | Operability | Medium | Open |
| NFR-006 | Backward compatibility | Existing valid missions, decision flows, retrospective records, and lane computations without the problematic patterns must keep working. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Scope limit | Only issues #1255, #1256, #1235, #1257, #1236, and #1258 are in scope. | Product | High | Open |
| C-002 | Decision command contract | Do not change the public contract of `spec-kitty agent decision open`, `defer`, or `cancel`; only closure via `resolve` or an added closure verb is allowed. | Technical | High | Open |
| C-003 | Implement command contract | Do not change the public contract of `spec-kitty agent action implement`; only pre-flight gates may change. | Technical | High | Open |
| C-004 | Bulk-edit skill boundary | Do not change the bulk-edit skill itself; adjust only runtime pre-flight classification/gating. | Technical | High | Open |
| C-005 | CLI stack | Use existing project stack and conventions: Typer, Rich, ruamel.yaml, pytest, pydantic, and existing helper APIs. | Technical | High | Open |
| C-006 | SaaS sync env on this machine | If a command touches hosted auth, tracker, sync, or SaaS behavior on this computer, run it with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Environment | High | Open |
| C-007 | No unrelated cleanup | Do not silently fix unrelated pre-existing bugs; file separate issues if discovered. | Process | Medium | Open |
| C-008 | PR #1251 as worked example | Use PR #1251 artifacts and the six issue bodies as technical context; the referenced retrospective file was not present in the fetched PR ref. | Evidence | Medium | Open |

### Key Entities *(include if feature involves data)*

- **Retrospective record**: The `.kittify/missions/<mission_id>/retrospective.yaml`
  file written by `retrospect create` and read by `agent retrospect synthesize`.
- **Decision record**: The persisted state and marker relationship for decisions
  opened, deferred, resolved, verified, and checked by acceptance gates.
- **Work package frontmatter**: The task prompt metadata containing
  `work_package_id`, `dependencies`, `owned_files`, `authoritative_surface`, and
  execution fields consumed by `finalize-tasks` and runtime gates.
- **Lane graph**: The computed execution-lane structure derived from
  dependencies and ownership, materialized in `lanes.json`.
- **Occurrence map**: The bulk-edit planning artifact that describes target
  categories and rewrite actions.

## Assumptions & Open Questions *(include when discovery leaves documented defaults or deferred decisions)*

### Assumptions

- The cheapest acceptable fix for #1235 is rejection at `finalize-tasks` time;
  auto-routing `kitty-specs/` paths is allowed only if it is already clearly
  supported by runtime architecture.
- The simplest acceptable fix for #1256 is allowing `deferred -> resolved`;
  adding `close-with-default` is acceptable if implementation evidence shows it
  is safer.
- The official docs target for #1258 is `docs/how-to/run-an-autonomous-mission.md`
  if present, otherwise create that page or the closest existing autonomous-run
  how-to.
- The six issues should become six WPs, with #1235 and #1257 allowed to share
  architectural context but remain separately reviewable.

### Open Questions

- None. The brief supplies enough scope and acceptance detail for planning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `spec-kitty agent retrospect synthesize --mission <slug>` runs
  end-to-end against a freshly-created retrospective file without pydantic
  validation errors in dry-run and `--apply` paths.
- **SC-002**: A decision can be deferred during planning and later resolved or
  closed with a default answer with zero `decision verify` drift warnings.
- **SC-003**: `spec-kitty agent mission finalize-tasks` rejects or explicitly
  routes every `kitty-specs/` entry in WP `owned_files` before lane work starts.
- **SC-004**: A WP whose deliverable is `occurrence_map.yaml` does not require
  `--acknowledge-not-bulk-edit`, while active bulk-edit WPs still trigger the
  full gate.
- **SC-005**: A fixture with six disjoint owned-file workstreams and one fan-in
  WP produces six lanes rather than one.
- **SC-006**: Mission workflow docs and official how-to docs document the
  `TARGET_BRANCH_NOT_SYNCHRONIZED` focused-PR fallback.
- **SC-007**: Affected pytest packages pass, new code meets the 90% coverage bar,
  and touched strict-typed modules remain `mypy --strict` clean.
