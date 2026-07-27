---
affected_files: []
cycle_number: 1
mission_slug: org-pack-subdir-and-doctrine-qol-01KVSRJ6
reproduction_command:
reviewed_at: '2026-06-23T10:22:38Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-06-23T10:36:37Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "Cycle-2 APPROVED (reviewer-renata); --force=flatten lane-currency, --skip-review-artifact-check=cycle-1 reject resolved in cycle 2 (e8098cbb5)"
---

# WP02 Review Feedback — Cycle 1 (reviewer-renata, REJECT)

The consumer-adoption core (the load-bearing SC-001 doctor-health fix, 9 sites through `effective_root`, `config.py` normalizer retired, exception re-raised, C-003 clone target intact) is **correct and well-tested**. Two CRITICAL functional regressions on the **fetch-reporting leg** must be fixed:

## CRITICAL-1 — `fetch_pack` puts a dict into `FetchResult.artifacts_written: int`
`src/specify_cli/doctrine/snapshot.py:~302`: `_count_artifacts(effective)` returns `dict[str,int]` (e.g. `{'directives':1,'tactics':1}`), but `FetchResult.artifacts_written` is contractually `int` (`protocol.py:48`; `git_source` uses an int count). Result: `doctrine.py:147` now prints `Pack 'x': {'directives':1,...} artifacts` — violates FR-007 ("report artifact **count**") and breaks the type contract.
- **Fix:** report a scalar count at the effective root (e.g. `sum(_count_artifacts(effective).values())`, or a dedicated yaml-file count consistent with `git_source._count_yaml_files`).
- **Add a test** that drives `fetch_pack` directly and asserts `artifacts_written` is an `int` — and `== 0` for the wrong-`subdir` case (the literal SC-003 wording; currently SC-003 only exercises the doctor path, never `fetch_pack`'s reporting).

## CRITICAL-2 — signature change broke 3 existing tests (main red)
`fetch_pack(pack, repo_root)` is now 2-arg, but `tests/specify_cli/doctrine/test_config.py::TestDoctrineFetchCLI` (`test_fetch_all_packs`, `test_fetch_single_pack_flag`, `test_fetch_reports_failures`) monkeypatch `fetch_pack` with 1-positional-arg fakes → `TypeError: takes 1 positional argument but 2 were given` → CLI exits 1. Proven: these pass at the WP02 base (lane-a @ 0d22725d3), fail on lane-b.
- **Fix:** update the three monkeypatch fakes to the `(pack, repo_root)` signature (and assert the `int` contract while there). This test file is a caller broken by your owned-file signature change — updating it is a justified out-of-map edit (record a one-line rationale).

## Verify after fix
`.venv/bin/pytest tests/specify_cli/doctrine/test_config.py::TestDoctrineFetchCLI tests/integration/test_org_pack_subdir_e2e.py -q` → all green; `_build_pack_entries`/consumer changes already verified — do not regress them.
