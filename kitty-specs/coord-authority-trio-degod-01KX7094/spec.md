# Mission Specification: Coord-Authority Trio Degod

**Mission**: coord-authority-trio-degod-01KX7094
**Type**: software-dev
**Closes**: #2464, #2465, #2508 · **Advances**: #2160 (artifact-authority split-brain, P0), epic #2173 (infra-logic separation), epic #1619 (runtime/state root, P0)
**Status**: Draft (hardened by post-spec squad 2026-07-11)

## Purpose (stakeholder-facing)

**TL;DR**: Break up the three coord-authority god-modules into injectable ports + pure cores so mission-lifecycle logic is testable, and make the trio consume the **already-central** coord/primary partition authority through one kind-aware seam instead of 33 hand-picked leaf calls.

The commands that drive the mission lifecycle — `agent/workflow.py` (2997 LOC), `implement.py` (1639 LOC), and `acceptance/__init__.py` (1737 LOC) — have each grown into god-modules with deeply complex command bodies. The coord/primary partition authority is **already centralized** (`missions/_read_path_resolver.py` + `mission_runtime/resolution.py::PlacementSeam`; raw `KITTY_SPECS_DIR` joins are already arch-banned) — but the trio reaches into it through **six different resolver entry points across ~33 direct leaf call sites**, and that inconsistent entry-point selection is the residual surface of the **#2160 artifact-authority split-brain** (e.g. #2508: identity meta read off the coord-worktree husk instead of primary). This mission decomposes the three modules **behaviour-preservingly** into a ports façade (infra injected as data), deterministic pure cores, and thin executor/renderer/Typer-shell layers — following the shipped **MissionResolver port (#2494)** and **tasks.py degod (#2308)** patterns — and routes the trio's leaf calls through the one kind-aware seam while **preserving the distinct read contracts** that seam already offers.

## Context & Motivation

Wave 2 of the degod roadmap (`docs/plans/3-2-x-milestone-roadmap.md`; the canonicalizer gate #2164 already closed → the trio is the remaining Wave-2 deliverable). Two open sub-tickets plus one live bug are symptoms of the same god-module + entry-point debt:

- **#2464** — `workflow.py`'s `implement` (radon CC 78, `@app.command` @1378) and `review` (CC 72, @2431) bodies carry Sonar **S3776 cognitive complexity 109/102**. (Note: these are **not** `# noqa: C901`-annotated and ruff's mccabe is blind to them — see NFR-002.)
- **#2465** — the trio selects among six read-resolver entry points across ~33 leaf call sites; consolidate the trio onto the one kind-aware `placement_seam(...).read_dir(kind)` projection (+ its write twin), preserving the guarded/blind contracts.
- **#2508** — `_load_coord_branch_meta` (`workflow.py:276`) reads mission identity off the coord-worktree husk instead of primary, misfiring the legacy `safe_commit` fallback in `_commit_workflow_change` (`workflow.py:571`) — a concrete instance of the #2160 class, in the exact functions this mission extracts.

This is **structural decomposition + the #2160-class read-source fix**, not a lifecycle-feature change. It advances #2173 (ports + pure cores) and unblocks #1619.

## User Scenarios & Testing

**Primary actor**: a Spec Kitty maintainer changing mission-lifecycle behaviour (or fixing a coord/primary bug).

**Primary scenario**: To change how a lifecycle transition resolves its artifact surface, a maintainer today edits a 1600–3000-line command body and must know which of six resolver entry points is correct. After this mission, the lifecycle logic lives in deterministic pure cores (unit-testable without a repo), the command is a thin Typer-shell + executor over injected ports, and the read surface is reached through the one kind-aware seam.

**Behaviour-preservation scenario**: Every existing lifecycle behaviour — `agent action implement/review`, `spec-kitty implement`, `spec-kitty accept`, the workflow `next`/decision loop, including rejection/rewind/resume — produces identical outputs (modulo non-deterministic SHA/timestamp/path fields) and identical mission-state transitions before and after the decomposition. The **exception** is the #2508 read-source fix, which is an intentional #2160-class correction pinned by a red-first repro.

**Partition-authority scenario**: The trio consumes the coord/primary read surface only through the seam's kind-aware projection and its guarded/blind siblings — never a raw leaf primitive. An arch test forbids the trio importing leaf resolvers directly, and the three distinct read contracts remain intact.

### Acceptance Scenarios

1. **workflow.py decomposed**: `implement` (CC78), `review` (CC72), and `_resolve_review_context` (CC37) are split into a Typer-shell + request dataclass + pure cores + a commit executor; each resulting function is ≤15 Sonar S3776.
2. **implement.py decomposed**: the two `# noqa: C901` bodies (`_ensure_planning_artifacts_committed_git`:756, `implement`:1105) are split into staging-decision cores + git executor + Typer-shell; both `noqa` suppressions are removed (not relocated).
3. **acceptance decomposed**: the matrix/readiness logic (`collect_feature_summary`:1212 CC25, `_build_recommended_fix_order`:1168 CC22, `_check_lane_gates`:965 CC19) is extracted into pure cores (e.g. `summary_core`/`gates_core`); the CLI/commit path is a thin executor.
4. **Seam consolidation (#2465)**: the trio's ~33 leaf call sites route through the kind-aware `placement_seam.read_dir(kind)` projection and its guarded/blind siblings; an arch test pins trio **seam-only consumption** (no direct leaf-primitive imports). The three read contracts (a/b/c below) are preserved.
5. **Characterization gate**: a characterization suite pinning the trio's current behaviour is authored and green **against pre-refactor code first**; every decomposition WP depends on it.
6. **#2508 fixed**: the identity-meta read anchors on primary; a red-first repro that fails on current code passes after the fix, and the `safe_commit` fallback no longer misfires.
7. **Seams pinned**: arch-enforcement tests assert ports are injected (cores import no infra ad-hoc) and pure cores perform no I/O.

### Edge Cases & named risks

- **Read contracts (corrected by post-tasks squad — the trio is LENIENT)**: the trio's status reads route through `resolve_handle_to_read_path(..., require_exists=False)` (LENIENT) plus an acceptance-specific existence-degrade (`_status_read_feature_dir`: `status_dir if status_dir.exists() else feature_dir` — documented "must stay LENIENT, degrade to primary"). There is **NO `require_exists=True` fail-closed site in the trio** — the fail-closed contract (b) is offered by the seam and used by OTHER modules, not here. The invariant to preserve is therefore: **keep every currently-lenient read lenient — do NOT introduce fail-close**, and preserve the not-exists degrade path. The seam still offers the guarded (b) and topology-blind (c) projections; the trio must not silently switch a lenient read onto a raising one (or vice-versa).
- **Typer entanglement**: the `implement`/`review` bodies are `@app.command`s with ~20 `Annotated`/`typer.Option` params; the marshalling shell stays ~150–200 LOC and cannot be "pure" — cores take a request dataclass. `workflow.implement` delegates to `implement.py::implement` (two nested giant `implement` functions).
- **Monkeypatch ripple**: the trio's private symbols are module-qualified-patched by many tests (workflow.py 44 files, implement.py 31, acceptance 26); relocating them breaks patch targets — requires thin re-export shims or a coordinated test-repin (FR-008).
- **Characterization is not naive byte-diff**: outputs carry git SHAs, status-event timestamps, and paths — assertions must normalize those fields.
- **Flat / no-coord missions** (`SINGLE_BRANCH`/`LANES`): the seam routes everything to primary exactly as today — unchanged.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `agent/workflow.py` is decomposed into a Typer-shell + request dataclass + deterministic pure cores + a commit executor, following the MissionResolver-port (#2494)/tasks.py-degod (#2308) pattern; the `implement`/`review`/`_resolve_review_context` bodies are the primary extraction targets. | Draft |
| FR-002 | `implement.py` is decomposed into the same shape; the two `# noqa: C901` bodies (`_ensure_planning_artifacts_committed_git`, `implement`) are split into staging-decision cores + git executor + shell, and the suppressions removed. | Draft |
| FR-003 | `acceptance/__init__.py` is decomposed; the matrix/readiness/gate logic becomes pure, unit-testable cores; the CLI/commit path is a thin executor. Scope is `acceptance/__init__.py` only (the `accept.py` CLI wrapper / #2482 residual-commit path is **out of scope**). | Draft |
| FR-004 | The trio's ~33 leaf resolver call sites route through the **already-central** seam wrappers (#2465), keeping each read's existing contract — the trio is LENIENT (`require_exists=False`) + acceptance existence-degrade; no lenient read is flipped to fail-close (nor vice-versa). No new resolver is created; zero diff to the shared seam modules. | Draft |
| FR-005 | Complexity is reduced by (file, function, **Sonar S3776**) — workflow.py `implement`/`review`/`_resolve_review_context`; implement.py `implement`/`_ensure_planning_artifacts_committed_git`; acceptance `collect_feature_summary`/`_build_recommended_fix_order`/`_check_lane_gates` — each resulting function ≤15 S3776, and every pre-existing `# noqa: C901` in the trio (implement.py×2) removed, none added. | Draft |
| FR-006 | The decomposition is **behaviour-preserving** for lifecycle semantics: identical CLI outputs (modulo normalized SHA/timestamp/path fields) and identical mission-state transitions for `agent action implement/review`, `spec-kitty implement`, `spec-kitty accept`, and the `next`/decision loop (incl. rejection/rewind/resume). | Draft |
| FR-007 | Arch-enforcement tests pin the new seams: ports injected (cores import no infra ad-hoc), pure cores perform no I/O, and the trio consumes the read seam only (no direct leaf-primitive imports). These tests do **not** rely on ruff C901 (which is blind to S3776). | Draft |
| FR-008 | **Characterization-first gate**: a characterization suite pinning the trio's current behaviour — via (i) direct pure-core in→out tests, (ii) the existing JSON envelope with SHA/timestamp/path normalized, (iii) status-event-reducer transition assertions — is authored and merged green against **pre-refactor** code as the first work package; every decomposition WP depends on it. | Draft |
| FR-009 | **Test-repin strategy**: the ~101 test files (44/31/26) that module-qualified-patch relocated trio symbols are kept green via thin re-export shims and/or a coordinated patch-path migration (precedent: the `mission_feature_resolution` WP09 shim) — sized as real in-scope work. | Draft |
| FR-010 | **#2508 fix** (folded — the #2160-class read-source bug): the identity-meta read (`_load_coord_branch_meta` / `_commit_workflow_change`) anchors on the primary surface, fixing the misfiring `safe_commit` fallback. Pinned by a red-first repro that fails on current code. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | No functional/behavioural regression (lifecycle semantics). | Full existing `tests/` suite green; characterization suite (FR-008) green pre & post; the only intended behaviour delta is FR-010 (#2508), covered by its red-first repro. | Draft |
| NFR-002 | Complexity ceiling honoured, on the **gate of record**. | **Sonar S3776 ≤15** on all new/touched trio functions (ruff C901 is blind here and is NOT the gate); zero `# noqa: C901` remaining in the trio; verified in-PR via a SonarCloud branch review, not just green ruff. | Draft |
| NFR-003 | God-modules broken up without shuffling into new god-fragments. | Complexity/cohesion is the primary gate; module LOC ~800 is a **target, not a hard gate** (the #2308 template itself exceeds it — `tasks_move_task.py` 1817); an irreducible core may exceed ~800 if cohesive. No new module re-creates a god-object; no extracted core shares mutable state across the shell boundary. | Draft |
| NFR-004 | Layer + quality gates preserved. | Pure cores contain no I/O and no infra imports; ports passed as data; layer rules intact; ruff + mypy zero issues; each new branch/helper carries a focused test in-PR. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | **Behaviour-preserving for lifecycle semantics** — no lane/state-machine change, no CLI-contract change. The single intended behaviour delta is FR-010 (#2508 read-source fix), explicitly carved out and red-first-pinned. | Draft |
| C-002 | Follow the **canonical degod pattern** (Typer-shell + request dataclass + pure cores + executor) from MissionResolver-port (#2494) and tasks.py degod (#2308) — the resolution family is already DI-ready (`resolver: MissionResolver | None`); reuse that seam, don't invent a bespoke one. | Draft |
| C-003 | The coord/primary partition is **settled, already-central** doctrine (coord = lifecycle bookkeeping: status/notes/trace/issue-matrix/move-task; primary = stable planning; no-coord → all primary), enforced by existing arch ratchets (`test_single_mission_surface_resolver.py`, `test_no_raw_mission_spec_paths.py`). This mission routes the trio onto it and preserves its three read contracts — it does not redefine or re-centralize it. | Draft |
| C-004 | **Campsite, not scope-creep**: touch only the three modules + their extracted seams + the trio's own leaf call sites. Do **not** repoint the 12+ non-trio callers of the shared read primitives (they already route correctly), and do not pull in adjacent god-modules (`sync.py`, `runtime_bridge.py` #2531, `charter/context.py` #2532, `orchestrator_api/commands.py`). | Draft |
| C-005 | Fold #2464 (workflow complexity), #2465 (seam consolidation), #2508 (read-source fix); close them here. | Draft |

## Key Entities

- **Ports façade** — the injected infra boundary per command (`safe_commit`, `feature_status_lock`, `git`/`subprocess`, `resolve_workspace_for_wp`, `BookkeepingTransaction`, `console`), passed as data.
- **Pure core** — deterministic lifecycle/matrix/gate logic (no I/O), unit-testable in isolation.
- **Typer-shell / executor** — thin layers: shell marshals `Annotated` params into a request dataclass; executor wires ports → core → output.
- **Partition seam** — the existing kind-aware `placement_seam` projection + its guarded/blind siblings; the read authority the trio routes onto.

## Success Criteria

| ID | Criterion | Measure |
|----|-----------|---------|
| SC-001 | The trio's command bodies are decomposed. | `implement`/`review`/`_resolve_review_context`/`acceptance` matrix logic live in pure cores; the modules trend toward ~800 LOC with no new god-object. |
| SC-002 | The trio consumes one read authority. | Arch test: the trio imports only the seam wrappers, not leaf resolver primitives; the three read contracts intact. |
| SC-003 | Complexity debt cleared on the gate of record. | Sonar S3776 ≤15 across the trio's touched functions (SonarCloud branch review); zero `# noqa: C901` in the trio. |
| SC-004 | Behaviour provably unchanged (± the #2508 fix). | Characterization suite (FR-008) + full suite green; FR-010 red-first repro green; no un-normalized output/transition diff. |

## Assumptions

- The coord/primary partition doctrine + its central resolver are settled and correct; this mission routes onto them and preserves their contracts.
- Characterization is feasible via pure-core direct tests + JSON-envelope (with SHA/timestamp/path normalization) + status-reducer transitions — not naive byte-diff.
- The #2494/#2308 template is proven (DI already present, no global singletons) — low architectural risk; the residual risk is gate-selection (S3776 not local) and test-repin ripple.

## Out of Scope

- Any lifecycle/state-machine/CLI-contract change beyond FR-010 (#2508).
- The 12+ non-trio callers of the shared read primitives (already routing correctly) and the other god-modules (`runtime_bridge.py` #2531, `charter/context.py` #2532, `sync.py`, `emitter.py`, `queue.py`, `orchestrator_api/commands.py`).
- `accept.py`'s residual-artifact commit path (#2482) — different module than `acceptance/__init__.py`.
- **#2463** (pre-3.2.x legacy-mission retirement) — deliberately sequenced to land **after** this mission (real rebase collision in `_read_path_resolver.py`/`resolution.py`; per the #2463 pre-spec-squad note 2026-07-09).
- Unshim / dead-symbol burn-down (#2293/#2322/#2323); the same-family coord-shadow bugs in other modules (#2510 status/emit, #2512 lane-allocator, #2502 dashboard).
