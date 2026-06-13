# Issue matrix — coordination-topology-stabilization-01KTZVQ2

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1164 | ff-merge treadmill / advance_branch_ref coordination-residue exclusion | in-mission | WP07 (T030–T031), WP08 (T036–T040) |
| #1878 | coordination read-surface and ff-merge treadmill (umbrella) | in-mission | WP09 (T041–T047) |
| #1883 | accept-gate transactional safety (FR-001/FR-002) | in-mission | WP06 (T025–T029) |
| #1884 | coordination-aware is_committed() read primitive (FR-003) | in-mission | WP01 (T001–T006, T048) |
| #1885 | next-loop fail-closed on missing coordination branch (FR-004) | in-mission | WP03 (T013–T020) |
| #1886 | stale-assertion FP on message-capture in-operator (FR-009) | fixed | 5480c58e8 feat(WP05): stale-assertion classifier — suppress message-content FPs, fix last-wins dict |
| #1887 | worktrees writer coordination-branch write path (FR-005) | in-mission | WP02 (T007–T012), WP10 (T048–T049) |
| #1888 | ownership-warning routing (FR-006) | in-mission | WP04 (T021 owner-warning tasks) |
| #1895 | PR stijn-dejongh/spec-kitty: name-vs-authority-remediation (coordination dependency, not a bug this mission owns) | deferred-with-followup | Pre-flight coordination required before WP01/WP03 dispatch (C-004); tracked via T048 |
| #1825 | .worktrees/ paths leaked to origin/main via squash commit (cleanup context) | in-mission | WP10 (T048–T049): index cleanup and ratchet test |
| #1771 | retrospective path canon — already landed before this mission | verified-already-fixed | Spec note: "already landed, provides the correct record path" |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
