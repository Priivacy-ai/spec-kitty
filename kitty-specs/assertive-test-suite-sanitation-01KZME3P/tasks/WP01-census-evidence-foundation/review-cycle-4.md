---
affected_files: []
cycle_number: 4
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T07:30:27Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 cycle 4 independent review — changes requested

Reviewer: Reviewer Renata  
Submission: `7863a9a22` (lane HEAD reviewed at `2fb789b64`)  
Verdict: **CHANGES_REQUESTED**

## Blocking issue 1 — route provenance still fails open

`audit.py:644-670` binds a `RouteMembership` only to an existing route ID and the frozen route's `environment_id`. It does not compare `role`, `required`, `events`, `selector.paths`, `selector.markers`, or `selector.ignores` with authoritative route data. The frozen route schema at `audit.py:728-768` also accepts any well-typed `argv`, `cwd`, `env`, `base_mapping`, and `head_mapping`; it has no verified provenance link to the tracked workflow/job/step or to an explicit local/E2E command authority.

Reproduction: a `full-collection` membership with `role=platform`, `required=false`, `events=[schedule]`, fabricated paths/markers/ignores, and only the real environment ID produced `fabricated_membership_errors=[]`. A wholly invented workload with `argv=[false]`, `cwd=/tmp`, `env={FAKE: 1}`, and fictional base/HEAD mappings produced `fabricated_workload_errors=[]`.

This blocks FR-001/FR-014, T003/T004, the RouteMembership/FrozenWorkloadDAG data model, and the CI-routing contract. Downstream deletion evidence could claim a fabricated owner/selector and still validate.

Required correction:

- Give every frozen route verifiable provenance: tracked workflow file + job/step + source/content hash for CI routes, or an explicit hash-addressed local/E2E command authority.
- Freeze and validate the normalized selector, trigger events, required status, command/`cwd`/environment, and base/HEAD mapping.
- Make candidate and routing-evidence memberships match that authority field-for-field; retain exactly-one-owner enforcement for changed narrow classes.
- Add negative selftests that mutate each provenance field independently and prove rejection. A route ID plus matching environment ID must never be sufficient.

## Blocking issue 2 — base execution evidence is not an exact outcome baseline

`raw/base-full-suite-summary.txt` has only six aggregate lines. It contains no exact nodeid/outcome records, run timestamp, environment ID, raw result/log hash, or per-failure attribution. `base-census.json` is collection inventory and contains zero `outcome` fields, so it cannot fill the gap. The reported outcomes total 37,437 while the census contains 37,444 nodes, leaving seven nodes unaccounted for.

This blocks T003/T006, FR-015, and the later exact known-red/delta comparison. A future deletion could remove or change a specific red/skipped node while preserving aggregate counts and remain undetected.

Required correction:

- Preserve a deterministic compact exact nodeid+outcome set for the healthy prewarmed base run, including explicit non-executed/error attribution so all 37,444 collected nodes reconcile.
- Record exact command, inventory SHA, environment ID, harness-patch state, start/end timestamp, and SHA-256 of the raw result source/log.
- Record each failure/error's phase and attributable node/collection source; keep the raw #3283 bootstrap failure separate.
- Hash the compact outcome artifact from `foundation-summary.yaml` and add selftests/validation that reject aggregate-only, count-mismatched, unknown-node, duplicate-node, and unaccounted-node evidence.

## Campsite constraint

Make the smallest changes that close these two reproduced bypasses, rerun current gates, then freeze WP01's schema. Do not add production APIs, a permanent sanitation test subtree, or more evidence framework. Remove the unused private `_source_matches` helper while touching the auditor.

## Validation evidence

- `audit.py selftest`: PASS, 85/85 checks.
- `audit.py validate base-census.json base-workloads.yaml`: PASS, but both negative provenance probes above also pass, proving vacuity.
- `ruff check audit.py`: PASS.
- `mypy --strict audit.py`: PASS.
- `pytest tests/docs -q -p no:cacheprovider`: PASS, 1,381 passed in 148.58s.
- `git diff --check`: PASS.
- Immutable-base test/config content-equivalence command: PASS.
- Diff scope: PASS; exactly the six WP01-owned evidence files changed; worktree clean.

## WP anti-pattern checklist

1. Dead code: **N/A** — mission-local evidence tooling is explicitly prohibited from production installation; command call sites exist in quickstart/foundation evidence. One unused private helper is called out for removal.
2. Synthetic-fixture test: **PASS** — disposable fixtures execute the real auditor paths.
3. Silent empty return: **PASS** — no undocumented silent-empty exception path found.
4. FR coverage: **FAIL** — exact route provenance and exact before/baseline outcomes are not enforced.
5. Frozen surface: **PASS** — no frozen test/config input changed; content-equivalence is green.
6. Locked decision: **FAIL** — accepting fabricated selectors/commands contradicts the data model's exact-selector/exact-argv contract and T003/T004.
7. Shared-file ownership: **PASS** — all changed paths are WP01-owned with no cross-WP collision.
8. Production fragility: **N/A** — no production path changed.

Exactly one verdict: **CHANGES_REQUESTED**.
