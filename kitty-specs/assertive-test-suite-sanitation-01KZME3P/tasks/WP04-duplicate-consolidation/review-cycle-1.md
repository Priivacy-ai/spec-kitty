---
affected_files:
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP04.yaml
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp04-results.json
  - tests/
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: 'See Independent verification below.'
reviewed_at: '2026-08-10T10:41:00Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP04
---

# WP04 — CHANGES REQUESTED

The consolidation itself is directionally sound: the authoritative WP01 census has exactly 82
WP04-owned groups and the shard carries exactly those 82 fingerprints; the net collected-node
reduction is independently reproducible as 104; the retained runtime-home, public-import, and
Windows/path seams exercise live production surfaces. The package is not mergeable because its
ledger and causal evidence do not account for the changes they certify.

## HIGH-1 — 51 removed test definitions have no ledger row

AST comparison over the 29 changed test paths finds 110 source test definitions removed and six
added. The 59 names in `deleted_members` match 59 of those removals exactly, leaving **51 removed
definitions absent from the ledger** while `promoted_semantic_groups` says `0`. Examples include
large semantic reductions in `tests/agent/glossary/test_primitives.py` and
`tests/runtime/test_home_unit.py`; these are not members of the mechanically exact groups.

This violates FR-014, NFR-002, T025, and the definition of done. The reported 104 is the **net**
change (110 removed minus six added), not complete deletion accounting.

Required:

- Add every one of the 51 removals to a promoted semantic family/member row, with family basis,
  production path, oracle, route roles, platform/boundary, named survivor, and terminal verdict; or
  restore it.
- Reconcile `promoted_semantic_groups` and separately report gross removed, added, and net nodes.
- Re-run the WP01 validator after the promoted families are included.

## HIGH-2 — KEEP divergence and route membership are not represented

All 25 KEEP rows say their members differ by input, boundary, platform, route, or production seam,
yet every row has `divergent_dimensions: []`. The whole shard records 82 observations for 168
members—one observation per group, including two- to four-member KEEP groups. This cannot prove the
claimed unique cases. For example, fingerprint `0aadb...` combines generic and Windows unsafe-name
cases, and `181bb...` combines distinct coercion boundaries, but neither expands the divergence.

Every one of the 82 rows also records only `full-parallel`. The frozen workload DAG gives all tests
`full-collection` plus `full-parallel`, with additional `architectural` and `contract` memberships
where applicable. Architectural fingerprints such as `074da...`/`60055...` and contract fingerprint
`181bb...` therefore have incomplete route evidence.

This violates FR-014, NFR-010, T025, and research decision R2.

Required:

- Expand divergent KEEP members to node-level observations and populate the actual divergent
  dimensions.
- Derive every applicable route/role/environment/required membership from WP01's frozen workload
  DAG; do not stamp a single route onto every group.

## HIGH-3 — the claimed causal proof is self-referential and covers only five probes

All 82 ledger rows cite the same SHA-256, `57716eb...`, which is the hash of
`raw/wp04-results.json` itself, and all use the placeholder command
`.venv/bin/pytest -q <WP04 focused survivors>`. That JSON contains summaries for only five actual
probes and no executable command/output receipt per deletion family. Generic fault text of
`forbidden behavior at authority for group <fingerprint>` does not demonstrate that Act executed or
that a survivor failed for the intended oracle.

The two DELETE groups (`80510e...`, `d06b...`) name no survivor, although their evidence still claims
the survivor fails. That is internally impossible.

This violates T024, NFR-002, and NFR-007.

Required:

- Supply executable fault/mutation receipts for every source cluster claimed by deletion, including
  exact command, production perturbation, candidate/survivor nodeids, Act-reached proof, intended
  failing oracle, result, and hash of the raw receipt—not the manifest containing the assertion.
- Family evidence is acceptable only where path, oracle, input boundary, platform, and outcome are
  identical; otherwise expand to nodes.
- For delete-all families, name the real replacement survivor or record the distinct reason no
  survivor is required; never claim a null survivor failed.

## HIGH-4 — the before/after run and skipped pre-review gate are not reproducible

The artifact reports 831→727 nodes and 829/725 passed with two skips, but records no exact selection
or raw pytest output. Independent collection of the 29 changed paths is 706 WP01 base-census nodes
versus 602 current nodes, again a 104-node delta, so the reduction is credible but the artifact's
831/727 cohort is unidentified. The two current skips are expected Windows-only nodes:

- `tests/review/test_baseline.py:360`
- `tests/runtime/test_home_unit.py:41`

The durable transition event says the pre-review gate was skipped via
`--skip-pre-review-gate`; `baseline-tests.json` says only `no JUnit XML artifact produced by scoped
run`. Neither artifact records a timeout command, duration, or output, despite the handoff claiming
a timeout.

Required:

- Record the exact before/after path/node selection, environment, command, raw output, and named
  skips so 831→727 can be reproduced—or replace it with the reproducible cohort.
- Run the canonical pre-review gate, or attach a durable timeout receipt with exact command,
  configured timeout, elapsed duration, and captured output. Do not describe “no JUnit artifact” as
  a proven timeout.

## Independent verification

- WP01 census reconciliation: 82 expected / 82 present / zero missing / zero extra.
- WP01 validator with authoritative census/workloads: valid, 82 dispositions, 168 members.
- AST change audit: 110 removed, six added, 59 ledgered removals, 51 unledgered, net -104.
- Changed-path collection: 706 base-census nodes / 602 current nodes; delta -104.
- Changed existing files: `600 passed, 2 skipped, 3 warnings in 51.36s`.
- Full WP04 owned existing-file cohort: `1348 passed, 6 skipped, 3 warnings in 68.78s`.
- Ruff over changed Python paths: all checks passed.

## Anti-pattern checklist

1. Dead-code promotion: PASS — no production code added.
2. Synthetic-fixture replacement: PASS for retained compatibility tests; live imports/delegates run.
3. Silent empty production return: N/A.
4. Functional-requirement coverage: **FAIL** — FR-014/NFR-002/NFR-007 proof incomplete.
5. Frozen-surface changes: PASS — no production/workflow frozen surface changed.
6. Locked-decision compliance: **FAIL** — R2/T024/T025 evidence lacks member divergence and causal receipts.
7. Shared-file ownership: PASS — diff confined to WP04-owned paths/artifacts.
8. Production fragility: N/A — test-only change.

After these four findings are discharged, rerun the focused suite, validator, lint, and canonical
pre-review gate. This is review cycle 1 of at most 3.
