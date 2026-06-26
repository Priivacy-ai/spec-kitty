# Issue matrix — retrospective-durable-home-01KVYM1W

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2119 | Retrospective durable home + topology-aware teardown (driver) | in-mission | WP01-06 (this mission) |
| #1771 | Retrospective written to ephemeral coord worktree (parent of #2119) | in-mission | WP03 routes retro write to primary + kills the false-green twin |
| #1878 | Terminal-artifact write-surface strangler (epic) | deferred-with-followup | Follow-up: #1878 — epic continues beyond this mission's retro slice |
| #2125 | Extract shared atomic-YAML writer (retrospective/writer.py dup) | deferred-with-followup | Follow-up: #391, #1797 — RELATED, not folded |
| #2129 | Lane-worktree exact-set teardown | verified-already-fixed | merged sibling (closed #2127); regression-ref only |
| #2136 | Canonicalize handle at PRIMARY read/write seam (universal cure) | in-mission | WP01 / FR-011 (caller-canonicalization) |
| #1890 | Phantom `agent worktree repair` recovery command | in-mission | WP05 / FR-007 (repoint to `doctor workspaces --fix`) |
| #2123 | Lane slug-prefix over-match (sibling-loss + discard false-positive) | verified-already-fixed | code done-by-#2129; ticket stays open as regression-reference |
| #2133 | Decompose merge.py god-module | verified-already-fixed | merged substrate (FR-004/005 re-anchored onto the seams) |
| #2114 | Decompose agent/tasks.py god-module | verified-already-fixed | merged substrate |
| #2134 | Decompose agent/mission.py god-module | verified-already-fixed | merged substrate |
| #2135 | Decompose cli/commands/doctor.py god-module | verified-already-fixed | merged substrate (FR-007 anchors re-censused live) |
| #2127 | close --discard deletes sibling lane worktree (slug-prefix) | verified-already-fixed | done-by-#2129 (closed) |
| #2121 | close --discard teardown helper | verified-already-fixed | merged to base |
| #2120 | mission close --discard no-ops on coord topology | verified-already-fixed | merged to base |
| #2057 | merge.py god-module (decomposition mission) | verified-already-fixed | merged substrate |
| #1716 | Read-surface strangler (epic) | deferred-with-followup | Follow-up: #1716 — epic continues beyond the retro write slice |
| #1868 | Mission-identity / write-surface strangler (epic) | deferred-with-followup | Follow-up: #1868 — epic continues |
| #2090 | Write-surface-coherence kind partition | verified-already-fixed | merged precedent (#2106); FR-002 RETROSPECTIVE extends the partition |
| #2101 | Kind-aware placement ADR | verified-already-fixed | merged precedent for the primary-anchored authority |
| #2138 | Decision-event payload persists slug as mission_id | deferred-with-followup | Follow-up: #1868 — OUT-OF-SCOPE sibling cluster, own mission |
| #2139 | Dual target_branch reader with silent main fallback | deferred-with-followup | Follow-up: #1868 — OUT-OF-SCOPE sibling cluster, own mission |
| #2140 | Verify is_committed spec-read surface post-#2090 | deferred-with-followup | Follow-up: #1868 — OUT-OF-SCOPE sibling cluster, own mission |
| #2122 | v3.2.2 accept-gate breaks for mid8-handle mission | verified-already-fixed | hotfix merged (#2126); FR-011 supersedes at the seam |
| #2059 | doctor.py god-module (decomposition mission) | verified-already-fixed | merged substrate |
| #2115 | Native-flow PRIMARY reads off primary surface (Ray-port) | deferred-with-followup | Follow-up: #2115 — separate effort owned by OTHER MAINTAINERS, out of #2119 scope |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
