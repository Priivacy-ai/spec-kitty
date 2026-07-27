---
affected_files:
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/decisions/service.py
- src/specify_cli/review/cycle.py
- tests/specify_cli/test_read_seam_leniency.py
cycle_number: 1
mission_slug: read-side-placement-seam-migration-01KYHP67
reproduction_command: uv run pytest tests/specify_cli/test_read_seam_leniency.py -q
reviewed_at: '2026-07-27T15:10:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP06
---

**Verdict: APPROVED** — WP06 (diagnostic-heavy cluster + leniency) conforms to the
WP02 classification ledger (`docs/development/read-side-seam-classification.md` §WP06)
site-for-site. Independent reviewer verification, not the implementer's word.

## Ledger conformance — migrate-fail-loud (all routed through `placement_seam(...).read_dir(kind)`)

- `coordination/status_transition.py` `_canonical_primary_feature_dir` (ledger :606/:623):
  both former `candidate_feature_dir_for_mission` calls (the `_is_under_worktree`
  fallback branch and the malformed-meta `except ValueError` branch) now route through a
  `_primary_anchor()` helper → `read_dir(PRIMARY_METADATA)`. Correct kind: this is the
  transaction-identity PRIMARY anchor for the status WRITE path, not a STATUS read;
  PRIMARY_METADATA is topology-blind so the degrade contract (never raises on deleted
  coord) is preserved verbatim. ✔
- `coordination/status_transition.py` `_tombstone_lane_workspace_context_on_cancel`
  (ledger :1259): former `resolve_planning_read_dir(..., LANE_STATE)` → `read_dir(LANE_STATE)`. ✔
- `decisions/service.py` `_mission_dir` (ledger :173): `read_dir(STATUS_STATE)`. Correct —
  the decision-log companion `status.events.jsonl` read must agree with the coord-authority
  write target (`emit.py`); a deleted/stale coord branch here is a genuine split-brain risk,
  so fail-loud is the right, ledger-sanctioned behavior. Pinned by
  `test_decisions_mission_dir_fails_loud_when_coord_deleted` (raises `CoordinationBranchDeleted`,
  error_code `COORDINATION_BRANCH_DELETED`, coord branch in message). ✔
- `review/cycle.py` `_review_cycle_wp_dir` (ledger :49): `read_dir(WORK_PACKAGE_TASK)`. ✔

## Ledger conformance — stay-lenient (THE CRITICAL CHECK: NONE converted to fail-loud)

Diff touches only the 3 migrate modules + the test; every stay-lenient site is byte-for-byte
untouched and independently confirmed still using its lenient resolver + catch/degrade:

- `dashboard/scanner.py:423,461` — both still `resolve_planning_read_dir` under
  `except (ValueError, MissionSelectorAmbiguous)` with the "dashboard scan must never crash" guard. ✔
- `dossier/api.py:227,397,435` — all three still `candidate_feature_dir_for_mission` feeding
  `load_snapshot`, "not found" → `error_response(404)` (SaaS-facing, must not raise CoordinationBranchDeleted). ✔
- `retrospective/summary.py:220` — still `candidate_feature_dir_for_mission`, returns (0,0,0) on any error. ✔
- `status/aggregate.py:527` — still `candidate_feature_dir_for_mission` with graceful
  `except StatusReadPathNotFound` translation. ✔

No non-WP06 site was touched; none of WP06's sites were missed. The ATDD test's AST bypass-pin
(`test_diagnostic_cluster_retains_only_ledger_approved_lenient_sites`) asserts the exact residual
lenient descriptor set equals the ledger's stay-lenient set — this guards against both
over-migration (removing a lenient bypass) and under-migration (leaving a bypass in a fail-loud module).

## ATDD genuineness

`tests/specify_cli/test_read_seam_leniency.py` is a genuine acceptance test, not a smoke test:
AST residual-bypass pin + real-git-repo deleted-coord leniency assertions (stay-lenient sites
return, do not raise) + fail-loud raise assertion (decisions STATUS_STATE raises
`CoordinationBranchDeleted`) + behavior-preservation for the migrated PRIMARY-partition sites.

## Gates (run in lane-f `.worktrees/read-side-placement-seam-migration-01KYHP67-lane-f`)

- `uv run pytest tests/specify_cli/test_read_seam_leniency.py -q` → 10 passed (exit 0). ✔
- `uv run pytest tests/specify_cli/decisions tests/specify_cli/review -q` → 167 passed (exit 0). ✔
- `uv run pytest tests/specify_cli/coordination -k status_transition -q` → 46 passed (exit 0). ✔
- `uv run mypy` on the 3 modules → exit 1, 6 errors. Baseline (`92f935a45~1`) → exit 1, 7 errors.
  WP06 introduced ZERO new mypy errors; net 7→6 because the explicit `Path` binding pattern
  FIXED the pre-existing `decisions/service.py:173 no-any-return`. Remaining 6 are all
  pre-existing (`status_transition.py:135/151/160/637`, `decisions/service.py:106/245`). ✔
- Baseline red `test_resolve_subtasks_gate_dir_direct_three_branches` reproduces with the
  pre-existing `/tmp/kitty-specs/irrelevant-slug` symptom — NOT a WP06 regression (untouched module). ✔

No defects. WP06 additionally leaves the campsite cleaner (net -1 mypy error).
