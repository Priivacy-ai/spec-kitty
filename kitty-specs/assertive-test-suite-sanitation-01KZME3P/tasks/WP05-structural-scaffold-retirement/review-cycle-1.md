---
affected_files:
- tests/architectural/test_no_parity_scaffold.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP05.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp05-results.json
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: .venv/bin/python -c "behavior-preserving resolved_mission_type local rename probe"
reviewed_at: '2026-08-10T10:32:23Z'
reviewer_agent: reviewer-renata
wp_id: WP05
---

# WP05 Review — Cycle 1

## Verdict

Changes requested. Deletion/count accounting is internally consistent and focused validation is green, but the retained structural surface and causal evidence do not yet satisfy WP05's non-vacuity contract.

## Issue 1 — Retained guard still pins behavior-preserving source shape

`tests/architectural/test_no_parity_scaffold.py::_is_exact_typeless_legacy_guard` requires the local identifier to be exactly `resolved_mission_type`. Renaming that local consistently to `resolved_context` preserves `_resolve_plan_template` behavior, leaves both `resolve_template("plan-template.md")` and `resolve_configured_template("plan")` calls intact, but the guard returns `False`; therefore `test_plan_legacy_selector_is_confined_to_typeless_compatibility_branch` fails on a behavior-preserving rename. The file also retains exact private-function/call-shape assertions and synthetic helper tests while its disposition calls it a live negative invariant.

This violates the Structural Survival Rule. Replace the exact local-name/AST-shape oracle with a production-path behavioral probe that proves configured resolution for typed missions and legacy resolution only for typeless missions, or delete the dominated shape guard if existing behavioral coverage already proves that contract.

## Issue 2 — Survivor family evidence is not a valid family proof

`wp05-results.json` assigns 28 retained files to six broad `proof_family` labels, but those groups combine different production paths, authorities, oracles, outcome classes, and faults. The generic family row supplies no exact corpus size, member list, node-level observation, executed command/result, or equivalence dimensions.

Add node-level survivor evidence or split survivors into genuinely equivalent families. Record exact nonzero corpus sizes, production symbols/callers, authority, actual realistic fault, Act/assertion result, command, and raw artifact for every survivor/family.

## Issue 3 — Deletion causal probes are asserted, not executed

All seven disposition probes use the same `raw_artifact_hash`, merely the hash of the hand-authored summary. Several commands cannot enact or observe their claimed fault. No raw output/patch identity demonstrates the behavior-preserving change, planted fault, red oracle, or restored green control.

Capture real two-sided probes in disposable copies/worktrees, hash raw command output/patch artifacts, and make each disposition's command reproduce its stated fault and oracle result.

## Verified Gates

- Frozen census/workload + WP05 disposition validation: valid; 7 dispositions, 39 unique members, zero errors.
- Terminal screening coverage: 35/35 owned test files; no missing/extra paths.
- Independent node accounting: 54 removed nodes = 41 nodes from seven deleted files + 13 removed assertions/parametrizations in retained files.
- Diff-scoped Ruff: passed.
- Focused retained cohort command: exit 0.
- Ownership: implementation diff touches only WP05-owned files; no product source or central shard-map edit.

## WP Anti-pattern Checklist

1. Dead code: N/A — no new production API/module.
2. Synthetic-fixture test: **FAIL** — retained scaffold helper tests validate synthetic AST shapes and exact local identifiers rather than production behavior.
3. Silent empty return: N/A — no production code change.
4. FR coverage: **FAIL** — FR-006/FR-007 structural survival and causal-proof requirements are not demonstrated for retained files.
5. Frozen surface: PASS.
6. Locked decision: **FAIL** — retained exact source-shape guard contradicts the mission's behavior-preserving-refactor survival rule.
7. Shared-file ownership: PASS.
8. Production fragility: N/A — no production code change.
