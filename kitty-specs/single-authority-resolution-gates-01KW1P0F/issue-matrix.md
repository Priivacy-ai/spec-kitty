# Issue matrix — single-authority-resolution-gates-01KW1P0F

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2154 | mark_status write-leg lands on coord; move_task validates primary (WP blocked) | fixed | WP02 (FR-001 — routes :1807 write through resolve_planning_read_dir kind=TASKS_INDEX) |
| #2155 | mixed-bundle auto-commit silently drops coord-owned status write | fixed | WP02 (FR-002 — routes implement.py:1311 [+ re-verify tasks.py:1555] via BookkeepingTransaction; guard untouched) |
| #2164 | Un-canonicalized handle reaches the topology-blind primitive (no regression guard) | fixed | WP01 gate + WP03/04/05 sweep (FR-004/005 — closed by construction) |
| #2160 | Coord-authority class (write leg bypasses the kind-aware authority) | deferred-with-followup | Core class #2154+#2155 closed by WP02; #2160 UMBRELLA stays OPEN for checklist children #2115/#2017/#2140 (out-of-scope/Phase-2) — do NOT auto-close on merge |
| #1842 | Literal `/tmp/` paths in test files | fixed | WP07 (FR-007 — frozen-baseline ratchet; full litter sweep OUT of scope) |
| #2034 | Mission-owned contract tests excluded from CI shards | verified-already-fixed | WP07 (FR-008 — conditional/empirical collect-only verify; named files already run → likely verify-only) |
| #2161 | Read-leg handle-safety fix (pre-condition) | verified-already-fixed | Landed on base; WP08-T037 (C-003) verifies present, not re-implemented |
| #2136 | Canonicalize handle at the read/write seam (pre-condition) | verified-already-fixed | Satisfied in #2161 (read leg); this mission extends to the write/gate legs |
| #2119 | Retrospective durable-home driver (pre-condition substrate) | verified-already-fixed | Landed in #2161 / PR #2106 substrate |
| #1887 | Wrong-surface `.worktrees/` commit leak protection | verified-already-fixed | Guard exists at commit_helpers.py:983-991; C-006 keeps it UNCHANGED (protection preserved, not re-opened) |
| #2173 | Infra-to-logic separation (epic parent) | deferred-with-followup | Follow-up: #2173 — Phase 1 (gate + routing) only; Phase 2 DI port continues |
| #1619 | Runtime/state overhaul (strategic root epic) | deferred-with-followup | Follow-up: #1619 — root epic continues beyond this mission |
| #1716 | Read-surface strangler (sibling epic) | deferred-with-followup | Follow-up: #1716 — referenced, scope not merged |
| #1868 | Mission-identity / write-surface strangler (sibling epic) | deferred-with-followup | Follow-up: #1868 — referenced, scope not merged |
| #1878 | Terminal-artifact write-surface strangler (sibling epic) | deferred-with-followup | Follow-up: #1878 — referenced, scope not merged |
| #2017 | Guard-friction backlog (incidental) | deferred-with-followup | Follow-up: #2017 — incidental overlap; not claimed closed by this mission |
| #2140 | Verify is_committed spec-read surface | deferred-with-followup | Follow-up: #2140 — MONITORED; note if the canonicalizer gate covers it incidentally |
| #2138 | Decision-event payload persists slug as mission_id | deferred-with-followup | Follow-up: #1868 — OUT-OF-SCOPE sibling cluster, own mission |
| #2139 | Dual target_branch reader with silent main fallback | deferred-with-followup | Follow-up: #1868 — OUT-OF-SCOPE sibling cluster, own mission |
| #2091 | Empty-mid8 coord branch (distinct surface) | deferred-with-followup | Follow-up: #1716 — OUT-OF-SCOPE distinct surface |
| #2100 | Inline meta reads off-surface (distinct surface) | deferred-with-followup | Follow-up: #1716 — OUT-OF-SCOPE distinct surface |
| #2123 | Lane slug-prefix over-match (distinct surface) | deferred-with-followup | Follow-up: #1716 — OUT-OF-SCOPE distinct surface |
| #2115 | Native-flow PRIMARY reads off primary surface (pinned residual) | deferred-with-followup | Follow-up: #2115 — OUT-OF-SCOPE, own mission / other maintainers |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
