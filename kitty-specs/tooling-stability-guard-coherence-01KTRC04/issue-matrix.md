# Issue matrix — tooling-stability-guard-coherence-01KTRC04

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

`in-mission` = being fixed by a WP in this mission (non-terminal; must reach a terminal verdict —
`fixed` / `verified-already-fixed` / `deferred-with-followup` — before mission `done`). Parent/out-of-scope
rows carry a documented `Follow-up: #NNN` handle.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1819 | record-analysis verdict substring-counts severity keywords | fixed | WP06 (approved): analysis-findings/v1 structured frontmatter carrier; infer_verdict/infer_issue_counts prose-substring inference deleted; severity reuses SEVERITY_ORDER |
| #1820 | safe-commit ergonomics: dir args rejected; --to-branch infer misfires | fixed | WP04 (approved): dir/bulk expansion + per-file report; explicit --to-branch honored; SPEC_KITTY_INFER_DESTINATION_REF retired; xfail repros flipped to pass |
| #1821 | thread carried StatusSurfaceFragment through MissionStatus.load + status_transition | fixed | WP07 (approved): resolve_status_surface_with_anchor threads the carried fragment through MissionStatus.load + status_transition — single resolution path |
| #1796 | Epic: safe-commit / protected-branch guard coherence | fixed | WP02+WP03 (approved): single pure policy core/commit_guard.py::evaluate behind the safe_commit facade; five privilege channels deleted; WP10 ratchet enforces permanently |
| #1334 | safe_commit() still honors message-prefix protected-branch | fixed | WP03 (approved): _is_protected_branch_exception message-prefix list DELETED; WP01 repro flipped xfail(strict)→pass at deletion; WP10 ratchet asserts zero refs |
| #1777 | /spec-kitty.specify: safe-commit refuses spec.md commit on protected branch | fixed | WP05 (approved): planning commits route through resolve_placement_only → resolved non-protected destination; zero guard relaxation; SC-6 e2e green |
| #1784 | 3.2.0rc40: finalize-tasks branch-model catch-22 (planning artifacts) | fixed | WP05 (approved): single placement authority (C-GUARD-3a); _resolve_planning_branch commit-destination authority retired; catch-22 e2e repro green (F-001 live instance recovered) |
| #1631 | Protected branch handling | fixed | WP02+WP03+WP05 (approved): one GuardCapability channel asserted at the surface; protection preserved (WP01 invariants 9 passed/0 xfail) |
| #1330 | safe-commit path handling for directory and bulk commit guidance | fixed | WP04 (approved): directory args expand to contained dirty files with per-file commit report (folded — #1796 child) |
| #1355 | tighten test_safe_commit_import_boundary once callers fixed | fixed | WP10 (approved): ratchet tightened — evaluate importers pinned to {commit_helpers, coordination/policy}; deleted-channel refs = 0; destination_ref shim allowlisted to merge.py only; strictness proven by 3 rogue-injection proofs + reviewer's independent proof |
| #1623 | [DIRECTIVE_013] doctor.py god-module: extract doctrine health-render | fixed | WP08 (approved): _profile_health_render.py extracted (337 LOC pure move); doctor.py 3271→3011 lines. Epic-level split continues upstream; this slice delivered |
| #1624 | [DIRECTIVE_013] merge.py: type the _tag_source provenance sidecar | fixed | WP09 (approved): declared provenance:str\|None field on DRGNode/DRGEdge (D2-revised); object.__setattr__ sidecar deleted; mypy --strict clean; graph.yaml byte-stable |
| #1619 | Epic: Unify mission execution context across coord/main/lane topology | deferred-with-followup | Follow-up: #1619 — parent epic; this mission is one slice, epic stays open |
| #1738 | issue-matrix completeness gate scans only spec.md | deferred-with-followup | Follow-up: #1738 — different surface (review-gate), explicitly out of scope here |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.
