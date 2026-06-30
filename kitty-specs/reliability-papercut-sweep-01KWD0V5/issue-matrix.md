# Issue matrix — reliability-papercut-sweep-01KWD0V5

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1878 | Coordination placement / identity strangler (parent epic) | deferred-with-followup | Parent epic; mission is a child — Follow-up: #1878 (epic continues beyond it) |
| #2251 | record-analysis DIRTY_WORKTREE on orphan kitty-ops debris | in-mission | WP01 (FR-001) — 4-gate self-bookkeeping authority |
| #2250 | COORDINATION_BRANCH_DELETED on never-created coord branch | in-mission | WP02 (FR-002) — lead-with-flatten + backfill git-probe |
| #2240 | doctor coordination recommends a non-working recovery | in-mission | WP03 (FR-003) — recovery efficacy + #1890 standing guard |
| #2138 | Decision-event persists slug as canonical mission_id | in-mission | WP04 (FR-004) — fail-closed via resolve_mission_identity |
| #2139 | Dual target_branch reader with silent main fallback | in-mission | WP05 (FR-005) — one primitive, thin adapters, fail-closed |
| #2091 | Empty-mid8 malformed coord branch (mint-once) | in-mission | WP04 (FR-006) — mint-once identity boundary |
| #2274 | Lane-hygiene guard compares by commit-history not content | in-mission | WP06 (FR-007) — content-diff vs planning tip |
| #2275 | Review-artifact lane-vs-coord authority split | in-mission | WP07 (FR-008) — write where the merge gate reads |
| #2157 | Implement-gate serial-bounce + freshness deadlock | deferred-with-followup | Out of scope (standalone, #1619); kept separate per investigation |
| #2267 | retrospect classifier mislabels review-rejection --force | deferred-with-followup | Out of scope (distinct retrospect subsystem) — Follow-up: #2267 (kept as its own open issue) |
| #1619 | Runtime/state overhaul (root epic) | deferred-with-followup | Root epic; not addressed here — Follow-up: #1619 |
| #1890 | doctor recommends a non-existent command (precedent) | verified-already-fixed | Closed (`ecf45f52c`); cited precedent, WP03 adds the standing guard |
| #2102 | record-analysis dirty-tree allowlist (precedent) | verified-already-fixed | Closed; cited precedent that WP01 extends |
| #2219 | backfill-topology repo-global (precedent) | verified-already-fixed | Closed; cited precedent for WP02 |
| #2136 | canonical handle at resolve entry (precedent) | verified-already-fixed | Closed; cited precedent for WP04 |
| #2065 | surface-resolver single-authority, fail-closed (precedent) | verified-already-fixed | Merged; cited doctrine for WP05 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
