# Issue matrix — coordination-merge-stabilization-01KTXRVR

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.
Verdicts recorded at WP01 review (2026-06-12) from the cluster-validation disposition
(`validation/cluster-validation-brief.md`, research.md R8) and the WP01 hygiene pass
(`docs/development/3-2-coord-merge-issue-hygiene-log.md`).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1770 | merge baking fails under gitignored .worktrees/ | verified-already-fixed | PR #1793 (`c5a10ce56`) + PR #1850 accept anchor; closed 2026-06-12 |
| #1789 | daemons/dashboard re-materialize status.json during git ops | verified-already-fixed | PR #1850 WP11/WP12 (`8544012fa`); closed 2026-06-12 |
| #1816 | planning artifacts split across primary and coordination branches | verified-already-fixed | PR #1850 WP06 CommitTarget/FLATTENED (`8544012fa`); closed 2026-06-12 |
| #1771 | retrospect create writes to gitignored .kittify/missions/ | verified-already-fixed | PR #1850 WP08 (`8544012fa`, `test_record_committable_1771.py`); closed 2026-06-12 |
| #1571 | merge blocked by divergence, destroys artifacts via reset --hard | verified-already-fixed | PR #1719 push-gated sync preflight; superseded by #1706; closed 2026-06-12 |
| #1784 | finalize-tasks branch-model catch-22 (dup of #1777) | verified-already-fixed | PR #1850 `resolve_placement_only`; P3 crumbs → WP02/WP03; closed 2026-06-12 |
| #1777 | finalize-tasks catch-22 (canonical of #1784) | verified-already-fixed | PR #1850 `resolve_placement_only` (`8544012fa`) |
| #1735 | retrospect completion gate reads primary checkout event log | verified-already-fixed | PR #1850 WP08 (`8544012fa`); residuals → WP05 + umbrella #1878; closed 2026-06-12 |
| #1814 | residual: finalize staging leaves lanes.json/tasks/* residue on primary | in-mission | WP02/T008; re-scoped 2026-06-12 |
| #1736 | residual: merge pipeline cleanup (_make_merge_env, narrow except, ratchet) | in-mission | WP03/T015–T017; Bugs A/B/C fixed `a5f30616e`/`c5a10ce56`/`8544012fa`; re-scoped 2026-06-12 |
| #1833 | residual: husk fall-through guards + doctor check | in-mission | WP04; F-001 naming trigger fixed in #1850; re-scoped 2026-06-12 |
| #1861 | residual: finalize-tasks --validate-only must not switch checkout | in-mission | WP02/T006; Part 2 resolved by `SafeCommitHeadMismatch` (`8e79b3f6d`); re-scoped 2026-06-12 |
| #1826 | coord worktree falls behind its branch mid-merge (safe_commit backstop) | in-mission | WP03 ref-advance-with-resync contract (class-b-ref-advance-resync.md) |
| #1827 | crash between event-record and commit strands state | deferred-with-followup | Umbrella #1878 item 7 (filed 2026-06-12 under epic #1666) |
| #1850 | landed stabilization PR (context reference, not a defect) | verified-already-fixed | Merged PR #1850 (`8544012fa`) on main |
| #1666 | epic: execution-state & context domain-boundary redesign | deferred-with-followup | Remains open as parent epic; post-3.2.0 remainder carried by umbrella #1878 |
| #1623 | doctor.py god-module split (FR-012 debt) | deferred-with-followup | Pre-existing deferred item; tracked on #1623, out of mission scope (C-001) |
