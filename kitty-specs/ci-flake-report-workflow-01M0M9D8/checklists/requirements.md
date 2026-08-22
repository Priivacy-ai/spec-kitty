# Specification Quality Checklist: CI Flake-Report Workflow

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *`gh`/`--durations` named as observable contracts, not prescribed architecture*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — *the two load-bearing ambiguities (gate semantics, scope) were resolved with the user*
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (<15 min, zero ruff/mypy, reference-window fidelity, determinism)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (two capabilities; Capability B partitioned as a separate WP)
- [x] Dependencies and assumptions identified (gh retention, durations truncation, CI auth)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Gate semantics resolved: draft = fail-fast, ready = full-*relevant*-signal, aggregate gate **still blocks merge** (branch protection unchanged) — FR-011/C-003.
- Scope resolved: flake-report tool+workflow is the shippable core; draft/ready topology is a separately-landable WP.
- FR-013/SC-006: runbook guidance for draft-PR monitoring (all-green) before RFR.

## Post-spec squad resolution (v2)

Three profile-loaded lenses (analyst-annie, architect-alphonso, reviewer-renata) reviewed v1. Blockers folded into v2:

- **False-red formula pinned** (FR-002): `(perf_timing_flake + infra_flake) / (…+ real)`; `needs_review` reported separately, excluded.
- **Conclusion taxonomy pinned** (FR-001, Edge Cases): cancelled/action_required/skipped/neutral/stale excluded from all metrics.
- **Delta boundary corrected** (FR-004): half-open on completion time; cursor advances only past completed runs; in-progress low-water mark; re-run/new-attempt handling; monotonic, never regress.
- **Golden fixture + concrete tolerance** (FR-017, NFR-003, SC-003): committed frozen fixture; false-red ±2pp, per-test median ±10%; NFR-003 verified against fixture, not live `gh` (C-006 retention).
- **Quantified caps** (FR-008): ≤200 classified failures, ≤50 duration-mined runs, per-fetch timeout, `--log-failed`/selective `gh api`.
- **continue-on-error false-green guard** (FR-011): gate reads `needs.<job>.result`; no `continue-on-error` on gating jobs.
- **Capability-B reconciled with existing machinery**: architect found `ci-quality.yml` already has a draft/ready model + `quality_gate_decision.py` + guard tests. Operator chose net-new **canceller** (FR-009, `actions: write`, allowlisted) + **full-relevant-signal** via `if: always()`/relevance with path-filtering preserved (FR-010) + **gate-contract guard** (FR-016) + **red-first re-run** (FR-018).
- Coverage metric + reproducible input set (FR-015); stable artifact lineage + retention pin + corrupt-state fallback (FR-007).
