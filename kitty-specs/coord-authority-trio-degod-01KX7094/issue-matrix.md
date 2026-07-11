# Issue matrix — coord-authority-trio-degod-01KX7094

Per FR-037 of the spec-kitty-mission-review skill Gate-4. Terminalized at mission close (2026-07-11).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2464 | workflow.py S3776 complexity (implement/review) | fixed | WP02: `implement` radon 78→11, `review` 72→7, `_resolve_review_context` 37→8; all ≤15; zero trio noqa:C901. |
| #2465 | Consolidate trio onto the kind-aware read seam | fixed | WP02/03/04 route the trio's leaf calls onto `placement_seam`/`resolve_handle_to_read_path`; WP05 `test_trio_seam_only.py` pins seam-only consumption (non-vacuous). |
| #2508 | Identity-meta read off coord husk (safe_commit misfire) | fixed | WP02 red-first repro via the real command entry (fails pre-fix), then anchors `_load_coord_branch_meta`/`_commit_workflow_change` on PRIMARY. |
| #2160 | Coord-authority split-brain remediation (P0) | deferred-with-followup | Wave 2 (structural degod) advances #2160; trio now consumes one seam. Epic stays open for the remaining coord-shadow bugs (#2510/#2512/#2502). |
| #2173 | Infra/logic separation (ports) epic | deferred-with-followup | Advanced: trio decomposed into ports façade + pure cores + executor (FR-007 arch-pinned). Epic remains open. |
| #1619 | Runtime/state overhaul umbrella (P0) | deferred-with-followup | Progressed by the trio decomposition; umbrella remains open. |
| #2494 | MissionResolver port (pattern lineage) | verified-already-fixed | Merged prior mission; referenced as the template followed — not modified. |
| #2308 | tasks.py degod (pattern lineage) | verified-already-fixed | Merged prior mission; referenced as the template — not modified. |
| #2164 | Canonicalizer gate (Wave 2 lineage) | verified-already-fixed | Already closed; the trio is the remaining Wave-2 deliverable. |
| #2482 | accept.py residual-commit path | deferred-with-followup | Explicit Out of Scope (different module than `acceptance/__init__.py`); untouched. |
| #2531 | runtime_bridge.py god-module decompose | deferred-with-followup | Filed this session (un-ticketed-gap fill); separate later wave. |
| #2532 | charter/context.py god-module decompose | deferred-with-followup | Filed this session; separate later wave. |
| #2463 | Legacy-mission retirement | deferred-with-followup | Explicit Out of Scope — deliberately sequenced AFTER this mission (rebase collision in the resolver files). |
| #2510 | Coord-shadow bug (status/emit) | deferred-with-followup | Same bug family as #2508, different module; out of scope. |
| #2512 | Coord-shadow bug (lane allocator) | deferred-with-followup | Different module; out of scope. |
| #2502 | Coord-shadow bug (dashboard handlers) | deferred-with-followup | Different module; out of scope. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (must reach a terminal verdict before mission `done`).
