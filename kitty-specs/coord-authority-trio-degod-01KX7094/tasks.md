# Tasks: Coord-Authority Trio Degod

**Mission**: coord-authority-trio-degod-01KX7094 | **Branch**: `feat/coord-authority-trio-degod` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Behaviour-preserving structural decomposition of the coord-authority trio (workflow.py/implement.py/acceptance) into Typer-shell + pure cores + executor, routing the trio onto the already-central partition seam (preserving 3 read contracts), folding #2508, under a characterization-first safety net. Sonar S3776 is the complexity gate of record (ruff C901 is blind).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Characterization scaffold + non-deterministic-field normalizer (SHA/timestamp/path/pid) + per-file pytestmark | WP01 | |
| T002 | DIRECT pure-core in→out characterization of the CC19-37 SPLIT targets (_resolve_review_context, collect_feature_summary, _build_recommended_fix_order, _check_lane_gates) + already-clean helpers, with a branch-coverage matrix | WP01 | |
| T003 | JSON-envelope characterization of ALL 4 CLI surfaces (agent action implement, agent action review, spec-kitty implement, spec-kitty accept), normalized; integration+git_repo markers | WP01 | |
| T004 | Status-reducer transition characterization (next/decision loop incl. rejection/rewind/resume); pin the not-exists DEGRADE path for the lenient status reads | WP01 | |
| T005 | Prove GREEN on pre-refactor code; WP01 DoD reviewer checklist enumerating pinned behaviours (lenient degrade, rejection/rewind/resume, #2508 pre-fix path) | WP01 | |
| T006 | #2508 (FR-010) RED-FIRST via the real command entry (agent action implement/review on coord-topology, observe safe_commit misfire) on UNTOUCHED code, THEN anchor _load_coord_branch_meta/_commit_workflow_change on primary | WP02 | |
| T007 | Extract workflow.py pure cores (review-context builder, review-feedback resolution, decision mapping, renderers, status-error classifier) → workflow_cores.py | WP02 | |
| T008 | Extract commit/workspace executor (_commit_workflow_change, _ensure_workspace_materialized) → workflow_executor.py | WP02 | |
| T009 | Reduce implement (CC78) → Typer-shell + request dataclass over cores; S3776 ≤15; characterization green | WP02 | |
| T010 | Reduce review (CC72) → shell over cores; S3776 ≤15; characterization green | WP02 | |
| T011 | Reduce _resolve_review_context (CC37) → cores; S3776 ≤15; characterization green | WP02 | |
| T012 | Route workflow's leaf resolver calls onto the seam (verify count); keep them LENIENT (no fail-close); zero diff to the shared seam module | WP02 | |
| T013 | Re-export shims at workflow.py (bare from-import, NOT in __all__); keep the workflow test files green (re-verify count) | WP02 | |
| T014 | Append workflow tracer; core unit tests (pytestmark unit); DoD re-verify the top_level_implement delegation call site after WP03 | WP02 | |
| T015 | Extract implement.py pure cores (git-porcelain/diff family, staging-decision, placement family) → implement_cores.py | WP03 | |
| T016 | Split _ensure_planning_artifacts_committed_git (noqa) → staging core + git executor; remove noqa | WP03 | |
| T017 | Reduce implement (CC60, noqa) → shell over cores + _run_recover_mode; remove noqa; S3776 ≤15 | WP03 | |
| T018 | Route implement's leaf resolver calls onto the seam (verify count); zero diff to the shared seam module | WP03 | |
| T019 | Re-export shims at implement.py (bare import, NOT in __all__); keep test files green; preserve top_level_implement 6-keyword signature (WP02 delegates) | WP03 | |
| T020 | Append implement tracer; core unit tests (pytestmark unit) | WP03 | |
| T021 | Extract acceptance summary cores (collect_feature_summary, recommended-fix-order) → summary_core.py | WP04 | |
| T022 | Extract acceptance gate cores (_check_lane_gates, terminal/unchecked/evidence) → gates_core.py | WP04 | |
| T023 | Reduce perform_acceptance/_commit_acceptance_meta → thin executor; S3776 ≤15 (tracer note if wiring raises complexity) | WP04 | |
| T024 | Route acceptance's leaf resolver calls onto the seam (verify count); keep _status_read_feature_dir LENIENT degrade; zero diff to shared seam module | WP04 | |
| T025 | Re-export shims at acceptance (bare import, NOT in __all__; keep the 2 existing accept.py-consumed exports); keep test files green | WP04 | |
| T026 | Append acceptance tracer; core unit tests (pytestmark unit) | WP04 | |
| T027 | Extend test_single_mission_surface_resolver.py + new test_trio_seam_only.py (pytestmark architectural): trio imports ONLY seam wrappers, non-vacuous | WP05 | |
| T028 | FR-007 arch test: cores perform NO I/O — AST FUNCTIONAL_FS_BYPASS classification (banned: open/Path.read_text/write_text/subprocess/etc.), non-vacuous self-check plants a real I/O call | WP05 | |
| T029 | Closeout: full suite + characterization + arch + ruff + mypy; radon cc -s -n B ≤15 local proxy + manual Sonar dispatch (gh workflow run ci-quality.yml --ref); zero trio noqa:C901; FR-009 shims-green verified | WP05 | |
| T030 | Verify 3 read contracts intact (no lenient site flipped to fail-close, no fail-close introduced); assess tracers | WP05 | |

## Work Packages

### WP01 — Characterization-first safety net (GATES EVERYTHING)

- **Goal**: FR-008. Pin the trio's current behaviour BEFORE any structure moves, pinning the CC19-37 SPLIT targets DIRECTLY (branch-coverage matrix), not just easy helpers.
- **Priority**: P0 (hard gate) · **Dependencies**: none · **Requirements**: FR-008, FR-006, NFR-001
- **Independent test**: green on untouched trio; all 4 CLI surfaces (coord+flat); lenient not-exists degrade pinned.
- **Prompt**: [tasks/WP01-characterization-harness.md](tasks/WP01-characterization-harness.md) (~5 subtasks)

- [x] T001 Scaffold + non-deterministic-field normalizer + per-file pytestmark (WP01)
- [x] T002 DIRECT pure-core characterization of the CC19-37 split targets + branch-coverage matrix (WP01)
- [x] T003 JSON-envelope characterization of ALL 4 CLI surfaces, normalized (integration+git_repo) (WP01)
- [x] T004 Status-reducer transitions incl. rejection/rewind/resume; pin the lenient not-exists degrade (WP01)
- [x] T005 Prove GREEN pre-refactor; reviewer checklist of pinned behaviours (WP01)

### WP02 — Decompose workflow.py (+ seam-route + #2508 red-first FIRST)

- **Goal**: FR-001/FR-005/FR-010. #2508 red-first FIRST (real command entry, untouched code), then split implement(CC78)/review(CC72)/_resolve_review_context(CC37) → shell+cores+executor; seam-route (lenient preserved).
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP03, WP04 · **Requirements**: FR-001, FR-005, FR-010, FR-004, FR-009
- **Independent test**: #2508 red-first fails on untouched code; characterization + workflow tests green; each function S3776 ≤15 (radon proxy).
- **Prompt**: [tasks/WP02-decompose-workflow.md](tasks/WP02-decompose-workflow.md) (~9 subtasks)

- [x] T006 #2508 red-first via real command entry (untouched code) + anchor identity read on primary (WP02)
- [x] T007 Extract workflow.py pure cores → workflow_cores.py (WP02)
- [x] T008 Extract commit/workspace executor → workflow_executor.py (WP02)
- [x] T009 Reduce implement (CC78) → shell+request over cores; S3776 ≤15; characterization green (WP02)
- [x] T010 Reduce review (CC72) → shell over cores; S3776 ≤15; characterization green (WP02)
- [x] T011 Reduce _resolve_review_context (CC37) → cores; S3776 ≤15; characterization green (WP02)
- [x] T012 Route leaf resolver calls onto the seam (verify count); keep LENIENT; zero seam-module diff (WP02)
- [x] T013 Re-export shims (bare import, NOT __all__); workflow tests green (re-verify count) (WP02)
- [x] T014 Tracer + core unit tests; DoD re-verify top_level_implement delegation after WP03 (WP02)

### WP03 — Decompose implement.py (+ seam-route)

- **Goal**: FR-002/FR-005. Split the two noqa:C901 bodies → staging cores + git executor + shell; remove both noqa; seam-route; preserve top_level_implement signature.
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP02, WP04 · **Requirements**: FR-002, FR-005, FR-004, FR-009
- **Independent test**: characterization + implement tests green; S3776 ≤15; zero noqa; delegation signature preserved.
- **Prompt**: [tasks/WP03-decompose-implement.md](tasks/WP03-decompose-implement.md) (~6 subtasks)

- [x] T015 Extract implement.py pure cores → implement_cores.py (WP03)
- [x] T016 Split _ensure_planning_artifacts_committed_git → staging core + git executor; remove noqa (WP03)
- [x] T017 Reduce implement (CC60) → shell over cores + _run_recover_mode; remove noqa; S3776 ≤15 (WP03)
- [x] T018 Route leaf resolver calls onto the seam (verify count); zero seam-module diff (WP03)
- [x] T019 Re-export shims (bare, NOT __all__); tests green; preserve top_level_implement 6-keyword signature (WP03)
- [x] T020 Tracer + core unit tests (WP03)

### WP04 — Decompose acceptance/__init__.py (+ seam-route)

- **Goal**: FR-003/FR-005. Extract matrix/gate logic → summary_core/gates_core; thin executor; seam-route (lenient degrade preserved). Scope = __init__.py only.
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP02, WP03 · **Requirements**: FR-003, FR-005, FR-004, FR-009
- **Independent test**: characterization + acceptance tests green; S3776 ≤15; _status_read_feature_dir lenient degrade preserved.
- **Prompt**: [tasks/WP04-decompose-acceptance.md](tasks/WP04-decompose-acceptance.md) (~6 subtasks)

- [x] T021 Extract acceptance summary cores → summary_core.py (WP04)
- [x] T022 Extract acceptance gate cores → gates_core.py (WP04)
- [x] T023 Reduce perform_acceptance/_commit_acceptance_meta → thin executor; S3776 ≤15 (WP04)
- [x] T024 Route leaf resolver calls onto the seam; keep _status_read_feature_dir LENIENT; zero seam-module diff (WP04)
- [x] T025 Re-export shims (bare, NOT __all__; keep accept.py-consumed exports); tests green (WP04)
- [x] T026 Tracer + core unit tests (WP04)

### WP05 — Seam-only arch gate + closeout

- **Goal**: FR-004/FR-007/SC-002. Pin trio seam-only + cores-no-I/O (AST); verify contracts unflipped; full closeout gate (radon proxy + manual Sonar).
- **Priority**: P2 (closeout) · **Dependencies**: WP02, WP03, WP04 · **Requirements**: FR-004, FR-007
- **Independent test**: seam-only + no-I/O arch tests bite on planted violations; full suite + characterization + arch + radon ≤ ceiling green.
- **Prompt**: [tasks/WP05-seam-gate-closeout.md](tasks/WP05-seam-gate-closeout.md) (~4 subtasks)

- [ ] T027 Extend resolver ratchet + new test_trio_seam_only.py: trio imports ONLY seam wrappers, non-vacuous (WP05)
- [ ] T028 FR-007: cores no-I/O via AST FUNCTIONAL_FS_BYPASS classification; plant-and-catch self-check (WP05)
- [ ] T029 Closeout: full suite + characterization + arch + ruff + mypy + radon ≤ ceiling + manual Sonar; zero trio noqa; file Sonar-script --branch gap (WP05)
- [ ] T030 Verify 3 read contracts unflipped; assess tracers (WP05)

## Dependency Graph

```
WP01 (characterization — GATES ALL; pins the CC19-37 split targets directly)
 ├──> WP02 (workflow: #2508-red-first-FIRST, +decompose) ─┐
 ├──> WP03 (implement) ───────────────────────────────────┼──> WP05 (seam+no-I/O arch-gate + closeout)
 └──> WP04 (acceptance) ───────────────────────────────────┘
   [WP02 ∥ WP03 ∥ WP04 after WP01; disjoint src files]
```

## MVP & Parallelization

- **Gate**: WP01 must be green on pre-refactor code before ANY decomposition WP — and must pin the CC19-37 split targets DIRECTLY (not just easy helpers), else it is a false-green net.
- **Parallel**: WP02 ∥ WP03 ∥ WP04 (disjoint files). **Coordination**: WP03 preserves `top_level_implement`'s 6-keyword signature (workflow.py:1601) so WP02's call site holds; WP02 re-verifies it after WP03.
- **Read contracts (corrected)**: the trio is LENIENT (`resolve_handle_to_read_path` require_exists=False) + acceptance existence-degrade — NO fail-closed site in the trio. Do not introduce one.
- **Gate of record**: Sonar S3776 (ruff C901 blind); local proxy `uvx radon cc -s -n B`; Sonar not on PRs → manual `gh workflow run ci-quality.yml --ref <branch>`. NFR-003 LOC ~800 is a target, not a gate.
- **Shims**: bare `from … import …`, NOT in `__all__` (dead-symbol gate — #2057 precedent); allowlist if public.
- **C-004 tripwire**: zero diff to the shared seam modules; missing capability → escalate.
- **Closeout** (WP05): full suite + characterization + arch (seam-only + no-I/O, both non-vacuous) + ruff + mypy + radon + manual Sonar + zero trio noqa:C901 + 3-contract verification.
