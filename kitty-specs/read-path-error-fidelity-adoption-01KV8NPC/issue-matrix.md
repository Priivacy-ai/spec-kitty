# Issue matrix — read-path-error-fidelity-adoption-01KV8NPC

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per GitHub issue referenced in spec.md.
`in-mission` rows are being fixed by a WP in this mission — they pass per-WP `approved` but MUST be
terminalized (`fixed`) before mission `done`/merge.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #15 | `next` collapses ActionContextError → MISSION_NOT_FOUND (P0) | fixed | WP02 (lane-b): typed-error pass-through across the next-family catch-sites; closes with no resolver change |
| #14 | STATUS_READ_PATH_NOT_FOUND reclassified/lost across callers | fixed | WP02: code+checked-paths preserved end-to-end |
| #12 | explicit-resolution failure flattened into generic "pass --mission" | fixed | WP02: typed code surfaced, not flattened |
| #11 | #2007 bug-index: fail-closed pre-read gates the primary read | fixed | WP03: finalize-tasks anchored on primary root (tracked under epic #2010); not a standalone GH issue |
| #1832 | `agent action implement` "no workspace could be resolved" | fixed | WP05 (lane-e): implement consumes the claim's already-resolved context (single resolution path) |
| #2011 | submodule/root misresolution (C6, launch-blocker) | fixed | WP06 (lane-f): `resolve_canonical_root` stops at the submodule boundary; real-submodule fixture, captured-red, 165 core tests green |
| #1884 | setup-plan entry gate coordination-blind: is_committed checks only HEAD (bug #7 tracker) | fixed | WP03: primary-target-branch leg added to `is_committed` + diagnostics |
| #1889 | decision open crashes (StatusReadPathNotFound) on coord-aware handle (bug #8 tracker) | fixed | WP04: delete escape-walk for resolved paths + structure the typed error (cmd_open + cmd_verify/M5) |
| #1692 | context resolve rejects primary mission dir when coord worktree absent (fail-closed-pre-read class) | fixed | WP02/WP03: typed pass-through + primary-anchored read |
| #1911 | restore richer query-mode error `next_step` lost in #1910 | fixed | WP02: emitter surfaces the typed code + actionable remediation |
| #1914 | governed/gate ops must be no-op-stable (read-path/status-read slice) | deferred-with-followup | WP07 (lane-g): charter status side-effect-free; broader umbrella stays on its own track |
| #2010 | [2007/C3] read-path resolver unification (umbrella) | fixed | Delivered across WP02/WP03/WP04/WP05/WP09 (single-authority adoption, FR-011) |
| #1619 | unify execution context / runtime-state SSOT (epic) | deferred-with-followup | WP01 (lane-a): ExecutionContext builder-hardening + single context factory + freeze + invariant (the bounded #1619 slice; flat-substrate retirement deferred) |
| #1827 | merge post-merge baseline circular failure | verified-already-fixed | WP08 (lane-h): full record→commit→assert + resume regression test passes on HEAD; falsification guard proves the broken ordering fails (D-3, no code fix) |
| #2012 | naming/identity routing rider (the mid8 SSOT seam) | verified-already-fixed | Merged to upstream/main; this mission adopts the seam it shipped (factory calls `branch_naming`) |
| #1990 | resolve spec.md from primary checkout in map-requirements | verified-already-fixed | Merged fix for #1981/#1982; the read-path adoption (WP02/03) consumes the canonical primitive it routes through |
| #1910 | query-mode error reconciliation (dropped `next_step`) | verified-already-fixed | The reconciliation landed as intended; the `next_step` restoration is tracked as #1911 (in-mission, WP02) |
| #1716 | coordination topology authority (write-side) | deferred-with-followup | DEFER entirely (D-1, decision `01KV8Q49WEG…`); becomes Mission B = write-side adoption against the frozen factory seam (#1878). See `docs/engineering_notes/context-factory-readwrite-symmetry/00-SYNTHESIS.md` |
| #1868 | complete the canonical naming/identity seam (epic) | deferred-with-followup | Advanced by WP01's factory + WP06's root unification; the epic stays open for the write-side seam adoption. Follow-up: #1868 (write-side adoption = Mission B / #1716 track) |
| #2007 | Epic: 3.2.0 training bugs (Robert) | deferred-with-followup | This mission delivers the read-path/error-fidelity class (#2010 + #2011); non-overlap (#2008/#2009/#1890/#1891) stays separate per Robert's alignment rules |
| #1981 | map-requirements resolves spec.md against coord worktree | deferred-with-followup | Fixed by #1990 (merged); verifying the fix routes through the SSOT is a read-side spot-check — no WP owns map-requirements in this bounded scope |
| #1971 | consolidate 3-way `locate_project_root` split-brain | deferred-with-followup | Sibling to FR-007/#2011 (which pins `resolve_canonical_root`); the 3-way consolidation is its own follow-on — #1971 alone is insufficient and not in a WP's owned files |
| #1888 | phantom-path ownership validation existence check | deferred-with-followup | Owned by the prior naming-rider verify-close; provenance flag — `00-OVERVIEW.md` wrongly says it "landed as #1886" (#1886 is a different issue); not this mission's scope |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this mission; must reach a terminal verdict before mission `done`).
