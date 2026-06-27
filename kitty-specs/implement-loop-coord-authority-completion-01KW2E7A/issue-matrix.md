# Issue matrix — implement-loop-coord-authority-completion-01KW2E7A

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2115 | Implement/review/merge surface reads WP tasks/ off coord (dir-read residual) | in-mission | CLAIMED — routed across WP03–WP06 (FR-001/002/003/004/005/006/009); terminal at mission done |
| #2140 | Verify is_committed spec-read surface post-write-surface-coherence | in-mission | CLAIMED — WP08 docstring + negative caller-contract pin (FR-010); terminal at done |
| #2183 | Teach is_def_use_canonical about _canonicalize_bare_modern_handle fold | in-mission | CLAIMED — WP07 discriminator fold + floor recompute (FR-011/012); terminal at done |
| #2160 | Coord topology: unify artifact authority (parent epic) | deferred-with-followup | Reference-only parent epic; stays open until #2185/#2186 + this mission land (C-006) |
| #2017 | Workflow guards lacking depth / blocking in-flight actions (umbrella) | deferred-with-followup | Reference-only investigation umbrella; flat-mission + lane-base friction noted in tracer (Follow-up: #2017 stays tracked) |
| #1716 | Planning-phase coordination-topology coherence (epic) | deferred-with-followup | Reference-only sibling epic; this mission is the named implement-loop follow-on (Follow-up: #1716 stays tracked) |
| #1878 | Post-3.2.0 coordination-placement strangler (umbrella) | deferred-with-followup | Reference-only umbrella (Follow-up: #1878 stays tracked) |
| #2173 | Infrastructure-to-logic separation (parent of #2183) | deferred-with-followup | Reference-only; #2183 is its child, folded here |
| #1619 | Runtime/state overhaul (root epic) | deferred-with-followup | Reference-only root epic (Follow-up: #1619 stays tracked) |
| #2185 | Sibling mission: route merge/+lanes/ lanes.json reads | deferred-with-followup | Filed by this mission (FR-015); pinned in _DIR_READ_KNOWN_RESIDUALS (Follow-up: #2185 stays tracked) |
| #2186 | Identity-read-routing (meta.json off coord, next_cmd telemetry) | deferred-with-followup | Filed by this mission (FR-015); pinned in ratchet (Follow-up: #2186 stays tracked) |
| #2106 | Write-surface coherence (planning artifacts → primary) | verified-already-fixed | Landed; the premise this mission builds on (background context) |
| #2181 | Single-Authority Resolution Gates (Phase 1) | verified-already-fixed | Merged to upstream/main 551044214; this mission consumes its seam |
| #2155 | safe_commit refuses coord-owned status writes | verified-already-fixed | Closed by #2181 (Phase 1 seed child) |
| #1848 | Coord-deleted structured hard-fail transient | verified-already-fixed | Existing behavior preserved (C-002); referenced as a KEEP invariant |
| #1622 | coordination.status_service dead-symbol debt | deferred-with-followup | Out of scope (C-007); tracked separately (Follow-up: #1622 stays tracked) |
| #1623 | doctor.py god-module split | deferred-with-followup | Out of scope (C-007); tracked separately (Follow-up: #1623 stays tracked) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
