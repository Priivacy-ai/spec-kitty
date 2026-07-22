# Issue matrix — mission-type-doctrine-authority-01KXH6GE

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #883 | Add mission-type governance profiles for non-software missions | deferred-with-followup | Partial close (spec.md §"#883 Coverage"): layered mission-aware governance (project_charter ⊕ shipped_mission_type ⊕ project_override), software-dev-default leak closure, doc/research/plan governance authoring, and the doctrine-as-authority swap DELIVERED across WP01–WP12. The mission-instance addendum layer + live action-grain union are deferred to #2651. No auto-close keyword. |
| #461 | EPIC: Charter as Synthesis & Doctrine Reference Graph | deferred-with-followup | Advanced (slice 1 of the doctrine→charter→core unification, ADR 2026-07-14-2); remaining epic scope continues in #2652. |
| #901 | Epic: Spec Kitty 4.0 central /spec-kitty governed front door | deferred-with-followup | Advanced (per-mission-type governance is the substrate for intent-scoped loading); epic continues, retirement slices tracked in #2652. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Follow-ups filed
- **#2651** — Mission-type resolution: union live action-grain into `ResolvedGovernance` (so FR-013 fires on live content) + the mission-instance governance addendum layer (#883 AC6) + minor cleanups.
- **#2652** — `specify_cli/missions` retirement, slice 2+ (templates, enumeration, `mission.py` sw-dev fallback, tree deletion).
