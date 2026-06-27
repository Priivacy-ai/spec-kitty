# Issue matrix — coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

**Addressed by this Mission:** #2185 (Lane A), #2186 (Lane B), and #2187 (Lane A). The rest are context/boundary and are not closed here.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2185 | Coord-authority: route merge/+lanes/ PRIMARY reads off coord-aware resolvers | fixed | WP02 (`e4998c21b`) + WP03 (`00c05255f`) route all merge/lanes/core reads (forecast/executor per-leg/resolve/done_bookkeeping/merge.py/lanes.merge/recovery/worktree_allocator/worktree_topology) onto `resolve_planning_read_dir(LANE_STATE/META/WP_TASK)`; proven by WP04 (`7ade8e294`) divergent-fixture revert-fails on returned domain values; statically gated by WP05 (`fce746b62`) live FR-007 lanes.json arm (10/10 sites, 0 un-pinned). STATUS legs (recovery:664, executor status_feature_dir) kept coord (NFR-001, WP04-proven). |
| #2186 | Coord-authority: route/guard meta.json identity reads (next_cmd telemetry drop) | fixed | WP01 (`b2616464c`) routes next_cmd :187/:253/:619, implement.py:1394, workflow.py :1282/:1644/:2739 + WP03 (`00c05255f`) routes status.py:132, executor :981/:1003, worktree_topology :139 onto primary anchors; proven by WP04; statically gated by WP05 live identity arm (12/12 sites, 0 un-pinned). |
| #2187 | Coord-authority: route agent_utils/status.py show_kanban_status tasks-read off coord | fixed | WP03 (`00c05255f`) routes status.py:126 to WORK_PACKAGE_TASK + drains the sole `_DIR_READ_KNOWN_RESIDUALS` pin (set shrank by exactly one); revert-fails proven on the kanban WP list. |
| #1848 | `MissionSelectorAmbiguous` structured hard-fail boundary (NFR-002) | verified-already-fixed | boundary issue (closed); this Mission PRESERVES the structured hard-fail and adds no silent fallback (C-002 / NFR-002) — verified by WP01 routing, which keeps the no-fallback semantics |
| #2106 | Kind-aware write-surface placement (the cause) | verified-already-fixed | merged 2026-06-24; this Mission consumes its read-side seam |
| #2115 | Implement/review/merge reads WP `tasks/` off coord (originating) | verified-already-fixed | closed by sibling `implement-loop-coord-authority-completion-01KW2E7A` (Follow-up: PR #2194, merged 2026-06-27); this Mission consumes its read-side seam |
| #2167 | Retire pre-3.0 `scripts/tasks/` legacy reader | deferred-with-followup | Follow-up: #2167 — separate tracking ticket; pin-and-cite only here (C-EXCL-2167), not routed by this Mission |
| #2160 | Coord topology: unify artifact authority (epic) | deferred-with-followup | Follow-up: #2160 — epic parent, reference-only; stays open until all children land, never claimed/closed by a child Mission |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this Mission; must reach a terminal verdict before Mission `done`).

**Claim:** #2185 + #2186 + #2187 assigned to the operator and a mission-naming comment posted on each (ticket-based mission hygiene). #2160 epic is operator-owned and reference-only — never re-claimed by this child.
