# Issue Matrix: 3.2.0a6 Tranche 2

**Mission**: `release-3-2-0a6-tranche-2-01KQ9MKP`
**Branch**: `release/3.2.0a6-tranche-2`
**Baseline**: `daaee89596fafb9919d831e1c8c1fce284b2ba27`
**Generated**: 2026-04-28 (post-merge backfill)

This matrix documents the disposition of every GitHub issue in the tranche-2
scope. Each row maps an issue to the WP that delivered the fix, the test(s)
that verify it, and a verdict.

Verdict legend (per `spec-kitty-mission-review` Gate 4 schema):
- `fixed` — issue resolved by code changes in this mission with verifying tests
- `verified-already-fixed` — issue was already fixed before this mission; this mission added verification
- `deferred-with-followup` — issue intentionally deferred; documented follow-up exists

---

## Matrix

| Issue | Title | WP | FR(s) | NFR(s) | SC | Verdict | Verifying tests |
|-------|-------|----|-------|--------|----|---------|-----------------|
| #840 | `spec-kitty init` must stamp `schema_version` and `schema_capabilities` | WP01 | FR-001, FR-002 | NFR-008 | SC-001 | `fixed` | `tests/integration/test_init_schema_stamp.py`; `tests/e2e/test_charter_epic_golden_path.py` |
| #842 | `--json` commands must emit strict JSON regardless of SaaS state | WP02 | FR-003, FR-004 | NFR-001 | SC-002 | `fixed` | `tests/integration/test_json_envelope_strict.py` (4 SaaS states × covered commands) |
| #833 | Colon-format `--agent` strings preserve `tool:model:profile:role` | WP03 | FR-005, FR-006, FR-007 | NFR-004 | SC-003 | `fixed` | `tests/unit/test_wp_metadata_resolved_agent.py` (arities 1/2/3/4 + empty segments); `tests/integration/test_agent_identity_prompt.py` |
| #676 | Review-cycle counter advances only on real rejections | WP04 | FR-008, FR-009, FR-010 | NFR-005 | SC-004 | `fixed` | `tests/unit/test_review_cycle_counter.py`; `tests/integration/test_review_cycle_rejection_only.py` (≥3 reclaim/regenerate runs without drift) |
| #843 | `spec-kitty next` writes paired profile-invocation lifecycle records | WP05 | FR-011, FR-012 | NFR-006 | SC-005 | `fixed` | `tests/integration/test_lifecycle_pairing.py`; `tests/integration/test_next_lifecycle_records.py`; orphan visibility via `doctor invocation-pairing` |
| #841 | `charter generate` and `charter bundle validate` agree on tracked `charter.md` | WP06 | FR-013, FR-014, FR-017 | (covered by integration test) | SC-006, SC-007 | `fixed` (Assumption A1: auto-track) | `tests/integration/test_charter_generate_autotrack.py`; non-git fail-fast path verified |
| #839 | `charter synthesize` works on a fresh project (no hand-seeded doctrine) | WP07 | FR-015, FR-016 | NFR-007 | SC-001, SC-007 | `fixed` (Assumption A2: public CLI fresh-project synthesis) | `tests/integration/test_charter_synthesize_fresh.py`; `tests/e2e/test_charter_epic_golden_path.py` (no longer hand-seeds `.kittify/doctrine/` or hand-edits `metadata.yaml`) |

---

## FR coverage roll-up

All 17 FRs map to at least one test owned by a mission WP. Verified via:

```bash
for fr in FR-001 ... FR-017; do
  grep -rn "$fr" tests/ --include="*.py" -l
done
```

Zero unmapped FRs. See `tasks.md` for the per-WP FR coverage matrix.

## NFR verification

| NFR | Threshold | Status |
|-----|-----------|--------|
| NFR-001 | Strict `json.loads(stdout)` across covered `--json` commands × 4 SaaS states | PASS — parametrised matrix in `test_json_envelope_strict.py` |
| NFR-002 | ≥ 90% line coverage on touched modules | PASS — coverage report in CI |
| NFR-003 | `mypy --strict` zero new errors | PASS — type-check clean across mission diff |
| NFR-004 | Regression tests at all 4 colon-string arities | PASS — `test_wp_metadata_resolved_agent.py` |
| NFR-005 | ≥ 3 reclaim/regenerate runs without counter drift | PASS — `test_review_cycle_rejection_only.py` |
| NFR-006 | ≥ 95% pairing across ≥ 5 actions; orphans observable | PASS — `test_lifecycle_pairing.py` + `doctor invocation-pairing` |
| NFR-007 | Golden-path E2E < 120s on CI | PASS — recent CI runs ~85s |
| NFR-008 | Existing keys byte-identical post-`init` | PASS — idempotency assertion in `test_init_schema_stamp.py` |

## Constraint compliance

| Constraint | Status |
|------------|--------|
| C-001 bug-only tranche (no new product features) | PASS |
| C-002 no direct landing on `main` | PASS — merged into `release/3.2.0a6-tranche-2` |
| C-003 SaaS-touching commands gated on `SPEC_KITTY_ENABLE_SAAS_SYNC=1` | PASS |
| C-006 no new top-level runtime dependencies | PASS |

## Acceptance summary

All 8 success criteria (SC-001..SC-008) met. The seven listed defects are
closed, verified by mission-owned tests, and the consolidated golden-path E2E
no longer requires manual metadata or doctrine seeding.

## Post-merge review follow-up fixes

A second-round adversarial review (2026-04-28, post issue-matrix backfill)
found 3 P1 release-blockers and 3 P2 evidence/coverage gaps that were not
caught by per-WP review. All were fixed in additive follow-up commits on
this branch before tagging:

| ID | Severity | Finding | Fix |
|----|----------|---------|-----|
| #839 follow-up | P1 | Fresh-project intercept excluded `dry_run`, leaving `synthesize --dry-run --json` on a fresh project to fall through to the production adapter and raise `GeneratedArtifactMissingError`. | `charter.py` now reports planned files and exits 0 in fresh + dry-run mode. New regression test `test_synthesize_dry_run_on_fresh_project_does_not_fall_through`. |
| #843 follow-up | P1 | Lifecycle groups keyed only on `canonical_action_id`; two missions issuing the same `mission_state::action` cross-paired and hid orphans. | Group key changed to `(mission_id, canonical_action_id)`. New regression class `TestCrossMissionIsolation`. data-model.md §4 pair-matching rule updated. |
| #833 follow-up | P1 | `_default_profile_for` returned `None` for partial colon strings like `claude:opus-4-7`, contradicting FR-006 ("fall back to default profile_id… with no silent discard"). | Added deterministic synthetic default `f"{tool}-default"` as final fallback. Tests assert non-empty `profile_id` for colon-formatted inputs across arities. data-model.md §2 defaults table updated. |
| JSON matrix | P2 | `_COVERED_COMMANDS` only exercised `mission branch-context --json`. | Expanded matrix to also cover `mission setup-plan --json` and `agent context resolve --json` (24 cases vs 4). |
| Golden-path JSON | P2 | E2E parsed first JSON object then allow-listed trailing SaaS-sync lines, contradicting `json-envelope.md` strict contract. | Replaced with strict `json.loads(stdout)` — any trailing data fails the test. Confirmed E2E still passes (diagnostics correctly on stderr). |
| NFR-006 evidence | P2 | Only test asserted overall pairing 0.7-0.9 (the orphan-injected scenario). | Added `TestNextLifecycleRecordsFullyPairedRun` covering ≥5 paired actions with `compute_pairing_rate >= 0.95`. |

All 73 focused tests for the tranche pass after fixes. The pre-existing 16
failures in `test_advise.py`, `test_do.py`, `test_record.py`, `test_router.py`,
and `test_clean_install_next.py` were verified to fail on baseline (stash test)
and are unrelated to this tranche.

## Out-of-scope items (record only)

The following issues from `start-here.md` were explicitly out of scope for this
tranche and are NOT addressed here. They remain open against their respective
follow-up tracks:

- #771 stale-lane auto-rebase
- #726, #728, #729 intake papercuts
- #303, #662, #595 CI/Sonar/release-readiness
- #260, #253, #631, #630, #629, #644, #323, #317 RC compatibility cleanup
