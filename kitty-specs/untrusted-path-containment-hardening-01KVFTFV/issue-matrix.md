# Issue matrix — untrusted-path-containment-hardening-01KVFTFV

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2036 | Untrusted-segment→FS sink containment (rides PR #2036) | fixed | WP01 audit `tests/architectural/untrusted_path_audit/inventory.md` (102f98ec9) enumerates 13 `routed-through-seam (TODO)` sinks routed to WP02/WP03; fixes land across WP02–WP04. Terminal verdict due before mission `done`. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
