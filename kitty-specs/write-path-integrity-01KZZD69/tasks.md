# Work Packages: Mission-Artifact Write-Path Integrity

**Inputs**: Design documents from `kitty-specs/write-path-integrity-01KZZD69/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: This mission is ATDD/red-first (charter). Test authoring is explicit, in-scope work.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). The 5 plan ICs
consolidate into 4 WPs — IC-02 (partition auto-commit) and IC-03 (Seam-A guard + #2549) merge into
**WP02** because both center on the `implement.py` commit path and must land in order (split before the
guard gets teeth — no silent mis-route window). Topology is `single_branch` (sequential; no lanes).

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** = safe to parallelize (different files). Completion recorded via
  `spec-kitty agent tasks mark-status <Txxx> --status done` (event log is the authority).

## Path Conventions

- Single project: `src/specify_cli/`, `src/mission_runtime/`, `src/charter/`, `tests/`.

---

## Work Package WP01: Unify the git-topology primitive (Priority: P2) — substrate, lands first

**Goal**: Collapse four re-implementations of the git-common-dir/toplevel probe into one primitive with
a single symlink-canonicalization contract; centralize the `effective_root` read-fork into one
`read_dir_for`; unify the nested/toplevel classifier. This is the substrate Seam B (WP03) stands on.
**Independent Test**: The four probes consume one primitive; the existing charter-caching / not-a-repo /
NESTED-refusal suite stays green (SC-005); static one-copy gates pass (SC-007, SC-008).
**Prompt**: `/tasks/WP01-git-topology-primitive.md`
**Requirement Refs**: FR-008, FR-009, FR-010

### Included Subtasks

T001 Create `src/specify_cli/git/git_topology.py` — one `git_common_dir()`/`git_toplevel()` primitive (caching + not-a-repo classification + `.git`-interior detection + one symlink-canonicalization contract)
T002 [P] Migrate `src/charter/resolution.py` to consume the primitive — preserve `@lru_cache`, not-a-repo classification, and its repo-root return shape (hot path, ~20 callers)
T003 [P] Migrate `core/checkout_ownership.py`, `git/commit_helpers.py`, `workspace/context.py` to the primitive — preserve each site's distinct error contract
T004 Consolidate the `effective_root ? legacy : compose_meta_json_path` fork (~12×) in `mission_runtime/resolution.py` into one `read_dir_for(...)` helper
T005 Unify the nested/toplevel-mismatch classifier to feed both the `is_worktree_of` gate and the comparator (preserve the NESTED refusal)
T006 Behavior-parity tests + static one-copy gates (SC-005/007/008)

### Dependencies

- None (substrate).

### Risks & Mitigations

- Unify the *primitive*, not the four *semantics*; preserve each error contract. Charter resolver already `.resolve()`s — unify the contract, don't re-add. Parity tests gate the merge.

---

## Work Package WP02: Partition-correct the P0 auto-commit + Seam-A guard + #2549 (Priority: P1) 🎯 the P0

**Goal**: Stop `implement.py`'s verbatim `placement_ref` arm from committing a mixed batch to the coord
ref (route PRIMARY→`target_branch`, COORD-residue→coord; skip empty groups; idempotent re-drive); add
the partition guard to the `BookkeepingTransaction` seam so a mis-route fails loud; fix the residual
#2549 lane-status leak.
**Independent Test**: The non-vacuous SC-001 reproduction goes RED→GREEN; SC-002 scan finds zero
cross-partition artifacts across `implement` and `move-task --force`.
**Prompt**: `/tasks/WP02-partition-correct-commit.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004; NFR-001; C-004, C-006, C-008

### Included Subtasks

T007 RED-first: author the **non-vacuous** SC-001 P0 reproduction — real `_ensure_planning_artifacts_committed_git` → `allocate_lane_worktree` on a coord + PR-bound `--start-branch` mission; pre-assert `lanes.json` present on the coord ref AND in the `planning_commit_sha` tree; then assert the specific `PlanningCommitMergeConflictError`
T008 Partition the `placement_ref is not None` arm (`implement.py:890-902`) via `_partition_files_for_commit`; copy the legacy arm's `if primary_files:`/`if coord_files:` skip-empty caller guard (`:948/:961`) — no `transaction.py` change
T009 Idempotent re-drive (crash-recovery): switch `commit()`→`commit_idempotent()` across the **four** arms sharing `_run_planning_artifact_commit`; re-baseline their tests
T010 Rewrite the pinned tests in `tests/…/test_implement_placement_routing.py` (`test_effective_destination_ref_is_placement_ref_verbatim` + siblings) with a **list-capture + mixed-kind** fixture asserting both refs
T011 Add the Seam-A guard at `_run_planning_artifact_commit` — classify staged paths by kind, apply the `is_self_bookkeeping_churn` exemption **first** (`meta.json` co-travel), raise on PRIMARY→coord / COORD→lane; add the positive "coord commit + `meta.json` succeeds" test
T012 #2549: author the current-code reproduction naming the leaking mechanism (`_mt_commit_lane_deliverables` `safe_commit`-on-lane vs the `commit_for_mission`-backed port); route the leaking path through Seam A, or reduce to a regression pin if already routed
T013 SC-002 cross-partition scan test (real-git lifecycle; `meta.json` excluded)

### Dependencies

- Soft merge-ordering with WP01 (shared `implement.py`/`coherence.py` imports); no logical dependence.

### Risks & Mitigations

- SC-001 false-GREEN if `lanes.json` is not on both sides → the two pre-assertions (T007). Reverses the pinned C-004 verbatim contract → rewrite, don't delete (T010). `meta.json` false-refusal → exemption before classification (T011). #2549 reroute may be a no-op → reproduction is the entry gate (T012).

---

## Work Package WP03: Seam-B checkout-identity refusal for implement/review (Priority: P1) — #3128

**Goal**: Refuse a WP-execution write when the invoking checkout ≠ the mission's declared execution
workspace (`workspace_path`), gated on write-intent at the WP mutation chokepoint — without
false-refusing reads or planning.
**Independent Test**: SC-004 — from a foreign mission's lane, `implement`/`review` refuse; from the own
lane, planning-from-root, and pure reads, they proceed (local two-mission fixture; no saas dependency).
**Prompt**: `/tasks/WP03-checkout-identity-seam-b.md`
**Requirement Refs**: FR-005; NFR-004; C-001, C-007

### Included Subtasks

T014 Define a **distinct refusal exception NOT subclassing `ActionContextError`** (so `except ActionContextError: return None` cannot degrade it)
T015 Add the write-intent-gated refusal at the WP mutation chokepoint (`resolve_workspace_for_wp`): compare symlink-canonicalized `current_cwd` vs `workspace_path`; planning compares `primary_root`; reads exempt
T016 Produce the MF-3 write-intent marker table; thread the write-intent signal from the true `implement`/`review` WP-write sites only (not `resolve_action_context`, a read vehicle)
T017 Physically narrow the swallow sites (`implement_cores.py:635`, `mission_record_analysis.py:347` `suppress(Exception)`) so a refusal cannot be swallowed
T018 SC-004 local two-mission fixture (foreign-lane refuse; own-lane / planning-from-root / pure-read proceed)

### Dependencies

- Depends on WP01 (symlink canonicalization on both compared sides), WP02 (settles `implement.py` edits).

### Risks & Mitigations

- Over-mark → false-refuse reads (SC-004 breach); under-mark → #3128 stays live: the marker table (T016) bounds it. `resolve_ownership_claim` is a non-authoritative fast-path only (compare own `workspace_path`).

---

## Work Package WP04: Architectural gate + regression pins (Priority: P2) — polish/hardening

**Goal**: Make the P0 class hard to reintroduce; pin the crash-recovery invariant; pin the honest-red
baseline so regressions are attributable.
**Independent Test**: The static gate fails CI on an un-partitioned coord-topology commit batch; the
SC-002 scan owns the runtime `lanes.json`-on-coord property; the baseline-red manifest matches CI.
**Prompt**: `/tasks/WP04-arch-gate-and-pins.md`
**Requirement Refs**: FR-011; NFR-001, NFR-003; SC-006

### Included Subtasks

T019 Static call-shape arch gate: every **coord-topology** `_run_planning_artifact_commit` batch traces through `_partition_files_for_commit`; **route the flat/legacy arm (`implement.py:909`) through the split** so no whitelist is needed (OD-3)
T020 Pin the honest-red baseline manifest for `tests/architectural/`, `tests/integration/test_coord_*`, `tests/{,specify_cli/}lanes/*` in the mission dir (verified-green gates: `test_write_surface_placement_guard`, `test_read_surface_placement_guard`, `test_no_write_side_rederivation`)
T021 Crash-between-commits regression pin (R5): a kill between the PRIMARY and COORD commit re-drives idempotently with no stranded residue
T022 Requirements-coverage check + quickstart validation

### Dependencies

- Depends on WP02, WP03.

### Risks & Mitigations

- "no `lanes.json` on coord" is a **runtime** property, not statically detectable → assigned to the SC-002 scan, not this AST gate. The static gate must not condemn the legitimate flat arm (T019 routes it through).

---

## Dependency & Execution Summary

- **Sequence**: WP01 & WP02 (independent) → WP03 → WP04. Single_branch → sequential.
- **MVP Scope**: WP02 is the P0 (mission-critical); WP01 is its substrate for WP03; WP03 closes #3128;
  WP04 hardens.

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP02 |
| FR-003 | WP02 |
| FR-004 | WP02 |
| FR-005 | WP03 |
| FR-008 | WP01 |
| FR-009 | WP01 |
| FR-010 | WP01 |
| FR-011 | WP04 |
| NFR-001 | WP02, WP04 |
| NFR-003 | WP04 |
| NFR-004 | WP03 |
| C-004 | WP02 |
| C-006 | WP02 |
| C-007 | WP03 |
| C-008 | WP02 |

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | git_topology primitive | WP01 | P2 | No |
| T002 | migrate charter resolver | WP01 | P2 | Yes |
| T003 | migrate 3 probes | WP01 | P2 | Yes |
| T004 | read_dir_for consolidation | WP01 | P2 | No |
| T005 | unify nested classifier | WP01 | P2 | No |
| T006 | parity + one-copy gates | WP01 | P2 | No |
| T007 | non-vacuous SC-001 repro (RED) | WP02 | P1 | No |
| T008 | partition the placement_ref arm | WP02 | P1 | No |
| T009 | idempotent re-drive (4 arms) | WP02 | P1 | No |
| T010 | rewrite pinned verbatim tests | WP02 | P1 | No |
| T011 | Seam-A guard + meta.json exemption | WP02 | P1 | No |
| T012 | #2549 repro + route/pin | WP02 | P1 | No |
| T013 | SC-002 scan test | WP02 | P1 | No |
| T014 | distinct refusal exception | WP03 | P1 | No |
| T015 | refusal at WP chokepoint | WP03 | P1 | No |
| T016 | write-intent marker table + threading | WP03 | P1 | No |
| T017 | narrow swallow sites | WP03 | P1 | No |
| T018 | SC-004 two-mission fixture | WP03 | P1 | No |
| T019 | static call-shape gate | WP04 | P2 | No |
| T020 | baseline-red manifest | WP04 | P2 | Yes |
| T021 | crash-between-commits pin | WP04 | P2 | Yes |
| T022 | coverage + quickstart | WP04 | P2 | Yes |
