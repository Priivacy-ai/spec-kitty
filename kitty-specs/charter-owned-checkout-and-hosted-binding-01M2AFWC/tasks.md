# Work Packages: Owned checkout charter operations and hosted binding governance

**Inputs**: spec.md and plan.md; CLI #4250, SaaS #1713.

## Work Package WP01: Owned checkout source propagation (Priority: P1)

**Goal**: Owned checkout source propagation.
**Independent Test**: Real canonical entry point positive and negative acceptance witnesses pass.
**Prompt**: `tasks/WP01-owned-checkout-source.md`
**Requirement Refs**: FR-001, FR-002, NFR-001, C-001, C-002

### Included Subtasks

T001 Reproduce primary-checkout authoring/context leakage through real CLI linked-worktree tests.
T002 Propagate validated explicit ownership through command, bundle freshness, include and JSON seams; test isolation and document usage.

### Dependencies

- None.

### Parallel Opportunities

Own source/tests separately from project doctrine; final integrated CLI witness follows both.

## Work Package WP02: Hosted binding doctrine and activation (Priority: P1)

**Goal**: Hosted binding doctrine and activation.
**Independent Test**: Real canonical entry point positive and negative acceptance witnesses pass.
**Prompt**: `tasks/WP02-hosted-binding-doctrine.md`
**Requirement Refs**: FR-003, FR-004, NFR-002, C-001, C-002

### Included Subtasks

T003 Author and canonically activate native repository identity and truthful hosted completion directive/procedure preserving existing authority.
T004 Prove actual active consumer content, missing/inactive failure, and source-only versus installed protection evidence.

### Dependencies

- None.

### Parallel Opportunities

Own source/tests separately from project doctrine; final integrated CLI witness follows both.

## Dependency & Execution Summary

WP01 and WP02 are parallel nonoverlapping source/governance streams. Independent review checks integrated final context after both; neither implementation is marked done by this plan.
