---
affected_files:
- path: tests/architectural/test_no_read_side_bypass.py
cycle_number: 1
mission_slug: read-side-placement-seam-migration-01KYHP67
reproduction_command: PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py tests/architectural/test_no_write_side_rederivation.py -q
reviewed_at: '2026-07-27T18:05:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP08
---

**Verdict: APPROVED** — WP08 (the capstone structural read-side gate,
`tests/architectural/test_no_read_side_bypass.py`) satisfies its binding
contract (`contracts/read-side-gate.md`, IC-06 / FR-003 / FR-005 / FR-006 /
NFR-003 / NFR-004). Independently verified against the WP02 ledger and by
running the gates, not the implementer's word.

## Contract conformance

- **(a) Mirrors the write gate + consumes the SAME `scan_scope()` (NFR-003).**
  `test_read_and_write_gates_share_the_same_scan_scope` proves it two ways:
  runtime identity (`_whole_tree_scan_scope is
  _placement_whole_tree_scan.scan_scope`) and an AST source-check that the
  write gate still `from tests.architectural._placement_whole_tree_scan import
  scan_scope`. No forked walk. The read gate layers ONE extra read-specific
  filter (`_READ_SANCTIONED_MODULES`) on the shared base — the same
  compose-a-filter pattern `_placement_whole_tree_scan` itself uses; not a
  fork. ✔
- **(b) Allow-list is a 1:1 match with the ledger's 16 stay-lenient sites.**
  Cross-checked all 16 `_ALLOW_LIST_SEED` entries against the ledger's
  stay-lenient rows (11 files): `tasks_move_task.py:2368`,
  `tasks_status_cmd.py:160`, `archive.py:65`, `_coordination_doctor.py:933`
  + `:1057`, `reconcile.py:126`, `retrospect.py:110` + `:1005`,
  `dashboard/scanner.py:423` + `:461`, `dossier/api.py:227` + `:397` + `:435`,
  `retrospective/summary.py:220`, `status/aggregate.py:527`, `manifest.py:272`.
  No migrate-marked site papered in; none of the 16 missing. Count pinned by
  `test_allow_list_reconciles_with_the_wp02_ledger_stay_lenient_count`
  (`== 16`), keyed by `(rel_path, qualname, token_line)` composites — never a
  bare-path blanket (C-003), asserted by
  `test_allow_list_is_content_addressed_not_a_blanket_file_escape` (which also
  pins the 3 distinct `dossier/api.py` qualnames by exact name-set equality). ✔
- **(c) 3 sanctioned infra modules asserted-sanctioned, not silently skipped
  (FR-003).** `_READ_SANCTIONED_MODULES` = `_read_path_resolver.py`,
  `coordination/surface_resolver.py`, `mission_runtime/write_target_degrade.py`,
  each with an inline rationale. Three meta-tests: rationale non-empty
  (`..._carry_a_rationale`), excluded from scope
  (`..._are_excluded_from_the_read_scan_scope`), and NON-VACUITY
  (`..._have_real_findings_that_would_otherwise_red` — asserts each of the three
  actually contains a real read-bypass call that would red the ratchet if
  scanned). ✔
- **(d) Bite test reds on a planted kind-blind read; prose stays green.**
  `test_ratchet_bites_on_a_planted_kind_blind_read_call` (planted
  `candidate_feature_dir_for_mission(...)`) and its kind-aware twin
  (`resolve_planning_read_dir(...)`) both flag; `test_ratchet_ignores_a_prose_only_mention`
  proves a docstring/comment mention never becomes an `ast.Call` node and stays
  green — the exact 3-false-positive discrimination the ledger's own AST census
  had to make. ✔
- **(e) Shrink-only staleness twin-guard.** `test_allow_list_entry_is_still_a_live_finding`
  is parametrized per descriptor and uses `descriptor_still_live` with
  exactly-one + key-equal semantics (the docstring explicitly rejects the D-1
  "≥1 finding matches" bite hole); a routed/removed residual reds until the
  stale entry is DELETED. ✔

## Gates (in-lane `.worktrees/...-lane-h`, strict exit codes)

- `PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q`
  → **exit 0, 26 passed**.
- `PWHEADLESS=1 uv run pytest tests/architectural/test_no_write_side_rederivation.py -q`
  → **exit 0, 27 passed** (the mirrored write gate stays green).
- `uv run mypy tests/architectural/test_no_read_side_bypass.py` → **exit 0,
  Success, no issues**.

## Anti-pattern checklist

1. Dead code — PASS (a test module; every helper is exercised by a test in the
   same file).
2. Synthetic-fixture test — PASS (the ratchet scans real `src/` via the shared
   `scan_scope()`; deleting the detector logic would flip the bite test red).
3. Silent empty return — PASS (`_scan_read_bypass` returns `[]` only on
   `SyntaxError` of a scanned module, a documented parse-skip; not a swallowed
   failure).
4. FR coverage — PASS (FR-003 sanctions, FR-005 ratchet, FR-006/NFR-004
   shrink-only twin-guard, NFR-003 shared-scope symmetry each carry a direct
   assertion).
5. Frozen surface — PASS (only `owned_files` = the new gate module touched).
6. Locked decision — PASS (C-001: no second read authority; C-003: no
   file-scoped blanket exemption).
7. Shared-file ownership — PASS (WP08 owns lane-h alone; the gate module is new
   and single-owned).
8. Production fragility — N/A (test-only module; no production `raise`).

## Mission-level finding (SEPARATE from this WP08 verdict — NOT introduced by WP08)

WP08's own owned surface is green, but the aggregate `tests/architectural/`
run carries **three mission-introduced regressions** from the WP03–WP07
read-seam migrations (green on the true mission base `d0a5bacf7`, red on
lane-h) that the per-WP scoped reviews missed. These do NOT belong to WP08
(its only owned file is the gate module) and do NOT block this approval, but
**they block mission accept/merge** and need a fix WP. See the reviewer's
Part-2 report for the base-vs-lane evidence table and file:line offenders:

- `test_trio_seam_only.py::test_allowed_read_path_resolver_names_are_currently_used`
  — stale allow-list; `_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES`
  (`tests/architectural/test_trio_seam_only.py:143`) still blesses
  `candidate_feature_dir_for_mission` + `resolve_planning_read_dir` which no
  trio module imports post-migration. Fix: drop those two names (shrink-only).
- `test_surface_resolution_audit.py::test_audit_passes_on_current_tree` — ghost
  inventory rows `tests/architectural/surface_resolution_audit/inventory.md:58`
  (`status_transition.py:268`) and `:60` (`status_transition.py:285`) reference
  `candidate_feature_dir_for_mission` callsites WP06 migrated away. Fix: remove
  the rows or tag `[inventory-only]`.
- `test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` — dead
  public symbol `src/specify_cli/merge/resolve.py::_merge_state_key_candidates`
  (defined :87, in `__all__` :266, used only intra-module). WP05 left it
  exported with no external importer. Fix: drop from `__all__` (internal
  helper), or wire/allowlist per the gate's options.

The fourth aggregate red,
`test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files`
(offender `src/specify_cli/cli/commands/accept.py:239`), is **pre-existing** —
red on `d0a5bacf7` with the identical single offender — an honest baseline red,
not a mission regression.
