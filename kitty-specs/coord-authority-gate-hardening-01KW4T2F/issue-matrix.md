# Issue matrix — coord-authority-gate-hardening-01KW4T2F

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

**Addressed by this Mission:** #2214 (call-shape arm cross-function blind-spot), #2197 (runtime_bridge next-query routing + scan-scope), #2198 (partition-stability gate verify-annotate), #2199 (coord-husk pre30 no-op test). The rest are context/boundary/lineage and are not closed here.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2214 | Call-shape arm cross-function blind-spot (parameter/attribute-passed coord dirs) | fixed | FR-001/002/003/008. One-hop param + ast.Attribute branch `test_gate_read_literal_ban.py` (`callshape_violations(..., module=)`, `_COORD_AWARE_CALLSHAPE_RESOLVERS` widened); live residual proof `test_coord_read_residuals_closeout.py::test_fr001_documentation_wiring_residual_is_pinned_and_flags` (pinned #2214 + live-flagged); SC-006 both shapes `test_sc006_executor_identity_reads_in_scope_both_shapes`. Merge 2399e2e (#152). The production routing of `_run_documentation_wiring` is deferred per C-003 (gate now catches it statically) — pinned shrink-only under #2214 |
| #2197 | Route the spec-kitty-next claimable-preview read (runtime_bridge) + gate it | fixed | FR-004/005. Caller-only leg-split `runtime_bridge.py:3090` (`resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` + coord `status_dir=candidate_feature_dir_for_mission`); behavioral SC-002 revert-fails `tests/integration/test_next_preview_primary_routing.py`; runtime/next scan-scope + non-vacuity floor `test_coord_read_residuals_closeout.py::test_fr005_runtime_next_floor_fails_if_scope_reverted`. Merge 2399e2e |
| #2198 | Arch-gate: guard MissionArtifactKind PRIMARY/STATUS partition stability | fixed | FR-006 net-new. Machine-read `PARTITION_RATIONALE` map + `test_partition_rationale_split_matches_live_frozensets` + all-load-bearing-kinds anti-mutant `test_write_surface_placement_guard.py`. CT7 exemplar (allowlist-free, no line-pins). Merge 2399e2e |
| #2199 | Test gap: check_pre30_layout against a STATUS-only coord husk | fixed | FR-007. `tests/integration/test_pre30_layout_coord_husk_noop.py` — production-shaped STATUS-only husk + tasks/-present-non-legacy variant, no-raise AND no-mutation (rglob snapshot), both `is_legacy_format` branches. Merge 2399e2e |
| #2160 | Coord topology: unify artifact authority (epic) | deferred-with-followup | Follow-up: #2160 — parent epic, umbrella, reference-only; stays open |
| #2077 | CT7: test-hygiene gate doctrine + recurrence guard | deferred-with-followup | Follow-up: #2077 — this Mission conforms to + cross-cites CT7; #2198 becomes its content-anchored exemplar (C-004) |
| #2071 | Epic: Tests as scaffold, not friction | deferred-with-followup | Follow-up: #2071 — governing test-hygiene epic; this Mission reduces (not adds) friction (NFR-005), does not absorb the broader remediation |
| #2167 | Retire pre-3.0 scripts/tasks legacy reader | deferred-with-followup | Follow-up: #2167 — separate legacy cleanup; coordinate the shared shrink-only `_DIR_READ_KNOWN_RESIDUALS` pin (C-005) |
| #2017 | Lane status-desync / workflow-guard friction | deferred-with-followup | Follow-up: #2017 — guard-friction umbrella; tracer tooling-friction items land here, not #2071 |
| #1057 | Pre-3.0 reader retirement / layout guard (the #2199 lineage) | verified-already-fixed | closed; #2199 covers the untested coord-husk no-op path it left, re-homed under this Mission |
| #2155 | Write-side STATUS/PRIMARY authority (no status leg routed to PRIMARY) | verified-already-fixed | Write-side canonical authority delivered with #2154/#2155 (spec.md §Context); preserved here as the C-001 boundary ("no #2155 re-opener") — this Mission must not move a status leg, not re-fixed here |
| #2194 | Prior coord-authority mission (lineage/context) | verified-already-fixed | Prior coord-authority mission already merged (spec.md: "Both prior coord-authority missions (#2194, #2212) are merged"); context/lineage, not closed here |
| #2212 | Prior coord-authority mission — pre-merge squad seeded this Mission's scope | verified-already-fixed | Prior coord-authority mission already merged; its pre-merge adversarial squad surfaced the static-gate residuals this Mission hardens (spec.md §Context). Lineage/context, not closed here |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this Mission; must reach a terminal verdict before Mission `done`).

**Claim:** #2214/#2197/#2198/#2199 to be assigned to the operator + a mission-naming comment posted on each at spec-commit (ticket-based mission hygiene). #2160 epic is operator-owned and reference-only.
