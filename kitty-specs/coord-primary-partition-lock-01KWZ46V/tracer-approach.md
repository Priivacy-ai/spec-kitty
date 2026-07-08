# Tracer: approach evolution

Append dated entries when the approach shifts; assess at close.

- **[specify] Seeded late (2026-07-08).** Retroactive initial context below.
- **Initial approach:** deliver the open functional roadmap slice (incoming PRs saturate DevEx/CI) — the coord/primary artifact-placement class. Selected as the **bounded #1716 opener** (materialize-at-create + golden-path test + setup-plan transaction routing).
- **Shift 1 (post-spec squad):** the bounded opener was largely **obsolete** — #2106/#2113 already reversed #1716's premise to planning-on-primary. Reframed to *complete + lock the existing placement SSOT* (extend, not build).
- **Shift 2 (operator decisions):** grew scope back up — whole #1878 write-side strangler → 3.2.x, and this mission is **authoritative** over sibling surfaces (they rebase onto it). C-005 inverted.
- **Shift 3 (operator constraint):** route BOTH read and write through the one topology-aware seam; the seam returning PRIMARY is not license to bypass it.
- **Shift 4 (post-tasks squad + rebase):** FR-005 **scoped down** to the ~5 named checkout-derived write bypasses; the broad `resolve_feature_dir_for_mission` read-site sweep (~71 sites) + `coord_authority` drain → deferred to **#2453**. FR-012 husk subsumed by #2062 (verify-only). WP08 #2429 gate moot.
- **Execution:** 9 WPs / 9 lanes; WP01 seam foundation → routing (WP02-05) → ratchet+char lock (WP07/08); WP06 bug/husk + WP09 docs parallel. Implementers sonnet, reviewers opus.
