---
work_package_id: WP03
title: End-to-end freshness acceptance + migration + performance
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-007
- NFR-002
- NFR-004
tracker_refs: []
planning_base_branch: gk/2758-2759
merge_target_branch: gk/2758-2759
branch_strategy: Planning artifacts for this mission were generated on gk/2758-2759. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into gk/2758-2759 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
phase: Phase 3 - Acceptance
assignee: ''
agent: ''
history:
- timestamp: '2026-07-17T13:20:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
create_intent:
- tests/specify_cli/charter_freshness/test_activation_freshness.py
- tests/charter/test_freshness_migration.py
execution_mode: code_change
mission_id: 01KXR0M1FQTBPSQ8S2GNM6K7XZ
authoritative_surface: tests/charter/synthesizer/test_performance_envelopes.py
owned_files:
- tests/charter/synthesizer/test_performance_envelopes.py
tags: []
wp_code: WP03
---

# Work Package Prompt: WP03 – End-to-end freshness acceptance + migration + performance

## Objectives & Success Criteria

Prove the mission end-to-end against the operator-facing surface (`charter status` output — state AND
remediation — not exit codes), covering every US1/US2 acceptance scenario, the two migration anchors, the
cross-caller bake, and the latency envelope. All quality gates green.

## Context & Constraints

- Read `spec.md` (US1/US2 AC, SC-001..005) + `data-model.md` (behavior + remediation matrix). Assert against
  `compute_freshness(repo).synthesized_drg.state`/`.remediation` (the API the landed `13caf4ca8` test uses).
- Derive activation ids from the resolver / monkeypatch the resolution seam — never hardcode `default.yaml`.
- New test files (avoid owned-file overlap with WP02): `test_activation_freshness.py`,
  `test_freshness_migration.py`; extend `test_performance_envelopes.py`.

## Subtasks & Detailed Guidance

### T005 — (RED-FIRST) End-to-end acceptance (`tests/specify_cli/charter_freshness/test_activation_freshness.py`)
- **US1**: references.yaml absent at a non-`built_in_only` state → `synthesized_drg` NOT stale; state +
  remediation internally consistent.
- **US2 (the #2759 fix)**: from `fresh`, `charter activate directive <id>` that changes the resolved set →
  `stale` (RED on base — 4-file recipe ignores config; GREEN post-fix); `deactivate` a directive → `stale`.
- **US2 boundary guard**: activate a **paradigm** and a **tactic** (real config byte-change) → stays `fresh`
  (must be `fresh` on BOTH base and post-fix — the false-stale boundary).
- **No-op**: re-activate a resolved directive id / validation-failure / deactivate no-op → unchanged.
- **Drift**: a config with an unresolvable activated stem → `charter status` returns recoverable `stale` and
  does NOT crash; `charter synthesize` surfaces the actionable resolution error (FR-005).
- **Recovery**: directive activation → `stale` → `charter synthesize` → `fresh` (FR-006).
- Commit RED first.

### T006 — Migration anchors + cross-caller bake (`tests/charter/test_freshness_migration.py`)
- **FR-003** (distinct): a pre-#2732 schema-"2" manifest with `bundle_content_hash = None` → `stale` →
  `fresh` after the standard generate→synthesize (legacy-`None` self-heal preserved).
- **FR-007** (distinct): a #2732-era schema-"3" manifest with a real 4-file hash mismatching the new recipe →
  one-time `stale` → `fresh` after a single `synthesize`.
- Confirm `promote()` (write_pipeline.py:685) and `resynthesize` (resynthesize_pipeline.py:205) bake the new
  digest (post-synthesize `stored == current`); confirm `project_drg.py:311` preserves (does not recompute)
  on the `built_in_only` toggle.

### T007 — Performance envelope + roster-stability invariant + quality gates
- Extend `tests/charter/synthesizer/test_performance_envelopes.py::TestNfr002FreshnessComputeUnder2Seconds`
  so the measured `compute_freshness` reaches the **graph-hash branch** (a non-`built_in_only` graph, present
  triad + directives) — i.e. it exercises the new `resolve_synthesis_graph_directives` → `load_doctrine_catalog()`
  cost; assert < 2s. NOTE (see tracer DD-8): the **absent-directives** case is already fast — WP02 added a
  short-circuit in the helper that skips the catalog load when no directives are activated. This T007 test must
  therefore seed a **config with activated directives present** (a non-`built_in_only` graph) so it exercises the
  real catalog-load branch; a config-present read pays one ~1s cold `load_doctrine_catalog()`, which is within the
  charter's <2s CLI NFR. Do NOT add `load_doctrine_catalog` caching (rejected in DD-8: test-isolation + one-shot
  CLI-cold concerns); if a config-present pytest measurement is inflated past 2s by pytest cold-import overhead,
  measure production-representatively (warm the imports first) rather than caching or retry-to-green.
- **Roster-stability invariant (SC-004 second clause).** Add a test that adds a built-in directive **NOT** in
  the project's activated set (monkeypatch the catalog/resolver seam or the doctrine tree) and asserts
  `compute_bundle_content_hash` is **unchanged** — pinning that the digest hashes only the RESOLVED activated
  set, never the full catalog/roster (the invariant the directives-only design rests on; guards against a
  regression that hashes `default.yaml`/catalog content).
- ≥90% diff coverage on new lines (specify_cli-side self-policed per NFR-004).
- `ruff check .` + `mypy --strict` clean (zero new suppressions);
  `pytest tests/architectural/test_no_legacy_terminology.py tests/architectural/test_no_dead_symbols.py` green.

## Validation
- `PWHEADLESS=1 pytest tests/specify_cli/charter_freshness/ tests/charter/test_freshness_migration.py tests/charter/synthesizer/test_performance_envelopes.py -q`
- `ruff check . && mypy --strict src/charter/bundle.py src/charter/compiler.py`
- `pytest tests/architectural/test_no_legacy_terminology.py tests/architectural/test_no_dead_symbols.py -q`

## Dependencies
- WP02.
