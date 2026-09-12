---
affected_files:
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/audit.py
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/foundation-summary.yaml
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/base-full-suite-summary.txt
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/base-workloads.yaml
cycle_number: 5
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: see commands below
reviewed_at: '2026-08-10T09:14:42Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 cycle 5 independent review — changes requested

Reviewer: Reviewer Renata
Submission: `527012138` (lane HEAD `7b07a3b9e`)
Verdict: **CHANGES_REQUESTED**

## Blocking issue 1 — a new/renamed route ID bypasses the frozen authority

The committed route IDs are pinned, and the tracked CI git-object checks work for those IDs. However, `validate_workload()` only applies `FROZEN_ROUTE_AUTHORITY_HASHES` when `route.id` is already present in that mapping. An unknown ID falls back to a self-computed `authority_sha256`. Therefore the original fabricated-owner bypass remains available by adding or renaming a route.

Two independent probes returned `errors=[]`:

1. A wholly invented `fabricated-owner` frozen-command route with `argv=[false]`, `cwd=/tmp`, `env={FAKE: 1}`, fictional base/HEAD mappings, matching synthetic membership, the primary inventory SHA, and a recomputed projection hash.
2. The real tracked `regression` route renamed to `fabricated-regression`, with its projection hash recomputed.

Because downstream candidate memberships need only match a route present in the submitted workload, either fabricated route can become the exactly-one `owner` authority for a deletion. This still blocks FR-001/FR-014 and T003/T004.

Required correction:

- Freeze and validate the complete base route universe, including route IDs. Reject unknown/renamed IDs in the base workload.
- If later HEAD routes must be introduced, require a separate explicit immutable authority (tracked git object plus locator/hash) rather than accepting a self-signed `frozen_command` projection.
- Add negative selftests for a wholly invented local owner route and a renamed tracked-CI route, with every self-hash recomputed. Both must fail for an authority reason.
- Retain the current field-for-field membership checks and tracked workflow/job/step verification; those passed independent mutation probes for known IDs.

## Blocking issue 2 — exact outcomes are self-signed, not bound to the raw run

The committed artifact positively contains 37,444 unique census identities, 9 explicit `not_run` exclusions, and 3 supplemental teardown errors. Its command/environment fields match the frozen `full-parallel` route, timestamps are present, and the foundation summary records its file hash. But `validate_base_execution()` validates only structure plus a recomputable `content_sha256`; it does not verify the raw event source or a non-self authority for the compact result.

After mutating each document and recomputing `content_sha256`, every probe returned `errors=[]`:

- replace `raw_result_sha256` with `000...000`;
- replace `raw_result_path` with `fabricated`;
- remove all 3 `phase_errors`;
- change `exit_code` from 1 to 0 despite 27 failed outcomes;
- rewrite both timestamps;
- replace a real failed nodeid with an arbitrary census-passed nodeid and rewrite its detail row.

The raw event is declared `external-untracked`, and the normalized compact record contains only `<TEMP_ROOT>`, so none of these changes can be checked against the source run. The supplied census is likewise accepted by file hash computed at validation time; the compact result is not pinned to the committed 37,444-identity artifact by an external authority. This blocks T003/T006 and any later NFR-004 exact known-red delta.

Required correction:

- Bind the compact result and the exact committed census to non-self authority: either validate against a durable raw event artifact, or pin/cross-validate their expected file/content hashes from a separately validated frozen manifest.
- Make the raw result reference resolvable/durable, or explicitly pin its captured SHA in the validator's frozen authority.
- Derive/reconcile outcome identities, phase errors, timestamps, command/environment, and exit status from that authority. Enforce unique phase records and exit/outcome consistency.
- Add negative selftests for raw SHA/path, timestamp, exit-code, phase-error removal/duplication, and failed-identity substitution with all self-hashes recomputed.

## Campsite constraint

Keep the next diff limited to these reproduced fail-open paths. Do not grow another evidence layer. Once these probes fail and the existing positive gates remain green, freeze WP01's schema.

## Validation evidence

- `audit.py selftest`: PASS, 140/140 reported checks.
- `audit.py validate base-census.json base-workloads.yaml base-full-suite-summary.txt`: PASS.
- `ruff check audit.py`: PASS.
- `mypy --strict audit.py`: PASS.
- `git diff --check`: PASS.
- Cycle-5 scope: PASS; exactly four WP01-owned files changed in `527012138`.
- `_source_matches`: removed.
- Route-ID fabrication probes: FAIL (both invalid workloads accepted).
- Exact-run tamper probes: FAIL (all six invalid compact records accepted).

## WP anti-pattern checklist

1. Dead code: **N/A** — mission-local tooling is intentionally not installed; the previously unused `_source_matches` helper is gone.
2. Synthetic-fixture test: **PASS with coverage gap** — selftests invoke real validator paths, but omit unknown-route/self-resigned exact-run attacks.
3. Silent empty return: **PASS** — no new undocumented silent-empty exception path found.
4. FR coverage: **FAIL** — fabricated owner routes and substituted exact outcomes remain valid.
5. Frozen surface: **PASS** — cycle 5 changes only four WP01-owned evidence files.
6. Locked decision: **FAIL** — self-signed unknown routes and exact outcomes contradict immutable base and exact-selector/outcome contracts.
7. Shared-file ownership: **PASS** — no cross-WP path collision in the cycle-5 commit.
8. Production fragility: **N/A** — no production path changed.

Exactly one verdict: **CHANGES_REQUESTED**.
