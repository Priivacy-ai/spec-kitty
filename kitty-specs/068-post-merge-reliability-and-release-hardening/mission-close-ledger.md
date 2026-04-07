# Mission Close Ledger

**Feature**: 068-post-merge-reliability-and-release-hardening
**Authored**: 2026-04-07
**DoD-4 Validation**: Every issue from the Tracked GitHub Issues table appears below with exactly one row.

---

## Validated DoD

> "Every issue from the Tracked GitHub Issues table appears below."

Tracked issues (from `spec.md`):
- Primary scope: #454, #456, #455, #457
- Verification-and-close scope: #415, #416

Row count (excluding header): 6. Expected: 6. **PASS**.

To mechanically verify: `grep -c "^| #" mission-close-ledger.md` → should return `6`.

---

## Ledger

| issue_id | decision | reference | notes |
|----------|----------|-----------|-------|
| #454 | `closed_with_evidence` | WP01 implementation — `src/specify_cli/post_merge/stale_assertions.py`, CLI at `spec-kitty agent tests stale-check`, tests at `tests/post_merge/`. Merge commit to be linked at close. | Post-merge stale-assertion analyzer shipped. AST-based identifier matching, confidence classification, integrated into merge summary. |
| #456 | `closed_with_evidence` | WP02 implementation — `--strategy` flag wired end-to-end in `_run_lane_based_merge`, squash default for mission→target, `merge.strategy` config key in `.kittify/config.yaml`, push-error parser for linear-history rejection. Tests at `tests/merge/test_merge_unit.py`, `tests/merge/test_merge_policy.py`. Merge commit to be linked at close. | Protected-branch linear-history support shipped. Strategy flag no longer discarded. |
| #455 | `closed_with_evidence` | WP03 validation report — `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md`. Merge commit to be linked at close. | Diff-coverage CI policy validated. Current main already satisfies the issue intent (critical-path hard-fail, full-diff advisory). Issue closed with evidence per FR-011. |
| #457 | `closed_with_evidence` | WP04 implementation — `spec-kitty agent release prep`, `src/specify_cli/cli/commands/agent/release.py`. Merge commit to be linked at close. FR-023 scope-cut documented: changelog draft, version bump, and structured release-prep payload are automated; PR creation, tag push, and workflow monitoring remain manual. | Release-prep CLI shipped. |
| #415 | `closed_with_evidence` | WP05 T024+T025+T026 — `src/specify_cli/lanes/recovery.py` (scan_recovery_state extended, `get_ready_to_start_from_target` added), `src/specify_cli/cli/commands/implement.py` (--base flag added), tests at `tests/lanes/test_recovery_post_merge.py` and `tests/cli/commands/test_implement_base_flag.py`. Verification report at `kitty-specs/068-.../wp05-verification-report.md`. Merge commit to be linked at close. | Post-merge recovery deadlock fixed. Scenario 7 reproduced in test suite. |
| #416 | `closed_with_evidence` | WP02 FR-019 — `safe_commit` inserted after mark-done loop in `_run_lane_based_merge` (`src/specify_cli/cli/commands/merge.py`). Regression test: `tests/cli/commands/test_merge_status_commit.py::test_done_events_committed_to_git`. Verification: WP05 `wp05-verification-report.md`. Merge commit to be linked at close. | Merge interruption/recovery idempotence fixed. Status events committed to git before workspace cleanup. |

---

## Carve-Out Follow-Up Issues

The following items were explicitly carved out of this mission's scope per the spec. Follow-up issues must be filed and linked before final mission close.

| carve_out | rationale | follow_up_issue |
|-----------|-----------|-----------------|
| FSEvents debounce / `_worktree_removal_delay()` empirical timing | Empirical sweeping of macOS CI runner timing is a separate workstream from the deterministic event-commit fix. | To be filed — link here before mission close. |
| Dirty classifier `git check-ignore` consultation | Whether the preflight dirty-check should consult `.gitignore` rules is a UX refinement orthogonal to the reliability fixes in this mission. | To be filed — link here before mission close. |

---

## Notes

- All `reference` fields marked "Merge commit to be linked at close" must be updated with the actual merge commit SHA (from `git log --oneline -1 main` after the final merge) before closing the issues.
- WP05 is the home of this ledger. Once the merge commit is known and all carve-out issues are filed, the ledger rows can be finalized and the issues closed with the closing comment per C-005.
