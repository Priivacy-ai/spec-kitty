# Specification Quality Checklist: Sync Deactivated By Default

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-29
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-###, NFR-###, and C-### entries
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Requirements reference specific env var names (`SPEC_KITTY_ENABLE_SAAS_SYNC`, etc.) and issue
  numbers as governance anchors; these are product-level toggles/traces, not implementation
  detail. File:line seams (e.g. dossier_pipeline.py:471) are deliberately deferred to /plan.
- `change_mode: bulk_edit` is set in meta.json for the ~194-file test-marker rollout;
  occurrence map to be produced during /spec-kitty.plan per DIRECTIVE_035.
- Three discovery decisions confirmed by operator: opt-in-to-enable model; clean-cut #2801
  decoupling; quiet surface = 4 named actions + create + implement.

## Post-spec squad fold (2026-08-29)

3-lens brownfield squad (architect/adversarial/completeness) folded — see `scratchpad/postspec-CONSOLIDATED.md`:
- Seam corrected to a single `sync_active()` that REPLACES scattered gates (FR-002, C-008); arming≠consent (C-007).
- #3470 guard re-keyed on sync-inactive, not disable-vars-only (FR-007) — the disable-only predicate never fires on a bare install.
- Emitter local-capture path (store-lock warning) gets its own FR-006 — SaaS-gating misses it (#1072).
- FR-005 broadened to ALL emission entrypoints; anti-swallow FR-008 + SC-005 added.
- Conftest de-masking (FR-010) makes SC-003 satisfiable; file-count census (FR-013) closes deletion loophole.
- NFR-004 restated as a `--collect-only` diff. Docs (FR-017) + CHANGELOG/doctor advisory (FR-018) added.
All checklist items remain PASS after the fold; no [NEEDS CLARIFICATION] markers.
