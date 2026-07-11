# Phase 0 Research: Coord-Authority Trio Degod

Grounded by the post-spec squad (feasibility/opus, related-issues/priti, adversarial/renata), 2026-07-11. All decisions are code-verified.

## Decision 1 — the partition authority is ALREADY central; the work is entry-point routing
- **Decision**: Do NOT build a new resolver. The coord/primary decision is already centralized (`missions/_read_path_resolver.py` + `mission_runtime/resolution.py::PlacementSeam`; raw `KITTY_SPECS_DIR` joins already arch-banned by `test_no_raw_mission_spec_paths.py`). The residual #2160 surface is the trio selecting among **six** resolver entry points across **~33 leaf call sites**. Route them onto the kind-aware `placement_seam.read_dir(kind)` projection + write twin.
- **Rationale**: "one resolver in the tree" is either already true (redundant work) or would drag in 12+ non-trio callers (violates C-004). The honest scope is trio-local routing + an arch pin on seam-only consumption.
- **Alternative rejected**: collapsing to a single resolver function — drops the three distinct read contracts (below).

## Decision 2 — preserve THREE distinct read contracts
- **Decision**: The seam offers three legitimately-distinct contracts that must survive: (a) lenient kind-aware `placement_seam.read_dir(kind)`; (b) fail-closed guarded `resolve_handle_to_read_path(require_exists=True)` (raises for the #1848 data-loss class); (c) topology-blind primary anchor `primary_feature_dir_for_mission`. Folding (b)/(c) into (a) drops data-loss protection / re-opens the coord-follow class.
- **Rationale**: unification-not-parity discipline — don't drop load-bearing invariants for a tidier signature.

## Decision 3 — S3776 is the complexity gate of record; ruff C901 is blind
- **Decision**: Measure/verify complexity with **Sonar S3776** (in-PR SonarCloud branch review), NOT ruff C901. Verified: `ruff --select C901` passes on all three modules even at threshold 5 despite radon CC 78 on `workflow.implement`. A post-refactor CC-40 core would pass ruff green — a false gate.
- **Rationale**: "gate-unmask cannot self-validate" — the gate must actually detect the target functions. FR-007 arch tests pin structure (seam/ports/purity), not complexity.

## Decision 4 — characterization FIRST, not naive byte-diff
- **Decision**: FR-008 authors the behaviour lock against pre-refactor code as WP1. No existing harness covers the trio's CLI surfaces. Strategy: (i) pure-core in→out; (ii) JSON envelope (`_json_safe_output`) with SHA/timestamp/path normalized; (iii) status-event-reducer transition pins. Byte-identical CLI assertions are infeasible (SHAs/timestamps/paths).
- **Rationale**: without a pre-built lock, characterization tests written after the refactor pin nothing (false-green, DIRECTIVE_041).

## Decision 5 — fold #2508 (the #2160-class read-source bug), sequence #2463 after
- **Decision**: #2508 (`_load_coord_branch_meta` reads coord husk not primary) is in the exact extraction target and IS the #2160 class — fold it (FR-010, red-first). #2463 (legacy-mission retirement) is deliberately sequenced AFTER this mission (real rebase collision in `_read_path_resolver.py`/`resolution.py`).

## Decision 6 — NFR-003 LOC is a target, not a gate; Typer shell stays impure
- **Decision**: ~800 LOC is a target + "no new god-object", not a hard gate — the #2308 template itself exceeds it (`tasks_move_task.py` 1817). Complexity/cohesion is the primary gate. The Typer `@app.command` shell (~150-200 LOC of `Annotated` params) stays impure; cores take a request dataclass.

## Out of scope (confirmed)
Non-trio resolver callers (already routing), other god-modules (#2531/#2532/sync/emitter/queue/orchestrator_api), accept.py residual-commit (#2482), same-family coord-shadow bugs in other modules (#2510/#2512/#2502), unshim burn-down (#2293/#2322/#2323).
