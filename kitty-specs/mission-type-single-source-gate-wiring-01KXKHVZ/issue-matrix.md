# Issue matrix — mission-type-single-source-gate-wiring-01KXKHVZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2669 | Consolidate the 3 hardcoded mission-type rosters onto the `MissionTypeRepository` source of truth | in-mission | FR-001..FR-006 (spec.md). Single-source accessor + derivation of Rosters A–E (2 extra rosters folded in per operator decision). Terminal verdict due before mission `done`. |
| #2667 | `load_action_index` should fail loud on a malformed-but-parseable action index | in-mission | FR-007/FR-008 (spec.md). Present-but-invalid raises `ActionIndexError`; missing file stays silent fallback. |
| #2666 | Wire the cross-grain integrity scan into `spec-kitty doctor` / a CI arch gate | in-mission | FR-009/FR-010/FR-011 (spec.md). `doctor doctrine` runtime caller + `__all__` re-add + CI structural gate. |
| #2668 | Promote `MissionTypeProfileRepository._default_built_in_dir` to a public `builtin_missions_root()` accessor | in-mission | FR-012 (spec.md). Public accessor, drop 2 SLF001 bypasses; single-class scope (C-005). |
| #2652 | EPIC: specify_cli/missions retirement — slice 2+ (activation-driven availability, single canonical mission-type source) | deferred-with-followup | Parent epic (spec.md). This mission is the roster-consolidation + gate-hardening slice only; provisioned default charter (#2657) and activation-driven enumeration (#2659) remain open under the epic. |
| #2651 | mission_type as a first-class DRG node + cross-grain integrity gate + lazy resolver seam (slice 1) | verified-already-fixed | Merged via PR #2664 (spec.md "Continues"). This mission builds on the shipped gate/seam; #2651 itself is not re-addressed. |
| #2664 | PR — slice-1 implementation of #2651 (the merged base this bundle follows up) | verified-already-fixed | Merged to upstream/main (HEAD 4e1e8ed34). Referenced as the design/base; not reopened. |
| #2657 | Provisioned default charter (external blocker under #461) | deferred-with-followup | Referenced in spec.md as the larger-arc pivot (retiring "all built-in doctrine" default). Out of scope; Follow-up: #2657 (separate mission under #461). |
| #2659 | Activation-driven enumeration + mission-runtime template discovery (epic sub-issue, blocked by #2657) | deferred-with-followup | Referenced in spec.md Out of Scope; this bundle is the roster-consolidation slice only. Follow-up: #2659 (blocked by #2657, under epic #2652). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Out-of-scope follow-ups to file (post-merge)

- Project/org-tier override collision coverage for the cross-grain scan (blocked on a multi-root action-index engine) — new issue under #2652.
