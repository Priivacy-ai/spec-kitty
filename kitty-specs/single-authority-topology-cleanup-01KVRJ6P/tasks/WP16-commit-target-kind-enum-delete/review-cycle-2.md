---
affected_files: []
cycle_number: 2
mission_slug: single-authority-topology-cleanup-01KVRJ6P
reproduction_command:
reviewed_at: '2026-06-23T10:15:45Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP16
review_artifact_override_at: "2026-06-23T13:32:05Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP16"
review_artifact_override_reason: "Arbiter override: review-cycle-2 was the operator-approved BLOCKED/re-sequence record (plan-sequencing defect correctly surfaced), NOT an unaddressed quality rejection; re-sequenced impl (WP16 LAST, dep WP07) delivers the expanded scope. Review PASSED: CommitTargetKind fully eradicated (rg src/ tests/ -> nothing but WP01 guard sentinel; no runtime attr; CommitTarget ref-only C-007). resolve_topology seam is a clean stored-topology READ delegating to pure _resolve_topology (WP02 SSOT), canonicalizing handle identically to resolve_placement_only. All 8 rewired sites behavior-neutral (old .kind-is-COORDINATION == routes_through_coordination over SAME stored topology; resolve_placement_only runs first so swallow-arm unreachable; mission_slug-None guard unreachable). is_coordination_owned deletion safe (zero callers; kind_is_coordination_residue live). Weld preserved (absolute per-topology table + negative controls, no enum import). WP01 AST guard green-by-emptiness + bites-on-reintroduction + ignores-flattened-string controls. C-006 meta.setdefault('flattened',False) intact. ruff+mypy clean on changed src (zero NEW issues). 4 test failures + 4 no-any-return mypy ALL verified pre-existing via HEAD^. Behavior spot-check passed all 4 topology cases. Scope eradication-necessary, no creep."
---

# WP16 — Cycle 1: BLOCKED (plan-sequencing defect, re-sequenced)

The WP16 implementer correctly STOPPED (no fake-green, no scope balloon) on a real
plan-sequencing defect: deleting the `CommitTargetKind` enum where WP16 was sequenced
(before WP05's FLATTENED-producer cleanup, before the ~27 enum-referencing test files
were drained) cannot be compile-green — and `WP05` depended on WP16 while owning a
FLATTENED producer (`upgrade.py:214`) that the deletion breaks (circular).

**Resolution (operator-approved 2026-06-23):**
- `WP05` dep re-pointed `WP16 → WP04` (WP05 cleans FLATTENED producers right after WP04).
- `WP16` re-sequenced to run **LAST in lane B** (dep `WP07`): chain
  WP04→WP05→WP06→WP17→WP07→WP16. Scope **expanded** to drain the ~27 enum-referencing
  test files (re-point enum-contract tests to the topology/predicate contract, or
  delete enum-only tests) before removing the VO field + deleting the enum.

Re-claim WP16 only after WP07 is approved. The expanded scope + new subtask T031 are
in the WP16 prompt.
