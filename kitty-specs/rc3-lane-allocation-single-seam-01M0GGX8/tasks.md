# Tasks: M8 — Lane-allocation single-seam (recurrence prevention for #3571)

**Branch**: `rc3-lane-allocation-single-seam-01M0GGX8` (planning + merge target; PR to `upstream/main` is
the closeout — the operator merges). Topology: `single_branch` (WPs execute sequentially in one workspace).

Execution order (dependency-driven): **WP1 → WP2 → WP4 → WP3 → WP5.**
See `plan.md` (dependency graph), `contracts/`, and `post-plan-squad-findings.md` for the grounded design.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author `test_topology_predicate_is_single_authority` (red-first via synthetic surrogate-gate AST fixture) | WP1 | |
| T002 | Companion exclusion-pin test: emit-annotation path keeps the bare `coordination_branch is None` (#2939) | WP1 | [P] |
| T003 | Census-verdict docstring: the 4 residual sites are value-reads, not surrogate gates | WP1 | [P] |
| T004 | Add `LaneAllocationRoute` enum + `LaneBaseDecision` frozen dataclass | WP2 | |
| T005 | Implement `resolve_lane_base_or_refuse` as a thin orchestrator over M1's `_guard_base_honorable` + `_resolve_lane_parent` | WP2 | |
| T006 | Route all four routes through the seam; remove the standalone inline parent-choice | WP2 | |
| T007 | Regression-pin the `--base` docstring ("never smuggled", ~:279-287) | WP2 | [P] |
| T008 | Red-first seam tests: INV-0 sole-computer, INV-1 base=None parity, INV-2 refuse, INV-7 atomicity | WP2 | |
| T009 | Create `mission_runtime/read_dir_degrade.py` (`ReadDegradeStrategy`, `ReadDirDecision`, `resolve_read_dir_or_degrade`) with deferred imports | WP4 | |
| T010 | Add `read_dir_degrade` to the `test_layer_rules.py` mission_runtime ledger | WP4 | [P] |
| T011 | Migrate `retrospective/generator.py:264` → `ZERO_EVIDENCE` (function-local import) | WP4 | |
| T012 | Migrate `core/worktree_topology.py:173` → `DEGRADE_TO_FEATURE_DIR` | WP4 | |
| T013 | Red-first read tests: INV-R1 per-site parity, INV-R2 #1848 pin, INV-R3 WARNING log | WP4 | |
| T014 | Author `tests/architectural/test_lane_allocation_single_seam.py` — positive def-use allocation check (FR-001/002) | WP3 | |
| T015 | Read-degrade family check + allowlist entries with failed-strategy rationale (FR-006/007) | WP3 | |
| T016 | Non-vacuity: synthetic-AST-fixture asserts the checker flags a bypass file:line; live module clean | WP3 | |
| T017 | Thread coord-availability/topology into the `PROTECTED_BRANCH_REFUSED` `Refused` at `policy.py:225-236` | WP5 | |
| T018 | Branch the remedy: coord-available (unchanged) vs no-coord (accurate, followable) | WP5 | |
| T019 | Pass the topology fact from `commit_router` to policy (the coupling point); cross-ref #2739 | WP5 | |
| T020 | Red-first #3536 tests: INV-3536-1 no-coord followable, -2 coord unchanged, -3 answer via shared predicate | WP5 | |

## Work Packages

## Work Package WP01: #3460 topology-predicate anti-divergence guard
- **Goal**: pin `_transaction_topology_available` as the single topology authority; prevent future
  surrogate-gate divergence. **No src change** (census found zero residual gates) — enforcement only.
- **Priority**: P2 · land first (lowest risk). **Independent test**: `test_topology_predicate_is_single_authority`.
- **Subtasks**: T001, T002, T003
- **Dependencies**: none
- **Requirements**: FR-004
- **Prompt**: `tasks/WP01-topology-predicate-anti-divergence-guard.md`
- **Risks**: vacuous test (mitigated by synthetic-red fixture); accidentally re-including the #2939 emit exclusion.

## Work Package WP02: Shared allocation seam resolve_lane_base_or_refuse
- **Goal**: fold M1's `_guard_base_honorable` + `_resolve_lane_parent` into ONE refuse-or-honor seam;
  route all four allocation routes through it (FR-001/002/003, NFR-001, C-001).
- **Priority**: P1 · core. **Independent test**: seam unit + all-four-routes coverage.
- **Subtasks**: T004, T005, T006, T007, T008
- **Dependencies**: none
- **Requirements**: FR-001, FR-002, FR-003, NFR-001, C-001
- **Prompt**: `tasks/WP02-shared-allocation-seam.md`
- **Risks**: S3776 ceiling (mitigated: thin orchestrator); atomicity on relocation (INV-7); NFR-001 parity.

## Work Package WP04: Read-side degrade companion resolve_read_dir_or_degrade
- **Goal**: ship the read companion for its two genuine degrade consumers; preserve #1848; keep the
  `mission_runtime` layering constraint (FR-006).
- **Priority**: P2. **Independent test**: read companion unit + per-site parity.
- **Subtasks**: T009, T010, T011, T012, T013
- **Dependencies**: none
- **Requirements**: FR-006
- **Prompt**: `tasks/WP04-read-side-degrade-companion.md`
- **Risks**: layering (`test_layer_rules.py`); collapsing #1848 (never migrate aggregate); M5 co-edit on `generator.py` (function-local import).

## Work Package WP03: Anti-bypass guard (recurrence prevention)
- **Goal**: structural test that fails when a new allocation/read-degrade route bypasses the seam (FR-007).
- **Priority**: P1 · the recurrence guarantee. **Independent test**: the guard itself + its synthetic-bypass fixture.
- **Subtasks**: T014, T015, T016
- **Dependencies**: WP02, WP04
- **Requirements**: FR-007
- **Prompt**: `tasks/WP03-anti-bypass-guard.md`
- **Risks**: fakeability (mitigated: positive def-use + synthetic fixture); allowlist rubber-stamp (criterion enforced).

## Work Package WP05: #3536 no-coord protected-branch refusal fix
- **Goal**: replace the un-followable "target the coordination branch" remedy on lanes/single-branch with
  an accurate one; converge with #2739 (FR-005).
- **Priority**: P2 · the only net-new user-facing behavior. **Independent test**: refusal-remedy branching.
- **Subtasks**: T017, T018, T019, T020
- **Dependencies**: WP01
- **Requirements**: FR-005
- **Prompt**: `tasks/WP05-no-coord-refusal-fix.md`
- **Risks**: keeping `evaluate` ref-only (thread topology at the refusal-construction site); #2739 divergence.

## MVP / sequencing note
WP2 (the seam) + WP3 (the guard) are the mission's core recurrence-prevention deliverable. WP5 carries
the only live user-facing fix. WP1 and WP4 are enforcement + companion consolidation.
