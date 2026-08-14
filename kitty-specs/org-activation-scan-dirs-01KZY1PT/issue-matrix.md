# Issue matrix — org-activation-scan-dirs-01KZY1PT

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3385 | `_org_scan_dirs` scans a phantom layout: one `charter activate` silently drops every org-pack artifact from the DRG | fixed | `dcc4f0c57` (red-first regression), `c88dd78dd` (fix) |
| #3384 | Org pack without a root-level `*.graph.yaml` silently zeroes ALL action-scoped doctrine | deferred-with-followup | Out of scope by design (spec.md: D1 is verification-only). Owned by a sibling upstream mission; this mission adds no competing fix. Follow-up: #3384 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
