# Post-Spec Adversarial Squad — Findings & Resolutions

**Date**: 2026-07-23 · **Phase**: post-spec, pre-plan · **Squad**: 3 read-only lenses, model-routed to complexity
**Lenses**: architect-alphonso (correctness, Opus) · paula-patterns (deletion-safety, Opus) · curator-carla (roadmap/doctrine, Sonnet)
**Verdict pre-amendment**: NOT ready for plan (2 BLOCKERs + several MAJORs). **Post-amendment**: resolved into FR-008..013 + NFR-005/006 + `SOURCE_MISMATCH`; ready for plan.
**Scope decision (operator)**: keep ONE mission, 3 WPs, sequenced **A→C** with **B parallel** (corrected from A→B→C).

All load-bearing code claims were verified against merged `main` (`564522eb8`) before amending.

## BLOCKERs → resolutions

| # | Lens | Finding (verified) | Resolution in spec |
|---|------|--------------------|--------------------|
| B1 | alphonso | **The naive fix ships the bug it kills.** `_capture_baseline_via_scope_source` (`baseline.py:517-522`) parses the artifact AFTER the base worktree is torn down. Safe for `GateCoverageScopeSource` (absolute tempfile JUnit) but for `DeclaredCommandScopeSource` with a worktree-relative `--junitxml` the artifact is deleted → text/synthetic identities → disjoint namespace from head → false `NEW_FAILURES`. | **FR-008** now requires the baseline artifact be read/relocated to a stable out-of-worktree path BEFORE teardown; **FR-010** parity test must cover the worktree-relative-artifact + FAIL-text cases; US1 AS1 + edge case updated. |
| B2 | alphonso | FR-009's class/command-shape identity can't catch B1 (same class, same command, different parse-mode); also under-specified WHERE the assertion runs (must not fire on the shared override tier) and lacks a backward-compat default. | **FR-009** rewritten: record **parse-mode/artifact-presence**; assert in the injected-`ScopeSource` head path ONLY; `from_dict` defaults a missing field to "unknown → unverified warn" (US1 AS4). |

## MAJORs → resolutions

| # | Lens | Finding | Resolution |
|---|------|---------|------------|
| M1 | alphonso | Mismatch verdict left as loud-fail/`NO_COVERAGE`-warn either-or; overloading `NO_COVERAGE` (empty-scope) conflates two conditions. | **FR-011** adds a dedicated warn-shaped `GateOutcome.SOURCE_MISMATCH` (fail-open); SC-004 + US1 AS2 pin the single behavior. |
| M2 | alphonso | NFR-001's golden drives only the (unchanged) registry path; it would pass even if the deletion severed a symbol the KEPT override tier needs. | **NFR-006** adds an override-tier golden + an import/functional survival assertion for the C-002 keep-live set. |
| M3 | alphonso + paula + carla | FR-004 was incomplete: **8 verdict-diff tests** (`test_pre_review_gate_engine.py:827,843,868,897,918,936,961,996`) pass `filter_groups=/composite_routing=` and are NOT `_derive`-based — the param drop makes them `TypeError` → red suite, and their verdict-diff coverage is unique. Also no pre-deletion audit of the sole-`scope_source=None`-caller precondition; "no coverage lost" was unfalsifiable. | **FR-004** rewritten to MIGRATE the 8 named tests to `scope_source=` injection + require a coverage-parity inventory; **FR-002** adds the pre-deletion audit. |
| M4 | alphonso | FR-003's factory hoist leaves the monkeypatched override seams' placement undefined (import-cycle risk); NFR-005 "equivalent" undefined. | **FR-003** requires the seams move with the factory or be parameterized; **NFR-005** defines equivalent = equal `test_command()` + equal parse-mode/identity. |
| carla-1 | carla | FR-004 "no coverage lost" unfalsifiable. | Folded into the FR-004 rewrite (coverage-parity inventory). |
| carla-2 | carla | US3 "eases half B" unverified; FR-006 ABC forces nominal inheritance where the port is structural; the two predicates might be one check renamed. | **FR-005** now requires the two predicates be **independently-evaluable** (separate signals); **US3 AS3** adds a synthetic-source proof; the "eases half B" framing softened to "removes the weld". |
| carla-3 | carla | Scope: bundling the urgent P1 correctness fix behind zero-risk hygiene. | **Operator chose one mission**; C-003 corrected to A→C with B parallel so WP-C is not gated on the full deletion, only the small factory hoist. |

## MINORs → resolutions

- **m1 (alphonso)**: the `diff_baseline` "fixed" element is unused by any live consumer; the broad-baseline mislabel is latent/harmless. → Edge case downgraded to "documented, not asserted"; no FR claims to fix it.
- **m3 (alphonso)**: nothing pins that the baseline runs WITHOUT head's per-file targets. → **FR-012** anti-narrowing guard test.
- **paula (docs/comment)**: `derive_test_scope` appears in plan/debrief docs + CHANGELOG; stale docstrings reference the dropped params. → **FR-013** docs + comment hygiene.
- **carla (template)**: `src/doctrine/templates/checklist-template.md` inherits "Feature" boilerplate — pre-existing template drift, NOT introduced here → file a separate doctrine ticket, out of scope for this mission.

## Positive confirmations
- All four #2873 items fully closed, none dropped (carla, item-by-item).
- The 13-symbol deletion list is complete + safe; the keep-live list correct and even stronger than stated (paula). Golden count `156→155` verified correct. No other gate scans the deleted symbols.
- The `GateCoverageScopeSource`-only correctness fix does NOT narrow the baseline (C-005 holds by construction); `NFR-001`'s "byte-identical" is legitimately backed by a captured golden (not a #2871-style "by construction" overclaim).

## Carried into plan
- data-model must name: the `BaselineTestResult` source-identity field (parse-mode) + `from_dict` default; the `SOURCE_MISMATCH` outcome + its verdict shape; the shared factory module + seam home; the two independent predicates + the ABC/mixin.
- WP-level tests: the artifact-before-teardown proof, the dual-impl/dual-parse-mode parity (FR-010), the override-tier golden (NFR-006), the pre-deletion audit (FR-002), the anti-narrowing guard (FR-012), the synthetic split-predicate source (US3 AS3), the 8-test migration (FR-004).
