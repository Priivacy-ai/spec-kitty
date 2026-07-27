# Issue matrix — read-side-surface-resolver-adoption-01KVJPEQ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2046 | Read-side desync residual: operator read CLIs bypass the canonical surface resolver | fixed | All 8 direct read-path callers routed through `resolve_handle_to_read_path` (WP02/WP03, lanes 7957a832c/b07c6c579); CLI bare-slug-coord e2e proves coord resolution (WP06, lane 2b101b828). |
| #2007 | Read/write surface desync epic — READ side | deferred-with-followup | READ side closed by this mission (seam adoption WP01–WP06). The aggregate-seam `CoordAuthorityUnavailable` error-type convergence (2 `*/slug-mid8` cells) remains the named follow-on per FR-008 — out of scope here, tracked under the epic. |
| #1718 | Create→first-write window must resolve PRIMARY | verified-already-fixed | NOT regressed — seam routes via existence-gated `resolve_mission_read_path`, NEVER the coord-composing surface; WP01 unit test (c) + WP06 create-window invariant (lane 2b101b828) both bite under mutation. |
| #2045 | Draft PR (single-mission-surface-resolver) — superseded by combined branch | fixed | PR closed as superseded; this stacked branch lands 01KVGCE8 + #2046 together (its intent is delivered here). |
| #1993 | Extraction-without-adoption shadow-path risk | fixed | C-003 honored — read paths routed THROUGH the seam, no new parallel resolver; WP05 selection-authority AST ratchet (lane 397912771) fails CI on any new bypass. |
| #1868 | Canonical seams "exist in name only" | fixed | WP05 selection-callsite discriminator binds read SELECTION to the seam (catches direct `resolve_mission_read_path` calls the raw-JOIN guard misses); mutation-proven. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
