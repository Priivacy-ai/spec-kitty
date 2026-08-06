---
affected_files: []
cycle_number: 1
mission_slug: verdict-seam-write-unification-01KZ9Q35
reproduction_command:
reviewed_at: '2026-08-06T05:38:20Z'
reviewer_agent: user
verdict: rejected
wp_id: WP06
---

# WP06 Review — Cycle 1 — CHANGES REQUESTED (reviewer-renata)

WP06's **own** deliverables are strong and are NOT the reason for rejection (see
"What is correct" below). The block is a genuine, reproducible regression
cluster hiding inside the ripple that the implementer's advisory misreported as
"1 new failure across 11 shards (concurrent worktree noise)". The terminal WP of
this mission cannot be approved while its lane ships **10 real red tests** in the
exact domain the mission exists to unify (verdict-seam single-authority).

---

## BLOCKER 1 — 10 lane-introduced regressions, misreported as "1 noise failure"

Run in the lane (`PYTHONPATH=<lane>/src`), fully isolated, deterministic:

```
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_preflight_detects_rejected_review_artifact_on_approved_wp
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_dry_run_emits_rejected_review_artifact_conflict
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_dry_run_emits_review_artifact_schema_invalid
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_dry_run_human_emits_rejected_review_artifact_conflict
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_dry_run_human_emits_review_artifact_schema_invalid
FAILED tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py::test_real_merge_schema_preflight_does_not_write_merge_state
FAILED tests/specify_cli/cli/commands/test_merge_cli_golden.py::test_dry_run_json_emits_rejected_review_artifact_conflict
FAILED tests/merge/test_forecast_seam.py::test_review_artifact_conflict_blocks_json
FAILED tests/integration/test_review_cycle_rejection_only.py::test_approving_a_rejected_wp_writes_no_verdict_artifact
FAILED tests/regression/test_issue_2996_approval_after_rejection_writes_no_verdict.py::test_approving_a_rejected_wp_writes_no_verdict_artifact
```

**These are real, not environmental.** I classified each against three trees:

| Tree | Commit | Result |
|------|--------|--------|
| Mission base | `9d99691c4` | **all 10 GREEN** |
| WP06 parent (WP05 applied, WP06 NOT) | `c396ebf0e` (`00c03ba89^`) | 9 already RED (verdict field still present) |
| WP06 tip | `00c03ba89` | 10 RED |

**Root cause — WP05's reader collapse, not WP06's schema removal.** The tests
fail at WP06's *parent* (where `verdict: str` still exists on the dataclass), so
the schema removal is not the trigger. WP05 made the merge-preflight/CLI-approve
readers **pure-event** but left these `.md`-only fixtures behind:

- `test_dry_run_emits_review_artifact_schema_invalid` expects `exit 1`, gets
  `exit 0` — a `.md` the pure-event gate no longer consults is no longer
  "schema invalid".
- `test_preflight_detects_rejected_review_artifact_on_approved_wp` /
  `..._emits_rejected_review_artifact_conflict` — the fixtures write a rejected
  `.md` with **no** corresponding `review_result` event, so
  `find_rejected_review_artifact_conflicts` (now event-sourced) finds nothing.
- `test_issue_2996::...` / `test_review_cycle_rejection_only::...` — the CLI now
  raises `WP01 ... has no parseable review verdict` because
  `tasks_transition_core.py:409` sources `req.review_verdict` from the event
  authority, which the `.md`-only fixture never populates → the fresh approval
  cycle is never written (`latest.cycle_number` stays `1`).

WP05's own `review-cycle-1.md` documents repointing *some* tests
(`test_malformed_review_artifact_frontmatter_becomes_schema_diagnostic`,
`test_forced_null_review_result_defers_to_frontmatter_and_still_refuses`) to
`findings == []` — but the ten above were **not** among them. They are an
unaddressed gap from the reader collapse, carried into this terminal lane.

**Why this blocks WP06 specifically.** WP06 is the last gate; approving it merges
lane-f (WP05's collapse + these reds) onto `feat/verdict-seam-write-unification`.
WP06's own commit *touched all these files* (dropping `verdict=` kwargs) and its
message claims "Fixed ripple across ~20 test files" — the ripple fix is
**incomplete**, and the "1 new failure … concurrent worktree noise" advisory is
**materially inaccurate**. The mission whose purpose is verdict single-authority
cannot ship with its merge-preflight rejected-artifact detection and its
reject→fix→approve CLI path red.

### Required fix
Repoint these 10 fixtures to the event authority — the **same pattern already
applied correctly** in this WP to `test_review_durability_matrix.py` and
`tests/post_merge/test_review_artifact_consistency.py` (assert on
`review_result.verdict` / emit a `review_result` event in the fixture), so the
pure-event merge preflight and the approve guard see the rejection. If any file
is deemed strictly WP05-owned, coordinate with WP05 — but the lane must be
**green** before the terminal WP is approved (record the coordination in the
move-task reason). Then correct the failure advisory to state the real count and
attribution.

### NOT blocking (correctly pre-existing / environmental — leave red, do not "fix")
- `tests/status/test_reducer.py::...::test_event_sourced_review_result_this_missions_own_meta_json_fixture` — #3220 self-referential meta.json fixture; red on the mission base (WP05 review item 3 confirms).
- `tests/integration/test_mission_review_contract_gate.py::test_mission_review_fails_when_done_wp_latest_review_artifact_is_rejected` — reproduces identically at the mission base (`MissionNotFoundError` in `resolve_mission_handle`); env-skew mission resolution, resolver untouched by the lane. WP06's only edit here (drop `verdict="rejected"` kwarg) is correct and unrelated.

---

## What is correct (verified — do NOT redo on the next cycle)

- **SC-007 schema removal COMPLETE**: `verdict` gone from the dataclass field,
  `to_dict`, `from_dict`/`validate_review_artifact` validation, and the
  `REVIEW_ARTIFACT_VERDICTS` constant; the two retired parser functions are
  absent. Surviving `verdict` tokens in `artifacts.py` are docstrings/comments
  only. No surviving `ReviewCycleArtifact.verdict` read anywhere in `src/`.
- **SC-007 test NON-VACUOUS** (`test_artifacts_no_verdict_field.py`): probes the
  production schema directly (`pytest.raises(AttributeError)`, clean `from_dict`
  without the key, stray-key-ignored). Red-against-old-schema is structural, not
  a synthetic fixture.
- **SC-001 test NON-VACUOUS** (`test_verdict_dir_co_resolution.py`): US2
  multi-consumer co-resolution under coord + flat topologies, plus the AST
  invariant with two live poison arms that assert `violations` is non-empty
  (divergent-kind + caller-supplied-dir) and two clean arms — all pass, so the
  poison arms genuinely red.
- **`.latest`/`.from_file` prose loading works without the field** (round-trip
  test) — no consumer crashes on the missing key; verdict still flows to the
  event `ReviewResult` and the commit message (cycle.py), just not the schema.
- **FR-006 census GREEN & honest**: the 5 `status: retire` resolver rows are
  `source: WP08/IC08` with valid `retiring_fr` (FR-003/007/009), retired by a
  later WP per the census docstring — correctly left in place, not a WP06 dodge.
  The added `_legacy_frontmatter_verdict` row is a genuine, disclosed
  legacy-recovery migration reader (raw-frontmatter read, returns `None`, never
  reintroduces the field). `test_verdict_seam_census.py` green.
- **FR-011 docstring correction is HONEST**: verified the merge gate
  (`post_merge/review_artifact_consistency.py`) does not call
  `_review_cycle_wp_dir`.
- **FR-007 location gate**: `doctor review-cycle-reconcile --json` asserts zero
  `live_coord_pre_adr_primary_record` — green.
- **T032 guard**: parse-based identity (no verdict read-back); WP06 added a
  genuine non-vacuous lock test.
- **Ripple sample adjudicated GENUINE**: durability-matrix and post_merge repoints
  go to `review_result.verdict` / `body.startswith("Approved by ")` /
  `cycle_number` — none weakened or deleted; several strengthened to assert
  SC-007 on the real committed git blob.
- **Gates**: `ruff` clean; `mypy --strict` clean on `review/` + migration;
  `test_no_legacy_terminology.py` green.
