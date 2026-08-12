---
affected_files:
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP10.yaml
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp10-results.json
  - tests/architectural/test_guard_capability_call_sites.py
  - tests/architectural/test_dossier_sync_boundary.py
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: .venv/bin/pytest -q -p no:cacheprovider <42 surviving owned test paths>
reviewed_at: '2026-08-10T15:53:20Z'
reviewer_agent: reviewer-renata
wp_id: WP10
---

# WP10 review cycle 1 — changes requested

Reviewed implementation commit `b7cf68425` independently against WP10, FR-003/FR-006/FR-007/FR-008/FR-014/FR-016, and the disposition/evidence contracts.

## Blocking findings

1. **The survivor and deletion evidence is not deep, path-bound, or replayable.** `WP10.yaml` has 12 deep rows, all `DELETE`; its 42 survivors exist only as terse strings in `terminal_screening`. The 12 materially changed survivor files therefore have no required deep `KEEP` row at all. `wp10-results.json` lists only eight unbound family summaries: they carry no exact member/path mapping, named current authority, live corpus count, mutation bytes/materialization command, exact node command, red output, restoration proof, or raw artifact. Both shared deletion evidence anchors point `raw_artifact_hash` at the summary JSON itself, not a retained mutation execution. The 12 deletion rows also reuse two generic prose probes with empty `production_paths`, null oracles/contracts, and no named live consumer/survivor mapping. This cannot prove the behavioral cases deleted from `test_cross_seam_consumers.py` and `test_wp03_bypass_writers_fr008.py` have no unique input/oracle boundary. Add deep rows for every materially changed/deletion-justifying survivor and bind every terminal KEEP path to a node or genuinely equivalent family. Families may group only identical production path, authority, corpus, oracle, and fault. Retain content-addressed replay records with exact base, mutation, command, exit/output, restore, and restored-green proof. For each deleted behavioral family, name and execute the real stronger survivor or restore the unique cases.

2. **Several claimed “two-sided” faults test only a classifier, not the retained oracle.** `test_guard_capability_scanner_has_two_sided_fault_bite` writes `GuardCapability.STANDARD`/`TEST_MODE` and only asserts which enum token the AST helper returns; it never drives `_PROTECTED_FLOW_ALLOWLISTS` or proves the retained allowlist assertion reds for a non-authority path. `TestDossierSyncBoundary.test_import_scanner_has_two_sided_fault_bite` similarly repeats the `startswith("specify_cli.sync")` filter instead of invoking the same enforcement callable as the live gate. Those probes can remain green while the actual enforcement is broken and do not satisfy the explicit no-literal-paste/no-scanner-self-test rule. Factor each live oracle into one callable, drive compliant and prohibited live-shaped corpora through that exact callable, and retain the replay evidence described above. Audit the other six summarized families to the same standard.

## Verified positives

- Exact ownership screening: all 54 owned test paths are present exactly once in the terminal map; 12 delete and 42 survive.
- Implementation diff: 12 whole test files deleted, 199 test-line insertions / 6,629 deletions, net `-6,430` test LOC; no production file or central shard-map edit.
- Recorded census delta is internally exact: `841 -> 537` (`-304`); deleted path handoff is deterministic. Fresh independent HEAD replay: `535 passed, 2 xfailed` across all 42 survivors.
- Fresh Ruff and focused mypy pass for all 12 changed Python survivors; `git diff --check` and WP01 validator pass.
- The apparent missing WP09 baseline file in a live symbolic-base diff is later mission-branch drift, not a WP10 implementation edit; no ownership finding is raised for it.

## WP anti-pattern checklist

1. Dead code: **N/A** — no production API added.
2. Synthetic-fixture test: **FAIL** — classifier-only/literal probes do not execute the retained enforcement oracle.
3. Silent empty return: **N/A** — no production path added.
4. FR coverage: **FAIL** — 42 survivors, including 12 materially changed files, lack required bound/replayable causal proof; deleted behavioral families lack executed survivor equivalence.
5. Frozen surface: **PASS** — implementation commit changes only owned files; central map remains untouched.
6. Locked decision: **PASS** — no product code path contradicts a locked `MUST NOT` clause.
7. Shared-file ownership: **PASS** — implementation commit has no outside-owned/shared-file edit.
8. Production fragility: **N/A** — no production `raise` added.

Verdict: **CHANGES REQUESTED**. Preserve the achieved deletion count unless evidence proves a unique boundary must be restored.
