# REASONS Canvas — Observable Pre-Review Gate

> Mission: `implement-review-loop-recovery-01KXG2TD`
> Revised: 2026-07-14
> Status: non-governing, exploratory, and advisory; the project charter and canonical Mission artifacts take precedence

## Requirements

- Residual problem and bounded intent: [spec.md § Purpose](./spec.md#purpose) and [§ Intent Summary](./spec.md#intent-summary).
- Acceptance scenarios: [spec.md § User Scenarios & Testing](./spec.md#user-scenarios--testing).
- Requirements and interruption boundaries: [spec.md § Functional Requirements](./spec.md#functional-requirements), [§ Non-Functional Requirements](./spec.md#non-functional-requirements), and [§ Constraints](./spec.md#constraints).
- Measurable outcome targets: [spec.md § Success Criteria](./spec.md#success-criteria). The quality checklist is not implementation or Definition-of-Done evidence.
- Planning-base dispositions: [spec.md § Issue Traceability and Code-Truth Disposition](./spec.md#issue-traceability-and-code-truth-disposition).

## Entities

- Canonical concepts and mode boundaries: [spec.md § Key Entities and Domain Language](./spec.md#key-entities-and-domain-language).
- Scope protections: [spec.md § Constraints](./spec.md#constraints) and [§ Non-Goals](./spec.md#non-goals).

## Approach

- Selected strategy: managed observation around the existing blocking gate at the exact command orchestration seam; see [plan.md § Selected Design](./plan.md#selected-design).
- Tradeoffs: [plan.md § Alternatives considered](./plan.md#alternatives-considered) and [traces/design-decisions.md](./traces/design-decisions.md).

## Structure

- Code surfaces and component boundaries: [plan.md § Project Structure](./plan.md#project-structure) and [§ Architecture and Data Flow](./plan.md#architecture-and-data-flow).
- Ownership boundaries: the gate engine remains authoritative; command orchestration owns only observation, output mode, and the pre-mutation boundary.

## Operations

- Implementation sequence: deferred to `tasks.md` and per-WP prompts after planning review.
- Test strategy: must preserve the separate RED-on-planning-base commit required by [NFR-005](./spec.md#non-functional-requirements) and exercise the exact entry point in both modes.

## Norms

- Charter and canonical Mission artifacts govern; this canvas is exploratory context only.
- Liveness is not a passing gate verdict, JSON standard output remains parseable, and retry-to-green is prohibited.
- Delivered planning-base behavior is regression context, not new implementation scope.

## Safeguards

- Hard boundaries: [spec.md § Constraints](./spec.md#constraints).
- Explicit exclusions: [spec.md § Non-Goals](./spec.md#non-goals).
- Non-fakeable measures: [NFR-001 through NFR-006](./spec.md#non-functional-requirements).
- Interruption safety is limited to the pre-mutation gate phase; uncatchable termination receives recovery/reconciliation semantics only.

## Deviations (append-only)

- 2026-07-14 — specify — Scope narrowed after post-spec squad and code-truth audit from four claimed issues to the residual #2573 default gate path — planning-base evidence showed the other facets delivered or unproven.
