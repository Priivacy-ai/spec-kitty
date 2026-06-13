# Implementation Plan — name-vs-authority-remediation-01KTYGTE

> **Branch retarget (2026-06-12):** PR #1895's branch (`feat/doctrine-glossary-consolidation-01KTNWFC`) entered review/merge; this mission now lands on `feat/name-vs-authority-remediation-01KTYGTE` (branched from that head). All branch-contract references to the old branch resolve to the new one.


**Branch contract:** planning base = merge target = `feat/doctrine-glossary-consolidation-01KTNWFC` (the PR #1895 draft branch). Flattened topology. PR stays draft until this mission lands.

## Summary

Bind worktree/branch/identity resolution to declared authorities (two seams + a ratchet), close the live 3.2.0 P0s rooted in convention-as-authority (#1884, #1883, #1885-residual), verify-with-proof the already-fixed P0s (#1889, #1885 symptom), and fold the ready items (doctrine deltas #1865–67, the proceduralized authority-path flip, #1863 extractor walk). Invariant: **name proposes, authority disposes.**

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib + existing in-tree surfaces only — `coordination/surface_resolver.py`, `lanes/branch_naming.py`, `mission_runtime` (resolve_placement_only), `acceptance/` gate, `runtime/next/runtime_bridge.py`, DRG extractor (`doctrine/drg/migration/extractor.py`), doctrine YAML schemas; typer (CLI), pydantic (models), pytest/ruff/mypy (gates). No new third-party dependencies.
**Testing**: pytest (focused suites per surface + the new architectural ratchet); rogue-injection strictness proofs for the ratchet; pinning regression fixtures for all four P0s.
**Architecture anchors (binding)**: C4 diagrams (`architecture/diagrams/`), ADR 2026-06-07-1 (mission_runtime canonical surface), ADR 2026-06-03-2 + addendum (CommitTarget/guard), ADR 2026-06-11-1 (Op tier + the authority-path flip procedure executed by IC-10). Research under `research/` — **alphonso's `research-authority-seams.md` is normative** for seam APIs, site lists, and the §Decision-Table.

## Plan-time decisions (all resolved — no open clarifications)

- **D1 seam homes:** topology authority in `coordination/surface_resolver.py` (Execution/Runtime per C4); branch-identity in `lanes/branch_naming.py` (Mission Management) — two cohesive surfaces, NOT a topology god-module (architect adjudication).
- **D2 dual-era rule:** legacy `\d{3}-` and mid8-era names both resolve; only unresolvable-modern rejects (`BranchIdentityUnresolved`, structured).
- **D3 #1889 R3 semantics:** declared coord + worktree absent + branch deleted → distinct loud structured error; composes with #1848's status-transition carve-out; never silent primary fallback (decision table normative).
- **D4 scope fences:** #1844 OUT (C-004); ~20 uncurated DRG orphans OUT (stay on #1863); #1862 deferred.

## Implementation Concerns

| IC | Scope | FRs | Sequencing |
|----|-------|-----|------------|
| IC-01 | ROOT-α quick fix: `is_committed` verifies via `resolve_placement_only(...).ref` (`git cat-file -e`); regression fixture = coord-branch-committed spec | FR-001 | independent, early |
| IC-02 | ROOT-β accept idempotency: snapshot-before-write ordering + accept-owned-path exclusion across all modes; convergence test (run accept twice on unchanged tree) | FR-002 | independent, early |
| IC-03 | #1885 residual: unresolvable handle → structured error (code + next_step) in runtime_bridge | FR-003 | independent, small |
| IC-04 | Verification rows: pinning tests for #1889 (flattened fixture) + #1885 symptom (fully-planned coord fixture); proof recorded; tickets closed with evidence | FR-004 | independent, early |
| IC-05 | Topology authority seam: `WorktreeTopology` enum + `classify_worktree_topology()` + `is_registered_coord_worktree()` (porcelain xref, injectable cached registry); migrate 7 sites | FR-005 | parallel with IC-06 |
| IC-06 | Branch-identity seam: `mission_branch_name_required` + `BranchIdentityUnresolved`; migrate 8 sites (incl. legacy-shape parsers); closes #1860 class | FR-006 | parallel with IC-05 |
| IC-07 | Fabrication eradication: status_transition.py:265 + implement.py:395 route through IC-06's authority or fail closed | FR-007 | after IC-06 |
| IC-08 | Decision-table row R3 (branch-deleted): one `git rev-parse --verify`, distinct error; all consumers via the IC-05 classifier | FR-008 | after IC-05 |
| IC-09 | Doctrine deltas #1865/#1866/#1867 + addenda (drafted in research-fold-cluster §1); DIRECTIVE_018 additive; DRG regen if refs change | FR-010 | independent lane |
| IC-10 | Authority-path flip: the ADR-recorded 7-link chain in ONE WP (resolver default → 2 source prompts → agent-copy regen → 2+3 tests → charter.md → parity baselines → full architectural green); ADR amended append-only to "executed" | FR-011 | independent lane |
| IC-11 | Extractor walk: `_resolve_path_ref()` 6-pattern helper + toolguide schema `references` field + graph regen (+~27 edges); 7 self-healing orphans only | FR-012 | independent lane |
| IC-13 | #1896 parser alignment: peer-field regex tolerates bullets; actionable blocked_reason; pinning test | FR-013 | rides the quick-fix WP |
| IC-12 | Ratchet `test_topology_resolution_boundary.py`: 3 assertions (coord-predicate allowlist; AST unbackstopped-compose scan; zero fabrication idiom); rogue-injection strictness proofs | FR-009 | LAST (after IC-05/06/07) |

## WP shaping guidance (for /spec-kitty.tasks)

Per architect estimate: quick-fix cluster (IC-01..04) = 1–2 small WPs, early and parallel; IC-05 (WP-A, M) ∥ IC-06 (WP-B, M); IC-07 rides or follows WP-B (S); IC-08 after WP-A (S–M); IC-09/IC-10/IC-11 = three independent lanes (S/M/M); IC-12 the closing WP (S) with strictness-proof DoD. Ownership: surface_resolver + its tests (WP-A); branch_naming + 8 consumer sites (WP-B); acceptance/ (idempotency WP); doctrine YAML (IC-09); templates+tests+baselines chain (IC-10); extractor+schema (IC-11). C-002: the two coord-merge-stab shared files only at non-adjacent ranges.

## Charter Check

Charter present (`.kittify/charter/charter.md`). Compliance: ATDD-first honored via pinning-fixtures-before-fix on every defect FR (NFR-004); `__all__` convention (C-007) for all new public symbols; burn-down policy respected (no test deletions); proof-trail via per-WP review evidence + ratchet strictness proofs. No conflicts identified; no charter amendments needed.

## Phase 0 (research)

Pre-completed: four-agent investigation committed under `research/` (p0 root causes, seam design [normative], fold-cluster deltas + chain verification, overlap/sequencing). No open unknowns; D1–D4 close all plan-time questions.

## Phase 1 artifacts

- `data-model.md` — seam types (WorktreeTopology, BranchIdentityUnresolved), the #1889 decision table (normative copy), accept-gate ownership model
- `contracts/authority-seams.md` — seam API contracts + ratchet assertions + gate idempotency contract
- `quickstart.md` — validation walkthrough per FR
