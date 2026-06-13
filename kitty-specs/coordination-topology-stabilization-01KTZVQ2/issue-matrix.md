# Issue matrix — coordination-topology-stabilization-01KTZVQ2

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.
Verdicts updated at WP05 review (2026-06-13).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1164 | Coordination topology stabilization (epic) | in-mission | WP07 (T030–T031), WP08 (T036–T040) address ff-merge treadmill / advance_branch_ref |
| #1878 | Coordination topology umbrella | in-mission | WP09 (T041–T047) closes coordination read-surface and ff-merge treadmill portions |
| #1883 | Accept gate counts its own previously-written artifacts as working-tree dirt | in-mission | WP06 (T025–T029) addresses FR-001 / FR-002 |
| #1884 | coord-aware read primitive missing | in-mission | WP01 (T001–T006, T048) addresses FR-003; PR #1895 (in-flight fork) coordinated per C-004 |
| #1885 | next-fail-closed hardening | in-mission | WP03 (T013–T020) addresses FR-004 |
| #1886 | stale-assertion FP on message-capture in-operator (FR-009) | fixed | 5480c58e8 feat(WP05): stale-assertion classifier — suppress message-content FPs, fix last-wins dict |
| #1887 | .worktrees/ paths leaked into git index (26 tracked paths from PR #1825 squash) | fixed | WP02: root anchor fixed in `_feature_dir_file_paths` (implement.py); `SafeCommitPathPolicyError` rejection gate in `safe_commit` (commit_helpers.py); write-side guard in `BookkeepingTransaction.write_artifact` (transaction.py); architectural ratchet test (xfail pending WP10 cleanup) |
| #1888 | Terminus retrospective never triggers on standard merge path | in-mission | WP07 (T030–T035), WP08 (T036–T040) address FR-007/FR-008 |
| #1895 | name-vs-authority-remediation (in-flight fork PR) | deferred-with-followup | Must coordinate before WS1 and WS5 dispatch per C-004; tracked as T048 in WP01. Follow-up: #1895 (external fork PR) |
| #1825 | do-dispatch-open-op-lifecycle coord squash introduced 26 leaked .worktrees/ paths | in-mission | WP10 (T048–T049): index cleanup and ratchet test after WP02 lands |
| #1771 | Retrospective path canon | verified-already-fixed | Already landed before this mission; provides correct record path |
