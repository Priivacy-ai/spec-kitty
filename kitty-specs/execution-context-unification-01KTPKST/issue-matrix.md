# Issue matrix — execution-context-unification-01KTPKST

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

`in-mission` = being fixed by a WP in this mission (non-terminal; must reach a terminal verdict before
mission `done`). Directly-fixed issues carry the owning WP. Parent/advances/out-of-scope issues carry a
documented follow-up (`deferred-with-followup`) since this mission does not close them.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1666 | Execution-state & context domain-boundary redesign (parent epic) | deferred-with-followup | Follow-up: #1666 — parent epic; this mission is one slice, epic stays open |
| #1619 | Runtime/state overhaul (root) | deferred-with-followup | Follow-up: #1619 — root overhaul; closed separately at completion |
| #1814 | record-analysis deadlock on coord residue | fixed | WP06 (FR-004/FR-009) — placement via context; SC-2 mutation-tested |
| #1816 | implement-claim blocked by planning-artifact branch-split | fixed | WP06 (FR-004) — CommitTarget-driven placement, no primary↔coord split |
| #1789 | Sync daemons + dashboard re-materialize status.json during git ops (+ daemon leak) | fixed | WP11 (dashboard read-only) + WP12 (daemon singleton) — both halves |
| #1071 | Sync daemon singleton leaking multiple daemons across checkouts (regression) | fixed | WP12 (FR-014b) — one-per-host/auth-scope + reaper at spawn |
| #1062 | git-op status clobber (sibling of #1789) | fixed | WP07 (FR-005) — git-op guard on materialize_if_stale |
| #1572 | status visibility skew primary↔coord | fixed | WP02 (FR-008) — single status surface |
| #1737 | status_transition re-derives coord path independently | fixed | WP02 (FR-008) — `_identity_for_request` consumes canonical surface |
| #1357 | CoordinationWorkspace.resolve not lock-serialized | fixed | WP02 (FR-008) — path-keyed lock, deadlock-free |
| #1735 | retrospect reads from wrong (primary) surface | fixed | WP08 (FR-006) — routed through resolve_status_surface |
| #1771 | retrospect writes to gitignored location | fixed | WP08 cycle-2 (FR-006) — record relocated to tracked kitty-specs/<mission>/; git check-ignore test |
| #1736 | merge coord-topology seams (PATH/env, baking) | verified-already-fixed | WP08 audit — seams already consume resolve_status_surface (strangled by WP02-07) |
| #1770 | merge mixed-JSONL coord handling | verified-already-fixed | WP08 audit — already context-resolved (WP02-07) |
| #1764 | analysis-report staleness keying false-stale | fixed | WP06/WP07 (FR-009) — context-aware staleness key |
| #1815 | occurrence-map can't model multi-path structural moves | fixed | WP10 (FR-010) — `moves:` schema, backward-compatible |
| #1622 | dead `coordination/status_service` symbols (#391 slice) | fixed | WP09 — 2 genuinely-dead symbols deleted; 3 became live facade internals post-#1614 rebase, de-exported from `__all__` (gate-prescribed). Premise of "5 dead" was stale; resolved to the extent they were dead |
| #391 | doctrine/debt dumping-ground epic | deferred-with-followup | Follow-up: #391 — only the dead-symbol slice (#1622) addressed via WP09; #1623/#1624 remain deferred |
| #1168 | Beads state backend | deferred-with-followup | Follow-up: #1168 — Beads backend, 3.3.0 replacement (out of scope here) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
