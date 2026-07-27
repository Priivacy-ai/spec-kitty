# Phase 0 Research — Test-Suite Friction Remediation

Read-only mining + a 4-lens pre-spec adversarial squad (planner-priti, reviewer-renata, architect-alphonso, python-pedro), each profile-loaded. Source-verified against `upstream/main` @ a94ac92dd and the tracker.

## D-01 — What is already shipped (do NOT re-scope)
- **Decision**: Exclude CT1 (composite_key ratchet re-key), CT2 (security xfail de-theater), the dead-code scanner rewrite, the #2077 positional-anchor guard, and the tasks.py degod from scope.
- **Rationale**: tracker-confirmed closed/merged 2026-07-12 — #2072, #2073, #2077, #2546/#2556, #2547, #2548, #2308. `tests/adversarial/test_path_validation.py` has zero `pytest.xfail`; `composite_key` is adopted across the gate family.
- **Alternatives considered**: re-running the CaaCS "biggest lever" (dead-symbol scanner replacement) — rejected: already delivered by #2546/#2556; the fresh CaaCS top-2 rows are historical tax, not remaining work.

## D-02 — The one true sequencing dependency (NFR-001)
- **Decision**: IC-01 (#2559 dead-code gate dynamic-access awareness) lands before IC-02 (#2561 delegate deletion) and IC-03 (#2293 burndown).
- **Rationale**: architect-alphonso + python-pedro converged — with the `module.attr` blind spot open, the gate cannot distinguish a repointed-and-now-dead delegate from a still-live façade; deletions fall back to fragile manual grep + allowlist. Fix the gate first → it becomes the automated proof of deletion safety.
- **Alternatives considered**: delete first + hand-allowlist — rejected: re-creates the exact debt #2559 exists to kill.

## D-03 — #2564 is a real, still-open P1 (not closed by the #2077 guard)
- **Decision**: Treat #2564 as in-scope P1 (IC-04).
- **Rationale**: source-verified OPEN. The #2077 guard `test_ratchet_positional_anchor_ban.py` landed, but #2564 is the residual **seed-tuple laundering** hole in it — a raw `(rel, N)` tuple laundered through a loop var into `composite_key` evades the int-to-line-sink detector. Vector confirmed present in `test_no_write_side_rederivation.py` / `test_trio_seam_only.py`.
- **Alternatives considered**: close as done — rejected: the guard covers direct positional anchors, not the laundering vector.

## D-04 — #2463 is UNSAFE to delete now → routed out
- **Decision**: Route #2463 to #1797 as its own sentinel-disambiguation slice; NOT in this mission.
- **Rationale**: unanimous (priti/pedro/alphonso). The empty-mid8 `""` sentinel conflates 3 meanings; meaning-2 (modern meta-less/no-coord/post-merge recording) is LIVE (`branch_naming.py:428` vs `:437`, consumed `status_transition.py:402`); 5 live callers; ~51 test files pin it; tests must be *split*, not bulk-deleted (the "flip-tests hide regressions" landmine that had #2463 HELD).
- **Alternatives considered**: fold as a quick delete — rejected: not dead, not safe, forces a split that would blow the mission's size.

## D-05 — Cluster A sits on already-clean units → fix directly (no degod)
- **Decision**: #2076/#2075/#2074/#2553/#2295 are fixed in place; #2603/#2604/#2465 degods are routed out.
- **Rationale**: the actual remaining Thread-A targets do not touch the god-surfaces (`next_step`, `_mt_commit_wp_file`, `workflow.py` resolver); the CaaCS overlap that would justify inlining a degod does not materialize. The next-loop/tasks integration tests are high-co-change *by design* (health, not smell).
- **Alternatives considered**: interleave targeted degod — rejected: no test-rewrite in scope exercises those surfaces.

## D-06 — Thread-B follow-ups are real and unfiled → filed as #2621/#2622/#2623
- **Decision**: File the three PR #2609 "Known follow-ups" as new sub-issues of the mission; deliver as Cluster B (IC-10/11/12).
- **Rationale**: architect-alphonso confirmed each: (B1) `tests/_next_shard_map.py:150` import-time mutation → bare `KeyError` + silent unmarked `tests/next`; (B2) `slow-tests`/`mutation-testing`/`sonarcloud` absent from `quality-gate.needs` by convention only; (B3) `coverage-ui-e2e.xml` never enters Sonar's denominator (same-workflow artifact discovery only).
- **Alternatives considered**: separate mission (priti's option) — operator chose in-mission fenced cluster.

## D-07 — Split-out items
- **Decision**: #2309 (product bug → red-first bugfix mission), #2342 (perf), #2323 (baseline-count churn) leave the test-hygiene framing.
- **Rationale**: #2309's daemon-reaper kill-gate contract is a *product* defect, not scaffold; #2342/#2323 are not "fixable friction" per the audit's own counterweight.

## Non-fakeable DoD anchors (carried into contracts/)
- Ratchet re-key: `test_ratchet_positional_anchor_ban.py` green on the real tree AND `git grep -E '\.py", *[0-9]{3}\)'` in `tests/architectural/` = 0.
- Factory: output `meta.json` byte-identical (minus overrides) to a direct `create_mission_core()` call; `tests/_factories/__init__.py` non-empty with ≥1 real importer.
- CT4 re-point: assertion on a persisted artifact, no `@patch` on the SUT.
- CT5: assertion on the exact `Lane` frozenset.
- Deshim delete: dead-code gate green post-delete AND `git grep <symbol>` = 0 across `src` and `tests`.
