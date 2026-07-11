# Implementation Plan: Coord-Authority Trio Degod

**Branch**: `feat/coord-authority-trio-degod` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/coord-authority-trio-degod-01KX7094/spec.md`

## Summary

Behaviour-preserving structural decomposition of the three coord-authority god-modules (`agent/workflow.py` 2997, `implement.py` 1639, `acceptance/__init__.py` 1737) into the canonical degod shape — Typer-shell + request dataclass + deterministic pure cores + executor — following the shipped MissionResolver-port (#2494) and tasks.py degod (#2308). The coord/primary partition is **already central** (`missions/_read_path_resolver.py` + `mission_runtime/resolution.py::PlacementSeam`); the mission routes the trio's ~33 leaf resolver call sites onto the one kind-aware seam while preserving its three read contracts, closes the #2160-class read-source bug (#2508), and clears the Sonar S3776 hotspots — under a characterization-first safety net authored against pre-refactor code.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich (CLI shells); the internal `mission_runtime.resolution` (`PlacementSeam`) + `specify_cli.missions._read_path_resolver` (read primitives); `specify_cli.status` (event reducer for transition characterization); `radon`/SonarCloud (S3776 measurement — the complexity gate of record). No new third-party dependency.
**Storage**: unchanged — mission artifacts on coord/primary git surfaces; no schema/state change.
**Testing**: `pytest`. New: a characterization suite (`tests/characterization/` — pure-core in→out + JSON-envelope-normalized + status-reducer transitions) authored FIRST; arch-enforcement tests (`tests/architectural/`) for seam-only consumption + ports-injected + cores-pure. Existing trio test fan-in (workflow 44, implement 31, acceptance 26 files) kept green via re-export shims / patch-path repin.
**Target Platform**: Linux/macOS dev + CI.
**Project Type**: single (Python CLI package); the change is internal structure of three `specify_cli` command modules + their extracted cores.
**Performance Goals**: unchanged (lifecycle commands, not a hot path); no added I/O.
**Constraints**: behaviour-preserving lifecycle semantics (only #2508 is an intended delta); **Sonar S3776 ≤15 is the gate of record** (ruff C901 is blind to these functions — do NOT rely on it; verify via SonarCloud branch review in-PR); pure cores no-I/O; layer rules intact; ruff+mypy zero-issue; NFR-003 LOC ~800 is a target not a hard gate.
**Scale/Scope**: ~6373 LOC across 3 modules → cores/executor/shell + seam routing + characterization harness + test repin. Three parallelizable per-module tracks gated by one characterization WP, sharing the seam + repin work.

## Charter Check

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

Charter present; plan-action context compact. Alignment:

- **Single canonical authority** (Governing Principle #1) — the mission routes the trio onto the *already-central* partition authority and forbids leaf re-entry; it consolidates consumption, it does not add a second authority. ✅
- **Architectural alignment / infra-logic separation (#2173)** — ports injected as data, pure cores no-I/O; the canonical Typer-shell + core + executor shape (#2494/#2308). ✅
- **Tidy-first / campsite** — behaviour-preserving decomposition + S3776 hotspot cleanup, scoped to the trio; non-trio callers (already routing correctly) left untouched (C-004). ✅
- **Architectural gate discipline** — arch-enforcement tests pin the new seams; the complexity gate of record is S3776 (not the blind ruff C901) — a "gate-unmask cannot self-validate" hazard explicitly handled via an in-PR SonarCloud review. ✅
- **Red-first for the one behaviour delta** — #2508 (FR-010) is pinned by a red-first repro; the rest is behaviour-preserving under the FR-008 characterization net. ✅

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-authority-trio-degod-01KX7094/
├── plan.md              # This file
├── spec.md              # Committed (hardened by post-spec squad)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (ports/cores/executor entities + 3 read contracts)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 (seam-consumption + characterization-envelope contracts)
├── tracers/             # 3 tracer files (one per module) — appended during implement
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT here)
```

### Source Code (target shape — illustrative, tasks refine)

```
src/specify_cli/cli/commands/agent/
├── workflow.py                  # → thin Typer-shell + executor (was 2997)
├── workflow_cores.py            # pure: review-context builder, decision mapping
├── workflow_executor.py         # commit executor (_commit_workflow_change), workspace materialize

src/specify_cli/cli/commands/
├── implement.py                 # → thin Typer-shell + executor (was 1639)
├── implement_cores.py           # pure: git-porcelain/diff family, staging-decision, placement family

src/specify_cli/acceptance/
├── __init__.py                  # → thin executor (was 1737)
├── summary_core.py              # pure: collect_feature_summary, recommended-fix-order
├── gates_core.py                # pure: _check_lane_gates, terminal/unchecked checks

# seam routing (FR-004): trio consumes mission_runtime.resolution.PlacementSeam projections only
# re-export shims (FR-009): keep module-qualified monkeypatch targets valid post-move

tests/
├── characterization/            # FR-008 — authored FIRST, green pre-refactor
├── architectural/               # seam-only-consumption + ports-injected + cores-pure gates
└── (existing trio test fan-in kept green via shims/repin)
```

**Structure Decision**: single package; the load-bearing move is extracting the lifecycle logic out of the three giant command bodies into pure cores + a commit/git executor, with the Typer signature staying in a thin shell (it cannot be made pure). The seam routing and test-repin are cross-cutting and shared by all three module tracks.

## Complexity Tracking

*No Charter Check violations — none.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. Code anchors are squad-verified (2026-07-11).

### IC-CHAR — Characterization-first safety net (GATES EVERYTHING)

- **Purpose**: FR-008. Pin the trio's current behaviour BEFORE any structure moves — the only defence against a false-green refactor.
- **Requirements**: FR-008, FR-006, NFR-001. **Sequencing**: FIRST; every other IC depends on it.
- **Approach (squad NOTE-8 — not naive byte-diff)**: (i) direct pure-core in→out tests for the already-clean helpers about to move; (ii) CLI-shell via the existing JSON envelope (`implement.py::_json_safe_output:113`, guarded by `tests/integration/test_json_envelope_strict.py`) with SHA/timestamp/path fields normalized; (iii) state-transition assertions via the deterministic status-event reducer (not wall-clock fields) over `agent action implement/review`, `spec-kitty implement`, `spec-kitty accept`, and the `next`/decision loop incl. rejection/rewind/resume.
- **Risk**: environment-coupled outputs (git SHAs, timestamps, worktree materialization) — mitigated by field normalization + reducer-level transition pins.

### IC-WORKFLOW — Decompose workflow.py (folds IC-2508)

- **Purpose**: FR-001/FR-005. Split `implement`(radon CC78, `@app.command`@1378), `review`(CC72 @2431), `_resolve_review_context`(CC37 @2085) into Typer-shell + request dataclass + pure cores + commit executor.
- **Seams (squad-verified)**: relocate already-clean cores (review-feedback resolution `_resolve_review_feedback_*`, prompt/banner renderers `_render_*`, status-error classifier `_is_missing_canonical_status_error:1030`); extract from the monsters — request-marshalling shell, workspace-materialization core (`_ensure_workspace_materialized:1318` already a seam), review-context builder core, commit executor (`_commit_workflow_change:571`).
- **Ports**: `safe_commit`, `feature_status_lock`, `subprocess`, `resolve_workspace_for_wp`, `_ensure_target_branch_checked_out`, `build_charter_context` — inject as data (these are today's monkeypatch targets → drive IC-REPIN).
- **IC-2508 fold (FR-010)**: red-first repro, then anchor `_load_coord_branch_meta:276`/`_commit_workflow_change:571` identity read on primary. **Note**: `workflow.implement` delegates to `implement.py::implement` (`top_level_implement`, called @1601) — two nested `implement` bodies; coordinate the split across IC-WORKFLOW + IC-IMPLEMENT.
- **Requirements**: FR-001, FR-005, FR-010. **Depends on**: IC-CHAR. **Shares**: IC-SEAM, IC-REPIN.

### IC-IMPLEMENT — Decompose implement.py

- **Purpose**: FR-002/FR-005. Split `_ensure_planning_artifacts_committed_git:756`(CC22, `# noqa: C901`) → staging-decision core + git executor; `implement:1105`(CC60, `# noqa: C901`, `@app.command`) → shell + `_run_recover_mode:1008` + commit executor. Remove both `noqa` (not relocate).
- **Clean extraction targets**: git-porcelain/diff family (`_feature_dir_status_entries:288`, `_files_changed_vs_ref:483`, `_exclude_coord_owned:571`, `_is_vcs_lock_only_meta_diff:595`, `_drop_vcs_lock_only_meta:641`) + placement family (`_resolve_placement_ref:678`, `_resolve_claim_commit_target:708`, `_placement_coord_filter:733`) — already near-pure.
- **Ports**: `git`, `safe_commit`, `BookkeepingTransaction`, `console`.
- **Requirements**: FR-002, FR-005. **Depends on**: IC-CHAR. **Shares**: IC-SEAM, IC-REPIN.

### IC-ACCEPT — Decompose acceptance/__init__.py

- **Purpose**: FR-003/FR-005. Extract matrix/gate logic into pure cores; thin executor for the CLI/commit path. Scope = `__init__.py` only (accept.py / #2482 residual-commit path OUT).
- **Pure cores (deterministic given file contents)**: `collect_feature_summary:1212`(CC25), `_build_recommended_fix_order:1168`(CC22), `_check_lane_gates:965`(CC19), `_all_work_packages_terminal:536`, `_find_unchecked_tasks:501`, `_check_workflow_run_evidence:1153` → `summary_core.py` + `gates_core.py`.
- **Executor/ports**: `perform_acceptance:1661`(CC13), `_commit_acceptance_meta:1468`(CC15), `normalize_feature_encoding:615`(CC16, file I/O).
- **Requirements**: FR-003, FR-005. **Depends on**: IC-CHAR. **Shares**: IC-SEAM, IC-REPIN.

### IC-SEAM — Route the trio onto the kind-aware seam (#2465)

- **Purpose**: FR-004. Route the trio's ~33 leaf call sites (workflow 21, implement 7, acceptance 5; six entry points: `placement_seam().read_dir`, `resolve_planning_read_dir`, `candidate_feature_dir_for_mission`, `primary_feature_dir_for_mission`, `resolve_handle_to_read_path`, `resolve_status_surface_with_anchor`) through the kind-aware `placement_seam(...).read_dir(kind)` projection + write twin.
- **PRESERVE the 3 read contracts (do NOT collapse — squad SHOULD-ADDRESS-4)**: (a) lenient kind-aware `placement_seam.read_dir(kind)`; (b) fail-closed guarded `resolve_handle_to_read_path(require_exists=True)` (data-loss #1848, at `workflow.py:323`, `acceptance:765`); (c) topology-blind primary anchor `primary_feature_dir_for_mission` (`_read_path_resolver.py:1254`).
- **Arch gate**: extend the existing resolver ratchet (`tests/architectural/test_single_mission_surface_resolver.py`) to pin **trio seam-only consumption** (no direct leaf-primitive imports). C-004: do NOT repoint the 12+ non-trio callers.
- **Requirements**: FR-004, C-003, C-004, SC-002. **Depends on**: IC-CHAR. **Shared by**: all three module ICs.

### IC-REPIN — Test-repin / re-export shims (FR-009)

- **Purpose**: FR-009. Keep ~101 module-qualified-monkeypatch test files green when private symbols move (workflow 44, implement 31, acceptance 26; symbols like `workflow.safe_commit`, `workflow._find_mission_slug`, `implement.git`, …).
- **Strategy**: thin re-export shims at the old module paths (precedent: the `mission_feature_resolution` WP09 shim) and/or a coordinated patch-path migration; each moved symbol either re-exported or its patch target repinned in-PR.
- **Requirements**: FR-009, NFR-001. **Shared by**: all three module ICs; sized as real work, not incidental.

### Sequencing

```
IC-CHAR (characterization-first, GATES ALL)
  └──> IC-WORKFLOW (+IC-2508) ∥ IC-IMPLEMENT ∥ IC-ACCEPT
         └── all three share ──> IC-SEAM (seam routing + arch gate) + IC-REPIN (shims/repin)
```

The three module tracks are parallelizable after IC-CHAR but **linearize on the shared IC-SEAM + IC-REPIN surfaces** (ownership overlap on the resolver seam + the re-export shim module) — tasks must sequence or single-own those. Closeout: full suite + characterization + arch gates + SonarCloud S3776 branch review.

## Tracer files (seed at planning, per standing practice)

Three tracer files (one per module: workflow / implement / acceptance) seeded under `tracers/` at planning, appended during implement (extraction decisions, S3776 before/after, surprises), assessed at close.
