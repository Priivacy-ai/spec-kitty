---
affected_files: []
cycle_number: 1
mission_slug: supply-chain-security-checks-layer-01KZBFBS
reproduction_command:
reviewed_at: '2026-08-06T20:29:04Z'
reviewer_agent: user
verdict: rejected
wp_id: WP02
---

# WP02 Review — Cycle 1 — Changes Requested

## Verdict: REQUEST CHANGES

All wiring is correct (action indexes, action-graph scope edges, step-contract
security stages, advisory-gate compatibility all verified against the diff and
pass every existing test — see checklist below). The block is a missing test
obligation the WP itself committed to.

## Blocking issue

**Issue 1 — No dedicated regression test for the new wiring; only golden-count
literal bumps.**

The WP's own "Test Strategy" and "Risk & Mitigations" sections commit to:
- "Targeted doctrine/contract tests validating action and step-contract resolution."
- "Focused assertions that transition gate semantics remain advisory-compatible."
- Mitigation for the "accidental hard-gate behavior" risk: "add tests asserting
  no new fail-closed handler path."

None of these were delivered. Every test file touched by this WP's commit
(`68ea6c70e`) is a golden-count literal bump (`_EXPECTED_EDGE_COUNT`,
`EXPECTED_EDGE_COUNT`, `326/906`, etc. in `tests/doctrine/drg/migration/test_extractor_projection.py`,
`tests/doctrine/drg/test_unknown_kind_fails_loudly.py`,
`tests/doctrine/test_loader_fail_closed.py`,
`tests/doctrine/test_pack_relocation_*.py`,
`tests/doctrine/test_packaging_parity.py`,
`tests/doctrine/fixtures/graph-identity.baseline.json`). These are well-documented
and legitimate (they correctly re-baseline after the 6 new `scope` edges), but
they only pin *cardinality*, not *content*. A bug that wired the new tactic to
the wrong action, or swapped `directive:DIRECTIVE_047` for a different directive,
while keeping the same total edge count, would sail through this suite unnoticed
(anti-pattern checklist item #2, synthetic-fixture risk).

Grep confirms zero references to this WP's own `requirement_refs`
(`FR-004`, `FR-005`, `FR-009`) anywhere in the commit's tests, and the mission-level
`FR-008`/`NFR-004` ("New or updated tests ... demonstrate red-to-green behavior
for at least one action-index wiring path, one step-contract wiring path...")
is not satisfied by this WP's test changes.

**This codebase already has the exact pattern needed** —
`tests/doctrine/missions/test_action_indexes.py::test_review_action_index_includes_living_documentation_sync`
is the template to extend/mirror.

### Suggested fix (please add, then move back to for_review)

1. In `tests/doctrine/missions/test_action_indexes.py`, add assertions (mirroring
   the existing `living-documentation-sync` test) that `plan`, `implement`, and
   `review` action indexes each include `"047-supply-chain-install-safety"` in
   `directives` and `"supply-chain-install-safety"` in `tactics`.
2. In `tests/doctrine/mission_step_contracts/test_shipped_contracts.py` (or a new
   sibling test module), add:
   - A parametrized assertion that each of the `plan`, `implement`, `review`
     step contracts contains a step whose `delegates_to.candidates` includes
     `"supply-chain-install-safety"`.
   - An ordering assertion for `implement.step-contract.yaml`: the index of the
     `supply_chain_security_check` step is strictly less than the index of the
     `quality_gate` step (this is the "must precede quality-gate semantics"
     requirement from the WP prompt and the contract's Rule 4).
   - An advisory-compatibility assertion: `review.step-contract.yaml`'s `gates`
     block is unchanged (`on_transition == "in_progress->for_review"`,
     `fail_open is True`), and `plan.step-contract.yaml` /
     `implement.step-contract.yaml` have no `gates` key at all. This directly
     covers the WP's own promised mitigation and contract Rule 5.

## Acceptance-criteria checklist

| # | Criterion | Result |
|---|-----------|--------|
| 1 | plan/implement/review action indexes reference `047-supply-chain-install-safety` + `supply-chain-install-safety` | PASS |
| 2 | `action.graph.yaml` has new `scope` edges for the three actions → directive + tactic | PASS (6 new edges confirmed: 2 per action × 3 actions) |
| 3 | plan/implement/review step-contracts each include an explicit security stage; implement's precedes quality-gate | PASS |
| 4 | No new fail-closed transition gate handler introduced; review's `in_progress->for_review` gate remains `fail_open: true`; plan/implement have no gate block | PASS |
| 5 | DRG/golden-count baseline files updated consistently and match live shipped graph | PASS (all touched tests green; counts internally consistent: 778/906, scope 159→165) |
| 6 | Tests added/updated are meaningful (not just literal-count bumps) and green | **FAIL** — see Issue 1 above; tests are green but are exclusively literal-count bumps |
| 7 | No changes outside WP02's owned scope (WP01/WP03/WP04/WP05 owned files untouched) | PASS — WP02's own commit (`68ea6c70e`) does not touch profiles, `agent_profile.graph.yaml`, directive/tactic content, or SOURCE mission-step prompts. (Shared golden-count files — `docs/architecture/doctrine-relationships.md`, `src/doctrine/drg/models.py`, `tests/doctrine/fixtures/graph-identity.baseline.json`, and the golden-count test files — are also touched by WP01's commit in this same diff range, but WP02's re-baseline is a necessary, well-documented consequence of the 6 new edges it legitimately owns, following the established projection-ledger convention: not a scope violation.) |
| 8 | Terminology canon compliance (no `feature`/`ceremony` in touched prose) | PASS (spot-checked added lines only; zero hits) |

## Anti-pattern checklist (WP-level)

1. Dead code — N/A (no new production functions; pure YAML wiring)
2. Synthetic-fixture test — **FAIL** (see Issue 1: golden-count tests would not catch a content-swap bug)
3. Silent empty return — N/A (no new code paths)
4. FR coverage (FR-004, FR-005, FR-009) — **FAIL** (no test references these FRs; coverage is indirect via golden counts only)
5. Frozen surface — PASS (no frozen files touched)
6. Locked decision — PASS (no `MUST NOT` clause violated; advisory-only preserved)
7. Shared-file ownership — PASS, with note above (golden-count files shared with WP01; re-baseline is additive and consistent, ledger entry (16) documents the delta explicitly)
8. Production fragility — N/A (no new `raise` in a production path)

## Tests run (this review)

- `uv run pytest tests/doctrine -q` → **2572 passed, 8 skipped** (exit 0)
- `uv run pytest tests/doctrine/mission_step_contracts/test_shipped_contracts.py tests/doctrine/missions/test_action_indexes.py tests/specify_cli/mission_step_contracts/test_software_dev_composition.py tests/doctrine/test_relation_doc_parity.py -q` → **64 passed** (exit 0)
- `uv run ruff check <each changed .py file>` → all "All checks passed!" (exit 0 each)
- `uv run pytest tests/architectural/test_no_legacy_terminology.py -q` → **10 passed** (exit 0)

## Action for implementer

Add the three focused tests described above (action-index content, step-contract
ordering, advisory-gate preservation), confirm they fail on the pre-WP02 baseline
(red) and pass on this branch (green), then move WP02 back to `for_review`.
